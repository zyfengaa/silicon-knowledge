#!/usr/bin/env python3
"""
roofline_plot.py — Roofline Model Visualizer

Generates a roofline plot for a given hardware configuration: peak GFLOPS and
peak memory bandwidth.  The plot shows the compute ceiling (horizontal line),
the memory ceiling (diagonal line), the ridge point, and example kernels
(SAXPY, matmul, stencil, convolution) as annotated scatter points.

Dependencies: numpy, matplotlib

Usage:
    python roofline_plot.py              # default A100-like hardware
    python roofline_plot.py --gflops 200 --gbps 100   # custom hardware

References
----------
- Williams, S., Waterman, A., & Patterson, D. (2009). "Roofline: An Insightful
  Visual Performance Model for Multicore Architectures." CACM 52(4).
- Lo, Y. J., et al. (2014). "Roofline Model Toolkit."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 10,
    "figure.facecolor": "white",
})


# ---------------------------------------------------------------------------
# Data class for kernel markers
# ---------------------------------------------------------------------------

class KernelPoint:
    """A kernel to annotate on the roofline plot."""

    def __init__(self, name: str, ai: float, perf: float, marker: str = "o",
                 color: str = "C0") -> None:
        self.name = name
        self.ai = ai           # Arithmetic Intensity (FLOP/Byte)
        self.perf = perf       # Achieved performance (GFLOPS)
        self.marker = marker
        self.color = color


# ---------------------------------------------------------------------------
# Roofline computation
# ---------------------------------------------------------------------------

def compute_ridge_point(peak_gflops: float, peak_gbps: float) -> float:
    """Return the arithmetic intensity (FLOP/Byte) at the ridge point."""
    if peak_gbps <= 0:
        raise ValueError("Peak bandwidth must be > 0")
    return peak_gflops / peak_gbps


def roofline_performance(
    ai: np.ndarray,
    peak_gflops: float,
    peak_gbps: float,
) -> np.ndarray:
    """Return attainable GFLOPS for given arithmetic intensities.

    Parameters
    ----------
    ai : np.ndarray
        Arithmetic intensity values.
    peak_gflops : float
        Peak compute throughput in GFLOPS.
    peak_gbps : float
        Peak memory bandwidth in GB/s.

    Returns
    -------
    np.ndarray
        Attainable GFLOPS (element-wise min of both ceilings).
    """
    return np.minimum(peak_gflops, ai * peak_gbps)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def make_roofline_plot(
    peak_gflops: float,
    peak_gbps: float,
    kernels: list[KernelPoint] | None = None,
    title: str | None = None,
    save_path: str | None = None,
    show: bool = True,
) -> plt.Figure:
    """Create and return a roofline model figure.

    Parameters
    ----------
    peak_gflops : float
        Peak compute in GFLOPS.
    peak_gbps : float
        Peak memory bandwidth in GB/s.
    kernels : list of KernelPoint, optional
        Kernels to annotate on the plot.
    title : str, optional
        Plot title.  Auto-generated if None.
    save_path : str, optional
        If provided, save the figure to this path.
    show : bool
        Whether to call plt.show().
    """
    ridge_ai = compute_ridge_point(peak_gflops, peak_gbps)

    # X axis: arithmetic intensity, log scale from 0.1 to 100 FLOP/Byte
    ai = np.logspace(-1, 2, 500)
    attainable = roofline_performance(ai, peak_gflops, peak_gbps)

    fig, ax = plt.subplots(figsize=(10, 7))

    # -- Ceiling lines ------------------------------------------------------
    # Memory ceiling: y = AI * bandwidth  (diagonal, shown for the whole range)
    mem_ceiling = ai * peak_gbps
    # Clamp memory ceiling to <= peak_gflops for drawing
    mem_ceiling_clipped = np.minimum(mem_ceiling, peak_gflops * 1.05)

    ax.loglog(ai, mem_ceiling, "b-", linewidth=2.0, label="Memory ceiling "
              f"(BW = {peak_gbps:.0f} GB/s)")

    # Compute ceiling
    ax.axhline(peak_gflops, color="r", linewidth=2.0, linestyle="--",
               label=f"Compute ceiling ({peak_gflops:.0f} GFLOPS)")

    # -- Ridge point --------------------------------------------------------
    ax.axvline(ridge_ai, color="gray", linewidth=1.0, linestyle=":",
               alpha=0.7)
    ridge_label = f"Ridge = {ridge_ai:.1f} FLOP/Byte"
    ax.annotate(ridge_label,
                xy=(ridge_ai, peak_gflops),
                xytext=(ridge_ai * 2.0, peak_gflops * 0.6),
                arrowprops=dict(arrowstyle="->", color="gray", lw=1.2),
                fontsize=11, color="gray",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow",
                          ec="gray", alpha=0.85))

    # -- Fill regions -------------------------------------------------------
    idx_ridge = np.searchsorted(ai, ridge_ai)
    ax.fill_between(ai[:idx_ridge], 1, attainable[:idx_ridge],
                    color="blue", alpha=0.06)
    ax.fill_between(ai[idx_ridge:], 1, attainable[idx_ridge:],
                    color="red", alpha=0.06)

    # Region label
    ax.text(0.18, peak_gflops * 0.12, "Memory-bound", fontsize=13,
            color="blue", alpha=0.6, rotation=90, va="bottom")
    ax.text(ridge_ai * 1.8, peak_gflops * 0.12, "Compute-bound",
            fontsize=13, color="red", alpha=0.6, rotation=90, va="bottom")

    # -- Kernel scatter points ----------------------------------------------
    if kernels:
        for k in kernels:
            ax.scatter(k.ai, k.perf, marker=k.marker, s=120, color=k.color,
                       zorder=5, edgecolors="black", linewidths=0.5)
            # Offset annotation slightly so it doesn't overlap the marker
            offset_x = k.ai * 1.25
            offset_y = k.perf * 1.15
            ax.annotate(k.name,
                        xy=(k.ai, k.perf),
                        xytext=(offset_x, offset_y),
                        fontsize=11, fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.3", fc="white",
                                  ec=k.color, alpha=0.85))

    # -- Axes limits & labels -----------------------------------------------
    ax.set_xlim(0.08, 120)
    ax.set_ylim(1, peak_gflops * 1.6)
    ax.set_xlabel("Arithmetic Intensity (FLOP/Byte)")
    ax.set_ylabel("Performance (GFLOPS)")
    ax.set_title(title or f"Roofline Model — Peak {peak_gflops:.0f} GFLOPS, "
                          f"{peak_gbps:.0f} GB/s")
    ax.grid(True, which="both", linestyle="--", alpha=0.3)
    ax.legend(loc="lower right")

    fig.tight_layout()

    if save_path:
        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out), dpi=150)
        print(f"Figure saved to {out.resolve()}")

    if show:
        plt.show()

    return fig


# ---------------------------------------------------------------------------
# Example kernels (representative of typical workloads on an A100)
# ---------------------------------------------------------------------------

def default_kernels() -> list[KernelPoint]:
    """Return a list of example kernels with measured/typical data.

    Arithmetic intensity and performance values are representative of
    well-optimized implementations on an NVIDIA A100-class GPU.
    """
    return [
        KernelPoint(
            name="SAXPY (y = ax + y)",
            ai=0.17,       # 2 FLOP / 12 Byte (FP32)
            perf=340.0,    # BW-limited: 2000 GB/s × 0.17 ≈ 340 GFLOPS
            marker="v",
            color="#2196F3",
        ),
        KernelPoint(
            name="Stencil 3D (7-pt)",
            ai=0.5,        # ~8 FLOP / ~16 Byte (with cache reuse)
            perf=900.0,    # Memory-bound on A100
            marker="s",
            color="#4CAF50",
        ),
        KernelPoint(
            name="SpMV (CSR)",
            ai=0.8,        # Sparse matrix-vector, ~2 non-zeros/row ops:Byte
            perf=1200.0,
            marker="D",
            color="#FF9800",
        ),
        KernelPoint(
            name="Conv (resnet50)",
            ai=8.0,        # Typical conv+im2col → GEMM
            perf=14000.0,  # Tensor Core accelerated
            marker="^",
            color="#9C27B0",
        ),
        KernelPoint(
            name="MatMul (4096, BF16 TC)",
            ai=180.0,      # 2*4096^3 / (3*4096^2*2) = 4096/3 ≈ 1365 → but
                           # with tiling memory traffic ~180 is more realistic
            perf=270000.0, # Tensor Core ~270 TFLOPS on A100
            marker="*",
            color="#E91E63",
        ),
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roofline model visualizer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--gflops", type=float, default=312000.0,
                        help="Peak compute throughput in GFLOPS (default: "
                             "A100 BF16 Tensor Core ~312 TFLOPS)")
    parser.add_argument("--gbps", type=float, default=2000.0,
                        help="Peak memory bandwidth in GB/s (default: "
                             "A100 HBM2e ~2 TB/s)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save figure to path (e.g. roofline.png)")
    parser.add_argument("--no-show", action="store_true",
                        help="Suppress interactive display")
    parser.add_argument("--title", type=str, default=None,
                        help="Plot title (auto-generated if omitted)")
    parser.add_argument("--no-kernels", action="store_true",
                        help="Omit example kernel annotations")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    kernels: list[KernelPoint] | None = (
        None if args.no_kernels else default_kernels()
    )

    make_roofline_plot(
        peak_gflops=args.gflops,
        peak_gbps=args.gbps,
        kernels=kernels,
        title=args.title,
        save_path=args.save,
        show=not args.no_show,
    )

    # Print summary to stdout
    ridge = compute_ridge_point(args.gflops, args.gbps)
    print(f"Roofline Summary")
    print(f"  Peak GFLOPS:      {args.gflops:>12.1f}")
    print(f"  Peak BW (GB/s):   {args.gbps:>12.1f}")
    print(f"  Ridge (FLOP/B):   {ridge:>12.1f}")
    if kernels:
        print(f"\n  {'Kernel':<30s} {'AI':>8s} {'GFLOPS':>10s} {'Bound':>12s}")
        print(f"  {'-'*60}")
        for k in kernels:
            bound = "compute" if k.ai > ridge else "memory"
            print(f"  {k.name:<30s} {k.ai:>8.2f} {k.perf:>10.1f} {bound:>12s}")


if __name__ == "__main__":
    main()
