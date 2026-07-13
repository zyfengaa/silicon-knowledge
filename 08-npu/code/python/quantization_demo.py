#!/usr/bin/env python3
"""
quantization_demo.py — INT8 Quantization Demo with Per-Tensor vs Per-Channel

Demonstrates the full quantization pipeline:
  1. Generate random FP32 tensor
  2. Compute scale & zero_point (minmax / percentile methods)
  3. Quantize to INT8  →  dequantize back to FP32
  4. Report MSE and MaxAbs errors
  5. Compare per-tensor with per-channel quantization
  6. Visualise results (saved to quantization_comparison.png)

References
----------
- Jacob, B. et al. (2018). "Quantization and Training of Neural Networks for
  Efficient Integer-Arithmetic-Only Inference." CVPR'18.
- Nagel, M. et al. (2021). "A White Paper on Neural Network Quantization."
  arXiv:2106.08295.
- Krishnamoorthi, R. (2018). "Quantizing Deep Convolutional Networks for
  Efficient Inference: A Whitepaper." arXiv:1806.08342.
- TensorFlow Lite / MLIR quantization pass documentation.
"""

from __future__ import annotations

import argparse
import math
from typing import Literal, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CI
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Core quantisation helpers
# ---------------------------------------------------------------------------

def compute_scale_zeropoint(
    tensor: np.ndarray,
    method: Literal["minmax", "percentile"] = "minmax",
    percentile: float = 99.9,
) -> Tuple[float, int]:
    """Compute scale and zero_point for symmetric / asymmetric INT8 quantisation.

    Parameters
    ----------
    tensor : np.ndarray
        Float tensor (any shape).
    method : str
        ``"minmax"`` — use observed min/max.
        ``"percentile"`` — clip outliers at the given percentile.
    percentile : float
        Percentile value (0–100) used when ``method="percentile"``.

    Returns
    -------
    scale : float
        Quantisation scale (positive).
    zero_point : int
        Quantisation zero-point in [0, 255] (INT8 quantised range).
    """
    if tensor.size == 0:
        raise ValueError("Empty tensor")

    if method == "minmax":
        t_min, t_max = float(tensor.min()), float(tensor.max())
    elif method == "percentile":
        low = (100.0 - percentile) / 2.0
        high = 100.0 - low
        t_min = float(np.percentile(tensor, low))
        t_max = float(np.percentile(tensor, high))
    else:
        raise ValueError(f"Unknown method '{method}'. Use 'minmax' or 'percentile'.")

    # Guard against degenerate range
    if t_max - t_min < 1e-10:
        t_min -= 0.5
        t_max += 0.5

    # Asymmetric quantisation to [0, 255]
    q_min, q_max = 0, 255
    scale = (t_max - t_min) / (q_max - q_min)
    zero_point = int(round(q_min - t_min / scale))
    zero_point = max(q_min, min(q_max, zero_point))  # clamp
    return scale, zero_point


def quantize(tensor: np.ndarray, scale: float, zero_point: int) -> np.ndarray:
    """Quantise FP32 tensor to INT8 using given scale & zero_point.

    ``q = clamp(round(tensor / scale) + zero_point, 0, 255)``

    Returns a uint8 (unsigned INT8) NumPy array.
    """
    q = np.round(tensor / scale) + zero_point
    q = np.clip(q, 0, 255).astype(np.uint8)
    return q


def dequantize(qtensor: np.ndarray, scale: float, zero_point: int) -> np.ndarray:
    """Dequantise INT8 tensor back to FP32.

    ``x = (q - zero_point) * scale``
    """
    return (qtensor.astype(np.float32) - zero_point) * scale


# ---------------------------------------------------------------------------
# Per-channel quantisation
# ---------------------------------------------------------------------------

def quantize_per_channel(
    tensor: np.ndarray,
    axis: int = 0,
    method: Literal["minmax", "percentile"] = "minmax",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Quantise along one axis with per-channel scales / zero-points.

    Parameters
    ----------
    tensor : np.ndarray
        Float tensor, typically (C, H, W) for a convolution weight.
    axis : int
        Channel axis.
    method : str
        Scale/zero-point computation method.

    Returns
    -------
    q_tensor : np.ndarray (uint8)
        Quantised tensor, same shape as input.
    scales : np.ndarray (float32)
        Per-channel scales, shape ``(tensor.shape[axis],)``.
    zero_points : np.ndarray (int32)
        Per-channel zero-points.
    """
    # Move channel axis to first position for uniform iteration
    t_moved = np.moveaxis(tensor, axis, 0)
    channels = t_moved.shape[0]

    q_slices = []
    scales = np.zeros(channels, dtype=np.float32)
    zps = np.zeros(channels, dtype=np.int32)

    for c in range(channels):
        s, zp = compute_scale_zeropoint(t_moved[c], method=method)
        scales[c] = s
        zps[c] = zp
        q_slices.append(quantize(t_moved[c], s, zp))

    # Stack and restore original axis order
    q_stacked = np.stack(q_slices, axis=0)
    q_tensor = np.moveaxis(q_stacked, 0, axis).astype(np.uint8)
    return q_tensor, scales, zps


# ---------------------------------------------------------------------------
# Error metrics
# ---------------------------------------------------------------------------

def mse(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Mean squared error between two arrays."""
    return float(np.mean((original.astype(np.float64) - reconstructed.astype(np.float64)) ** 2))


def max_abs_error(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Maximum absolute error."""
    return float(np.max(np.abs(original.astype(np.float64) - reconstructed.astype(np.float64))))


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_comparison(
    original: np.ndarray,
    per_tensor_rec: np.ndarray,
    per_channel_rec: np.ndarray,
    save_path: str = "quantization_comparison.png",
) -> None:
    """Side-by-side histogram comparison: original vs per-tensor vs per-channel."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)

    titles = ["Original (FP32)", "Per-Tensor INT8", "Per-Channel INT8"]
    data = [original.ravel(), per_tensor_rec.ravel(), per_channel_rec.ravel()]
    colors = ["#4C72B0", "#DD8452", "#55A868"]

    for ax, title, vals, color in zip(axes, titles, data, colors):
        ax.hist(vals, bins=80, density=True, alpha=0.75, color=color)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Value")
        ax.set_ylabel("Density")

    fig.suptitle("Quantisation Comparison: Original vs Reconstructed (INT8)", fontsize=14)
    plt.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"\nPlot saved to {save_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the full quantisation demo."""
    parser = argparse.ArgumentParser(description="INT8 quantisation demo")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--shape", type=int, nargs="+", default=[8, 16, 7, 7],
                        help="Tensor shape (default 8×16×7×7)")
    parser.add_argument("--percentile", type=float, default=99.9,
                        help="Percentile value for percentile method")
    parser.add_argument("--plot", type=str, default="quantization_comparison.png",
                        help="Path to save comparison plot")
    args = parser.parse_args()

    np.random.seed(args.seed)
    shape = tuple(args.shape)

    # ---- Generate random FP32 tensor (simulating weights or activations) ----
    tensor = np.random.randn(*shape).astype(np.float32)
    # Add a few outliers to make percentile calibration meaningful
    tensor.ravel()[np.random.choice(tensor.size, size=max(1, tensor.size // 50), replace=False)] *= 5.0

    print("=" * 72)
    print("INT8 Quantisation Demo")
    print("=" * 72)
    print(f"  Tensor shape : {tensor.shape}")
    print(f"  Range        : [{tensor.min():.4f}, {tensor.max():.4f}]")
    print(f"  Mean / Std   : {tensor.mean():.4f} / {tensor.std():.4f}")

    methods: list[Literal["minmax", "percentile"]] = ["minmax", "percentile"]
    results: list[dict] = []

    for method in methods:
        print(f"\n{'─' * 72}")
        print(f"Method: {method.upper()}")
        print(f"{'─' * 72}")

        # ---- Per-Tensor ----
        scale, zp = compute_scale_zeropoint(tensor, method=method, percentile=args.percentile)
        q_pt = quantize(tensor, scale, zp)
        r_pt = dequantize(q_pt, scale, zp)
        err_mse_pt = mse(tensor, r_pt)
        err_max_pt = max_abs_error(tensor, r_pt)

        print(f"  Per-Tensor : scale={scale:.6f}  zero_point={zp}")
        print(f"    MSE={err_mse_pt:.6e}  MaxAbs={err_max_pt:.6e}")

        # ---- Per-Channel (axis=0, i.e. output channels for Conv weight) ----
        q_pc, scales_pc, zps_pc = quantize_per_channel(tensor, axis=0, method=method)
        # Dequantise per-channel
        # Move channel axis to front, dequantise slice by slice, move back
        t_moved = np.moveaxis(tensor, 0, 0)  # no-op for axis=0, but illustrative
        slices = []
        for c in range(scales_pc.shape[0]):
            slice_q = np.moveaxis(q_pc, 0, 0)[c]
            slices.append(dequantize(slice_q, scales_pc[c], zps_pc[c]))
        r_pc = np.stack(slices, axis=0)  # shape (C, ...)

        err_mse_pc = mse(tensor, r_pc)
        err_max_pc = max_abs_error(tensor, r_pc)

        print(f"  Per-Channel: scales mean={scales_pc.mean():.6f}  zero_points mode={np.bincount(zps_pc).argmax()}")
        print(f"    MSE={err_mse_pc:.6e}  MaxAbs={err_max_pc:.6e}")

        results.append({
            "method": method,
            "per_tensor_mse": err_mse_pt,
            "per_tensor_maxabs": err_max_pt,
            "per_channel_mse": err_mse_pc,
            "per_channel_maxabs": err_max_pc,
        })

    # ---- Summary table ----
    print(f"\n{'═' * 72}")
    print("Summary Table")
    print(f"{'═' * 72}")
    header = f"{'Method':<14} {'Type':<16} {'MSE':<18} {'MaxAbs':<18}"
    sep = "─" * len(header)
    print(header)
    print(sep)
    for r in results:
        print(f"{r['method']:<14} {'Per-Tensor':<16} {r['per_tensor_mse']:<18.6e} {r['per_tensor_maxabs']:<18.6e}")
        print(f"{r['method']:<14} {'Per-Channel':<16} {r['per_channel_mse']:<18.6e} {r['per_channel_maxabs']:<18.6e}")
        print(sep)

    # ---- Analysis ----
    print("\nKey observations:")
    for r in results:
        ratio = r["per_tensor_mse"] / max(r["per_channel_mse"], 1e-30)
        print(
            f"  {r['method'].upper()}: Per-Channel reduces MSE by "
            f"{(ratio - 1) * 100 if ratio > 1 else (1 - 1/ratio) * 100:.1f}% "
            f"vs Per-Tensor."
        )

    # ---- Plot ----
    if args.plot:
        # Re-run with minmax for the plot
        s_pt, zp_pt = compute_scale_zeropoint(tensor, method="minmax")
        q_pt_plot = quantize(tensor, s_pt, zp_pt)
        r_pt_plot = dequantize(q_pt_plot, s_pt, zp_pt)

        q_pc_plot, sc_pc, zp_pc = quantize_per_channel(tensor, axis=0, method="minmax")
        slices = []
        for c in range(sc_pc.shape[0]):
            slices.append(dequantize(np.moveaxis(q_pc_plot, 0, 0)[c], sc_pc[c], zp_pc[c]))
        r_pc_plot = np.stack(slices, axis=0)

        plot_comparison(tensor, r_pt_plot, r_pc_plot, args.plot)

    print("\nDone.")


if __name__ == "__main__":
    main()
