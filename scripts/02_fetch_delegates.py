#!/usr/bin/env python3
"""
Build forum_username → wallet_address mapping for Arbitrum DAO delegates.

Phase 1: Mine delegate communication threads for 0x addresses and ENS names.
Phase 2: Resolve ENS names via Ethereum mainnet RPC (no API key needed).
Phase 3: Query Tally GraphQL for remaining delegates by display-name fuzzy match.
Phase 4: Store results in DuckDB as `delegate_wallet_map` table.
Phase 5: Join with Snapshot vote data and AI scores for preliminary analysis.

Run:
    python3 02_fetch_delegates.py
"""

import os, re, json, time, sys
import duckdb
import requests
from difflib import SequenceMatcher

HERE        = os.path.dirname(os.path.abspath(__file__))
ROOT        = os.path.dirname(HERE)   # project root
DB_PATH     = os.path.join(ROOT, "data", "arbitrum.db")
DEL_CACHE   = os.path.join(ROOT, "data", "figure8_delegate_cache.json")
VOTES_CACHE = os.path.join(ROOT, "data", "figure5_votes_cache.json")
TALLY_CACHE = os.path.join(ROOT, "data", "tally_delegates_cache.json")

ETH_RPC     = "https://ethereum.publicnode.com"
TALLY_URL   = "https://api.tally.xyz/query"
# Arbitrum DAO governor on Arbitrum One
ARB_GOV_ID  = "eip155:42161:0xf07DeD9dC292157749B6Fd268E37DF6EA38395B9"

ETH_RE      = re.compile(r'0x[0-9a-fA-F]{40}')
ENS_RE      = re.compile(r'[\w.-]+\.eth\b', re.I)

HEADERS = {"User-Agent": "Mozilla/5.0 (arbitrum-research-bot)"}


# ── helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def name_sim(a, b):
    a = a.lower().replace("_", "").replace("-", "").replace(".", "").replace(" ", "")
    b = b.lower().replace("_", "").replace("-", "").replace(".", "").replace(" ", "")
    return SequenceMatcher(None, a, b).ratio()

def checksum(addr):
    """Return lowercase hex; skip non-addresses."""
    addr = addr.strip()
    return addr.lower() if len(addr) == 42 and addr.startswith("0x") else None


# ── Phase 1: mine threads ─────────────────────────────────────────────────────

def mine_threads(delegate_cache):
    """Return {username: {wallets: [...], ens: [...]}} from first posts."""
    results = {}
    for tid, topic in delegate_cache.items():
        first = next((p for p in topic.get("posts", []) if p.get("post_number") == 1), None)
        if not first:
            continue
        uname = first.get("username", "")
        text  = first.get("text", "")
        wallets  = list(set(w.lower() for w in ETH_RE.findall(text)
                            if len(w) == 42))
        ens_list = list(set(ENS_RE.findall(text.lower())))
        results[uname] = {"wallets": wallets, "ens": ens_list}
    return results


# ── Phase 2: resolve ENS via eth_call ─────────────────────────────────────────

_w3 = None

def _get_w3():
    global _w3
    if _w3 is None:
        from web3 import Web3
        _w3 = Web3(Web3.HTTPProvider(ETH_RPC))
    return _w3

def resolve_ens(name: str) -> str | None:
    """Resolve an ENS name to a lowercase address via web3.py."""
    try:
        w3 = _get_w3()
        addr = w3.ens.address(name.lower().strip())
        return addr.lower() if addr else None
    except Exception:
        return None


# ── Phase 3: Tally GraphQL ────────────────────────────────────────────────────

TALLY_QUERY = """
query Delegates($governorId: AccountID!, $cursor: Cursor) {
  delegates(
    input: {
      filters: { governorId: $governorId }
      pagination: { limit: 50, afterCursor: $cursor }
      sort: { field: DELEGATED_VOTES, order: DESC }
    }
  ) {
    nodes {
      ... on Delegate {
        account {
          address
          name
          bio
          twitter
          ens
        }
        delegatorsCount
        votesCount
      }
    }
    pageInfo {
      lastCursor
    }
  }
}
"""

def fetch_tally_delegates(cache_path):
    if os.path.exists(cache_path):
        print("  Using cached Tally data")
        with open(cache_path) as f:
            return json.load(f)

    delegates = []
    cursor = None
    page = 0
    while True:
        variables = {"governorId": ARB_GOV_ID}
        if cursor:
            variables["cursor"] = cursor
        try:
            r = requests.post(
                TALLY_URL,
                json={"query": TALLY_QUERY, "variables": variables},
                headers=HEADERS,
                timeout=20
            )
            data = r.json()
            if "errors" in data:
                print(f"  Tally API error: {data['errors']}")
                break
            nodes = data.get("data", {}).get("delegates", {}).get("nodes", [])
            page_info = data.get("data", {}).get("delegates", {}).get("pageInfo", {})
            delegates.extend(nodes)
            cursor = page_info.get("lastCursor")
            page += 1
            print(f"  Fetched page {page}: {len(nodes)} delegates (total {len(delegates)})")
            if not nodes or not cursor:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"  Tally fetch error: {e}")
            break

    save_json(cache_path, delegates)
    return delegates


def match_tally(forum_username: str, tally_delegates: list) -> str | None:
    """Find the best matching Tally delegate and return their address."""
    best_score = 0.60   # minimum similarity threshold
    best_addr  = None
    for d in tally_delegates:
        acct = d.get("account", {})
        candidates = [
            acct.get("name") or "",
            acct.get("ens")  or "",
            acct.get("twitter") or "",
        ]
        for c in candidates:
            if not c:
                continue
            s = name_sim(forum_username, c)
            if s > best_score:
                best_score = s
                best_addr  = acct.get("address", "").lower()
    return best_addr


# ── Phase 4: store in DuckDB ──────────────────────────────────────────────────

def store_mapping(con, mapping: dict):
    con.execute("""
        CREATE TABLE IF NOT EXISTS delegate_wallet_map (
            forum_username VARCHAR PRIMARY KEY,
            wallet_address VARCHAR,
            source         VARCHAR,
            ens_name       VARCHAR
        )
    """)
    # Wrap delete + re-insert in a single transaction so a crash mid-loop
    # cannot leave the table empty (previously: autocommitted DELETE, then
    # one INSERT per row with no rollback on failure).
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DELETE FROM delegate_wallet_map")
        for username, info in mapping.items():
            con.execute(
                "INSERT INTO delegate_wallet_map VALUES (?, ?, ?, ?)",
                (username, info["wallet"], info["source"], info.get("ens"))
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    print(f"  Stored {len(mapping)} delegate→wallet mappings")


# ── Phase 5: voting power analysis ───────────────────────────────────────────

def analyze(con):
    # Load votes cache: proposal_id → [{voter, vp}]
    with open(VOTES_CACHE) as f:
        votes_raw = json.load(f)

    # Flatten: (proposal_id, voter_wallet, vp)
    records = []
    for prop_id, voter_list in votes_raw.items():
        for v in voter_list:
            records.append((prop_id, v["voter"].lower(), v["vp"]))

    print(f"\n  Snapshot votes cache: {len(votes_raw)} proposals, "
          f"{len(records)} voter-proposal pairs")

    # Get delegate wallet map
    mapped = con.execute(
        "SELECT forum_username, wallet_address FROM delegate_wallet_map "
        "WHERE wallet_address IS NOT NULL"
    ).fetchall()
    wallet_to_username = {w.lower(): u for u, w in mapped}
    print(f"  Matched delegates with wallets: {len(wallet_to_username)}")

    # For each voter in Snapshot, check if they're a known delegate
    delegate_vp = {}  # username → {proposal_id → vp}
    for prop_id, voter, vp in records:
        uname = wallet_to_username.get(voter)
        if uname:
            delegate_vp.setdefault(uname, {})[prop_id] = vp

    print(f"  Delegates found in Snapshot votes: {len(delegate_vp)}")

    # Get AI scores per delegate
    ai_scores = con.execute("""
        SELECT p.username, AVG(s.fraction_ai) as avg_ai,
               COUNT(*) as n_posts,
               MIN(p.created_at) as first_post
        FROM posts p
        JOIN post_ai_scores s ON p.id = s.post_id
        WHERE s.fraction_ai IS NOT NULL
        GROUP BY p.username
    """).fetchall()
    ai_map = {r[0]: {"avg_ai": r[1], "n_posts": r[2], "first_post": r[3]}
              for r in ai_scores}

    # Summary table
    print("\n{'Username':<25} {'avg_ai':>7} {'posts':>6} {'proposals_voted':>16} {'avg_vp':>14} {'first_post':>12}")
    print("-" * 90)
    rows = []
    for uname, vpdata in sorted(delegate_vp.items(), key=lambda x: -len(x[1])):
        ai = ai_map.get(uname, {})
        avg_vp = sum(vpdata.values()) / len(vpdata)
        rows.append({
            "username": uname,
            "avg_ai": ai.get("avg_ai", float("nan")),
            "n_posts": ai.get("n_posts", 0),
            "proposals_voted": len(vpdata),
            "avg_vp": avg_vp,
            "first_post": (ai.get("first_post") or "")[:10],
        })
        print(f"{uname:<25} {ai.get('avg_ai', float('nan')):>7.3f} "
              f"{ai.get('n_posts', 0):>6d} {len(vpdata):>16d} "
              f"{avg_vp:>14,.0f} {(ai.get('first_post') or '')[:10]:>12}")

    return rows


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading delegate cache...")
    delegate_cache = load_json(DEL_CACHE)
    print(f"  {len(delegate_cache)} delegate threads loaded")

    # Phase 1: mine threads
    print("\nPhase 1: Mining threads for wallets and ENS names...")
    mined = mine_threads(delegate_cache)
    mapping = {}   # username → {wallet, source, ens}

    for uname, info in mined.items():
        if info["wallets"]:
            addr = checksum(info["wallets"][0])
            if addr:
                mapping[uname] = {
                    "wallet": addr,
                    "source": "thread_mining",
                    "ens":    info["ens"][0] if info["ens"] else None
                }
        elif info["ens"]:
            # defer to Phase 2
            mapping[uname] = {
                "wallet": None,
                "source": "ens_pending",
                "ens":    info["ens"][0]
            }

    unresolved = [u for u in mined if u not in mapping]
    print(f"  {sum(1 for v in mapping.values() if v['wallet'])} with direct wallet")
    print(f"  {sum(1 for v in mapping.values() if not v['wallet'])} with ENS only")
    print(f"  {len(unresolved)} with nothing")

    # Phase 2: resolve ENS
    print("\nPhase 2: Resolving ENS names...")
    ens_resolved = 0

    # Also try username itself as ENS if it ends in .eth
    for uname in list(mined.keys()):
        if uname not in mapping and uname.lower().endswith(".eth"):
            mapping[uname] = {"wallet": None, "source": "ens_pending", "ens": uname.lower()}

    for uname, info in list(mapping.items()):
        if info["wallet"] is None and info.get("ens"):
            ens_name = info["ens"]
            print(f"  Resolving {ens_name} for {uname}...", end=" ", flush=True)
            addr = resolve_ens(ens_name)
            if addr:
                mapping[uname]["wallet"] = addr
                mapping[uname]["source"] = "ens_resolved"
                ens_resolved += 1
                print(f"→ {addr}")
            else:
                print("→ not found")
            time.sleep(0.1)
    print(f"  Resolved {ens_resolved} ENS names")

    # Phase 3: Tally for remaining
    need_tally = set(mined.keys()) - set(mapping.keys())
    # Also try Tally for ENS-only that still have no wallet
    need_tally |= {u for u, v in mapping.items() if v["wallet"] is None}
    print(f"\nPhase 3: Querying Tally for {len(need_tally)} remaining delegates...")
    tally_data = fetch_tally_delegates(TALLY_CACHE)
    print(f"  {len(tally_data)} delegates fetched from Tally")

    tally_matched = 0
    for uname in need_tally:
        addr = match_tally(uname, tally_data)
        if addr:
            mapping[uname] = {
                "wallet": addr,
                "source": "tally",
                "ens": None
            }
            tally_matched += 1
            print(f"  Tally match: {uname} → {addr}")
    print(f"  Matched {tally_matched} via Tally")

    # Phase 4: store
    print("\nPhase 4: Storing in DuckDB...")
    con = duckdb.connect(DB_PATH)
    store_mapping(con, mapping)

    total_with_wallet = sum(1 for v in mapping.values() if v["wallet"])
    print(f"\nFinal: {total_with_wallet} / {len(mapping)} delegates have wallet addresses")

    # Phase 5: analysis
    print("\nPhase 5: Voting power analysis...")
    analyze(con)
    con.close()


if __name__ == "__main__":
    main()
