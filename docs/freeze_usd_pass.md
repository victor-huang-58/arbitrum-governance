# Freeze + USD Pass — Runbook

*Victor, Aug 2026. Two jobs in one pass: (1) freeze the live-fetch descriptive
scripts so their numbers stop drifting; (2) convert ARB→USD once Joseph picks the
price. Built so the USD decision is a **one-line edit**. Infra lives in
`scripts/freeze.py`.*

## How the infrastructure works

`scripts/freeze.py` exposes:
- `frozen_json(name, fetch_fn)` — caches an API pull to `data/frozen/<name>.json`.
  First run (or `--refresh` / `FREEZE_REFRESH=1`) hits the network; every later run
  reads the frozen copy → exact reproduction.
- `to_value(arb)` — returns ARB now, `arb * ARB_USD_PRICE` once the price is set.
- `money_label(base)` / `unit()` — axis labels that auto-track ARB vs. USD.
- **The three constants to set on decision:** `ARB_USD_PRICE`, `PRICE_DATE`,
  `PRICE_NOTE`. That is the *only* edit needed to flip the whole paper to USD.

## The one-line USD flip (when Joseph decides)

1. In `scripts/freeze.py`, set e.g. `ARB_USD_PRICE = 1.30`, `PRICE_DATE = "2023-03-23"`.
2. Re-run the batch below. Every wired figure re-renders in USD with correct labels.
3. Update the text numbers (treasury, holdings, DIP) — see "Text touch points".

## Script status

**Freeze only (native units — do now, no price needed):**

| Script | Pulls live | Cache name | Status |
|---|---|---|---|
| `fig02_proposals.py` | Snapshot (all proposals) | `fig02_proposals` | ✅ **converted + frozen (415)** |
| `fig01_forum_activity.py` | Snapshot | `fig01_forum` | ⬜ template ready |
| `fig03_power_concentration.py` | Snapshot | `fig03_power` | ⬜ |
| `fig04_taxonomy.py` | Snapshot | `fig04_taxonomy` | ⬜ |
| `fig09_amendments.py` | Snapshot | `fig09_amend` | ⬜ |
| `fig10_crossdao.py` | Snapshot (multi-DAO) | `fig10_crossdao` | ⬜ |
| `fig10b_participation.py` | Snapshot | `fig10b_part` | ⬜ |
| `fig05_dip_test.py` | Snapshot | `fig05_dip` | ⬜ |
| `fig15_distraction_first.py` | Snapshot | `fig15_first` | ⬜ |
| `rob01_uniswap_placebo.py` | Snapshot (Uniswap) | `rob01_uniswap` | ⬜ |
| `rob02_concentration_control.py` | Snapshot | `rob02_conc` | ⬜ |
| `rob03_cooks_bootstrap.py` | Snapshot | `rob03_cooks` | ⬜ |
| `02_fetch_delegates.py` | Tally/Snapshot | `delegates_raw` | ⬜ (already has a cache; standardize) |

**Freeze + USD (wire `to_value` / `money_label` at the plot points):**

| Script | Native unit | USD touch point | Status |
|---|---|---|---|
| `fig07_fiscal.py` | ARB millions (ANCHORS, `GENESIS_M`) | disbursement + balance axes | ⬜ freeze + wire |
| `fig06_lobbyfi.py` | ARB voting power | `lobbyfi_vp` axis | ⬜ freeze + wire |
| `fig11_delegates.py` | ARB voting power | delegate VP axis | ⬜ freeze + wire |

**Already fine (skip):**
- `fig08_main_causal.py`, `fig12_panel.py`, `tab_ols_structural_break.py`, etc. —
  core-result scripts already read frozen caches (`figure8_*cache.json`).
- `fig_dao_treasuries.py` — already in USD (DeFiLlama snapshot).

## Text touch points (USD flip, in `main_flat.tex`)

Not scripts — hard-coded numbers to convert with the same price:
- Treasury: 2.75–2.77B ARB → `× price` (this sets the "$3.5B" title fate)
- Delegate holdings: 71K / 1.9M / 40K / 680K ARB
- DIP: 5,000 ARB/month
- Any per-proposal ARB participation figures in §2

## Conversion template (per freeze-only script)

```python
from aer_style import ...          # existing
import freeze                       # add

def _fetch():
    ...                             # move the existing live-pull loop here, `return` it
    return out

data = freeze.frozen_json("<cache_name>", _fetch)   # replace the inline loop
```

For USD scripts, additionally wrap plotted ARB amounts in `freeze.to_value(...)` and
set axes with `freeze.money_label("...")`.

## Run the batch

```bash
# freeze everything from cache (reproducible; no network):
for f in scripts/fig0*.py scripts/fig1*.py scripts/rob*.py; do python3 "$f"; done
# one-time (re)build of a cache after a data change:
python3 scripts/fig02_proposals.py --refresh
```

## Remaining work
- Convert the 12 freeze-only scripts (mechanical, ~10 min each — same template).
- Wire the 3 USD scripts.
- Then, on decision: set the price, re-run, update the text numbers, finalize the
  figure captions (see `meeting_agenda_2026-08-11.md`) in the same pass.
