"""Draws the two report diagrams: OS layers and experiment architecture.

Usage (from the repo root, no local Python needed):
  docker run --rm -v "$PWD":/repo -w /repo python:3.12-slim \
    bash -c "pip install -q matplotlib==3.9.2 && python informe/figuras/diagramas.py"
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent
INK, INK_2 = "#0b0b0b", "#52514e"
BLUE, BLUE_BG = "#2a78d6", "#e8f1fc"
GRAY_BG, LINE = "#f4f3f0", "#c9c7c0"

plt.rcParams.update({"font.size": 9, "figure.dpi": 200, "savefig.bbox": "tight"})


def box(ax, x, y, w, h, title, body="", fill=GRAY_BG, edge=LINE, title_color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor=fill, edgecolor=edge, linewidth=1))
    ax.text(x + 0.15, y + h - 0.18, title, ha="left", va="top", fontsize=9.5,
            fontweight="bold", color=title_color)
    if body:
        ax.text(x + 0.15, y + h - 0.5, body, ha="left", va="top", fontsize=8.3,
                color=INK_2, linespacing=1.45)


def arrow(ax, a, b, label="", color=INK_2):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11,
                                 color=color, linewidth=1.2))
    if label:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, label, fontsize=7.8,
                color=INK_2, ha="center", va="bottom")


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 1.6)
    ax.set_ylim(0, h * 1.6)
    ax.axis("off")
    return fig, ax


def layers():
    fig, ax = canvas(8, 6.0)
    W, x = 10.0, 0.3
    rows = [
        ("Aplicaciones (espacio de usuario, dentro del contenedor)",
         "scarb execute (VM de Cairo + bootloader, 1 hilo)\n"
         "→ scarb prove (Stwo, multihilo) → scarb verify\n"
         "run_once.sh lee /sys/fs/cgroup: memory.peak, memory.events, cpu.stat", 1.9, BLUE_BG, BLUE),
        ("Servicios del sistema",
         "docker CLI → dockerd → containerd → runc\n"
         "systemd: el cgroup del contenedor es docker-<id>.scope", 1.6, GRAY_BG, LINE),
        ("Kernel Linux",
         "namespaces (PID, mnt, net, UTS, IPC): aislamiento\n"
         "cgroups v2, cpu.max: cuota por período de 100 ms → throttling\n"
         "cgroups v2, memory.max (sin swap): OOM killer → SIGKILL\n"
         "planificador (EEVDF + CFS bandwidth control)", 2.25, GRAY_BG, LINE),
        ("Virtualización",
         "VMware Workstation: VM Ubuntu Server 24.04, 14 vCPU, 24 GiB", 1.2, GRAY_BG, LINE),
        ("Hardware",
         "Intel Xeon W-11955M: 8 núcleos / 16 hilos, 32 GB de RAM", 1.2, GRAY_BG, LINE),
    ]
    gap = 0.2
    y = 0.3 + sum(r[2] for r in rows) + gap * (len(rows) - 1)
    tops = {}
    for title, body, h, fill, edge in rows:
        y -= h
        box(ax, x, y, W, h, title, body, fill, edge, BLUE if fill == BLUE_BG else INK)
        tops[title.split()[0]] = (y, y + h)
        y -= gap
    # Limits travel from the docker run request down to the kernel's cgroup files.
    y_from = tops["Servicios"][1] - 0.3
    y_to = tops["Kernel"][0] + 0.6
    ax.annotate("", xy=(x + W + 0.3, y_to), xytext=(x + W + 0.3, y_from),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.4))
    ax.text(x + W + 0.5, (y_from + y_to) / 2, "--cpus\n--memory\n--memory-swap\n\nse escriben en\nlos archivos\ndel cgroup",
            fontsize=7.8, color=BLUE, va="center")
    fig.savefig(OUT / "capas.png")
    plt.close(fig)


def architecture():
    fig, ax = canvas(7.4, 4.4)
    # Host
    box(ax, 0.3, 0.3, 11.2, 6.4, "Host: VM Ubuntu Server 24.04 con Docker Engine (cgroups v2)")
    box(ax, 0.6, 4.3, 2.9, 1.6, "Repositorio", "cairo/\nscripts/\nMakefile", "white")
    box(ax, 0.6, 2.2, 2.9, 1.5, "sweep.sh", "un docker run por\nmedición, con límites\nE1 / E2 / E3", "white")
    box(ax, 0.6, 0.6, 2.9, 1.1, "results/", "raw/*.csv → plot.py\n→ figures/*.png", "white")
    # Container
    box(ax, 4.6, 0.9, 6.5, 5.0, "Contenedor (cgroup propio)", fill=BLUE_BG,
        edge=BLUE, title_color=BLUE)
    steps = [("scarb execute", "traza + entrada del prover"),
             ("scarb prove (Stwo)", "prueba STARK, ~11 MB"),
             ("scarb verify", "OK / FAIL")]
    y = 4.4
    for t, b in steps:
        box(ax, 5.0, y, 3.4, 0.85, t, b, "white", BLUE)
        y -= 1.2
    for y0 in (4.4, 3.2):
        arrow(ax, (6.7, y0), (6.7, y0 - 0.35))
    box(ax, 8.7, 2.0, 2.2, 3.25, "run_once.sh", "mide tiempos y\nlee el cgroup:\n\nmemory.peak\nmemory.events\ncpu.stat\ncpu.max\nmemory.max",
        "white", BLUE)
    ax.text(7.85, 1.25, "imprime 1 fila CSV", fontsize=8, color=INK_2, ha="center")
    # Arrows host <-> container
    arrow(ax, (3.5, 5.1), (4.6, 5.1), "montaje")
    arrow(ax, (3.5, 2.95), (4.6, 2.95), "límites")
    arrow(ax, (4.6, 1.15), (3.5, 1.15), "CSV")
    fig.savefig(OUT / "arquitectura.png")
    plt.close(fig)


if __name__ == "__main__":
    layers()
    architecture()
    print("informe/figuras/capas.png, informe/figuras/arquitectura.png")
