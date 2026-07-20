# Replication Package: The Effect of AI Writing on Governance: Evidence from a $3.5 Billion DAO

**Authors:** Victor Huang, Joseph Hall (Georgia Institute of Technology)

This package contains all code, cached data, and pre-generated output for the paper *The Effect of AI Writing on Governance: Evidence from a $3.5 Billion DAO* (Huang & Hall, 2026).

---

## Requirements

- Python 3.10+
- A LaTeX distribution (TeX Live, MiKTeX) for compiling the paper

Install all Python dependencies:

```bash
pip install duckdb pandas numpy matplotlib scipy statsmodels scikit-learn \
            requests pillow lxml python-pptx
```

**Note on Pangram API:** Scoring posts with the Pangram AI-detection API (`scripts/01_score.py`) requires a Pangram API key set in the environment:

```bash
export PANGRAM_API_KEY=your_key_here
```

The pre-scored results are already cached in `data/figure8_ai_scores.json`, so you do not need a key to reproduce the figures.

---

## Repository Structure

```
arbitrum-governance/
├── main_flat.tex              # Paper source
├── references.bib             # Bibliography
├── scripts/                   # All figure and data scripts
│   ├── 00_scrape.py           # Scrape Discourse forum
│   ├── 01_score.py            # Score posts with Pangram API
│   ├── 02_fetch_delegates.py  # Fetch Snapshot delegate data
│   ├── 03_fetch_missing.py    # Fill gaps in delegate data
│   ├── 04_rescrape_missing.py # Re-scrape any missing posts
│   ├── aer_style.py           # Shared AER-style plot config
│   ├── fig01_*.py – fig16_*.py  # Figure scripts (in order)
│   ├── rob01_*.py – rob03_*.py  # Robustness checks
│   └── tab_ols_structural_break.py
├── data/                      # Cached API responses (< 10 MB each)
├── output/
│   ├── figures/               # Pre-generated PNGs
│   └── tables/                # Pre-generated LaTeX tables
└── .gitignore
```

---

## Data

The `data/` folder contains all cached API responses needed to reproduce figures and tables. The raw SQLite database (`arbitrum.db`, ~230 MB) and three large cache files are excluded from the repo due to size limits, but are **available on request**:

| File | Size | Used by |
|------|------|---------|
| `data/arbitrum.db` | ~230 MB | fig01–04, fig07, fig11, fig15 |
| `data/figure8_forum_cache.json` | ~24 MB | fig08, fig15, rob03, tab_ols |
| `data/figure5_votes_cache.json` | ~31 MB | fig05, fig11, fig12, rob02 |
| `data/figure10_voter_cache.json` | ~31 MB | fig10 |

Contact: **vhuang5858@gmail.com**

To re-collect data from scratch, run the pipeline in order:

```bash
python scripts/00_scrape.py          # Scrape forum posts (Discourse API)
python scripts/01_score.py           # Score posts with Pangram (API key required)
python scripts/02_fetch_delegates.py # Fetch Snapshot delegate/wallet data
python scripts/03_fetch_missing.py   # Fill gaps
python scripts/04_rescrape_missing.py
```

---

## Reproducing Figures and Tables

All scripts are run from the **project root** (not from inside `scripts/`):

```bash
python scripts/fig01_forum_activity.py
python scripts/fig02_proposals.py
python scripts/fig03_power_concentration.py
python scripts/fig04_taxonomy.py
python scripts/fig05_bimodal.py
python scripts/fig06_lobbyfi.py
python scripts/fig07_fiscal.py
python scripts/fig08_main_causal.py   # ← also writes data/matched_proposals.csv
python scripts/fig09_amendments.py
python scripts/fig10_crossdao.py
python scripts/fig10b_participation.py
python scripts/fig11_delegates.py
python scripts/fig12_panel.py
python scripts/fig13_chow.py          # requires fig08 to have run first
python scripts/fig14_distraction.py   # requires fig08 to have run first
python scripts/fig15_reads_decline.py
python scripts/fig16_distraction_events.py  # requires fig08 to have run first
python scripts/fig_dao_treasuries.py
python scripts/fig_ai_post_content.py
python scripts/tab_ols_structural_break.py
python scripts/rob01_uniswap_placebo.py
python scripts/rob02_concentration_control.py
python scripts/rob03_cooks_bootstrap.py
```

**Dependency note:** `fig13_chow.py`, `fig14_distraction.py`, and `fig16_distraction_events.py` all require `data/matched_proposals.csv`, which is generated automatically when you run `fig08_main_causal.py`.

Output is written to `output/figures/` (PNG) and `output/tables/` (LaTeX `.tex`).

---

## Compiling the Paper

```bash
pdflatex main_flat.tex
bibtex main_flat
pdflatex main_flat.tex
pdflatex main_flat.tex
```

---

## Contact

Victor Huang — vhuang5858@gmail.com  
Joseph Hall — Georgia Institute of Technology
