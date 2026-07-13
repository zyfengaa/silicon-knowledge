#!/usr/bin/env python3
"""
perf_model.py — Roofline Performance Model

A simple performance modelling class that, given hardware parameters (peak
GFLOPS and peak memory bandwidth), predicts a kernel's attainable performance
based on its arithmetic intensity.

Usage:
    python perf_model.py                         # demo with built-in examples
    python perf_model.py --gflops 10000 --gbps 500

References
----------
- Williams, S., Waterman, A., & Patterson, D. (2009). "Roofline: An Insightful
  Visual Performance Model for Multicore Architectures." CACM 52(4).
- Hennessy, J. L., & Patterson, D. A. (2019). *Computer Architecture: A
  Quantitative Approach* (6th ed.). Morgan Kaufmann.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Tuple


# ---------------------------------------------------------------------------
# Roofline Model
# ---------------------------------------------------------------------------

@dataclass
class Prediction:
    """Result of a roofline performance prediction."""
    arithmetic_intensity: float       # FLOP/Byte
    attainable_gflops: float          # GFLOPS
    bound_type: str                   # "compute" or "memory"
    ridge_point: float                # FLOP/Byte
    peak_gflops: float                # GFLOPS
    peak_bandwidth: float             # GB/s

    def __post_init__(self) -> None:
        if self.bound_type not in ("compute", "memory"):
            raise ValueError(f"bound_type must be 'compute' or 'memory', "
                             f"got '{self.bound_type}'")


class RooflineModel:
    """Predict attainable performance using the Roofline model.

    Parameters
    ----------
    peak_gflops : float
        Peak floating-point throughput of the hardware in GFLOPS.
        e.g. 312000 for A100 BF16 Tensor Core.
    peak_bandwidth_gbps : float
        Peak memory bandwidth of the hardware in GB/s.
        e.g. 2000 for A100 HBM2e.
    """

    def __init__(self, peak_gflops: float, peak_bandwidth_gbps: float) -> None:
        if peak_gflops <= 0:
            raise ValueError(f"peak_gflops must be > 0, got {peak_gflops}")
        if peak_bandwidth_gbps <= 0:
            raise ValueError(f"peak_bandwidth_gbps must be > 0, "
                             f"got {peak_bandwidth_gbps}")
        self.peak_gflops = peak_gflops
        self.peak_bw = peak_bandwidth_gbps
        self._ridge = peak_gflops / peak_bandwidth_gbps

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def ridge_point(self) -> float:
        """Return the arithmetic intensity at the ridge point (FLOP/Byte)."""
        return self._ridge

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_performance(
        self, arithmetic_intensity: float
    ) -> Prediction:
        """Predict attainable performance for a given arithmetic intensity.

        Parameters
        ----------
        arithmetic_intensity : float
            FLOP/Byte ratio of the kernel.

        Returns
        -------
        Prediction with attainable_gflops and bound_type.
        """
        if arithmetic_intensity <= 0:
            raise ValueError(
                f"arithmetic_intensity must be > 0, "
                f"got {arithmetic_intensity}"
            )

        bw_limited = arithmetic_intensity * self.peak_bw

        if arithmetic_intensity > self._ridge:
            attainable = self.peak_gflops
            bound = "compute"
        else:
            attainable = bw_limited
            bound = "memory"

        return Prediction(
            arithmetic_intensity=arithmetic_intensity,
            attainable_gflops=attainable,
            bound_type=bound,
            ridge_point=self._ridge,
            peak_gflops=self.peak_gflops,
            peak_bandwidth=self.peak_bw,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (f"RooflineModel(peak={self.peak_gflops:.1f} GFLOPS, "
                f"BW={self.peak_bw:.1f} GB/s, "
                f"ridge={self._ridge:.2f} FLOP/Byte)")


# ---------------------------------------------------------------------------
# Example usage & CLI
# ---------------------------------------------------------------------------

def demo(model: RooflineModel) -> None:
    """Run a demonstration with several common kernel patterns."""
    print(f"\nRoofline Demo — {model}")
    print(f"{'─' * 72}")
    print(f"{'Kernel':<30s} {'AI':>10s} {'Predicted':>12s} {'Bound':>10s} "
          f"{'Util %':>8s}")
    print(f"{'─' * 72}")

    examples = [
        ("SAXPY (FP32)", 0.17),
        ("DAXPY (FP64)", 0.17),
        ("Stencil 3D 7pt (FP32)", 0.5),
        ("SpMV (CSR, FP32)", 0.8),
        ("FFT (large, FP32)", 2.0),
        ("Conv (ResNet, FP16 TC)", 8.0),
        ("MatMul 1024 (FP32)", 60.0),
        ("MatMul 4096 (BF16 TC)", 180.0),
        ("MatMul 8192 (FP16 TC)", 341.0),
    ]

    for name, ai in examples:
        pred = model.predict_performance(ai)
        util = (pred.attainable_gflops / pred.peak_gflops) * 100.0
        print(f"{name:<30s} {ai:>10.2f} {pred.attainable_gflops:>12.1f} "
              f"{pred.bound_type:>10s} {util:>7.1f}%")


def compute_arithmetic_intensity(
    total_flops: float,
    total_bytes: float,
) -> float:
    """Compute arithmetic intensity given total operations and bytes.

    Parameters
    ----------
    total_flops : float
        Total floating-point operations.
    total_bytes : float
        Total bytes transferred between DRAM and processor.

    Returns
    -------
    float
        Arithmetic intensity in FLOP/Byte.
    """
    if total_bytes <= 0:
        raise ValueError("total_bytes must be > 0")
    return total_flops / total_bytes


def matmul_ai(M: int, N: int, K: int, bytes_per_elem: int = 4) -> float:
    """Compute theoretical arithmetic intensity for C(M,N) = A(M,K) @ B(K,N).

    The minimum data movement is reading A (M*K * bytes), B (K*N * bytes),
    and writing C (M*N * bytes).  No cache effects are considered.

    Parameters
    ----------
    M, N, K : int
        Matrix dimensions.
    bytes_per_elem : int
        Bytes per element (4 for FP32, 2 for FP16/BF16).

    Returns
    -------
    float
        Arithmetic intensity (FLOP/Byte).
    """
    flops = 2.0 * M * N * K
    bytes_moved = (M * K + K * N + M * N) * bytes_per_elem
    return compute_arithmetic_intensity(flops, bytes_moved)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roofline Performance Model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--gflops", type=float, default=312000.0,
                        help="Peak GFLOPS (default: A100 ~312 TFLOPS BF16 TC)")
    parser.add_argument("--gbps", type=float, default=2000.0,
                        help="Peak memory bandwidth GB/s (default: A100 HBM2e)")
    parser.add_argument("--ai", type=float, default=None,
                        help="Single arithmetic intensity to predict "
                             "(omit to run demo)")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    model = RooflineModel(peak_gflops=args.gflops,
                          peak_bandwidth_gbps=args.gbps)

    if args.ai is not None:
        pred = model.predict_performance(args.ai)
        print(f"RooflineModel({args.gflops:.0f} GFLOPS, "
              f"{args.gbps:.0f} GB/s)")
        print(f"  AI = {args.ai:.2f} FLOP/Byte")
        print(f"  Ridge point = {pred.ridge_point:.2f} FLOP/Byte")
        print(f"  Attainable = {pred.attainable_gflops:.1f} GFLOPS")
        print(f"  Bound by: {pred.bound_type}")
    else:
        print(f"Roofline Performance Model")
        print(f"{'─' * 72}")
        print(f"HW config: {args.gflops:.0f} GFLOPS, "
              f"{args.gbps:.0f} GB/s")
        print(f"Ridge point: {model.ridge_point:.2f} FLOP/Byte")
        demo(model)

        # MatMul AI examples
        print(f"\n{'─' * 72}")
        print("Matrix Multiply Arithmetic Intensities (FP32)")
        print(f"{'─' * 72}")
        for N in [128, 256, 512, 1024, 2048, 4096]:
            ai = matmul_ai(N, N, N, bytes_per_elem=4)
            print(f"  MatMul {N:>5d} × {N:<5d} → {ai:>8.1f} FLOP/Byte")

        print(f"\nMatrix Multiply Arithmetic Intensities (BF16)")
        for N in [128, 256, 512, 1024, 2048, 4096]:
            ai = matmul_ai(N, N, N, bytes_per_elem=2)
            print(f"  MatMul {N:>5d} × {N:<5d} → {ai:>8.1f} FLOP/Byte")


if __name__ == "__main__":
    main()
