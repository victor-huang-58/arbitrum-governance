## Arbitrum DAO Governance — Replication Package
## One-click replication: make replicate
## Requires: Python 3.11+, PANGRAM_API_KEY in .env

PYTHON   := python3
SCRIPTS  := scripts
OUT_FIG  := output/figures
OUT_TAB  := output/tables
PAPER    := main_flat
DB       := data/arbitrum.db

.PHONY: replicate environment data figures tables paper clean help

# ── Master target ─────────────────────────────────────────────────────────────
replicate: environment data figures tables paper

# ── 0. Environment ────────────────────────────────────────────────────────────
environment:
	@echo "==> Installing Python dependencies..."
	$(PYTHON) -m pip install -q -r requirements.txt
	@echo "==> Checking API keys..."
	@test -f .env || (echo "ERROR: .env not found. Copy .env.example and fill in PANGRAM_API_KEY." && exit 1)
	@echo "==> Environment OK."

# ── 1. Data pipeline ─────────────────────────────────────────────────────────
# Scraping is slow (~2h for full forum). Skip if DB already populated.
data: $(DB)

$(DB):
	@echo "==> [1/3] Scraping Arbitrum forum..."
	$(PYTHON) $(SCRIPTS)/00_scrape.py
	@echo "==> [2/3] Scoring posts with Pangram AI detector..."
	$(PYTHON) $(SCRIPTS)/01_score.py
	@echo "==> [3/3] Fetching delegate wallet mappings..."
	$(PYTHON) $(SCRIPTS)/02_fetch_delegates.py

# Force re-scrape even if DB exists
rescrape:
	@echo "==> Re-scraping missing posts..."
	$(PYTHON) $(SCRIPTS)/03_fetch_missing.py
	$(PYTHON) $(SCRIPTS)/04_rescrape_missing.py

# ── 2. Figures ────────────────────────────────────────────────────────────────
# Main body figures (required for replication package)
MAIN_FIGS := \
	$(OUT_FIG)/fig01_forum_activity.png \
	$(OUT_FIG)/fig02_proposals.png \
	$(OUT_FIG)/fig03_power_concentration.png \
	$(OUT_FIG)/fig08_main_causal.png \
	$(OUT_FIG)/fig11_delegates.png

# Appendix figures
APPENDIX_FIGS := \
	$(OUT_FIG)/fig04_taxonomy.png \
	$(OUT_FIG)/fig05_ai_score_bimodality.png \
	$(OUT_FIG)/fig06_lobbyfi.png \
	$(OUT_FIG)/fig07_fiscal.png \
	$(OUT_FIG)/fig09_amendments.png \
	$(OUT_FIG)/fig10_crossdao.png \
	$(OUT_FIG)/fig10b_participation.png \
	$(OUT_FIG)/fig12_panel.png \
	$(OUT_FIG)/fig13_chow.png \
	$(OUT_FIG)/fig14_distraction.png \
	$(OUT_FIG)/fig15_reads_decline.png \
	$(OUT_FIG)/rob03_cooks_bootstrap.png

figures: main_figures appendix_figures

main_figures: $(DB) $(MAIN_FIGS)

appendix_figures: $(DB) $(APPENDIX_FIGS)

$(OUT_FIG)/fig01_forum_activity.png: $(SCRIPTS)/fig01_forum_activity.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig01_forum_activity.py

$(OUT_FIG)/fig02_proposals.png: $(SCRIPTS)/fig02_proposals.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig02_proposals.py

$(OUT_FIG)/fig03_power_concentration.png: $(SCRIPTS)/fig03_power_concentration.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig03_power_concentration.py

$(OUT_FIG)/fig04_taxonomy.png: $(SCRIPTS)/fig04_taxonomy.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig04_taxonomy.py

$(OUT_FIG)/fig05_ai_score_bimodality.png: $(SCRIPTS)/fig05_bimodal.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig05_bimodal.py

$(OUT_FIG)/fig06_lobbyfi.png: $(SCRIPTS)/fig06_lobbyfi.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig06_lobbyfi.py

$(OUT_FIG)/fig07_fiscal.png: $(SCRIPTS)/fig07_fiscal.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig07_fiscal.py

$(OUT_FIG)/fig08_main_causal.png: $(SCRIPTS)/fig08_main_causal.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig08_main_causal.py

$(OUT_FIG)/fig09_amendments.png: $(SCRIPTS)/fig09_amendments.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig09_amendments.py

$(OUT_FIG)/fig10_crossdao.png: $(SCRIPTS)/fig10_crossdao.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig10_crossdao.py

$(OUT_FIG)/fig10b_participation.png: $(SCRIPTS)/fig10b_participation.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig10b_participation.py

$(OUT_FIG)/fig11_delegates.png: $(SCRIPTS)/fig11_delegates.py $(DB) data/figure5_votes_cache.json
	$(PYTHON) $(SCRIPTS)/fig11_delegates.py

$(OUT_FIG)/fig12_panel.png: $(SCRIPTS)/fig12_panel.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig12_panel.py

$(OUT_FIG)/fig13_chow.png: $(SCRIPTS)/fig13_chow.py $(DB) $(OUT_FIG)/fig08_main_causal.png
	$(PYTHON) $(SCRIPTS)/fig13_chow.py

$(OUT_FIG)/fig14_distraction.png: $(SCRIPTS)/fig14_distraction.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig14_distraction.py

$(OUT_FIG)/fig15_reads_decline.png: $(SCRIPTS)/fig15_reads_decline.py $(DB)
	$(PYTHON) $(SCRIPTS)/fig15_reads_decline.py

$(OUT_FIG)/rob03_cooks_bootstrap.png: $(SCRIPTS)/rob03_cooks_bootstrap.py $(DB)
	$(PYTHON) $(SCRIPTS)/rob03_cooks_bootstrap.py

# ── 3. Tables ─────────────────────────────────────────────────────────────────
# Both tables below are \input directly by the paper.
tables: $(DB) $(OUT_TAB)/tab_ols_structural_break.tex $(OUT_TAB)/rob02_concentration_control.tex

$(OUT_TAB)/tab_ols_structural_break.tex: $(SCRIPTS)/tab_ols_structural_break.py $(DB)
	$(PYTHON) $(SCRIPTS)/tab_ols_structural_break.py

$(OUT_TAB)/rob02_concentration_control.tex: $(SCRIPTS)/rob02_concentration_control.py $(DB)
	$(PYTHON) $(SCRIPTS)/rob02_concentration_control.py

# ── 4. Paper ──────────────────────────────────────────────────────────────────
paper: $(PAPER).tex
	@echo "==> Compiling paper..."
	pdflatex -interaction=nonstopmode $(PAPER).tex > /dev/null 2>&1
	bibtex $(PAPER) > /dev/null 2>&1
	pdflatex -interaction=nonstopmode $(PAPER).tex > /dev/null 2>&1
	pdflatex -interaction=nonstopmode $(PAPER).tex > /dev/null 2>&1
	@echo "==> Paper compiled: $(PAPER).pdf"

# ── Utilities ─────────────────────────────────────────────────────────────────
clean:
	@echo "==> Cleaning generated outputs (preserving data/)..."
	rm -f $(OUT_FIG)/*.png $(OUT_FIG)/*.pdf
	rm -f $(OUT_TAB)/*.tex
	rm -f $(PAPER).pdf $(PAPER).aux $(PAPER).bbl \
	      $(PAPER).blg $(PAPER).log $(PAPER).out

help:
	@echo ""
	@echo "Arbitrum DAO Governance — Replication Package"
	@echo "============================================="
	@echo ""
	@echo "  make replicate      Full replication: data + figures + tables + paper"
	@echo "  make environment    Install dependencies (run first)"
	@echo "  make data           Scrape forum + score with Pangram (slow, ~2h)"
	@echo "  make figures        Generate all figures (uses cached data)"
	@echo "  make main_figures   Generate main body figures only"
	@echo "  make appendix_figures  Generate appendix figures only"
	@echo "  make tables         Generate all LaTeX tables"
	@echo "  make paper          Compile paper PDF"
	@echo "  make clean          Remove all generated outputs"
	@echo ""
	@echo "  Prerequisites:"
	@echo "    Python 3.11+, pip install -r requirements.txt"
	@echo "    .env with PANGRAM_API_KEY=<key>"
	@echo "    pdflatex (for 'make paper')"
	@echo ""
