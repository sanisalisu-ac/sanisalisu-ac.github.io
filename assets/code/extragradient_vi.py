"""Projected gradient vs. extragradient (Korpelevich) for a monotone variational inequality.

Find x* in C = [-1, 1]^2 with <F(x*), y - x*> >= 0 for all y in C, where
F(x) = M x + q, M = [[eps, 1], [-1, eps]] (monotone, Lipschitz with L = sqrt(1 + eps^2)).
q is chosen so that x* = (0.3, -0.2) lies inside C.

    python extragradient_vi.py --eps 0 --tau 0.3 --iters 80 --plot
"""
import argparse
import numpy as np


def proj_box(x, lo=-1.0, hi=1.0):
    return np.clip(x, lo, hi)


def run(eps=0.0, tau=0.3, iters=80, x0=(-0.8, 0.7), xstar=(0.3, -0.2)):
    M = np.array([[eps, 1.0], [-1.0, eps]])
    xs = np.asarray(xstar, float)
    q = -M @ xs
    F = lambda x: M @ x + q
    pg, eg = [np.asarray(x0, float)], [np.asarray(x0, float)]
    for _ in range(iters):
        x = pg[-1]
        pg.append(proj_box(x - tau * F(x)))
        x = eg[-1]
        y = proj_box(x - tau * F(x))           # trial (prediction) step
        eg.append(proj_box(x - tau * F(y)))    # correction with F evaluated at y
    return np.array(pg), np.array(eg), xs


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eps", type=float, default=0.0)
    ap.add_argument("--tau", type=float, default=0.3)
    ap.add_argument("--iters", type=int, default=80)
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    L = np.hypot(1.0, a.eps)
    if a.tau >= 1 / L:
        print(f"warning: tau = {a.tau} >= 1/L = {1 / L:.3f}; convergence of extragradient is not guaranteed")
    pg, eg, xs = run(a.eps, a.tau, a.iters)
    print(f"{'n':>4} {'proj. gradient':>16} {'extragradient':>16}")
    for n in range(0, a.iters + 1, max(1, a.iters // 10)):
        print(f"{n:>4} {np.linalg.norm(pg[n] - xs):>16.6f} {np.linalg.norm(eg[n] - xs):>16.3e}")
    if a.plot:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.add_patch(plt.Rectangle((-1, -1), 2, 2, fill=False, ls="--", color="0.4"))
        ax.plot(*pg.T, "o-", color="0.6", ms=3, lw=1, label="projected gradient")
        ax.plot(*eg.T, "o-", color="#2d3e8c", ms=3, lw=1.5, label="extragradient")
        ax.plot(*xs, "o", color="#a6741f", ms=8, label="solution")
        ax.set_aspect("equal"); ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.25, 1.25)
        ax.legend(); plt.tight_layout(); plt.show()
