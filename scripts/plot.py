"""CSV -> figures for the report.

Reads results/raw/E{1,2,3}.csv and writes PNGs to results/figures/.
Each point is the mean of the repetitions; error bars are one standard deviation.
Labels are in Spanish (decimal comma) because the report is in Spanish.

Usage (no local Python needed):
  docker run --rm -v "$PWD":/repo -w /repo python:3.12-slim \
    bash -c "pip install -q matplotlib==3.9.2 && python scripts/plot.py"
"""

import csv
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, FixedLocator, MultipleLocator, NullLocator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
FIG = ROOT / "results" / "figures"
GIB = 2**30

# Palette (validated: blue/orange pass CVD and contrast checks on white).
BLUE, ORANGE = "#2a78d6", "#eb6834"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"  # status: always paired with a text label
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.figsize": (6.4, 3.8),
    "figure.dpi": 200,
    "font.size": 10,
    "axes.edgecolor": INK_2,
    "axes.labelcolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "legend.frameon": False,
    "lines.linewidth": 2,
    "lines.markersize": 6,
    "savefig.bbox": "tight",
})


def num(x, decimals=1):
    """Spanish number format: thousands with '.', decimals with ','."""
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_axis(decimals=0):
    return FuncFormatter(lambda v, _: num(v, decimals))


def load(name):
    with open(RAW / f"{name}.csv") as f:
        return list(csv.DictReader(f))


def group(rows, key):
    """Group rows by `key`, keeping first-seen order."""
    out = {}
    for r in rows:
        out.setdefault(r[key], []).append(r)
    return out


def mean_sd(rows, col, scale=1.0):
    vals = [float(r[col]) / scale for r in rows if r[col]]
    if not vals:
        return None, None
    return st.mean(vals), (st.stdev(vals) if len(vals) > 1 else 0.0)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name)
    plt.close(fig)
    print(f"  {FIG.relative_to(ROOT) / name}")


def compact(v):
    """5172 -> '5,2 k', 1005072 -> '1,0 M'."""
    if v >= 1e6:
        return f"{num(v / 1e6)} M"
    return f"{num(v / 1e3, 1 if v < 1e5 else 0)} k"


def steps_axis(ax, steps):
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(steps))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    ax.set_xlabel("steps de ejecución (escala log, incluye bootloader)")
    ax.margins(x=0.08)


# --- E1: complexity -----------------------------------------------------------

def e1():
    g = group(load("E1"), "n")
    steps = [int(rows[0]["steps"]) for rows in g.values()]
    ns = list(g)

    # 1. Proving time vs steps.
    m, s = zip(*(mean_sd(r, "t_prove") for r in g.values()))
    fig, ax = plt.subplots()
    ax.errorbar(steps, m, yerr=s, color=BLUE, marker="o", capsize=3)
    for x, y, n in zip(steps, m, ns):
        ax.annotate(f"n = {num(int(n), 0)}\n{num(y)} s", (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8, color=INK_2)
    steps_axis(ax, steps)
    ax.set_ylim(0, max(m) * 1.35)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.set_major_formatter(fmt_axis())
    ax.set_ylabel("tiempo de prueba (s)")
    ax.set_title("E1. Tiempo de generación de la prueba según la complejidad")
    save(fig, "e1_prove_time.png")

    # 2. Verify vs re-execute.
    me, se = zip(*(mean_sd(r, "t_execute") for r in g.values()))
    mv, sv = zip(*(mean_sd(r, "t_verify") for r in g.values()))
    fig, ax = plt.subplots()
    ax.errorbar(steps, me, yerr=se, color=ORANGE, marker="o", capsize=3, label="re-ejecutar (scarb execute)")
    ax.errorbar(steps, mv, yerr=sv, color=BLUE, marker="s", capsize=3, label="verificar la prueba (scarb verify)")
    ax.annotate("re-ejecutar", (steps[-1], me[-1]), textcoords="offset points", xytext=(-6, 6),
                ha="right", fontsize=8, color=INK_2)
    ax.annotate("verificar", (steps[-1], mv[-1]), textcoords="offset points", xytext=(-6, 6),
                ha="right", fontsize=8, color=INK_2)
    steps_axis(ax, steps)
    ax.set_ylim(0, max(me) * 1.2)
    ax.yaxis.set_major_formatter(fmt_axis(1))
    ax.set_ylabel("tiempo (s)")
    ax.set_title("E1. Verificar la prueba vs. re-ejecutar el programa")
    ax.legend(loc="upper left")
    save(fig, "e1_verify_vs_execute.png")

    # 3. Peak memory vs steps.
    mm, sm = zip(*(mean_sd(r, "mem_peak", GIB) for r in g.values()))
    fig, ax = plt.subplots()
    ax.errorbar(steps, mm, yerr=sm, color=BLUE, marker="o", capsize=3)
    for x, y in zip(steps, mm):
        ax.annotate(f"{num(y)} GiB", (x, y), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8, color=INK_2)
    steps_axis(ax, steps)
    ax.set_ylim(0, max(mm) * 1.2)
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.yaxis.set_major_formatter(fmt_axis())
    ax.set_ylabel("memoria pico (GiB)")
    ax.set_title("E1. Memoria pico del contenedor según la complejidad")
    save(fig, "e1_memory_peak.png")


# --- E2: CPU limit ------------------------------------------------------------

def e2():
    g = group(load("E2"), "cpu_max")
    cpus = [int(k.split("/")[0]) / int(k.split("/")[1]) for k in g]
    m, s = zip(*(mean_sd(r, "t_prove") for r in g.values()))

    # Ideal scaling anchored at 1 CPU: t(c) = t(1) / c.
    t1 = m[cpus.index(1.0)]
    ideal = [t1 / c for c in cpus]

    fig, ax = plt.subplots()
    ax.plot(cpus, ideal, color=INK_2, linestyle="--", linewidth=1.2, label="escalado ideal (t(1) / cpus)")
    ax.errorbar(cpus, m, yerr=s, color=BLUE, marker="o", capsize=3, label="medido")
    for x, y in zip(cpus, m):
        ax.annotate(f"{num(y)} s", (x, y), textcoords="offset points", xytext=(8, 4),
                    fontsize=8, color=INK_2)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(FixedLocator(sorted(cpus)))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(fmt_axis(1))
    ax.yaxis.set_major_locator(FixedLocator([20, 40, 80, 160, 320]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(fmt_axis())
    ax.set_ylim(30, 360)
    ax.margins(x=0.1)
    ax.set_xlabel("límite de CPU, --cpus (escala log)")
    ax.set_ylabel("tiempo de prueba (s, escala log)")
    ax.set_title("E2. Tiempo de prueba según el límite de CPU (n = 10.000)")
    ax.legend(loc="upper right")
    save(fig, "e2_cpu_limit.png")


# --- E3: memory limit ---------------------------------------------------------

def e3():
    g = group(load("E3"), "mem_max")
    limits = [int(k) / GIB for k in g]
    peaks = [mean_sd(r, "mem_peak", GIB)[0] for r in g.values()]
    oom = [any(r["oom_kill"] != "0" for r in rows) for rows in g.values()]

    labels = [num(l, 1 if l % 1 else 0) for l in limits]
    xs = range(len(limits))
    fig, ax = plt.subplots()
    for x, peak, lim, dead in zip(xs, peaks, limits, oom):
        ax.bar(x, peak, width=0.6, color=CRITICAL if dead else GOOD,
               hatch="///" if dead else None, edgecolor="white", linewidth=0)
        ax.hlines(lim, x - 0.38, x + 0.38, color=INK, linewidth=1.5)
        status = "OOM (exit 137)" if dead else "OK, verifica"
        ax.annotate(status, (x, lim), textcoords="offset points", xytext=(0, 5),
                    ha="center", fontsize=8, color=INK)
    ax.set_xticks(list(xs), labels)
    ax.set_xlabel("límite de memoria, --memory = --memory-swap (GiB)")
    ax.set_ylabel("memoria pico (GiB)")
    ax.set_ylim(0, max(limits) * 1.12)
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.yaxis.set_major_formatter(fmt_axis())
    ax.set_title("E3. Memoria pico y resultado según el límite de memoria (n = 10.000)")
    ax.plot([], [], color=INK, linewidth=1.5, label="límite del cgroup")
    ax.legend(loc="upper right", bbox_to_anchor=(1, 1.0))
    save(fig, "e3_memory_limit.png")


if __name__ == "__main__":
    print("Figuras:")
    e1()
    e2()
    e3()
