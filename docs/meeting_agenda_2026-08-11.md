# Meeting Agenda — Post-Refine-Review Decisions & Next Steps

*Prepared by Victor, August 2026. For discussion with Joseph.*

## Context

We ran the current draft through **Refine** (automated referee tool), which returned **95 comments**. I've worked through everything that is *objectively fixable without a decision* (fabricated/miscited references, a sign error, sample-count inconsistencies, unsupported claims, a data reconciliation). What remains are **judgment calls that need us** — the model, the welfare framing, unit conventions, and a reproducibility pass. This agenda lists those decisions in priority order, with a recommendation on each, plus a status scorecard.

**Headline:** the empirical core is sound and reproducible (the main regression, Chow battery, delegate tables, and readership figure all compute from *frozen* caches). The problems are concentrated in (a) overclaiming — in the model, welfare, and prose — and (b) descriptive numbers/figures that drift because several scripts fetch live data. Both are fixable; several need a decision first.

---

## Decisions needed (priority order)

### 1. Model — derive properly, or reframe as illustrative? *(the core call)*
Refine (#1–3) says the model as written does **not derive** Proposition 1, the interior vote margins, or the welfare formula from its primitives (a single representative delegate can't produce interior margins; with a nonatomic continuum no contributor is pivotal, so costly posting isn't an equilibrium).

- **Recommendation:** *reframe as a stylized/illustrative framework* — state the key relationships as assumptions, downgrade "Proposition 1" to a stated prediction, and keep the model as scaffolding for the two mechanisms and the calibration. Deriving it properly is effectively a separate theory paper, and adding formal machinery is where new errors come from. **The sign error (#77) is already fixed** regardless.
- **Alternative:** derive it fully (higher reward, much more work/risk).
- **What deriving it fully would take** (researched Aug 2026): the three gaps share one root — a single representative delegate can't produce a *population* margin or *aggregate* posting volume. The fix is a three-part rebuild: (i) **two-tier structure** — informed contributors/delegates post; a continuum of uninformed voters read the forum aggregate and vote, so the For-share Φ and the margin become *derived* (Feddersen–Pesendorfer aggregation, already cited); (ii) **reputation / career-concern posting** — delegates post to attract and retain delegated voting power, which resolves the pivotality problem, matches our own delegate cross-section, and ties to DIP; from this Prop 1 follows (posts ∝ p(1−p), margin ∝ |2p−1| ⟹ negative covariance); (iii) the welfare loss as the **decision-theoretic value of information** (closeness × informativeness), though the exact 4p(1−p)(q−½)² form may need adjusting. Realistically ~2–4 weeks of careful theory work, with the risk the welfare form shifts — which is why the recommendation is to reframe as illustrative.

### 2. Welfare / calibration — "empirical lower bound" or "sensitivity calculation"?
The ≥858-words-per-delegate / ~43,000-words-per-proposal figures rest on assumptions (π ≥ λ, and the normalization I_H = c_p), not identification (#12, #18, #74).

- **Recommendation:** present as an **illustrative calibration under stated assumptions**, not an identified bound. Keeps the compelling magnitude, drops the overclaim. (Follows from Decision 1.)

### 3. USD conversion — pick the price/date *(also settles the title)*
Decided (Joseph, July 30): **dollar units throughout, not ARB.** Remaining call: **which conversion price**. This is entangled with the title:
- At ≈$1/ARB (the deck's convention): treasury 2.77B ARB ≈ **$2.8B** → the "$3.5 Billion DAO" title would change.
- At ~$1.30/ARB (launch, Mar 2023): ≈ **$3.6B** → title holds, but delegate holdings/DIP (contemporaneous) get ×1.3.
- At mid-2024 (~$0.85): ≈ **$2.3B**, and Uniswap (~$2.8–3.2B) was likely larger → the "largest treasury" claim fails.
- **Only the 27× voting-power ratio is price-invariant.**
- **Recommendation:** pick one stated convention and apply it everywhere; decide consciously whether the title survives it. Conversion touches: delegate holdings (71K/1.9M/40K/680K ARB), DIP (5,000 ARB/mo), treasury (2.75–2.77B ARB), and figures **fig07 (fiscal), fig11 (delegate VP), fig06 (LobbyFi)** need USD axes.

### 4. Reproducibility pass — run now, or note as a limitation?
Several descriptive scripts (`fig01/02/03/04/06/07/09`) fetch Snapshot/price **live and don't cache**, so their numbers drift (this is why "19 contested," "0.65 margin," and the §2 taxonomy/LobbyFi/fiscal numbers don't reproduce). The core-result scripts are frozen and fine.
- **Recommendation:** **do the freeze-and-recompute now** — add caching, run once, hard-code the results. "Our descriptive stats may not reproduce" isn't viable for a journal, and it's especially bad for a paper about verification. Best done **as one combined pass with the USD conversion** (same scripts), once Decision 3 sets the price. Will change §2 numbers — Joseph reviews the new values.

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
| Model derive-vs-illustrative (Decision 1) | ⏳ Joseph |
| Welfare framing (Decision 2) | ⏳ Joseph |
| USD conversion + title (Decision 3) | ⏳ price pending |
| Reproducibility freeze + recompute (Decision 4) | ⏳ blocked on Decision 3 |
| Convention picks (Decision 5) | ⏳ quick, need calls |
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

- **Decisions 1–2 (model/welfare):** I reframe §5 and the calibration language in one pass.
- **Decision 3 (USD price):** unblocks the combined **USD + reproducibility** pass (Decision 4) — regenerate fig06/07/11 in USD, freeze the drift scripts, recompute and hard-code §2.
- **Decision 5:** each is a one-line/one-number apply.

Everything that did **not** need a decision is already committed and pushed (`victor-huang-58/arbitrum-governance`, `main`). The paper compiles clean with zero undefined references.

## Suggested order for the meeting
1. Model (1) and welfare (2) — the intellectual calls that shape everything else.
2. USD price (3) + title.
3. How far to walk back the abstract's thesis (the one A3 item left to Joseph's tone).
4. Convention picks (5) as a quick round.
