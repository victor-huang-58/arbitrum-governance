# Formal Results — Drop-in Lemmas and Propositions

*Victor, Aug 2026. Paper-ready statements and proofs for the derived model in
`model_derivation_notes.md`. Notation matches that memo. Everything here is exact
unless explicitly labeled an approximation. The last section, §6, is where the new
mileage is.*

## Setup

One proposal. State $\theta\in\{G,B\}$, common prior $p=\Pr(\theta=G)\in(0,1)$.

- **Voters:** continuum of mass 1. Voter $j$ has iid private taste
  $b_j\sim\mathrm{Unif}[-a,a]$. Common value $v(G)=+1,\ v(B)=-1$. Choosing *For*
  yields $v(\theta)+b_j$; *Against* yields $0$.
- **Forum:** publicly summarized by a binary signal $\sigma\in\{G,B\}$ with
  precision $Q\equiv\Pr(\sigma=G\mid G)=\Pr(\sigma=B\mid B)\in(\tfrac12,1]$. Write
  the signal-conditional posteriors
  $$
  \mu_G=\frac{pQ}{pQ+(1-p)(1-Q)},\qquad
  \mu_B=\frac{p(1-Q)}{p(1-Q)+(1-p)Q},
  $$
  and the marginal signal probabilities $D_1\equiv\Pr(\sigma=G)=pQ+(1-p)(1-Q)$,
  $D_2\equiv\Pr(\sigma=B)=p(1-Q)+(1-p)Q$, with $D_1+D_2=1$.

Two identities used throughout (both one line):

$$
\textbf{(I1)}\quad D_1(\mu_G-p)=D_2(p-\mu_B)=p(1-p)(2Q-1),
\qquad
\textbf{(I2)}\quad \mu_G-\mu_B=\frac{p(1-p)(2Q-1)}{D_1 D_2}.
$$

*Proof of (I1).* $D_1\mu_G=pQ$, so $D_1(\mu_G-p)=pQ-pD_1=p\big(Q-pQ-(1-p)(1-Q)\big)
=p(1-p)(2Q-1)$; symmetric for $D_2$. (I2) follows since
$\mu_G-\mu_B=(\mu_G-p)+(p-\mu_B)=p(1-p)(2Q-1)(1/D_1+1/D_2)$ and $1/D_1+1/D_2=
(D_1+D_2)/D_1D_2=1/D_1D_2$. $\qquad\blacksquare$

---

## 1. Lemma 1 (Interior vote margin)

**Statement.** If all voters share posterior $\mu$, the *For*-share is
$\Phi(\mu)=\tfrac12+\tfrac{2\mu-1}{2a}$ (for $|2\mu-1|\le a$; otherwise clamped to
$\{0,1\}$), and the realized **margin** is
$$
M(\mu)\equiv|2\Phi-1|=\frac{|2\mu-1|}{a}.
$$

**Proof.** A voter chooses *For* iff $\mathbb E[v\mid\mu]+b_j\ge0
\iff b_j\ge-(2\mu-1)$. With $b_j\sim\mathrm{Unif}[-a,a]$ and threshold
$\tau=-(2\mu-1)$, the mass above $\tau$ is $(a-\tau)/(2a)=\tfrac12+\tfrac{2\mu-1}{2a}$
by the LLN. Then $2\Phi-1=(2\mu-1)/a$. $\qquad\blacksquare$

**Remark.** The margin is interior for any interior $\mu$ — the private taste $a>0$
is exactly what breaks the continuum's full-revelation degeneracy (with $a\to0$ the
margin jumps to $1$ whenever $\mu\neq\tfrac12$). Margins are finite because voters
disagree on *values*, not only on *facts*.

---

## 2. Lemma 2 (Margins rise with contestedness and with forum quality)

**Statement.** Let $M(p,Q)=\mathbb E_\sigma[\,|2\mu_\sigma-1|\,]/a
=\big(D_1|2\mu_G-1|+D_2|2\mu_B-1|\big)/a$. Then
$$
M(p,Q)\ \ge\ \frac{|2p-1|}{a},\qquad\text{with equality iff }Q=\tfrac12,
$$
and $M(p,Q)$ is nondecreasing in $Q$. Moreover $M(\tfrac12,Q)=(2Q-1)/a$ and
$M(p,Q)\to 1/a$ as $p\to\{0,1\}$, so $M$ is increasing in $|p-\tfrac12|$.

**Proof.** Posteriors are a martingale: $\mathbb E_\sigma[\mu_\sigma]=p$, hence
$\mathbb E_\sigma[2\mu_\sigma-1]=2p-1$. Since $x\mapsto|x|$ is convex, Jensen gives
$\mathbb E_\sigma|2\mu_\sigma-1|\ge|\mathbb E_\sigma(2\mu_\sigma-1)|=|2p-1|$, with
equality iff $\mu_\sigma$ is degenerate, i.e. $Q=\tfrac12$. A mean-preserving spread
of $\mu$ (larger $Q$) raises $\mathbb E|2\mu-1|$, giving monotonicity in $Q$. The two
endpoints are direct: at $p=\tfrac12$, $\mu_G=Q,\mu_B=1-Q$, so
$M=(2Q-1)/a$; as $p\to1$, $\mu_G,\mu_B\to1$. $\qquad\blacksquare$

---

## 3. Lemma 3 (Readership — closed form, with reading cost)

Reader $j$ reads iff the private value of information (VOI) of the forum to their own
For/Against choice weakly exceeds a reading cost $c_r\ge0$.

**Statement.** The per-voter VOI is a symmetric tent in $b_j$ on the swing band
$[\,1-2\mu_G,\ 1-2\mu_B\,]$, with peak height
$$
h(p,Q)\equiv 2p(1-p)(2Q-1)\quad\text{at } b_j=1-2p,
$$
and base half-width $\mu_G-\mu_B$. Hence the reading mass (readership) is
$$
\boxed{\ A(p;Q,c_r)=\frac{\mu_G-\mu_B}{a}\Big(1-\frac{c_r}{h(p,Q)}\Big)_{\!+}
=\frac{p(1-p)(2Q-1)}{a\,D_1 D_2}\Big(1-\frac{c_r}{2p(1-p)(2Q-1)}\Big)_{\!+}. }
$$
In particular $A$ is symmetric about $p=\tfrac12$, single-peaked there, and $=0$ at
$p\in\{0,1\}$; and $A(\tfrac12;Q,0)=(2Q-1)/a$.

**Proof.** Without reading, $j$ acts on the prior: *For* iff $b_j\ge t_0\equiv1-2p$.
After $\sigma$, *For* iff $b_j\ge t_\sigma\equiv1-2\mu_\sigma$. Since $\mu_B<p<\mu_G$,
$t_G<t_0<t_B$. Reading changes $j$'s action only for $b_j\in[t_G,t_B)$:

- $b_j\in[t_G,t_0)$: switches to *For* only when $\sigma=G$; gain
  $=D_1\big((2\mu_G-1)+b_j\big)\ge0$.
- $b_j\in[t_0,t_B)$: switches to *Against* only when $\sigma=B$; gain
  $=D_2\big(-(2\mu_B-1)-b_j\big)\ge0$.

Both pieces are linear in $b_j$, vanish at the band edges $t_G,t_B$, and meet at
$b_j=t_0$ where, using (I1), each equals $2D_1(\mu_G-p)=2p(1-p)(2Q-1)=h$. So VOI is
a symmetric tent of peak $h$ over a base of width $t_B-t_G=2(\mu_G-\mu_B)$. The mass
with VOI $\ge c_r$ is the tent's width above height $c_r$, namely
$2(\mu_G-\mu_B)(1-c_r/h)_+$; dividing by the taste support $2a$ and applying (I2)
gives the boxed expression. $\qquad\blacksquare$

**Corollary 3.1 (posting volume).** If contributors post iff a reward proportional
to readers reached covers an idiosyncratic cost, $c_i\le R\,A(p)$, then
$n(p)=F\big(R\,A(p)\big)$, which for $F$ near-linear at $0$ gives
$n(p)\propto A(p)\propto p(1-p)$ — peaked at contested proposals. Crucially the
reward is *per reader reached*, positive for a measure-zero poster, so posting is an
equilibrium without any pivotality.

**Corollary 3.2 (career concerns give the wrong sign — ruled out).** Suppose instead
contributors post to raise a reputation for ability $\alpha\in\{H,L\}$, $q_H>q_L$.
The expected reputational gain from posting signal $s$ is
$R\big(\mathbb E_\theta[\Pr(H\mid s,\theta)\mid s]-\gamma\big)=R\big(\Pr(H\mid s)-\gamma\big)$
by iterated expectations. At $p=\tfrac12$, $\Pr(g\mid H)=\tfrac12=\Pr(g\mid L)$, so
$\Pr(H\mid g)=\gamma$ and the gain is $0$; it is strictly positive as $p\to\{0,1\}$.
Thus reputation-driven posting is **V-shaped — minimized at $\tfrac12$**, implying
$\mathrm{Cov}(\text{posts},\text{margin})>0$, the opposite of the data. Reputation is
therefore rejected as the posting motive. $\qquad\blacksquare$

---

## 4. Proposition 1 (Negative posts–margin covariance — the paper's Prop 1, derived)

**Statement.** Draw proposals' priors from any distribution with nondegenerate
$d\equiv|p-\tfrac12|$. Under Corollary 3.1 and Lemma 2,
$$
\mathrm{Cov}\big(n(p),\,M(p)\big)<0.
$$

**Proof.** By Lemma 3, $A$ — hence $n=F(RA)$ — is a nonincreasing function
$\nu(d)$ of $d$ (symmetric about $\tfrac12$, single-peaked). By Lemma 2, the
conditional mean margin $\mathbb E[M\mid p]$ is a nondecreasing function $\rho(d)$ of
$d$. Since $n(p)$ is $p$-measurable, the law of total covariance gives
$\mathrm{Cov}(n,M)=\mathrm{Cov}\big(n,\mathbb E[M\mid p]\big)
=\mathrm{Cov}\big(\nu(d),\rho(d)\big)$. Chebyshev's association (sum) inequality: for
a nonincreasing $\nu$ and nondecreasing $\rho$ of the same random variable $d$, the
covariance is $\le0$, strict when both are nonconstant and $d$ nondegenerate.
$\qquad\blacksquare$

**Remark (why this is the honest ceiling on the data test).** Prop 1 pins a sign,
not a shape. Because $(1-M^2)$ and $-M$ are near-collinear over the observed margin
range, the structural locus and the linear reduced form are empirically
indistinguishable at $n=29$ ($R^2=0.114$ vs $0.111$). The model's *discriminating*
content is cross-equation (§5), not in this one covariance.

---

## 5. Proposition 2 (Welfare — exact forms, and a correction to the paper)

Let the collective payoff be the correctness of the governance decision (the object
that matters for a paper about decision quality).

**2a — Exact decision value (the tent).** With optimal use of the forum (follow
$\sigma$ only where it can flip the prior-optimal action, i.e. $p\in(1-Q,Q)$), the
value of the forum is
$$
W(p,Q)=\big(Q-\max\{p,1-p\}\big)\,\mathbf 1\{p\in(1-Q,Q)\},
$$
piecewise linear, peaked at $p=\tfrac12$ with $W(\tfrac12,Q)=Q-\tfrac12$, and $0$
outside the flip window. *Proof.* Inside the window both posteriors cross $\tfrac12$
($\mu_G>\tfrac12>\mu_B$), so following $\sigma$ is optimal and correct with prob
$Q$; outside, the signal never overturns the prior, so the value is $0$; the prior
baseline is $\max\{p,1-p\}$. $\qquad\blacksquare$

**2b — Exact belief-accuracy value (variance reduction).** The expected reduction in
squared belief error is, by (I1)–(I2) and $\mathbb E_\sigma[(\mu_\sigma-p)^2]=
D_1(\mu_G-p)^2+D_2(\mu_B-p)^2$,
$$
\mathrm{VR}(p,Q)=\frac{[p(1-p)(2Q-1)]^2}{D_1 D_2},
\qquad
\mathrm{VR}\xrightarrow[Q\to\frac12]{}16\,[p(1-p)]^2\big(Q-\tfrac12\big)^2.
$$

**Correction to the paper.** The current draft's welfare kernel
$4p(1-p)(q-\tfrac12)^2$ is **not** exactly either object: the decision value is the
*tent* (2a), and the belief-accuracy value carries $[p(1-p)]^2$, not $p(1-p)$ (2b).
The paper's monomial captures the right comparative statics (single-peak at
$\tfrac12$, increasing in signal quality) but does not drop out of a standard
welfare notion. **Recommendation:** replace it with 2a (for a decision-quality story)
or 2b (for a belief-accuracy story); both are exact and closed-form. This removes an
"asserted formula" the referee can flag, at no cost to the narrative.

---

## 6. What to build on (the actual prize)

The derivation throws off three things the current paper does *not* have. The third
is, I think, a genuine contribution.

**6.1 A new, sharp, testable prediction: AI dilutes the audience.** Model AI as
signal dilution, $2Q_{\text{eff}}-1=(1-\pi)(2Q-1)$ for AI share $\pi$. Then by
Lemma 3, readership is **linear in $(1-\pi)$**:
$A(p)\propto(1-\pi)$. This is a *distinct* prediction from the posts–margin story:
as AI content rises, **reads/views per proposal should fall** (and decouple from
contestedness). The forum scrape already stores a per-post `reads` field — this is
directly testable and is *not* in the paper.

*First look (exploratory, Aug 2026).* Using per-post `reads`: contested proposals do
draw more readers in **all four** cross-sectional cuts (corr $+0.18$ to $+0.28$,
pre and post) — the sign the model predicts — but none reach significance
($p=0.14$–$0.34$, $n=29/73$). The raw over-time drop (median $76\to52$ reads/post) is
confounded by post age (post-period posts have had less time to accrue reads) and is
*not* usable without an age control. Verdict: directionally consistent,
underpowered — same pattern as the rest of the empirics. A clean test needs an
age-adjusted read rate (reads per day since posting) or view-level data.

**6.2 Welfare upgrade.** Swap the heuristic monomial for the exact §5 form. Small,
safe, and closes a referee line.

### 6.3 ⭐ Proposition 3 (Endogenous forum unraveling — a market-for-lemons for governance)

Two ingredients are already derived: (i) readership $A$ falls in AI share $\pi$
(Lemma 3), $A=\kappa(1-\pi)$; (ii) posting reward $\propto$ readers reached
(Cor. 3.1). Close the loop by making $\pi$ *endogenous*. Genuine posters have
heterogeneous cost, giving an adoption curve $H(A)$ (mass of genuine posts,
increasing in audience); fluffers post AI content at near-zero cost, fixed supply
$Z_0$. Then $\pi=Z_0/(Z_0+H(A))$ and the audience is a fixed point of

$$
A \;=\; T(A)\;\equiv\;\kappa\,\frac{H(A)}{Z_0+H(A)}.
$$

**Statement.** (a) $A=0$ (total collapse, $\pi=1$) is an equilibrium for *every*
$Z_0$. (b) If genuine-poster adoption $H$ is **S-shaped** (convex near $0$: few
zero-cost genuine contributors), there is a threshold $Z_0^\*$ such that for
$Z_0<Z_0^\*$ the system is **bistable** — a healthy equilibrium ($A$ high, $\pi$
low) and the collapse coexist, separated by an unstable interior equilibrium — while
for $Z_0>Z_0^\*$ **only collapse survives**. (c) At $Z_0^\*$ the healthy and unstable
equilibria annihilate in a **saddle-node**: the audience jumps discontinuously to $0$
and $\pi$ to $1$. (d) Because $A=0$ is stable for all $Z_0$, the collapse is
**hysteretic** — once collapsed, *reducing* $Z_0$ does not restore the healthy forum;
recovery requires a coordinated jump, not merely undoing the shock.

**Proof sketch + numerical instance.** $H(0)=0\Rightarrow T(0)=0$, giving (a).
$T$ is increasing (composition of increasing maps) and inherits the S-shape of $H$,
so it crosses the $45^\circ$ line either once (at $0$) or three times; the middle
crossing has $T'>1$ (unstable), the outer two $T'<1$ (stable) — bistability, (b).
Raising $Z_0$ shifts $T$ down uniformly, sliding the unstable and healthy roots
together until they meet and vanish — a saddle-node, (c)–(d). With
$H(A)=A^3/(A^3+0.4^3)$, $\kappa=1$: the healthy equilibrium persists up to
$Z_0^\*\approx0.75$, at which point the forum sustains **up to $\pi^\*\approx0.62$ AI
content before tipping**, then collapses discontinuously to $\pi=1$. Verified by
root-scan. $\qquad\blacksquare$

**Why this matters.** AI writing does not merely add noise — by lowering the cost of
fluff (raising $Z_0$) it can push a forum *past* $Z_0^\*$ and **tip** it from the
healthy basin to irreversible collapse. This is a Gresham/Akerlof dynamic for DAO
governance and a genuine *second* theoretical contribution: it converts the paper's
finding from "AI correlates with weaker deliberation" into "AI can trigger a
discontinuous, hysteretic collapse of the deliberation mechanism," with fresh
comparative statics (the fluff-cost threshold, the maximal sustainable $\pi^\*$, and
irreversibility).

**Honest caveats.** (1) Multiplicity *requires* $H$ S-shaped — with concave adoption
the equilibrium is unique and the decline is smooth (no tipping). So this is a
*possibility* result (à la Diamond–Dybvig / Akerlof), conditional on a plausible but
unverified adoption shape. (2) It is a steady-state/representative-forum reduction of
the per-proposal model; the aggregation step needs to be written carefully. (3) It is
not yet disciplined by data — $Z_0^\*$ and $\pi^\*$ are illustrative. It earns its
place as *theory*, and should be presented as a mechanism, not a calibrated forecast.

---

*Caveats carried forward:* truthful posting is imposed (needs an off-path belief or
a reputational-cheap-talk cite); the unraveling result in §6.3 is a sketch with
derived ingredients, not yet a theorem; and the empirical over-identification is
currently underpowered (see `model_derivation_notes.md` §9).
