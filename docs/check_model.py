"""Numerical verification of every result in docs/model_rebuild.tex.

Unified two-tier model:
  - state theta in {G,B}, prior p
  - voters: taste b ~ U[-a,a]; may read ONE randomly sampled post at cost c_r
  - sampled post: human w.p. 1-pi (reveals signal of precision q), AI w.p. pi (50/50)
  - effective precision Q = 1/2 + (1-pi)(q-1/2)
  - non-readers vote on prior; readers vote on posterior after their sampled message
"""
import numpy as np

def post(p, Q):
    D1 = p*Q + (1-p)*(1-Q)
    D2 = p*(1-Q) + (1-p)*Q
    muG = p*Q/D1
    muB = p*(1-Q)/D2
    return D1, D2, muG, muB

def voi(b, p, Q):
    D1, D2, muG, muB = post(p, Q)
    U0 = np.maximum(2*p-1+b, 0.0)
    U1 = D1*np.maximum(2*muG-1+b, 0.0) + D2*np.maximum(2*muB-1+b, 0.0)
    return U1 - U0

def numeric_margins(p, Q, a, cr, nb=4_000_001):
    """Direct integration over tastes; returns (mG, mB, A)."""
    b = np.linspace(-a, a, nb)
    D1, D2, muG, muB = post(p, Q)
    read = voi(b, p, Q) >= cr
    A = read.mean()
    # vote-for probability conditional on theta
    prior_for = (2*p-1+b >= 0)
    forG_read = Q*(2*muG-1+b >= 0) + (1-Q)*(2*muB-1+b >= 0)
    forB_read = (1-Q)*(2*muG-1+b >= 0) + Q*(2*muB-1+b >= 0)
    PhiG = np.where(read, forG_read, prior_for).mean()
    PhiB = np.where(read, forB_read, prior_for).mean()
    return 2*PhiG-1, 2*PhiB-1, A

def formula_margins(p, Q, a, cr):
    D1, D2, muG, muB = post(p, Q)
    D = D1*D2
    x = p*(1-p)
    h = 2*x*(2*Q-1)                      # peak VOI (indifferent voter b0 = 1-2p)
    if h <= cr:                          # no readers: prior voting
        return (2*p-1)/a, (2*p-1)/a, 0.0
    A = (2*x*(2*Q-1) - cr) / (2*a*D)
    mG = (Q*(1-Q)*(2*p-1) + (2*Q-1)**2*x - cr*(1-p)*(2*Q-1)) / (a*D)
    mB = (Q*(1-Q)*(2*p-1) - (2*Q-1)**2*x + cr*p*(2*Q-1)) / (a*D)
    return mG, mB, A

def EM(p, Q, a, cr):
    mG, mB, _ = formula_margins(p, Q, a, cr)
    return p*abs(mG) + (1-p)*abs(mB)

def A_formula(p, Q, a, cr):
    return formula_margins(p, Q, a, cr)[2]

# ---------- CHECK 1: closed forms vs direct integration ----------
print("CHECK 1: margin & readership closed forms vs numeric integration")
rng = np.random.default_rng(0)
worst = 0.0
for _ in range(300):
    p = rng.uniform(0.02, 0.98)
    Q = rng.uniform(0.505, 0.99)
    a = rng.uniform(1.0, 3.0)
    x = p*(1-p); h = 2*x*(2*Q-1)
    cr = rng.uniform(0, 1.3*h)   # include dead-zone cases
    mGn, mBn, An = numeric_margins(p, Q, a, cr)
    mGf, mBf, Af = formula_margins(p, Q, a, cr)
    err = max(abs(mGn-mGf), abs(mBn-mBf), abs(An-Af))
    worst = max(worst, err)
print(f"  max abs error over 300 random draws: {worst:.2e}  (grid step ~ {2*3/4e6:.1e})")
assert worst < 5e-6, "closed forms FAIL"
print("  PASS")

# ---------- CHECK 2: E[M|p] strictly increasing in d=|p-1/2| ----------
print("CHECK 2: expected margin monotone increasing in |p - 1/2|")
bad = 0
for Q in [0.51, 0.6, 0.7, 0.8, 0.86, 0.95, 0.999]:
    for a in [1.0, 1.5, 3.0]:
        hmax = 0.5*(2*Q-1)
        for cr in [0.0, 0.1*hmax, 0.5*hmax, 0.9*hmax, 1.5*hmax]:
            ps = np.linspace(0.5, 0.9999, 20000)
            vals = np.array([EM(p, Q, a, cr) for p in ps])
            d = np.diff(vals)
            if (d < -1e-12).any():
                bad += 1
                print(f"  VIOLATION Q={Q} a={a} cr={cr}: min diff {d.min():.2e} at p={ps[np.argmin(d)]:.4f}")
print(f"  violations: {bad}")
assert bad == 0
print("  PASS")

# ---------- CHECK 3: A(p) single-peaked / increasing in x; n-M covariance < 0 ----------
print("CHECK 3: readership increasing in p(1-p); Cov(posts, margin) < 0")
bad = 0
for Q in [0.55, 0.7, 0.9]:
    for cr in [0.0, 0.02, 0.1]:
        ps = np.linspace(0.5, 0.999, 5000)
        Av = np.array([A_formula(p, Q, 1.5, cr) for p in ps])
        dd = np.diff(Av)
        if (dd > 1e-12).any():   # should be decreasing in p on [1/2,1)
            bad += 1
assert bad == 0
# covariance under p ~ Beta(2,2), theta drawn, margin realized
rng = np.random.default_rng(1)
Q, a, cr, R, f0 = 0.75, 1.5, 0.02, 1.0, 1.0
ps = rng.beta(2, 2, 200000)
Av = np.array([A_formula(p, Q, a, cr) for p in ps])
n = f0*R*Av   # F near-linear
th = rng.uniform(0, 1, ps.size) < ps
Ms = np.empty(ps.size)
for i, p in enumerate(ps):
    mG, mB, _ = formula_margins(p, Q, a, cr)
    Ms[i] = abs(mG) if th[i] else abs(mB)
cov = np.cov(n, Ms)[0, 1]
print(f"  Cov(posts, realized margin) = {cov:.5f} (should be < 0)")
assert cov < 0
print("  PASS")

# ---------- CHECK 4: welfare window = full aggregation inside, prior outside ----------
print("CHECK 4: decision correct iff mB<0 (p>1/2 branch); window inside active region")
ok = True
for Q in [0.6, 0.8, 0.95]:
    for cr in [0.0, 0.05]:
        for p in np.linspace(0.5, 0.99, 200):
            mG, mB, A = formula_margins(p, Q, 1.2, cr)
            if A > 0 and not (mG > -1e-12):
                ok = False; print("  mG<0 in active region!", p, Q, cr)
            if mB < 0 and A == 0:
                ok = False; print("  window outside active region!", p, Q, cr)
print("  PASS" if ok else "  FAIL")
assert ok

# ---------- CHECK 5: endogenous tipping (Prop on z*, jump, hysteresis) ----------
print("CHECK 5: endogenous contamination fixed point")
q, a, cr, R, cbar, x = 0.75, 1.2, 0.02, 1.0, 0.25, 0.25   # p = 1/2 forum
IH = 2*x*(2*q-1)
pibar = 1 - cr/IH
def F(y): return np.clip(y/cbar, 0, 1)          # uniform posting costs on [0, cbar]
def T(A, z):
    nn = F(R*A)
    if z == 0 and nn == 0: return 0.0
    pi = z/(z+nn) if (z+nn) > 0 else 1.0
    Qe = 0.5 + (1-pi)*(q-0.5)
    D1, D2, _, _ = post(0.5, Qe)
    num = 2*x*(2*Qe-1) - cr
    return max(num, 0.0)/(2*a*D1*D2)
def largest_fp(z, Agrid):
    Ts = np.array([T(A, z) for A in Agrid])
    sign = Ts - Agrid
    fps = [0.0]
    for i in range(len(Agrid)-1):
        if sign[i] >= 0 and sign[i+1] < 0:
            lo, hi = Agrid[i], Agrid[i+1]
            for _ in range(60):
                mid = 0.5*(lo+hi)
                if T(mid, z) - mid >= 0: lo = mid
                else: hi = mid
            fps.append(0.5*(lo+hi))
    return max(fps)
Agrid = np.linspace(1e-9, 1.2/a, 20001)
zs = np.linspace(1e-6, 0.4, 4001)
health = np.array([largest_fp(z, Agrid) for z in zs])
zstar_i = np.argmax(health < 1e-6)
zstar = zs[zstar_i-1]
Ajump = health[zstar_i-1]
npost = F(R*Ajump); pi_pre = zstar/(zstar+npost)
print(f"  pibar (reading threshold) = {pibar:.3f}")
print(f"  z* ~ {zstar:.4f}; healthy A just before collapse = {Ajump:.4f} (jump size, discontinuous)")
print(f"  realized AI share at healthy eq just before collapse: pi = {pi_pre:.3f}  (< pibar: {pi_pre < pibar})")
assert Ajump > 0.005 and pi_pre < pibar
# T should be identically 0 near A=0 for z>0 (dead zone from c_r)
z0 = 0.05
Az = None
for A in np.linspace(1e-9, 0.5, 50001):
    if T(A, z0) > 0: Az = A; break
print(f"  dead zone at z={z0}: T(A)=0 for A < {Az:.4f} (> 0, so collapse locally absorbing)")
assert Az > 1e-4
# hysteresis: iterate best response from collapsed state after lowering z
A = 0.0
for _ in range(200): A = T(A, 0.01)
print(f"  after collapse, lower z to 0.01 and iterate: A -> {A:.4f} (stays 0: hysteresis)")
assert A == 0.0
# and from healthy start at same z:
A = 1.0/a
for _ in range(500): A = T(A, 0.01)
print(f"  same z=0.01 from healthy start: A -> {A:.4f} (healthy eq exists: bistability)")
assert A > 0.01
print("  PASS")

# ---------- CHECK 6: career concerns give wrong sign for ANY increasing phi ----------
print("CHECK 6: career-concerns posting V-shaped (min at p=1/2) for linear & convex & concave phi")
qH, qL, gam = 0.85, 0.6, 0.4
qbar = gam*qH + (1-gam)*qL
r_plus = gam*qH/(gam*qH + (1-gam)*qL)                    # rep if vindicated (p-invariant)
r_minus = gam*(1-qH)/(gam*(1-qH) + (1-gam)*(1-qL))       # rep if wrong (p-invariant)
def mass(p, phi, cbar=0.05):
    # Pr(signal) and vindication prob per signal, for an average-type contributor
    Pg = p*qbar + (1-p)*(1-qbar)
    Pright_g = p*qbar/Pg                    # Pr(theta=G|g)
    Pb = 1-Pg
    Pright_b = (1-p)*qbar/Pb
    out = 0.0
    for Ps, Pr_ in [(Pg, Pright_g), (Pb, Pright_b)]:
        gain = Pr_*phi(r_plus) + (1-Pr_)*phi(r_minus) - phi(gam)
        out += Ps*np.clip(gain/cbar, 0, 1)
    return out
for name, phi in [("linear", lambda r: r), ("convex", lambda r: r**3),
                  ("concave", lambda r: np.sqrt(r))]:
    ps = np.linspace(0.01, 0.99, 99)
    ms = np.array([mass(p, phi) for p in ps])
    i_min = np.argmin(ms)
    print(f"  phi {name:8s}: mass(1/2)={mass(0.5,phi):.4f}  mass(0.95)={mass(0.95,phi):.4f}  "
          f"argmin p={ps[i_min]:.2f}  (V-shape: {ms[49] <= ms[0] and ms[49] <= ms[-1]})")
    assert mass(0.5, phi) < mass(0.95, phi)
print("  PASS")

# ---------- CHECK 7: E[M|p] responses to Q (AI dilution compresses contested margins) ----------
print("CHECK 7: margin at p=1/2 rises with Q; floor |2p-1|/a binds for consensus p")
for Q in [0.55, 0.75, 0.95]:
    print(f"   Q={Q}: E[M|.5]={EM(0.5,Q,1.2,0.0):.4f}  E[M|.9]={EM(0.9,Q,1.2,0.0):.4f}  floor(.9)={0.8/1.2:.4f}")
print("done — all checks passed")
