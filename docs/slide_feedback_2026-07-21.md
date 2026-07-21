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

## 8. Strengthen the capability-threshold evidence with independent, human-judged sources

The paragraph supporting the indistinguishability threshold currently leans on
vendor-reported benchmarks (Anthropic/OpenAI model-card figures). Two independent
lines are stronger and directly on point:

- **Blind human preference (LMSYS Chatbot Arena):** Claude 3 (Mar 4, 2024)
  almost immediately unseated GPT-4 at the top of the Arena — the first
  non-OpenAI model ever to outrank the GPT-4 family — on 600k+ blind pairwise
  human votes. Claude 2 never reached that tier. This is the ordinal claim
  ("breaks cluster at the first models able to emulate human prose") established
  by blind human judgment rather than self-reported benchmarks.
- **Controlled Turing tests:** Jones & Bergen, "People cannot distinguish GPT-4
  from a human in a Turing test" (arXiv:2405.08007; ACM FAccT 2025) — in a
  randomized, preregistered interactive test, GPT-4 was judged human 54% of the
  time (actual humans: 67%; ELIZA: 22%); a follow-up with GPT-4o reached 77%,
  above the human baseline. Direct evidence that the Nov-2023/Mar-2024
  capability generation reached near-human indistinguishability in text.

Suggested use: cite both in the §6.4 timing discussion (and/or where the quality
threshold is introduced), alongside the existing model-card numbers. Honest gap
to acknowledge if pressed: no benchmark measures indistinguishability of
*governance-forum prose* specifically; Arena and the Turing studies are the
nearest instruments.

**A ready-made figure exists.** For the deck we built a time-series chart of the
best available AI's Turing-test pass rate across the three Jones & Bergen waves
(GPT-4 41% → GPT-4 54% → GPT-4.5 73%), with the 50% chance line and the
Nov 2023–Mar 2024 structural-break window shaded — **the series crosses 50%
inside the break window**. Figure + generating script (data hard-coded from the
three papers): `ArbitrumProject/slides/figs_v4/fig_turing_timeline.{png,py}` in
Dropbox. Candidate for §6.4 as visual support for the capability threshold.
Caveats stated on the slide: prompts improved across waves; conversational text,
not governance prose; the crossing date is an interpolation between two waves.

## 9. The Delegate Incentive Program (DIP) is absent from the paper — and the policy point deserves intro/conclusion billing

**Joseph's framing, now on the deck's conclusion slide:** governance is
underprovided due to positive externalities, so the naive remedy is to subsidize
participation — which Arbitrum literally does (DIP pays delegates per posted
rationale). **The paper explains why this natural policy backfires in the AI
era — and the failure mode is worse than waste.** The subsidy attaches to text,
and once text is free, each subsidized zero-content post pushes expected
contamination toward the tipping point π\*. Past π\* the collapse is discrete
and total: the subsidy can *finance the destruction of the very forum it exists
to support*. (Joseph's phrase: it's not wasting money, it's buying a bullet for
your own head.) That is a headline contribution, not a robustness footnote —
consider billing it in the introduction or conclusion, alongside the mechanism
result.

Background and the three supporting angles:

The SEEDGov-administered DIP pays delegates monthly in ARB for voting **and
publicly posting voting rationales** (eligibility >50K ARB voting power, >25%
participation, KYC; first program month **March 2024**; ~5,000 ARB/month cap in
later versions; 38 of 40 qualified in month one). The paper never mentions it,
but it matters three ways:

- **Confounder someone will raise, with a clean timing defense:** the program
  launched inside the Nov 2023–Mar 2024 break window, and it directly subsidizes
  forum text production. But the QLR break (Nov 25, 2023) and the readership
  decline (Nov 2023) both *predate* it — same ruled-out-by-timing structure as
  the vesting cliff in §8.5. It belongs in that battery explicitly.
- **Microfoundation for the adoption result:** who has a pecuniary motive to
  mass-produce rationale posts at minimum cost? Low-power delegates, for whom
  ~5,000 ARB/month is material — exactly the 27×-gap population in §7. DIP gives
  the cross-sectional finding an institutional *why*.
- **A Goodhart framing worth a paragraph:** governance has positive
  externalities, so subsidizing participation is sensible — but DIP subsidizes
  the observable proxy (posted text). Once c_p^AI ≈ 0, the subsidy flows to
  zero-content compliance prose. Paying per rationale while AI makes rationales
  free is precisely the combination the model says destroys the forum. It also
  plausibly amplifies the post-2024 volume surge and the posts-per-user tripling.

(Also a naming hazard we tripped on: `fig05_dip_test` refers to Hartigan's dip
test for bimodality, not the Delegate Incentive Program — consider renaming the
script/label to avoid the collision now that DIP may enter the paper.)

## 10. Deepen the Dewatripont–Tirole contextualization — the paper is closer to "Advocates" than the lit section lets on

The related-literature paragraph correctly names D–T (JPE 1999) as the closest
structural antecedent, but the connection is richer than "advocates pay
investigation costs to present arguments to a principal," and developing it
would sharpen the paper's positioning:

- **The forum is a decentralized advocacy mechanism.** D–T's main result: two
  opposed advocates beat one neutral investigator because partisan mandates
  restore high-powered incentives that a "find both sides" mission dilutes
  (multitask moral hazard). The no-AI forum equilibrium — both sides posting in
  proportion to support, the delegate aggregating — is exactly this structure,
  arising without design.
- **The key frame: D–T's mechanism runs on *verifiable* (hard) evidence —
  advocates can suppress but not fabricate.** Forum posts were never
  verifiable; their credibility came entirely from being costly to produce.
  The paper can be positioned as: *what happens to an advocacy mechanism when
  its discipline device is production cost rather than verifiability, and that
  cost goes to zero.* Answer: it unravels — consistent with D–T's own logic
  about why verifiability matters.
- **The stated contribution (endogenous principal attention) is right and worth
  foregrounding against D–T specifically:** their principal passively processes
  whatever advocates bring; ours pays c_r per post, rationally chooses whether
  to listen, and past π\* stops entirely. The collapse is on the *demand side*
  of persuasion, which the advocacy literature does not model.
- **DIP ties in here too:** D–T's insight is that what you pay for determines
  what gets discovered. DIP pays for posted text irrespective of content — the
  degenerate limit of an advocacy reward scheme (see item 9).
- Adjacent citations to consider: Milgrom–Roberts (1986) persuasion games /
  hard information; Shin (1998) adversarial vs. inquisitorial procedures;
  Che–Kartik (2009) opinions and incentives; Gentzkow–Kamenica on competition
  in persuasion. The paper already cites Persico (2004) and Gerardi–Yariv
  (2008) for committees — the asymmetric-roles distinction (many posters, one
  reader) is the right one to keep.

Seminar-ready line: "D–T show adversarial advocacy is the efficient way to fund
information discovery — but their mechanism runs on verifiable evidence. The
forum ran on costly soft information; when AI removed the cost, there was no
verifiability to fall back on. Our addition is the demand side: unlike their
principal, ours can rationally stop listening — and did, discretely."

## 11. Poke at the aligned-delegate assumption — and exploit the delegate-level data to test it

The model gives the delegate a ±1 correctness payoff, making them a perfect
agent of the DAO. Three reasons that's dubious here: (i) **non-pivotality** — a
majority needs 4 delegates, so the private value of correctness is near zero for
almost everyone (rational ignorance); (ii) **the delegation market rewards
observable activity, not decision quality** — delegation is revocable, delegators
see posts/rationales/participation, and DIP monetizes exactly those observables;
(iii) **conflicts** (professional delegates, grant ecosystems, LobbyFi).

Consequences — mostly favorable:

- **Reinterprets the fragility finding.** Misalignment predicts a razor-thin
  private return to reading; c_r/I_H ≈ 0.95 is what a non-pivotal,
  activity-rewarded delegate market *should* look like. The calibration found
  fragility; misalignment explains why.
- **Strengthens the lower bound again.** Reading is a public good (good votes
  benefit all holders), so private I_H < social I_H. The collapse point then
  identifies the *private* surplus margin, and the social value destroyed
  exceeds the calibrated figure. "At least 555 words" survives misalignment and
  becomes more conservative under it. Corollary: the observed π\* is the
  private threshold; the socially optimal one is higher — delegates quit
  reading too early from society's perspective even before AI.
- Cover-story dynamic worth a sentence: crossing π\* legitimizes disengagement
  delegates already privately preferred — consistent with fast, non-reversing exit.

Tests feasible with existing or public data:

1. **Readership/engagement decline by VP tier** (panel supports now): stakes
   alignment predicts high-VP delegates disengage less — sorts the
   heterogeneity behind the −36%-not−100% reads decline.
2. **Vote-timing herding** (needs Snapshot timestamps): did small delegates
   condition more on whales' earlier votes post-break, substituting
   whale-following for forum-reading?
3. **DIP eligibility discontinuity** (needs DIP roster): around the 50K ARB
   cutoff, does eligibility raise rationale posting and AI fraction without
   changing voting independence?
4. **Within-delegate AI-adoption timing vs. DIP enrollment** (panel supports
   now): does adoption cluster at enrollment rather than at model releases?

## 12. Smaller items

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
