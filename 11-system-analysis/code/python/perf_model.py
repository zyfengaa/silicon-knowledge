"""
perf_model.py — Simple Performance Model for Roofline Analysis

Given arithmetic intensity (FLOP/Byte), peak GFLOPS, and peak bandwidth (GB/s),
compute the achievable performance using the Roofline model.

The model classifies a kernel as compute-bound or memory-bound and returns
the expected upper-bound performance.

Usage:
    python perf_model.py              # run built-in examples
    python -c "from perf_model import roofline_perf; print(roofline_perf(0.5, 1000, 200))"
"""

from __future__ import annotations


def roofline_perf(
    arithmetic_intensity: float, peak_gflops: float, peak_bw_gbps: float
) -> float:
    """
    Compute the expected achievable performance under the Roofline model.

    Parameters
    ----------
    arithmetic_intensity : float
        FLOP per byte loaded from DRAM (FLOP/Byte).
    peak_gflops : float
        Peak compute throughput (GFLOPS).
    peak_bw_gbps : float
        Peak memory bandwidth (GB/s).

    Returns
    -------
    achieved_gflops : float
        Upper-bound GFLOPS given the kernel's characteristics.
    """
    if arithmetic_intensity <= 0.0:
        raise ValueError("arithmetic_intensity must be > 0")
    if peak_gflops <= 0.0:
        raise ValueError("peak_gflops must be > 0")
    if peak_bw_gbps <= 0.0:
        raise ValueError("peak_bw_gbps must be > 0")

    ridge_point = peak_gflops / peak_bw_gbps

    if arithmetic_intensity >= ridge_point:
        # Compute-bound: limited by peak compute
        achieved_gflops = peak_gflops
    else:
        # Memory-bound: limited by memory bandwidth
        achieved_gflops = peak_bw_gbps * arithmetic_intensity

    return achieved_gflops


def classify_bound(
    arithmetic_intensity: float, peak_gflops: float, peak_bw_gbps: float
) -> str:
    """Return a string identifying the bottleneck type."""
    ridge_point = peak_gflops / peak_bw_gbps
    if arithmetic_intensity >= ridge_point:
        return "compute-bound"
    else:
        return "memory-bound"


def utilization_fraction(
    arithmetic_intensity: float, peak_gflops: float, peak_bw_gbps: float
) -> float:
    """Return the fraction (0-1) of peak compute utilised."""
    achieved = roofline_perf(arithmetic_intensity, peak_gflops, peak_bw_gbps)
    return achieved / peak_gflops


# ──────────────────────────────────────────────────────────────────────


def main():
    # Example hardware: NVIDIA A100 (FP16 Tensor Core)
    PEAK_GFLOPS = 19500.0
    PEAK_BW_GBPS = 2039.0

    kernel_database = {
        "SAXPY (y = a*x + y)": 0.17,
        "3D 7-point stencil": 0.50,
        "SpMV (CSR)": 1.0,
        "FFT (N=2^20)": 2.0,
        "1x1 Conv (large batch)": 15.0,
        "SGEMM (N=2048)": 30.0,
        "DGEMM (ideal cache)": 100.0,
    }

    print(f"{'Kernel':<30} {'AI':>6} {'Bound':<16} {'GFLOPS':>8} {'Util%':>7}")
    print("-" * 70)

    for kernel_name, ai in kernel_database.items():
        achieved = roofline_perf(ai, PEAK_GFLOPS, PEAK_BW_GBPS)
        bound = classify_bound(ai, PEAK_GFLOPS, PEAK_BW_GBPS)
        util = utilization_fraction(ai, PEAK_GFLOPS, PEAK_BW_GBPS) * 100
        print(
            f"{kernel_name:<30} {ai:>6.2f} {bound:<16} {achieved:>8.1f} {util:>6.1f}%"
        )


if __name__ == "__main__":
    main()
