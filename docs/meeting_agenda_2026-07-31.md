# Arbitrum paper — outstanding items (meeting July 31, 2026)

*Status first: all 12 items from the July 21 notes are implemented in
`407f09d`…`b727f79` — verified against the diff, terminology greps, and a full
tectonic compile (clean, no undefined references). Several implementations are
better than what the notes asked for, and you caught two factual errors in the
notes themselves (the deck's 41% Turing figure and my "GPT-4o 77%"). This
document is only what remains, grouped by workflow. Full detail and rationale
for every item: `slide_feedback_2026-07-21.md` (same directory).*

## 1. Discuss before fixing (substantive, in order)

**1a. §5.5 delegate-alignment paragraph has the bound backwards (~l. 1153).**
It says "razor-thin private return ($c_r/I_H \ge 0.95$, from $\pi^* \ge
0.053$)" — but π\* ≥ 0.053 gives c_r/I_H **≤ 0.947**, as the paper itself says
at ~l. 1134 and ~l. 1547. And the fix is more than a sign flip: under the
lower-bound logic the calibration no longer *establishes* a thin margin. The
consistent version runs the other way — misalignment (non-pivotality,
activity-rewarded delegation) *predicts* a thin private margin, and the data
are *consistent with* one as thin as 5.3%. Prediction → consistency, not
measurement → explanation. The rest of the paragraph (private vs. social I_H,
"at least 555" more conservative under misalignment, too-early-exit corollary)
survives untouched.

**1b. New Table 2 note misstates the Chow test.** The note says the Chow
statistic shares the robust framework; F = 8.38 is the classical RSS-based
Chow (`fig13_chow.py`) while the slopes are HC3. Pick one fix:
(i) reword the note — slopes robust, Chow classical, with the permutation
check (p_perm = 0.0009) as the assumption-free companion; or
(ii) report the HC3 interaction Wald that `tab_ols_structural_break.py`
already computes, which can carry the stars honestly.

**1c. §7.6 DIP timing: replace vagueness with exact dates and confront the
March 2024 coincidence.** "Introduced during 2024 … by many months … later
that year" is checkable and wrong-ish: first program month is March 2024 —
the *same month* as our primary Claude-3 break. Pin the SEEDGov dates, then
make the defense head-on: the QLR break (Nov 25, 2023), the readership-decline
onset (Nov 2023), and GPT-4 Turbo in the break battery all predate any DIP
payment. Stated crisply, the coincidence becomes a reason we don't lean on the
March date alone; left vague, it reads as evasion.

## 2. Mechanical text fixes (Joseph can send as one PR)

- Intro ~l. 162–165: both correlations stated twice in four lines — cut one
  instance. (Related: the classical p-values on r there sit oddly with Table
  2's new "descriptive" stance — drop or keep knowingly.)
- Abstract: "at least 555 words … per proposal" → insert "per delegate"
  (DAO-wide figure is ~24,000).
- Intro ~l. 188: "rising to below 8%" at the Claude-3 break → state the exact
  λ from the figT01 series (need the number from you).
- Turing evidence: the 49.7% point is from the 2023 online study
  (arXiv:2310.20216), currently folded into the `jones2024turing` cite — add
  it as its own bib entry; harmonize the human baseline (67% in text vs. ≈66%
  in caption).
- Label collision: `fig:dip` (Hartigan dip-test bimodality figure) vs. the new
  `sec:dip` — rename to `fig:bimodal` and, when convenient,
  `fig05_dip_test.py` → something without "dip".
- Two short additions from lab-talk feedback:
  (i) objection-and-answer paragraph where the AI-message assumption is
  introduced — "an AI-drafted post could carry a genuine human signal;
  empirically, flagged posts are non-directional and uncorrelated with
  outcomes, so zero-information is the right description of this sample";
  (ii) one sentence in the conclusion's policy paragraph adding the
  restore-the-posting-cost lever (bond / fee / proof-of-personhood) alongside
  identity and staked reputation.
- Name and cite Goodhart's Law formally where the conclusion invokes "a
  Goodhart failure" (decided July 30 — don't assume readers know the classics).
  Ready-made bib entries:

  ```bibtex
  @incollection{goodhart1975,
    author    = {Goodhart, Charles A. E.},
    title     = {Problems of Monetary Management: The {U.K.} Experience},
    booktitle = {Papers in Monetary Economics},
    volume    = {1},
    publisher = {Reserve Bank of Australia},
    address   = {Sydney},
    year      = {1975}
  }
  @article{strathern1997,
    author  = {Strathern, Marilyn},
    title   = {`Improving Ratings': Audit in the {British} University System},
    journal = {European Review},
    volume  = {5},
    number  = {3},
    pages   = {305--321},
    year    = {1997}
  }
  ```

  Suggested text: "…a Goodhart failure \citep{goodhart1975}---when a measure
  becomes a target, it ceases to be a good measure
  \citep[the popular formulation is due to][]{strathern1997}---in which
  subsidizing the measure (posted rationales) degrades the target (informative
  deliberation)."
- Word choices to settle: "exclusive formal pre-vote deliberation channel" in
  the lit review (keep "formal" or soften like the other two rewrites?);
  `kamenica2011` under "biased communication with soft information" is a
  stretch — swap for competition-in-persuasion or drop.

## 3. Pangram work package (Victor — your pipeline)

- **Saturation test** (from lab Q&A: a half-human/half-AI mix reportedly
  scores 1.0): mixture gradient at 0/25/50/75/100% AI content, plus
  AI-drafted-then-human-edited and the reverse. If saturation is confirmed,
  soften the fig05 "either fully human or fully AI, rather than hybrid"
  caption — bimodality is then partly the instrument. Nothing load-bearing
  breaks (1.0 still validly means "contains substantial AI text"), and it
  strengthens the objection-and-answer paragraph above. Verify before any
  rewording — the claim is secondhand.
- **Score the ~102 proposal texts themselves.** Closes an open confounder: if
  proposals turned AI-written at the break, the correlation could have died
  because the object under debate changed. No break in proposal AI-share →
  one sentence in robustness; a break → interesting in its own right.
- One clarifying sentence in §4 either way: our λ is a post-level share; a
  word-level AI share would differ if scores saturate.

## 4. New empirics (decide who runs what)

- **π proxy — the best suggestion from the lab talk:** monthly series of forum
  posts mentioning/complaining about AI content. A spike in Nov 2023–Mar 2024
  while λ ≈ 5% is direct evidence that beliefs moved before volume — the
  unverifiability mechanism observed, not inferred. Slots into §6.4 next to
  the readership decline. (Joseph happy to take.)
- **Directional-post volume as the activity measure** (Sharada): the model's
  object is n_h + n_l, not raw counts. Re-run the main spec on posts with a
  clear stance. Bonus: if humans still produce controversy-tracking
  directional posts post-break while the margin no longer responds, the
  *reading* side died — clean supply-vs-demand separation. May reuse the
  stance machinery from the AI-directionality analysis.
- **Alignment tests from the July notes, still open:** readership decline by
  VP tier, and within-delegate AI-adoption timing vs. DIP enrollment (both
  run on the existing panel); vote-timing herding and the 50K-ARB DIP
  eligibility discontinuity if we can get Snapshot timestamps / the DIP
  roster.
- **Exploratory only** (Sharada): within-thread human stance response to
  co-located AI posts. Endogeneity caveat up front — thread AI-share is
  endogenous to contentiousness. Appendix material at most; nearly free once
  the stance classifier exists.

## 5. Small yes/no decisions

- One sentence in the intro billing the DIP/Goodhart policy result (the
  conclusion has it; the intro contribution list doesn't)?
- **Decided (Joseph, July 30): dollar units throughout, not ARB** — matching
  the deck. Remaining call for the meeting: pick the conversion date/price
  convention (deck used ≈$1/ARB) and apply it consistently (delegate holdings,
  DIP's 5,000 ARB/month, treasury figures); only the 27× voting-power ratio is
  price-invariant.
