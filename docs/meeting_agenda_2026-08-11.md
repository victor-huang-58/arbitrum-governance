# Meeting Agenda — Post-Refine-Review Decisions & Next Steps

*Prepared by Victor, August 2026. For discussion with Joseph.*

## Context

We ran the current draft through **Refine** (automated referee tool), which returned **95 comments**. I've worked through everything that is *objectively fixable without a decision* (fabricated/miscited references, a sign error, sample-count inconsistencies, unsupported claims, a data reconciliation). What remains are **judgment calls that need us** — the model, the welfare framing, unit conventions, and a reproducibility pass. This agenda lists those decisions in priority order, with a recommendation on each, plus a status scorecard.

**Headline:** the empirical core is sound and reproducible (the main regression, Chow battery, delegate tables, and readership figure all compute from *frozen* caches). The problems are concentrated in (a) overclaiming — in the model, welfare, and prose — and (b) descriptive numbers/figures that drift because several scripts fetch live data. Both are fixable; several need a decision first.

> **Update (Aug 12 — PR #3 "derived-model-integration", merged).** Joseph derived the
> model in full and integrated it end-to-end, which **resolves Decisions 1 and 2**. §5
> rewritten, ~14pp Model Appendix added, the non-derivable welfare kernel replaced with
> the exact object, calibration reframed as illustrative-under-stated-assumptions.
> Numerically verified (`docs/check_model.py` — all 7 checks pass). What remains for the
> meeting: **ratify Joseph's 5 judgment calls** (§below) and **Decisions 3–5** (USD
> price/title, freeze/USD pass, convention picks), which the PR deliberately left
> untouched. The freeze pass is now **partly done** (Decision 4).

---

## Decisions needed (priority order)

### 1. Model — ✅ RESOLVED: derived & integrated (PR #3)
Joseph took the **derivation** path (the two-tier model from the theory notes) and folded it into the paper. Proposition 1, the interior margins, the reading rule (`π* = 1 − c_r/I_H`, with `I_H = 2p(1−p)(2q−1)` pinned to primitives), and the welfare object are now **derived from primitives**; the career-concerns alternative is included as a *negative* theorem (provably wrong-signed). This answers Refine #1–3 directly, and it came with two genuine upgrades over the roadmap: a **stronger tipping theorem** (discontinuous, hysteretic collapse from a positive reading cost *alone* — no S-shaped adoption needed) and the **exact welfare form**. **No decision left here — only the ratifications below.** (Sign error #77 already fixed.)

### 2. Welfare / calibration — ✅ RESOLVED: illustrative under stated assumptions (PR #3)
Done as recommended. The non-derivable kernel `4p(1−p)(q−½)²` is **replaced** by the exact forum-value object `V(p) = min(p,1−p)` on a contested "flip window" (a footnote flags the swap; nothing quantitative changes — the words calibration never used it). The ≥858-words figure is retained but now explicitly carries a stated **non-redundancy assumption**; the load-bearing derived numbers (`π* ≥ 0.082`, 19.4 words/post) survive unconditionally.

### ★ Joseph's 5 judgment calls (from PR #3) — ✅ RATIFIED (Aug 13)
Positions agreed; branch `ratify-pr3-calls` (PR open) carries the only code change.
1. **Career-concerns theorem** kept in the appendix. ✅ **Keep** — pre-empts the obvious "why not career concerns" referee objection. No change.
2. **Tipping theorem** — compact in main text + full in appendix. ✅ **Keep compact, framed as a *mechanism*, not the explanation of the 8%.** §5.5 is already honest ("matching the observed collapse at 8% still requires the expectations channel"); no edit needed there. Not spun off — the full development can still seed a follow-up later.
3. **Delegate-alignment paragraph** retained in §5.6. ✅ **Keep** — but this is where the **M2** reading-incentive gap lives (see below); strengthen it there.
4. **Prior-work paragraph** (Feddersen–Pesendorfer + sincere-voting cites). ✅ **Approve.**
5. **Abstract** voice. ✅ **Approve with one edit** — credited the **expectations (π vs λ) channel** so "derived from primitives" isn't misread as deriving the 8% collapse. In `ratify-pr3-calls` (+ a typo fix).

**Still for the meeting (not ratifications — substantive):**
- **M1** — the expectations jump driving the empirical 8% is asserted, not modeled (tipping benchmark collapses at ~40–70%). Now flagged honestly in the abstract; whether to model it is open.
- **M2** — reading-incentive tension: non-pivotal, activity-rewarded delegates aren't microfounded to *read*. Natural fix: reading as an input to attention-rewarded posting. Belongs in the §5.6 paragraph (call 3).
- **M3** — `π` notation: appendix `π = z/(z+n)` is realized (= text `λ`); §5.3 `π` is the expectation. Relabel the expectation `π^e`.
- **Checked & cleared:** the earlier date worry (M4) — the paper deliberately uses the QLR break (Nov 2023, ~8%) and Claude 3 (Mar 2024, ~6%); consistent throughout.

### 3. USD conversion — ✅ RESOLVED: single TGE rate, $3.5B holds
Decided (Aug 2026): **one fixed conversion date for everything — the March 2023 TGE at $1.30/ARB** — chosen so the treasury reads **$3.5B**, consistent with the paper's existing "traded at $1.30 at launch, $13B market cap" statement. Title survives. A **caveat footnote** (added at the token-distribution paragraph) states the price varied several-fold over the sample, that dollar values differ at other dates/today, and that the convention is **descriptive only** — every ratio (the 27× voting-power gap) and every regression is ARB/USD-invariant. `ARB_USD_PRICE = 1.30` is set in `scripts/freeze.py`, so the combined pass converts at one rate. *Treated as a red herring — settled, not re-litigated per figure.*
- **Remaining (mechanical, part of the freeze pass):** wire `freeze.to_value`/`money_label` into **fig06/07/11** so their axes render USD at the fixed rate (the price is set; the plot-point wiring is the last step).

### 4. Reproducibility pass — freeze **partly done**; two blockers surfaced
The Group-A drift scripts (`fig02/03/04/06/07/09`) are now converted to a frozen cache (`scripts/freeze.py` + `data/frozen/`) and **verified reproducible** (2nd run reads cache, no re-fetch). Group-B scripts already cache-if-missing. Runbook: `docs/freeze_usd_pass.md`. **Still open — two blockers + the USD swap:**
- **`fig01` is blocked** — its ARB price source is dead (CryptoCompare 401s; CoinGecko's public tier refuses full history). Needs a price key/source, or redraw on a single date — the *same* question as Decision 3.
- **The repo is not self-reproducing for the CORE figures** — `figure8_forum_cache` (24M, feeds the headline `fig08`) and `figure5_votes_cache` (31M) are `.gitignore`d, and `figure10_voter_cache` is missing. **Decision:** commit them (+~55M), move to **Git LFS**, or ship a **release/Zenodo artifact** + regeneration script. For a paper about verifiability this can't stay a gap.
- **USD unit-swap** (`fig06/07/11`) is staged behind one constant in `freeze.py`, pending Decision 3.
- **Recommendation:** finish as **one combined pass with the USD price** — set the constant, run the batch, recompute/hard-code §2, finalize captions. Joseph reviews the new §2 numbers.

### 5. Convention picks (quick, once chosen)
- **λ measure** — the §5.5 recompute uses the monthly 8.2% at the QLR break; confirm vs. matched-thread or cumulative.
- **Chow test: slope-only or joint?** (#5/#91) — determines the Andrews critical value (8.85 is the k=1 value) and whether we report a one-restriction slope test.
- **Stale-stat universe** — recompute the descriptive stats on 306 (binary) vs 102 (matched), and which participation measure.
- **DIP intro billing** — elevate the Goodhart/DIP point to the introduction's contribution list, or keep it in the conclusion?

---

## Status scorecard

| Item | Status |
|---|---|
| Citations — **~25% of refs had errors** (1 fabricated, 5 wrong-paper incl. `kim2024`/`eisfeldt2023`, ~6 miscited claims) | ✅ fixed & web-verified; `nabben2021` venue + `andrews1993` CV still noted |
| Sample-count reconciliation (102/29/73; delegate funnel 62→54→52→51) | ✅ fixed |
| Sign error #77 (reading condition) | ✅ fixed |
| Overclaims (A3) — high-value ones | ✅ softened |
| λ correction + calibration recompute (8.2%) | ✅ done |
| Model — derived & integrated (Decision 1) | ✅ **PR #3**; ratify placement only |
| Welfare — exact form + illustrative calibration (Decision 2) | ✅ **PR #3** |
| Model integration — verify | ✅ `check_model.py` all 7 checks pass |
| USD conversion + title (Decision 3) | ✅ TGE $1.30/ARB fixed + caveat footnote; fig06/07/11 USD-wiring pending |
| Reproducibility freeze (Decision 4) | 🟡 Group-A frozen; **`fig01` price + cache-hosting policy** open |
| Convention picks (Decision 5) | ⏳ quick, need calls |
| Joseph's 5 judgment calls (PR #3) | ⏳ ratify — esp. tipping placement |
| Figure captions | 🔴 **systematic mismatch confirmed** — captions describe older figures than the PNGs show (7 figures, main body + appendix); needs a rewrite (see below). *Correction: this is NOT a PDF-parse artifact, as first assumed.* |

---

## Figure-caption rewrite needed (pass-3 audit finding)

Opening every flagged figure confirmed the captions describe **different/older figures than the PNGs actually plot** — the figures were regenerated but captions never updated:

| Fig | Caption claims | PNG shows |
|---|---|---|
| Fig 3 (fig02) | 4 categories, one panel | 3 categories + a 2nd margin panel |
| A3 (fig06) | distribution by proposal/vote-size | LobbyFi VP **time series** |
| A5 (fig09) | scatter (posts × duration) | **timeline/Gantt** of proposals |
| A6 (fig10) | 3 dims; incl. Optimism/Uniswap | **4-panel** bars; Aave/ENS/Lido/Compound |
| A7 (fig10b) | Arbitrum bar+line | **5-DAO scatter** of median voters |
| A8 (fig12) | 2-panel coeff plots by quarter | single **rolling-correlation** series |
| A4 (fig07) | USD | ARB (already fixed) |

Also: fig12 shows **N=5,354 / 52 delegates** vs Table 5's **1,832 / 54** (reconcile); and figures use a **3-category** taxonomy (Treasury Spend / Rules Change / Institution Building) while the text uses **4** (Treasury Allocation / Protocol Governance / Ecosystem Programs / Procedural) — pick one.

Draft corrected captions exist (matched to the current PNGs). **Do the caption rewrite *with* the freeze/USD figure regeneration** (Decisions 3–4) — the figures change again there, so finalize captions in that same pass.

## What unblocks once we decide

- **Decisions 1–2 (model/welfare):** ✅ done in PR #3 — only ratification remains.
- **Decision 3 (USD price):** unblocks the combined **USD + freeze** pass (Decision 4) — set one constant in `scripts/freeze.py`, run the batch, recompute/hard-code §2, finalize captions.
- **Decision 4 blockers:** `fig01` needs a price source; the core caches need a hosting call (commit / LFS / artifact).
- **Decision 5:** each is a one-line/one-number apply.

Everything that did **not** need a decision is committed and pushed (`victor-huang-58/arbitrum-governance`, `main`, now including PR #3). The paper compiles clean (113 pp, zero undefined references).

## Suggested order for the meeting
1. **Ratify the model integration (PR #3)** — the 5 judgment calls, especially **tipping placement** (main-text capstone vs. second paper).
2. **USD price (3) + title** — unblocks the combined USD + freeze pass.
3. **Decision 4 blockers:** the `fig01` price source, and the cache-hosting policy (commit / LFS / artifact).
4. **Convention picks (5)** as a quick round.
