"""bioscout.plot.activation_dynamics - effect of CEINMS c1, c2 and shape factor A
on excitation -> activation (Lloyd & Besier 2003).

    u(t) = alpha*e(t-d) - beta1*u(t-1) - beta2*u(t-2)
    beta1 = c1 + c2,  beta2 = c1*c2,  alpha = 1 + beta1 + beta2
    a(t) = (exp(A*u) - 1) / (exp(A) - 1)          (A -> 0: linear)

    python -m bioscout.plot.activation_dynamics [out.png]
"""
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

DT = 0.001  # s (CEINMS runs the filter at ~1 kHz)


def neural_activation(e, c1, c2, d=0):
    b1, b2 = c1 + c2, c1 * c2
    al = 1 + b1 + b2
    u = np.zeros_like(e)
    for t in range(len(e)):
        u[t] = (al * e[t - d] if t >= d else 0) - b1 * (u[t - 1] if t > 0 else 0) \
               - b2 * (u[t - 2] if t > 1 else 0)
    return u


def muscle_activation(u, A):
    return u if abs(A) < 1e-6 else (np.exp(A * u) - 1) / (np.exp(A) - 1)


def excitation(t):
    """0.3 s pulse to 1, then a 0.4 s ramp 0 -> 0.5 -> 0."""
    e = np.where((t >= 0.1) & (t < 0.4), 1.0, 0.0)
    r = (t >= 0.6) & (t < 1.0)
    e[r] = 0.5 * (1 - np.abs((t[r] - 0.8) / 0.2))
    return e


def plot(out=None, cs=(-0.9, -0.7, -0.5, -0.3, -0.1, 0.0), shapes=(0, -0.5, -1.1, -2, -3)):
    t = np.arange(0, 1.2, DT)
    e = excitation(t)
    cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))

    a = ax[0, 0]  # c1 = c2 swept
    a.plot(t, e, "k--", lw=1, label="excitation")
    for i, c in enumerate(cs):
        a.plot(t, neural_activation(e, c, c), color=cmap(i / len(cs)), label=f"c1 = c2 = {c}")
    a.set_title("(a) c1 = c2: more negative = slower, smoother")

    a = ax[0, 1]  # c1 fixed, c2 swept
    a.plot(t, e, "k--", lw=1, label="excitation")
    for i, c in enumerate(cs):
        a.plot(t, neural_activation(e, -0.5, c), color=cmap(i / len(cs)), label=f"c1 = -0.5, c2 = {c}")
    a.set_title("(b) c1 = -0.5, c2 swept")

    a = ax[1, 0]  # rise time map
    grid = np.linspace(-0.95, 0.0, 20)
    step = np.where(t >= 0.1, 1.0, 0.0)
    T = np.full((len(grid), len(grid)), np.nan)
    for i, c1 in enumerate(grid):
        for j, c2 in enumerate(grid):
            u = neural_activation(step, c1, c2)
            k = np.argmax(u >= 0.9)
            T[i, j] = (t[k] - 0.1) * 1000 if u[k] >= 0.9 else np.nan
    im = a.pcolormesh(grid, grid, T, shading="auto", cmap="magma_r")
    fig.colorbar(im, ax=a, label="time to 90 % of a step (ms)")
    a.set_xlabel("c2"); a.set_ylabel("c1")
    a.set_title("(c) response time vs c1, c2 (poles at -c1, -c2)")

    a = ax[1, 1]  # shape factor
    u = np.linspace(0, 1, 200)
    for i, A in enumerate(shapes):
        a.plot(u, muscle_activation(u, A), color=cmap(i / len(shapes)), label=f"A = {A}")
    a.plot(u, u, "k:", lw=0.8)
    a.set_xlabel("neural activation u"); a.set_ylabel("muscle activation a")
    a.set_title("(d) shape factor A: negative lifts low excitations")

    for a in ax[0]:
        a.set_xlabel("time (s)"); a.set_ylabel("excitation / neural activation")
    for a in ax.flat:
        if a is not ax[1, 0]:
            a.legend(fontsize=7); a.grid(alpha=0.3)
    fig.suptitle("CEINMS excitation-activation dynamics (Lloyd & Besier 2003), dt = 1 ms, d = 0")
    fig.tight_layout()
    if out:
        fig.savefig(out, dpi=150); plt.close(fig); print("saved", out)
    return fig


if __name__ == "__main__":
    matplotlib.use("Agg")
    plot(sys.argv[1] if len(sys.argv) > 1 else "activation_dynamics.png")
