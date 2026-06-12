# Replication Package: AI and the Market for Governance Lemons

**Authors:** Victor Huang, Joseph Hall (Georgia Institute of Technology)

This repository contains the replication code and data for the paper *AI and the Market for Governance Lemons*.

---

## Requirements

```
Python 3.10+
duckdb
pandas
numpy
matplotlib
scikit-learn
requests
```

Install dependencies:
```bash
pip install duckdb pandas numpy matplotlib scikit-learn requests
```

LaTeX compilation requires a TeX distribution (e.g., TeX Live, MiKTeX) with the standard packages.

---

## Data

The `data/` folder contains cached API responses used to reproduce all figures and tables. The raw database (`arbitrum.db`) is available upon request due to size constraints.

Three large cache files excluded from this repo due to GitHub size limits are also available upon request:
- `figure8_forum_cache.json` — forum post data for matched proposals
- `figure5_votes_cache.json` — Snapshot vote-level data
- `figure10_voter_cache.json` — cross-DAO voter data

**To re-scrape from scratch**, run the scripts in order:
```
scripts/00_scrape.py       # Scrape forum posts from Discourse API
scripts/01_score.py        # Score posts with Pangram AI detection API
scripts/02_fetch_delegates.py
scripts/03_fetch_missing.py
```

---

## Reproducing Figures and Tables

Run each figure script from the project root:

```bash
python scripts/fig01_forum_activity.py
python scripts/fig08_main_causal.py
python scripts/fig11_delegates.py
python scripts/fig13_chow.py
python scripts/fig15_reads_decline.py
# ... etc.
```

Output is written to `output/figures/` and `output/tables/`.

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
