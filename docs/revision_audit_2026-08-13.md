# Revision Audit — verification of the "problems introduced by the revision" list

*Victor, Aug 13 2026. Each flagged item checked against the current `main_flat.tex`,
the table/figure files, and the data. Verdict + exact refs + recommended action.
One clean fix (§6.4) already landed on `main` (`08816c2`); everything here needs an
author decision or a re-run, so it's on this branch for review rather than committed.*

## Serious

### 1. Vesting-cliff placebo (Table `tab:concentration_control`) — REAL, sample mismatch
- **What I found.** The table (`output/tables/rob02_concentration_control.tex`) has
  subsamples 20+58 and 26+53 = **157 observations** (46 pre / 111 post) and a footer
  full-sample of **pre $r=-0.391$, post $r=-0.050$, Chow $F=8.22$**. The section
  claims "**for each of the 102 matched proposals**." 157 ≠ 102, and the pre/post
  split (46/111) ≠ the paper's 29/73.
- **Not a stale render.** Re-running `rob02_concentration_control.py` today
  reproduces the 157-obs numbers exactly. So the script uses a **different sample
  definition** than the 102-matched main analysis (it pulls proposals with per-voter
  VP data, ~157, not the 102 matched pairs).
- **Action (needs decision + re-run).** Either (a) restrict `rob02` to the 102
  matched sample so the placebo matches the main test (numbers will change — review),
  or (b) fix the prose to state the placebo's actual sample and why it differs. As-is,
  the table silently contradicts the paper's headline sample.

### 2. Cross-DAO evidence — REAL, load-bearing but inconsistent
- **Three different DAO sets** appear: {Aave, ENS, Compound, Gitcoin, Optimism}
  (§4 identification, l.1024), {Aave, Optimism, Uniswap, MakerDAO} (figure, l.3217),
  {Aave, MakerDAO, Optimism, Curve} (conclusion, l.2309).
- **Intro/§4 lean on it** as "the strongest cross-sectional evidence against
  Arbitrum-specific confounders," but the **conclusion disclaims** a "systematic
  cross-DAO study" as future work (l.2310). The figure the text points to should be
  checked against its caption (the recurring caption-mismatch issue).
- **Substantive:** a participation *decline* across five DeFi DAOs over 2023–24 is
  weakly diagnostic — a crypto bear market produces the same. It is **not** a
  cross-DAO test of the posts–margin break. Either downgrade the claim to match the
  conclusion, or run the actual posts–margin break on the other DAOs.

## Real, fixable

### 3. Conflicting pre-period post counts — REAL, affects the headline number
- Calibration §5.6 (l.1145): $\bar n = 44.2$ human posts/proposal (1,283 over 29),
  and "**454** unique members" (l.1164).
- Mechanism §6–§7: human posts on matched threads "**from 2,650 to 5,898**"
  (l.1639, 1708) = 91.4/proposal, and "**740** distinct authors" (l.1363, 1534).
- Two internally-consistent clusters (740×3.6≈2,650). **The 858-word surplus scales
  linearly in $\bar n$, so it roughly doubles under 91.4.** Likely different
  universes (the 29 pre-period matched proposals vs all matched threads), but the
  paper must reconcile them and state which the calibration uses. **Decision needed.**

### 4. Dilution benchmark arithmetic — REAL (and it helps us)
- l.1644–46: "122% post increase would predict ~55% decline in reads/post; observed
  is only 36%." The 122% is **raw totals over unequal windows** (14 pre-months vs
  ~25 post-months). Per month it's ~189→236 ≈ **25%**, predicting ~20% decline — so
  the observed **36% *exceeds*** the dilution benchmark rather than falling short.
- **Action:** recompute on a per-month basis. Strengthens the argument, but the
  current calc is wrong and a referee will redo it.

### 5. Reads-per-post age confound — PARTLY addressed
- Discourse `reads` accumulate with post age: an old post has had years to accrue
  reads, a recent one months, so a monotone calendar-time decline is partly
  mechanical. The paper argues *timing* (sharp drop Nov 2023–Feb 2024, then stable at
  45–70; l.1636–55, 1923), which does cut against a pure age artifact — but there is
  **no fixed-window normalization**. **Action:** add a reads-within-N-days-of-posting
  series (or age-adjusted), and make the argument explicit.

## Minor / mixed

- **6a. Fig (reads) caption "292 forum threads" vs 102 matched pairs** (l.1671 vs
  §3.4). Possibly legitimate (a broader thread match for the reads figure vs the 102
  proposals-with-margins), but unexplained. **Confirm it's intentional and say so**,
  or reconcile.
- **6b. Matching thresholds 0.55 vs 0.65** (l.788 vs l.798) — **NOT a contradiction.**
  It's two stages: 0.55 to generate candidates, 0.65 enforced as the final minimum
  (data confirms every match ≥ 0.65). Optional one-clause clarification.
- **6c. §6.4 "all six candidate dates… post near zero"** — REAL; **FIXED on `main`
  (`08816c2`)** to match Table 3 (Claude 2 post $-0.22$, DeepSeek R1 $-0.38$).
- **6d. Table 2 `**` vs Table 7 col (1) `*` on the identical coefficient/SE** —
  reported by the audit; **not independently confirmed** (two separate tables). Worth
  a direct check when reconciling tables.
- **6e. Participation figure caption "concentration of voting power *increases*…
  consolidates among a smaller number"** (l.3233) contradicts the paper's dispersion
  thesis (rising Nakamoto = *more dispersed*, l.497; abstract's "inconsistent with
  power capture"). REAL directional conflict. **Verify the actual concentration/
  Nakamoto trend in the data and fix whichever caption is wrong.**

## Bottom line
The two "serious" flags (1 and 2) are real and would damage credibility if a referee
hit them; 3 moves a headline number; 4 is a wrong-but-self-helping calculation; 5 is
a genuine methodological gap. 6b is a false alarm; 6c is already fixed. None except
6c were safe to auto-commit — they need a re-run or a which-number/which-claim call.
