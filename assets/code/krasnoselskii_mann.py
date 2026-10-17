"""Picard vs. Krasnoselskii-Mann iterations for a rotation of the plane.

T rotates R^2 by theta about the origin: nonexpansive, unique fixed point 0.
Picard x_{n+1} = T x_n never converges; the averaged (Krasnoselskii-Mann) iteration
x_{n+1} = (1 - lam) x_n + lam T x_n converges to 0 for every lam in (0, 1).

    python krasnoselskii_mann.py --theta 70 --lam 0.5 --iters 40 --plot
"""
import argparse
import numpy as np


def rotation(theta_deg):
    t = np.deg2rad(theta_deg)
    return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])


def run(theta=70.0, lam=0.5, iters=40, x0=(0.9, 0.5)):
    R = rotation(theta)
    pic = [np.asarray(x0, float)]
    km = [np.asarray(x0, float)]
    for _ in range(iters):
        pic.append(R @ pic[-1])
        km.append((1 - lam) * km[-1] + lam * (R @ km[-1]))
    return np.array(pic), np.array(km)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theta", type=float, default=70.0)
    ap.add_argument("--lam", type=float, default=0.5)
    ap.add_argument("--iters", type=int, default=40)
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    pic, km = run(a.theta, a.lam, a.iters)
    print(f"{'n':>4} {'Picard |x_n|':>14} {'KM |x_n|':>14}")
    for n in range(0, a.iters + 1, max(1, a.iters // 10)):
        print(f"{n:>4} {np.linalg.norm(pic[n]):>14.6f} {np.linalg.norm(km[n]):>14.3e}")
    rate = abs((1 - a.lam) + a.lam * np.exp(1j * np.deg2rad(a.theta)))
    print(f"Theoretical KM contraction factor per step: {rate:.4f}")
    if a.plot:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.plot(*pic.T, "o-", color="0.6", ms=3, lw=1, label="Picard")
        ax.plot(*km.T, "o-", color="#2d3e8c", ms=3, lw=1.5, label="Krasnoselskii-Mann")
        ax.plot(0, 0, "o", color="#a6741f", ms=8, label="fixed point")
        ax.set_aspect("equal"); ax.legend(); plt.tight_layout(); plt.show()
