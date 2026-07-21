# Notes from the FSIL slide build — changes to back-propagate to the paper

*Joseph Hall, July 21, 2026. These came out of preparing the FSIL lab deck
(`ArbitrumProject/slides/FSIL_slides_Hall_Jul21.tex` in Dropbox). Ordered by
importance.*

## 1. The §5.5 calibration point-identifies π\* with the wrong object — restate as a lower bound (strengthens the result)

§5.5 sets π\* = 0.053, the **realized AI share (λ)** at the QLR break. But the
unverifiability mechanism (and §6.4) argues that the delegate's expectation π runs
**ahead of** λ at a capability shock. Both can't hold. The internally consistent
statement:

- Reading continued until Nov 25, 2023 ⟹ π (just before the break) ≤ π\*
- π ≥ λ while λ is rising (π is the forward-looking expectation of a rising realized share)
- ⟹ **π\* ≥ λ_break = 0.053 — a lower bound, not a point estimate**

Everything downstream then becomes a conservative bound: net reading surplus
≥ 12.56 words/post, **≥ 555 words per delegate per proposal**, **≥ 24,000 words
per proposal DAO-wide**. "At least X, and it was destroyed" is a stronger claim
than a point estimate resting on an inconsistent assumption. The abstract's "555
words" should read "at least 555 words."

Also worth adding explicitly (it's a nice identity): rearranging the threshold,
**π\* = (I_H − c_r)/I_H — the tipping point *equals* the per-post surplus share.**
The collapse point therefore identifies (a lower bound on) the surplus margin
directly, the same way an exit price reveals a firm's margin.

## 2. Table 2 mixes inference frameworks across rows

The slope rows use heteroskedasticity-robust SEs (col. 1: t = −1.34, no stars),
while the Pearson-r rows carry stars from the classical r-test (col. 1:
r = −0.21, p ≈ 0.03 classical, two stars). Same null, different variance
estimators — a referee will flag the inconsistency. Options: drop stars on the r
rows (present r as descriptive; the deck does this), or footnote "slope SEs
robust; r p-values classical."

## 3. Terminology: "perceived" → "expected"

We replaced "perceived contamination" with **"expected contamination"**
throughout the deck: π is the delegate's *expectation* of λ going forward
(λ = backward-looking realized share; π = its forward-looking expectation, which
converges to λ in the long run but need not equal it at a shock). "Expectation"
is the correct economics term and makes point 1 above easier to state.

## 4. Q\* does no formal work — demote it to prose

No equilibrium object depends on the level of Q; it enters only through the
indicator 1{Q ≥ Q\*} (the paper's own comparative-statics discussion concedes
this). The deck now says: "at a point in time T, it becomes possible to emulate a
genuine human post — carrying zero information — at essentially zero cost," and
"breaks cluster at the first models able to emulate human governance prose."
Consider the same treatment in §5.3 to avoid a theorist reading Q\* as a lever.

## 5. Cut the "sole deliberation channel" claim

We cannot show mega-delegates aren't coordinating privately, and nothing in the
identification rests on their not doing so. Reframe "the forum is the *only*
intermediary between information and vote" (intro and elsewhere) as "the public,
recorded deliberation channel." Same identification, no unprovable exclusivity
claim.

## 6. "Selection" language in §6.3

"A selection interpretation of AI adoption" reads as sample-selection/selection
bias to an econ audience. The deck now says: low-power delegates adopt AI; the
signal died from unverifiability, not strategic manipulation by insiders.

## 7. Model exposition order (worked well in the deck)

Define the two objects before the two mechanisms, as a fact/expectation pair:

- λ = fraction of posts that **are** AI-generated ⇒ uninformative posts *in fact*
  → delegates cast worse votes and the Prop.-1 correlation dilutes **gradually**
- π = expectation that the next post read is AI ⇒ uninformative posts *in
  expectation* → past π\* delegates abandon the forum entirely, and with no
  reader, writing stops paying too: a **self-fulfilling collapse** (Akerlof) —
  **discrete**, even while λ is small

Avoid forward references to the volume data inside the model section (the reader
doesn't have the time series yet); "gradual dilution vs. discrete abandonment is
an empirical question" is all the setup the timing test needs.

## 8. Smaller items

- **Dollar denomination:** the deck states token amounts as dollars ("$13B worth
  of ARB at launch," "$3.5B treasury"). Delegate holdings (71K / 1.9M ARB) were
  converted at ≈$1/ARB — if the paper adopts dollar framing it should fix a
  conversion date/price; only the 27× ratio is price-invariant.
- **Heterogeneity footnote worth adding:** reads fell 36%, not 100% ⟹ delegates
  have heterogeneous (c_r, I_H), i.e., a distribution of thresholds π\*ᵢ; the
  discrete cliff is the representative-agent limit and the observed partial
  decline is exactly what the smoothed version looks like. Converts an objection
  into corroboration.
- **Notation collision:** I_H's subscript (Human-authored) vs. θ = H (High
  quality). Consider renaming one.
- **§6 duplicated phrase** ("at the QLR break (November 2023)" twice in one
  sentence) — already fixed in PR #1.

*(The deck itself: 31 slides, five sections with roadmap check-ins, style per
Shapiro's applied-micro-talk notes and paulgp/beamer-tips. Happy to walk through
any of it.)*
