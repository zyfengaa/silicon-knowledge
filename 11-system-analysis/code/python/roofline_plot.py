"""
roofline_plot.py — Generate Roofline Model Visualisation

This script creates a Roofline model plot for a given hardware configuration
and overlays example program characteristics as data points.

Usage:
    python roofline_plot.py

The plot is saved as 'roofline.pdf' and displayed interactively.
"""

import numpy as np
import matplotlib.pyplot as plt


def draw_roofline(
    peak_gflops: float,
    peak_bw_gbps: float,
    programs: list[dict],
    title: str = "Roofline Model",
    save_path: str = "roofline.pdf",
) -> None:
    """
    Draw a Roofline model plot.

    Parameters
    ----------
    peak_gflops : float
        Peak compute throughput (GFLOPS).
    peak_bw_gbps : float
        Peak memory bandwidth (GB/s).
    programs : list[dict]
        Each dict must have keys: 'name' (str), 'ai' (FLOP/Byte), 'gflops' (float).
    title : str
        Plot title.
    save_path : str
        Output file path for the saved figure.
    """
    ridge_point = peak_gflops / peak_bw_gbps

    # ---- Create figure ----
    fig, ax = plt.subplots(figsize=(10, 7))

    # ---- Axes: log-log ----
    ax.set_xlim(0.1, 100)
    ax.set_ylim(1, peak_gflops * 1.5)

    # ---- Memory-bound ceiling (diagonal line) ----
    ai_range = np.logspace(np.log10(0.1), np.log10(ridge_point), 100)
    mem_ceiling = peak_bw_gbps * ai_range
    ax.plot(ai_range, mem_ceiling, color="C0", linewidth=2.5, label="Memory Ceiling")

    # ---- Compute-bound ceiling (horizontal line) ----
    ax.axhline(y=peak_gflops, color="C1", linewidth=2.5, label="Compute Ceiling")

    # ---- Ridge point marker ----
    ax.axvline(
        x=ridge_point,
        color="gray",
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        label=f"Ridge Point (AI={ridge_point:.1f})",
    )

    # ---- Fill regions ----
    # Memory-bound region shading
    ax.fill_between(
        ai_range,
        1,
        mem_ceiling,
        color="C0",
        alpha=0.08,
    )
    # Compute-bound region shading
    ax.fill_between(
        [ridge_point, 100],
        1,
        peak_gflops,
        color="C1",
        alpha=0.08,
    )

    # ---- Annotations for regions ----
    ax.text(
        0.15,
        peak_gflops / 10,
        "Memory-Bound",
        rotation=37,
        fontsize=12,
        color="C0",
        fontweight="bold",
    )
    ax.text(
        10,
        peak_gflops * 0.9,
        "Compute-Bound",
        fontsize=12,
        color="C1",
        fontweight="bold",
        horizontalalignment="center",
    )

    # ---- Plot example programs ----
    markers = ["o", "s", "^", "D", "v", "p", "h", "x"]
    for idx, prog in enumerate(programs):
        marker = markers[idx % len(markers)]
        ax.scatter(
            prog["ai"],
            prog["gflops"],
            s=120,
            marker=marker,
            color="C2",
            edgecolors="black",
            linewidths=0.5,
            zorder=5,
        )
        ax.annotate(
            prog["name"],
            (prog["ai"], prog["gflops"]),
            textcoords="offset points",
            xytext=(10, 8),
            fontsize=10,
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
        )

    # ---- Labels & formatting ----
    ax.set_xlabel("Arithmetic Intensity (FLOP/Byte)", fontsize=13)
    ax.set_ylabel("Performance (GFLOPS)", fontsize=13)
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right", fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()
    print(f"Roofline plot saved to {save_path}")


def main():
    # ---- Hardware configuration (example: NVIDIA A100) ----
    PEAK_GFLOPS = 312.0  # TFLOPS * 1000 = FP64 GFLOPS (A100: 9.7 TFLOPS FP64)
    # Use FP16 Tensor Core for more realistic AI workloads:
    PEAK_GFLOPS = 19_500.0  # 19.5 TFLOPS * 1000 = 19500 GFLOP FP16
    PEAK_BW_GBPS = 2039.0  # HBM2e: 2.039 TB/s * 1024 = 2088 GB/s => ~2039

    # ---- Example programs (name, AI, measured GFLOPS) ----
    programs = [
        {"name": "SAXPY",        "ai": 0.17,     "gflops": 350},
        {"name": "Stencil-3D",   "ai": 0.50,     "gflops": 1020},
        {"name": "SpMV",         "ai": 0.80,     "gflops": 1630},
        {"name": "FFT (N=2^20)", "ai": 2.00,     "gflops": 4080},
        {"name": "SGEMM (N=2048)", "ai": 30.00,   "gflops": 17500},
        {"name": "Conv (1x1, Lg)", "ai": 15.00,  "gflops": 16000},
        {"name": "GEMM (ideal roofline)", "ai": 100.0, "gflops": 19500},
    ]

    draw_roofline(
        peak_gflops=PEAK_GFLOPS,
        peak_bw_gbps=PEAK_BW_GBPS,
        programs=programs,
        title="Roofline Model — NVIDIA A100 (FP16 Tensor Core)",
        save_path="roofline.pdf",
    )


if __name__ == "__main__":
    main()
