# Model rebuild — one-page summary for Joseph

*Companion to `docs/model_rebuild.tex` / `.pdf` (full derivations, proofs, and the
meeting verdict). Every claim below is proved there and verified numerically
end-to-end; nothing is asserted-only anymore.*

## What holds (the good news)

**The model derives. All three referee objections are answerable.** One unified
two-tier structure — informed contributors post; a continuum of voters with
private tastes decides whether to *read* (one sampled post at cost c_r) and then
votes — delivers, from primitives:

- **Interior margins** (O1): exact closed forms; expected margin *strictly
  increasing* in consensus |p−1/2|, with exact floor |2p−1|/a. Proved for all
  parameter values (the key derivative is literally 4 + κ − κ_c > 0).
- **Posting volume** (O2): posters are paid in *audience* (positive mass even for
  a measure-zero poster — no pivotality needed); volume ∝ p(1−p) to first order,
  exact closed form available.
- **Paper's Proposition 1** (Cov(posts, margin) < 0): now a theorem.
- **Paper's reading rule** V(π) = (1−π)I_H − c_r and threshold π\* = 1 − c_r/I_H:
  derived *exactly*, with I_H pinned to primitives: I_H = 2p(1−p)(2q−1).
- **Tipping, strengthened**: with endogenous contamination, a positive reading
  cost *alone* makes collapse discontinuous, hysteretic (lowering AI afterward
  does not restore the forum), and located at a realized AI share *strictly
  below* the reading threshold. Victor's S-shaped-adoption condition is no
  longer needed — his sketch is now a clean theorem, and stronger.

## What changed (the corrections)

1. **The welfare formula 4p(1−p)(q−½)² is dead.** It is not derivable in any
   version of the model. The exact value of the forum is **min(p, 1−p) on an
   interior "flip window"** that AI narrows and eventually closes. Same
   qualitative message (AI destroys the most value on contested decisions),
   different — and now exact — formula. Must be swapped in the paper.
2. **Career concerns (the roadmap's posting motive) is provably wrong-signed.**
   For *any* increasing reputation payoff, posting-to-signal-ability concentrates
   on foregone conclusions, not contested calls (vindication payoffs are
   p-invariant; vindication *probability* rises with consensus). It would flip
   Prop 1. Replaced by the attention/value-of-information motive. Also: stop
   narrating the delegate posting↔VP correlation as career-concerns evidence.
3. **Honest assumptions stated.** Pivotality is *bypassed*, not solved: voters
   are decision-theoretic/expressive (standard in large-election models) and
   posters are paid per reader. Given those two behavioral primitives,
   everything else is derived. That is the right answer to the referee.
4. **Calibration**: the identity π\* = 1 − c_r/I_H, the bound π\* ≥ 0.082, and the
   19.4 words/post surplus all survive. **The ×44.2 step to 858 words/delegate
   (and 43,000/proposal) survives only under a stated non-redundancy assumption**
   (posts cover distinct aspects, so per-post value doesn't decay). With
   redundant posts, only the 19.4 floor is derivable. So: keep 858, but present
   it exactly as agenda Decision 2 recommends — illustrative under stated
   assumptions.

## Honest misses (say them in the paper)

- Post-break margins **rose** in the data; the model predicts compression toward
  the prior floor. Needs a composition story (fewer contested proposals reach
  votes post-shock) — outside the model.
- The model sends human posting to zero at collapse; data show ~8.9k words
  persist. Trivial patch (small intrinsic posting motive), not yet formalized.
- Deriving buys rigor, not extra empirical validation: the sharper structural
  tests remain underpowered at n = 29 (Victor's finding stands).

## Decision recommendation implied by the math

**Derive — the hybrid version.** "Reframe as illustrative" was the safe call only
while deriving looked risky; the derivation now exists and is checked. Concretely:

1. Replace §5.1–5.3 with the two-tier model (≈1–1.5 weeks, exposition only).
2. Replace the welfare formula (mandatory — a referee can discover it's
   underivable). Costless: the words calibration never used it.
3. Reframe the calibration as illustrative-under-stated-assumptions (= Decision 2),
   keeping 0.082 and 19.4 as the load-bearing numbers, NR stated when quoting 858.
4. Tipping theorem: include compactly as capstone *or* seed the follow-up paper —
   both defensible now that it's a theorem; my lean is a compact inclusion since
   it directly upgrades the abstract's headline mechanism.
5. Purge career-concerns language everywhere.

**Estimated remaining work:** Option "derive" ≈ 2–3 weeks total to a
referee-solid §5 (writing + welfare swap + calibration reframe; no open math on
the critical path). Option "illustrative" ≈ 2–3 days but leaves the strongest
referee line answered only rhetorically — no longer recommended given the above.
