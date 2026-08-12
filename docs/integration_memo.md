# Integration Memo — Derived Model Folded Into the Paper

*Prepared for the Aug 13 meeting. Working tree is uncommitted: `git diff` is the
review surface. Companion documents: `docs/model_rebuild.pdf` (full derivations),
`docs/model_rebuild_summary.md` (one-pager), `docs/check_model.py` (numerical
verification).*

## What changed, section by section

**Section 5 (rewritten in full).** Now presents the unified two-tier model:
- **5.1 Setup**: contributors (private signals, posting costs, *attention
  rewards*) + continuum of taste-heterogeneous voters (read-then-vote). The four
  assumptions are stated plainly, including the honest caveat that
  decision-theoretic voting *bypasses* voter-side pivotality (standard
  large-election device), and the DIP as the institutional microfoundation for
  attention rewards. A4 explicitly notes the career-concerns alternative is
  provably wrong-signed (proof in the appendix).
- **5.2 Equilibrium**: reading rule V(π) = (1−π)I_H − c_r now *derived* with
  I_H = 2p(1−p)(2q−1) pinned to primitives; posting volume n = F(RA) ∝ p(1−p);
  margins interior with closed forms, E[M|p] strictly increasing in consensus.
  Proposition 1 (Cov(posts, margin) < 0) is stated with a proof sketch and full
  proof in the appendix — it is now a theorem.
- **5.3 AI shock**: the λ (realized) vs. π (expected) architecture is unchanged;
  the dilution identity Q − ½ = (1−π)(q − ½) is now derived from the sampling
  protocol. The unverifiability threshold proposition restates honestly:
  individual reading decisions are discrete; aggregate readership declines
  continuously to exactly zero at interior π*(p).
- **5.4 Welfare**: the old kernel 4p(1−p)(q−½)² is **gone** (it is not derivable;
  a referee could discover this). Replaced by the exact object: forum value =
  min(p, 1−p) on an interior flip window that contamination narrows to nothing.
  Same qualitative message — AI destroys the most value on contested decisions —
  now exact. A footnote flags the replacement. Nothing quantitative changes: the
  words calibration never used the old kernel.
- **5.5 (new) Tipping theorem**: discontinuous, hysteretic collapse from a
  positive reading cost alone (no S-shaped adoption needed); collapse always at
  realized contamination strictly below the reading threshold. Matching the
  observed 8% still runs through the expectations channel, as before.
- **5.6 Calibration**: reframed as *illustrative under stated assumptions*
  (= agenda Decision 2). Derived and solid: the threshold identity, π* ≥ 0.082,
  the 19.4 words/post floor. Assumption-carrying (now formalized as the
  Non-Redundancy assumption, stated in-text): the ×44.2 step to 858
  words/delegate and the ×62 step to ~43,000/proposal. The delegate-alignment
  paragraph is retained (it is *more* coherent now — "the delegation market
  rewards observable activity" is precisely attention motive A4). New closing
  paragraph states the two honest model–data discrepancies (post-break margins
  rose → compositional story flagged, not claimed; residual posting → intrinsic
  motive footnote).

**New Model Appendix (first appendix section, ~14 pages).** Full derivations
ported from the theory note: primitives, reading tent, readership closed form,
posting equilibrium, the career-concerns negative theorem, interior-margin
closed forms, the margin-monotonicity theorem, the covariance theorem, exact
welfare, comparative statics in contamination, and the tipping theorem. All
meeting-facing commentary stripped; numerical verification referenced
(`check_model.py`).

**Abstract**: "model of endogenous posting and voting" → "derived from
primitives"; adds the below-threshold + hysteresis characterization of the
collapse; 858 now carries "(under a stated non-redundancy assumption)".

**Conclusion (DIP/Goodhart passage)**: collapse now "discrete, total, and
irreversible" — licensed by the tipping theorem's hysteresis.

**Preamble**: theorem/corollary/assumption/remark environments, math macros,
enumitem.

## Judgment calls for the authors to ratify

1. **Career-concerns theorem kept in the appendix** (as the justification for
   A4). Alternative: cut to a remark. I kept it — referees will ask "why not
   career concerns," and the theorem answers.
2. **Tipping theorem placed in the main text as Proposition 4 (compact) + full
   theorem in appendix** — the note's "compact inclusion" lean. Alternative:
   spin off. Reversible.
3. **Delegate-alignment paragraph retained nearly verbatim** in 5.6 — it reads
   even better under the attention motive.
4. **Prior-work paragraph** in 5.0 rewritten to add Feddersen–Pesendorfer and
   sincere-voting citations; Lohmann/Austen-Smith/Dewatripont kept.
5. Abstract edit is the lightest touch consistent with the theorem — check the
   voice.

## Explicitly untouched (pending Decisions 3–4)

USD/ARB conversion, the title, all descriptive statistics, all empirical
sections (regressions, figures, samples) except where prose referenced the old
theory. The fig-caption rewrite remains bundled with the USD/freeze pass.

## Build status

`tectonic main_flat.tex`: zero errors, zero undefined references, 113 pp.
