"""Central freeze + USD-conversion helpers for the descriptive figures.

Two jobs, one import:

  1. REPRODUCIBILITY FREEZE.  Several descriptive scripts pull live from Snapshot /
     price APIs every run, so their numbers drift.  Wrap the pull in
     `frozen_json(name, fetch_fn)`: the first run (or `--refresh` / FREEZE_REFRESH=1)
     hits the network and writes data/frozen/<name>.json; every later run reads the
     frozen copy, so figures reproduce exactly.

  2. USD CONVERSION (staged).  Single source of truth for the ARB->USD price.  Until
     Joseph picks the price, ARB_USD_PRICE is None and every wired figure renders in
     native ARB units.  Setting the three constants below flips the whole paper to
     USD in ONE edit — then re-run the batch.

Usage in a script:
    import freeze
    data  = freeze.frozen_json("fig07_fiscal", _fetch_fn)   # reproducible pull
    yval  = freeze.to_value(arb_millions)                   # ARB now, USD when set
    ax.set_ylabel(freeze.money_label("Disbursements"))      # auto ARB/USD label
"""

import os
import re
import json
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FROZEN_DIR = os.path.join(ROOT, "data", "frozen")
os.makedirs(FROZEN_DIR, exist_ok=True)

# Re-pull only when explicitly asked; default is to use the frozen cache.
REFRESH = os.environ.get("FREEZE_REFRESH", "0") == "1" or "--refresh" in sys.argv


def frozen_json(name, fetch_fn):
    """Return cached JSON for `name`; fetch + save on first run or when REFRESH set."""
    path = os.path.join(FROZEN_DIR, f"{name}.json")
    if os.path.exists(path) and not REFRESH:
        with open(path) as fh:
            return json.load(fh)
    data = fetch_fn()
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)
    print(f"  [freeze] wrote {name}.json ({len(data) if hasattr(data,'__len__') else '?'} records)",
          flush=True)
    return data


# ── USD conversion — DECIDED (Aug 2026): single TGE reference rate ────────────
# One fixed date for all ARB→USD conversions, for comparability. Chosen so the
# treasury reads $3.5B, consistent with the paper's stated "$13B market cap at
# launch" (10B ARB × $1.30). The price varied several-fold over the sample; the
# convention is descriptive only and no result depends on it (see the footnote at
# the token-distribution paragraph in main_flat.tex). Do NOT re-pick per figure.
ARB_USD_PRICE = 1.30
PRICE_DATE    = "2023-03-16"   # Token Generation Event
PRICE_NOTE    = "TGE reference rate; single fixed date for comparability"

USD_READY = ARB_USD_PRICE is not None


def require_price():
    if not USD_READY:
        raise RuntimeError(
            "ARB_USD_PRICE is unset — this output needs the USD decision. "
            "Set ARB_USD_PRICE/PRICE_DATE in scripts/freeze.py, or run the "
            "native-ARB version. (" + PRICE_NOTE + ")")


def to_value(arb):
    """ARB -> USD if the price is set; otherwise pass through unchanged (native ARB)."""
    return arb * ARB_USD_PRICE if USD_READY else arb


def unit(symbol=False):
    """Axis/label unit string that tracks whether the price is set."""
    if USD_READY:
        return "$" if symbol else "USD"
    return "ARB"


def money_label(base, scale="millions"):
    """e.g. 'Disbursements (ARB millions)' now → '(USD millions)' once priced."""
    scale = (" " + scale) if scale else ""
    return f"{base} ({unit()}{scale})"
