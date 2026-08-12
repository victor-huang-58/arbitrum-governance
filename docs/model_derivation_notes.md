# Deriving the Model — Working Notes

*Victor, Aug 2026. A first attempt to derive Proposition 1, the interior vote
margin, and the welfare kernel from primitives, rather than assert them. Draft
for discussion with Joseph — flags what is exact vs. a stated approximation.*

The referee's complaints #1–3 share one root: a single representative delegate
making a binary choice cannot produce a **population-level continuous margin** or
an **aggregate posting volume**. The fix is to make both objects *populations* and
to give posting a motive that survives a nonatomic continuum (no pivotality). We
rebuild in three blocks. Each block outputs one of the three contested objects.

---

## 1. Environment and primitives

One proposal. Binary state $\theta \in \{G, B\}$ ("should pass" / "should fail"),
common prior $p \equiv \Pr(\theta = G) \in (0,1)$. Read $p$ as the proposal's
*ex-ante consensus*: $p$ near 0 or 1 = foregone conclusion, $p \approx \tfrac12$ =
contested. The empirical **margin** and **posting volume** will both be derived as
functions of this single latent $p$ — which is what lets us invert one from the
other in the data.

Two continua, each of unit mass:

- **Contributors** (delegates / forum posters), index $i$. Each draws a private
  signal $s_i \in \{g, b\}$ with precision $q \equiv \Pr(s_i = g \mid G) =
  \Pr(s_i = b \mid B) \in (\tfrac12, 1)$, and an idiosyncratic posting cost
  $c_i \sim F$ on $[0, \bar c]$, iid, independent of $s_i$. Each has latent
  *ability* $\alpha_i \in \{H, L\}$, $\Pr(H) = \gamma$, with $q_H > q_L > \tfrac12$
  (used in Block B only).
- **Voters**, index $j$. Uninformed about $\theta$ except through the forum. Each
  has a private taste $b_j \sim \text{Unif}[-a, a]$ for the proposal passing
  (idiosyncratic value, orthogonal to $\theta$).

**Timing.** (1) Nature draws $\theta$, signals, tastes. (2) Contributors post or
not; a post truthfully reveals $s_i$ (truthfulness is enforced by the reputation
mechanism of Block B — misreporting is caught ex post and punished). (3) The forum
aggregate $(n_g, n_b)$ = masses of $g$- and $b$-posts is public. (4) Voters read
the aggregate, form a posterior, vote For/Against; the proposal passes iff the
For-share $\Phi > \tfrac12$. (5) $\theta$ is realized; collective and reputational
payoffs pay out.

---

## 2. Block A — Voting gives the interior margin

Voter $j$'s payoff if the proposal passes is $v(\theta) + b_j$ with $v(G) = +1$,
$v(B) = -1$. Reading the forum yields posterior $\mu \equiv \Pr(\theta = G \mid
n_g, n_b)$. The voter votes For iff $\mathbb{E}[v \mid \mu] + b_j \ge 0$, i.e.
$b_j \ge -(2\mu - 1)$. With $b_j$ uniform, the **For-share** is deterministic by a
law of large numbers:

$$
\Phi \;=\; \Pr\!\big(b_j \ge -(2\mu-1)\big) \;=\; \tfrac12 + \frac{2\mu - 1}{2a},
\qquad
\boxed{\;\text{margin} \equiv |2\Phi - 1| = \frac{|2\mu - 1|}{a}.\;}
$$

So the margin is **interior and derived** — it is the posterior's distance from
$\tfrac12$, scaled by taste dispersion $a$. Two consequences:

1. **Dependence on the prior.** When the forum is uninformative (a contested
   proposal, split posts), $\mu \approx p$ and $\text{margin} \approx |2p-1|/a$ —
   small for contested proposals, large for consensus ones. To leading order
   $\mathbb{E}[\text{margin} \mid p] \propto |2p - 1|$.
2. **Dependence on signal quality $q$** (the hook for AI). A more informative
   forum pushes $\mu$ away from $p$ toward 0 or 1, widening the margin. This is the
   $q$ that will reappear in the welfare kernel — the cross-equation restriction.

> Why this avoids the old degeneracy: a pure continuum with no aggregate noise
> would let voters infer $\theta$ *exactly* from $(n_g, n_b)$, forcing
> $\text{margin} \to 1$ always. The private taste $b_j$ is what keeps $\Phi$
> interior even under a sharp posterior — margins are finite because voters
> disagree on *values*, not only on *facts*.

---

## 3. Block B — Posting gives the volume

Each contributor is measure-zero, so pivotality is dead: no one posts to change the
outcome. The question is what motive delivers posting **peaked at contested
proposals** ($n(p) \propto p(1-p)$) while surviving the continuum. The roadmap
guessed *reputation / career concerns*. **I checked it numerically and it fails —
it predicts the opposite sign.** That failure is instructive, so it stays in the
record.

### 3a. Why career concerns give the WRONG sign (ruled out)

Let delegators observe a contributor's post $s$ and, ex post, $\theta$, and update
ability $\alpha \in \{H, L\}$ (with $q_H > q_L$), routing VP toward apparent
high-types. A contributor's expected reputational gain from posting $s$ is
$G(s;p) = R\,(\mathbb{E}_\theta[\Pr(H \mid s, \theta) \mid s] - \gamma)$. By the law
of iterated expectations this equals $R\,(\Pr(H \mid s) - \gamma)$ — the
*informativeness of the signal itself about type*. And here is the killer:

$$
\text{at } p = \tfrac12:\quad \Pr(g \mid H) = \tfrac12 q_H + \tfrac12(1-q_H) = \tfrac12 = \Pr(g \mid L)
\;\Rightarrow\; \Pr(H \mid g) = \gamma \;\Rightarrow\; G(g; \tfrac12) = 0.
$$

On a contested proposal your signal is a coin flip regardless of ability, so
**posting reveals nothing about your type — reputational incentive vanishes exactly
at $p=\tfrac12$.** Numerically the posting mass is **V-shaped: zero at $\tfrac12$,
maximal at the extremes** — because near a foregone conclusion, holding (and being
vindicated on) the majority signal *is* diagnostic of ability. Career concerns push
posting toward consensus, which would give $\mathrm{Cov}(\text{posts},\text{margin})
> 0$ and flip Proposition 1. **Reputation-for-ability is therefore rejected as the
posting motive.** (This also cautions against reading the delegate posting↔VP
correlation as clean support for a career-concern story — it is consistent with the
wrong-signed mechanism.)

### 3b. What actually works: posting follows attention, attention follows VOI

The object that *is* correctly peaked at $\tfrac12$ is the **value of information**
(§5): a post matters most when the decision is close. But raw "influence on the
decision" is measure-zero (pivotality again) and pure common-value posting
free-rides (a public good). The fix that survives the continuum: contributors are
rewarded per **unit of information delivered to an audience of readers**, not per
decision flipped. A measure-zero poster still reaches a positive *mass* of readers.

Readership is where the peak comes from. A reader (a voter/delegator) reads iff the
private value of information to their own decision exceeds the reading cost,
$\text{VOI}_{\text{reader}}(p) \ge c_{\text{read}}$. Since $\text{VOI}$ peaks at
$\tfrac12$ and vanishes at the extremes (§5), **readership $A(p)$ concentrates on
contested proposals.** Posting reward $\propto$ readers reached, so a contributor
posts iff $c_i \le R\,A(p)$, and

$$
n(p) \;=\; F\big(R\,A(p)\big)
\;\;\xrightarrow[\text{$F$ near-linear at }0]{}\;\;
\boxed{\; n(p) \;\propto\; A(p) \;\propto\; p(1-p). \;}
$$

**This $A(p)$ peak is derived, not assumed** (checked numerically): solving the
reader's problem — voter with private taste $b_j$, reads iff the private value of
information to their own For/Against choice exceeds $c_{\text{read}}$ — yields
$A(p)$ **single-peaked at exactly $p=\tfrac12$, vanishing at the extremes, and
$\approx 2p(1-p)$**. It is robust to $c_{\text{read}}$: raising the reading cost
trims the tails first (foregone conclusions stop being read at all) while the peak
stays put. So the readership figure's shape is a *prediction* of the model, and the
posting parabola inherits it.

Posting peaks on contested proposals **because that is where the audience is** —
and the audience is there for the same value-of-information reason that drives the
welfare block. This unifies posting, reading, and welfare under one force (VOI at
$\tfrac12$), survives the continuum (reward = readers reached, $>0$ for a
measure-zero poster), and dodges both pivotality and free-riding. Reputation can
ride on top (delegators who read update delegation), but it is a *passenger*, not
the driver — and on its own it drives the wrong way.

The $237$-word average post and posts-per-proposal count pin $F$ and mean cost;
$A(p)$'s peak is disciplined by the readership figure (the one already in the paper).

---

## 4. Proposition 1 (now derived)

Combining Blocks A and B, both objects are deterministic functions of the single
latent $p$:

$$
\mathbb{E}[\text{posts} \mid p] \propto p(1-p) \quad\text{(peaks at } \tfrac12),
\qquad
\mathbb{E}[\text{margin} \mid p] \propto |2p - 1| \quad\text{(troughs at } \tfrac12).
$$

Both are monotone in $|p - \tfrac12|$ with **opposite** signs. Hence across a
cross-section of proposals with any nondegenerate distribution of $p$,

$$
\boxed{\; \mathrm{Cov}\big(\text{posts}, \text{margin}\big) < 0. \;}
$$

That is Proposition 1 — a *consequence* of the two equilibrium blocks, not an
assumption. **Caveat (honest):** this predicts a specific one-parameter locus, but
the data cannot separate it from the linear reduced form. On the pre-Claude-3
sample ($n=29$), `posts ~ (1−margin²)` and `posts ~ margin` fit identically
($R^2 = 0.114$ vs. $0.111$) because $(1-\text{margin}^2)$ and $-\text{margin}$ are
nearly collinear over the observed range. **So Proposition 1 alone is not the test
of the model.** The test lives in the cross-equation restrictions of §6.

---

## 5. Block C — Welfare as the value of the forum signal

Collective payoff = probability the decision matches $\theta$. Without the forum,
the DAO decides on the prior and is right with probability $\max(p, 1-p)$. The
forum supplies a signal of precision $q$; its value is the resulting rise in
prob(correct), concentrated where the decision is close.

**Exact object.** For a symmetric binary signal and binary action, the value of
information $V(p,q)$ is a *tent*: strictly positive only for priors within the
flip window $p \in (1-q,\, q)$, peaked at $p = \tfrac12$, zero outside. A single
$g$-signal flips an Against-leaning decision iff $pq > (1-p)(1-q) \iff p > 1-q$.

**Smooth approximation → the paper's kernel.** Expand around an uninformative
signal, $\varepsilon \equiv q - \tfrac12 \to 0$, in a quadratic-loss / $\pm1$-payoff
formulation. The prior "closeness" enters as the payoff variance
$\mathrm{Var}(v) = 4p(1-p)$; the signal enters through its Fisher information
$\propto (q-\tfrac12)^2$. To second order the per-proposal welfare value factorizes:

$$
\boxed{\; V(p, q) \;\approx\; 4\,p(1-p)\,\big(q - \tfrac12\big)^2 \; \times \text{const}. \;}
$$

This **derives the paper's welfare kernel as the second-order (Gaussian)
approximation** to the exact tent — [closeness] $\times$ [signal quality]. The
factor $4p(1-p)$ is the same closeness that suppresses the margin in Block A; the
$(q-\tfrac12)^2$ is the same $q$. **Honest flag:** the *exact* form under your
literal $\pm1$ payoff is the tent, not the parabola; $4p(1-p)(q-\tfrac12)^2$ is its
smooth cousin. Whether to present the exact tent or the approximation is a writing
choice — but either is *derived*, which the current draft's version is not.

---

## 6. Where AI enters — and the over-identifying test

Model AI writing as **signal dilution**: a fraction $\pi$ of posts are eloquent but
carry no private signal (a coin flip). The forum's effective precision is

$$
q_{\text{eff}} - \tfrac12 \;=\; (1 - \pi)\,\big(q - \tfrac12\big).
$$

This threads $\pi$ — the paper's central object — through *both* derived equations:

- **Margin (Block A):** higher $\pi$ pulls $\mu$ back toward $p$, so the margin
  **compresses**. Testable at the structural break.
- **Welfare (Block C):** $V \approx 4p(1-p)(1-\pi)^2(q-\tfrac12)^2$ — the loss is
  quadratic in $(1-\pi)$ and hits **contested proposals hardest**.
- **Reading threshold $\pi^\*$:** a reader reads iff expected informativeness beats
  the reading cost, $(1-\pi)I_H \ge c_{\text{read}}$, giving
  $\pi^\* = 1 - c_{\text{read}}/I_H$ — the paper's unverifiability threshold, now
  grounded, with $I_H$ the value of a genuine post from §5.

**The actual scientific payoff (over-identification).** The *same* precision $q$
governs three different moments:

| Structural object | Identified from (data you have) |
|---|---|
| $q$ (signal precision) | posts→margin slope (the $-0.33$), and its change at the break |
| $q$ (again) | the welfare/AI-degradation kernel $(q-\tfrac12)^2$ |
| $R$, and readership $A(p)$ | delegate cross-section ($\Delta$VP per post) sets the *scale* $R$; the **readership figure** disciplines the *shape* $A(p)\propto p(1-p)$ — see §3b caution |
| $F$, mean cost | the 237-word calibration + posts-per-proposal |
| distribution of $p$ | inverted from the observed margins, $|2p-1| = a\cdot\text{margin}$ |

$q$ estimated from the **posting/margin** equation must equal $q$ backed out of the
**welfare** kernel. If they disagree, the model is wrong — and that
*over-identifying test is something the single-equation posts–margin curve can
never provide.* That is the reason to derive rather than assert: not a prettier
Proposition 1, but a falsifiable cross-restriction.

---

## 7. Honest ledger — exact vs. approximate

**Exact / clean:**
- Interior margin $= |2\mu-1|/a$ from private-value voting (Block A).
- $n(p) = F(Rk\Sigma(p))$ increasing in the reputational stake (Block B structure).
- Prop 1 sign: $\mathrm{Cov}(\text{posts},\text{margin}) < 0$ from opposite
  monotonicities.
- $q_{\text{eff}} = \tfrac12 + (1-\pi)(q-\tfrac12)$ and the $\pi^\*$ threshold.

**Rejected on inspection (kept as a warning):**
- *Reputation / career concerns as the posting motive.* Numerically gives posting
  **peaked at the extremes, zero at $\tfrac12$** — opposite sign, would flip Prop 1
  (§3a). The delegate posting↔VP correlation is therefore *not* clean evidence for
  a career-concern mechanism.

**Now derived (numerically; analytic write-up pending):**
- $A(p)$ single-peaked at $p=\tfrac12$, $\approx 2p(1-p)$, from the reader's own
  VOI problem — robust to the reading cost. This was flagged as the make-or-break
  step and it **held**. Remaining work is the closed-form (or a clean bound), not a
  question of whether the shape exists.

**Stated approximations (label or grind):**
- $V \approx 4p(1-p)(q-\tfrac12)^2$ is a second-order expansion; the exact
  binary-binary object is the tent on $(1-q, q)$. **To do:** decide which to present.
- Truthful posting is imposed, justified informally. **To do:** state the off-path
  belief, or cite Ottaviani–Sørensen reputational cheap talk.

**Biggest open risk (now singular):** the exact welfare form under the literal
$\pm1$ payoff (parabola vs. tent). The *structure* — everything driven by VOI
peaking at $\tfrac12$ — is robust and now includes a *derived* readership peak. What
remains is closed-form polish and the over-identification estimate, not an
existence question.

---

## 8. What "starting" looks like, concretely

1. **Lock Block A** — it is the cleanest; write the private-value voting lemma and
   the margin $= |2\mu-1|/a$ result formally.
2. ~~Grind Block B~~ **Done.** Career concerns *rejected* (§3a, wrong sign); the
   attention/VOI replacement's key input — readership $A(p)$ single-peaked at
   $\tfrac12$ — is *derived* (numerically, §3b). Remaining: closed-form for $A(p)$.
3. **State Block C both ways** (tent and quadratic approximation), pick one.
4. **Estimate $q$ twice** (margin eq. vs. welfare kernel) and report the
   over-identifying gap — the one number that tells us whether the derived model
   earns its keep.

**Decision gate — updated after actually doing the work:** the make-or-break step
*passed*. The honest scorecard: Block A derived; Block B's naive keystone disproven
but the corrected VOI/attention mechanism holds with a *derived* readership peak;
Block C derived as a second-order approximation; Prop 1 and the $\pi^\*$ threshold
fall out; one clean over-identifying test remains to run. This is now a **credible
path to a genuinely derived model**, not a hope — the two things most likely to
break (does reputation work? does readership peak?) have been resolved, one negative
and one positive, and the model survives both. The residual work is closed-form
polish + estimation (~2–3 weeks), not open existence questions. That tips the A1
decision toward *derive* being achievable — worth putting to Joseph with this memo.

---

## 9. Results from actually running (b) and (c)

### (b) Closed form for A(p) — clean win
A reader reads iff the forum could flip their vote; the swingable taste-band has
width 2(mu_G - mu_B), and the algebra collapses to

    A(p) = p(1-p)(2Q-1) / [ a (pQ+(1-p)(1-Q)) (p(1-Q)+(1-p)Q) ]

Verified exact against simulation. The p(1-p) is explicit; the denominator is a
mild modulation. A(1/2) = (2Q-1)/a, zero at the extremes. Under AI dilution
(2Q_eff - 1) = (1-pi)(2Q-1), so **readership is linear in (1-pi)** — a bonus
prediction: AI fluff shrinks the audience, tying directly to the reading /
unverifiability story.

### (c) Over-identification on the data — headline holds, sharper tests do NOT
Honest result. pi (AI post share) roughly doubles, 0.064 -> 0.124, pre->post
Claude 3.

- **Core moment (supported):** corr(posts, margin) weakens -0.34 -> -0.10 as AI
  rises — consistent with dilution breaking the VOI structure. *But this is the
  reduced-form result the paper already had.*
- **Human-vs-AI split (NOT supported / confounded):** pre-shock, AI posts track
  margin as much as human posts (-0.34 vs -0.33) — with few AI posts,
  ai_posts ~ total_posts, so it just inherits volume. Not a clean discriminating
  test.
- **Margin compression (NOT supported):** margins move toward *unanimity*
  (0.72 -> 0.91), not toward the prior as Block A predicts, and
  corr(pi, margin) = +0.06 (null).

**Verdict:** the model is internally *derivable*, but the data currently confirms
only the headline correlation the reduced form already delivered — the sharper
*over-identifying* restrictions that would distinguish the structural mechanism are
null or underpowered (n=29 pre, tiny AI counts). So deriving buys **theoretical
rigor**, not extra **empirical validation** — at least not with this sample. That
tempers the §8 optimism: the theory comes together; the data does not yet reward
the extra structure. Derive for a rigorous self-consistent theory section; keep it
illustrative if the goal is empirical credit.
