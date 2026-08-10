# Proposal: Derive the Model, and the Unraveling Mechanism It Reveals

*Victor → Joseph, Aug 2026. A decision memo for the model direction. Backed by
`model_derivation_notes.md` (working) and `model_proofs.md` (formal lemmas/props).*

## The decision on the table

Refine's most damaging line is **"the model does not derive its own results"**
(Proposition 1, the interior margin, the welfare formula). We have two options:
reframe the model as *illustrative*, or *derive it properly*. **I went ahead and
tried to derive it — and it works, with one motive replaced and one formula
corrected.** This memo lays out what we can now claim, and asks for a go/no-go on
folding it into the paper.

---

## The points we are making (the contributions)

**① The model now derives its results — from primitives.**
Two populations (informed posters, taste-heterogeneous voters) and three short
proofs deliver the three objects the referee said were asserted:
- **Margin** = $|2\mu-1|/a$ — interior, derived (Lemma 1).
- **Posting volume** $\propto p(1-p)$ — peaks on contested proposals, derived (Lemma 3).
- **Proposition 1** ($\mathrm{Cov}(\text{posts},\text{margin})<0$) — now a *theorem*,
  not an assumption (Prop 1).

**② The reason people post is *attention*, not *reputation* — and we can prove the
reputation story is wrong.**
We tested the intuitive "delegates post to build a reputation for being right." It
predicts the **opposite sign** — posting would peak on *obvious* proposals, because
being vindicated is only diagnostic of ability there. The mechanism that fits is
**value-of-information**: readers concentrate on close calls, and posters follow the
audience. This *reframes* the delegate posting↔voting-power correlation the paper
documents — it is evidence for an information channel, not a reputation channel.

**③ AI writing shrinks the audience — a new, sharp prediction.**
The derived readership is **linear in $(1-\pi)$**: as AI content rises, reads/views
per proposal should fall. This is a *distinct* prediction the current paper never
makes. First look at our `reads` data: right sign in all four cuts, underpowered
(needs an age-adjusted read rate). A clean, cheap extension.

**④ ⭐ AI can *tip* a governance forum into irreversible collapse (Proposition 3).**
Making AI share endogenous closes a feedback loop — more fluff → fewer readers →
the *costly, genuine* posters quit first → more fluff. The result is a
**market-for-lemons dynamic with a tipping point and hysteresis**:
- Below a critical AI-fluff level, a *healthy* forum and a *collapsed* forum coexist.
- Past the threshold, the healthy equilibrium **vanishes discontinuously** (a forum
  can sustain ~62% AI content in our instance, then collapses to 100%).
- Collapse is **irreversible**: lowering AI afterward does *not* restore the forum.

This is the headline upgrade — it turns the paper from *"AI correlates with weaker
deliberation"* into *"AI can trigger a discontinuous, hysteretic collapse of the
deliberation mechanism."* A genuine second theoretical contribution.

**⑤ We found and fixed our own error.**
The paper's welfare kernel $4p(1-p)(q-\tfrac12)^2$ is **not** exact — the true
decision value is a tent, the true belief-accuracy value carries $[p(1-p)]^2$. We
replace it with a closed form. Fixing a flagged formula before a referee does is
credibility, not a cost.

---

## What this does *not* fix (stated plainly)

- **The empirics are unchanged.** One DAO, $N\approx102$, identification off a single
  aggregate shock (Claude 3). Theory can't substitute for design.
- **The over-identification test does not pass.** The sharper structural predictions
  are null/underpowered ($n=29$ pre). We can claim the data is *consistent with* the
  mechanism, not that it *confirms* it.
- **New risk:** an elegant, heavy theory on thin data invites *"a theory in search of
  data."* Real, and the flip side of deriving everything.

---

## The proposal (three moves, decreasing certainty)

1. **Derive the model (do it).** Replace §5 with Lemmas 1–3 + Prop 1. Defensive,
   high-certainty, kills the worst referee line. ~1 week to write in.
2. **Correct the welfare formula (do it).** Swap in the exact closed form. Trivial.
3. **Proposition 3 — decide together.** Two ways to play it:
   - *(a) Mechanism section:* include a compact version as a "why this matters"
     capstone, clearly labeled a possibility result.
   - *(b) Second paper:* spin the tipping/hysteresis model into a theory-forward
     follow-up, where thin empirics don't drag it. **My lean: (b)** — it's strong
     enough to stand alone, and bolting it onto $N=102$ risks the mismatch critique.

---

## Positioning (honest scoring)

| Tier | Now | With ①②⑤ integrated |
|---|---|---|
| Top-3 finance (JF/JFE/RFS) | reject (~48) | reject (~50) — *empirical design is the wall* |
| Strong field (Mgmt Sci, RoF, JLEO) | — | **credible R&R (~65)** |
| Fintech / econ-of-AI outlet | — | **R&R, plausible accept (~70)** |

The model work lifts the *field-journal* ceiling from ~60 to ~68. It does **not**
move top finance — that ceiling is set by the data (one DAO, one shock), and the next
investment to break past it is **a second DAO or within-DAO cross-sectional variation
in the AI shock**, not more theory.

## Bottom line

Derive (1) and fix the welfare formula (2) — both are clear wins and the paper needs
them. Then let's decide whether Proposition 3 is this paper's capstone or the seed of
the next one. Either way, we now have a model that **stands on its own** and a
mechanism — *AI-driven forum collapse* — that is genuinely worth naming.
