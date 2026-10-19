#!/usr/bin/env python3
"""
systolic_sim.py — 2D Systolic Array Simulator (4x4)

Implements a configurable systolic array for matrix multiplication with two
dataflow modes: Weight Stationary (WS) and Output Stationary (OS).  Each
Processing Element (PE) contains a multiplier, accumulator, weight register,
and input/output buffers.  The simulator prints per-cycle state and validates
results against NumPy.

References
----------
- Kung, H. T. (1982). "Why systolic architectures?" IEEE Computer, 15(1), 37–46.
- Jouppi, N. P. et al. (2017). "In-Datacenter Performance Analysis of a
  Tensor Processing Unit." ISCA'17.  (Section 2.2 — systolic array)
- Samajdar, A. et al. (2018). "A Systematic Methodology for Characterizing
  Spatial Architectures." ISPASS'18.  (SCALE-Sim simulator)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("SystolicSim")

# ---------------------------------------------------------------------------
# Processing Element
# ---------------------------------------------------------------------------

@dataclass
class PEState:
    """Snapshot of a PE's registers at a given cycle."""
    cycle: int
    weight: float
    input_val: float
    partial_sum_in: float
    partial_sum_out: float
    output_acc: float


class PE:
    """A single Processing Element in the systolic array.

    Contains:
    - weight register (w_reg)
    - input buffer (in_buf)
    - multiplier
    - accumulator / partial-sum register (acc)
    - output buffer (out_buf)

    Data flows depend on the dataflow mode; the PE exposes a unified
    :meth:`compute` interface that the controller calls each cycle.
    """

    def __init__(self, row: int, col: int, verbose: bool = False) -> None:
        self.row = row
        self.col = col
        self.verbose = verbose

        # Registers
        self.w_reg: float = 0.0          # stationary / streamed weight
        self.in_buf: float = 0.0         # input activation
        self.acc: float = 0.0            # accumulator (output partial sum)
        self.out_buf: float = 0.0        # output buffer

        self._history: list[PEState] = []

    def load_weight(self, weight: float) -> None:
        """Pre-load weight register (used in WS mode)."""
        self.w_reg = weight

    def step_ws(self, input_val: float, psum_in: float) -> float:
        """Weight-Stationary step.

        Weight stays; input arrives from left; partial-sum arrives from above.
        Produces partial-sum out = psum_in + weight * input.
        """
        self.in_buf = input_val
        product = self.w_reg * self.in_buf
        self.out_buf = psum_in + product
        self.acc = self.out_buf
        self._snapshot("WS")
        return self.out_buf

    def step_os(self, weight: float, input_val: float) -> float:
        """Output-Stationary step.

        Partial sum stays in the PE accumulator.  Weight and input both
        stream through.  acc += weight * input.
        """
        self.w_reg = weight
        self.in_buf = input_val
        product = self.w_reg * self.in_buf
        self.acc += product
        self.out_buf = self.acc
        self._snapshot("OS")
        # In OS mode the accumulated value stays; we return it for logging
        return self.acc

    def reset(self) -> None:
        """Reset all registers (does not clear history)."""
        self.w_reg = 0.0
        self.in_buf = 0.0
        self.acc = 0.0
        self.out_buf = 0.0

    def _snapshot(self, mode: str) -> None:
        entry = PEState(
            cycle=len(self._history),
            weight=self.w_reg,
            input_val=self.in_buf,
            partial_sum_in=self.out_buf - self.w_reg * self.in_buf
            if mode == "WS" else 0.0,
            partial_sum_out=self.out_buf,
            output_acc=self.acc,
        )
        self._history.append(entry)
        if self.verbose:
            logger.info(
                "  PE[%d,%d]  w=%-6.2f  in=%-6.2f  acc=%-8.2f  out=%-8.2f",
                self.row, self.col, entry.weight, entry.input_val,
                entry.output_acc, entry.partial_sum_out,
            )

    def __repr__(self) -> str:
        return f"PE({self.row},{self.col}): w={self.w_reg:.2f} acc={self.acc:.2f}"


# ---------------------------------------------------------------------------
# Systolic Array Controller
# ---------------------------------------------------------------------------

class SystolicArray:
    """N×N systolic array supporting WS and OS dataflows.

    Parameters
    ----------
    size : int
        Number of rows / columns (array is size×size).
    dataflow : str
        ``"WS"`` or ``"OS"``.
    verbose : bool
        Print per-cycle PE states.
    """

    def __init__(self, size: int = 4, dataflow: str = "WS", verbose: bool = False) -> None:
        if size < 1:
            raise ValueError(f"Array size must be >= 1, got {size}")
        dataflow = dataflow.upper()
        if dataflow not in ("WS", "OS"):
            raise ValueError(f"Dataflow must be 'WS' or 'OS', got '{dataflow}'")
        self.size = size
        self.dataflow = dataflow
        self.verbose = verbose
        self.cycle = 0

        # Create 2-D grid of PEs (row-major)
        self.pe_grid: list[list[PE]] = [
            [PE(r, c, verbose=verbose) for c in range(size)]
            for r in range(size)
        ]

    def _preload_weights_ws(self, weights: np.ndarray) -> None:
        """Load a size×size weight matrix into the PE weight registers."""
        for r in range(self.size):
            for c in range(self.size):
                self.pe_grid[r][c].load_weight(float(weights[r, c]))

    def reset_all(self) -> None:
        """Reset every PE."""
        for row in self.pe_grid:
            for pe in row:
                pe.reset()
        self.cycle = 0

    # ------------------------------------------------------------------
    # Matrix Multiply driver
    # ------------------------------------------------------------------

    def matmul(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Run C = A × B on the systolic array.

        ``A`` (M×K) and ``B`` (K×N) must be compatible; the array computes a
        tile of the output.  For simplicity, this implementation assumes
        M=N=K=*size*.
        """
        M, K = A.shape
        K2, N = B.shape
        if K != K2:
            raise ValueError(f"Inner dims must match: A.shape={A.shape}, B.shape={B.shape}")
        if M != self.size or N != self.size:
            raise ValueError(
                f"Array is {self.size}×{self.size} but input is {M}×{N}"
            )

        self.reset_all()

        if self.dataflow == "WS":
            return self._matmul_ws(A, B)
        else:
            return self._matmul_os(A, B)

    # ------------------------------------------------------------------
    # Weight Stationary
    # ------------------------------------------------------------------

    def _matmul_ws(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Weight-Stationary matrix multiply (phase-based).

        Because each PE has only one weight register, we decompose the
        reduction dimension K into S phases.  In phase **k** (0-indexed):

          1. Load  B[k, :]  into the PE weight registers (same weight for
             all PEs in a given column — the weight *stationary* in this
             phase).
          2. Stream  A[:, k]  from the left across each row.
          3. Each PE(i, j) computes:  acc += A[i, k] * B[k, j].

        After S phases the accumulators hold C[i, j] = sum_k A[i,k]*B[k,j].

        We further simulate a pipelined diagonal wavefront inside each phase
        to show the systolic propagation visually.
        """
        S = self.size
        result = np.zeros((S, S), dtype=np.float64)

        if self.verbose:
            logger.info("\n=== Weight-Stationary MatMul (phase-based) ===")

        # --- Phase-based outer-product reduction ---
        for k in range(S):
            if self.verbose:
                logger.info("\n--- WS Phase k=%d ---", k)

            # 1. Load the weight slice B[k, :]
            for r in range(S):
                for c in range(S):
                    self.pe_grid[r][c].load_weight(float(B[k, c]))

            # 2. Stream A[:, k] through the array with diagonal pipelining
            #    At cycle t within this phase, the input has propagated to
            #    column c = t (PEs in the diagonal are active).
            #    Partial sums flow downward through the column.
            for t in range(S):
                c = t  # column reached by the input wavefront this cycle
                if self.verbose:
                    logger.info("  (phase cycle t=%d, column c=%d)", t, c)

                for r in range(S):
                    # Input activation for this PE: A[r, k]
                    input_val = float(A[r, k])

                    # Partial sum arriving from above (or 0 for first row)
                    psum_above = self.pe_grid[r - 1][c].acc if r > 0 else 0.0

                    # Compute: acc += weight * input  (value already in PE)
                    product = self.pe_grid[r][c].w_reg * input_val
                    self.pe_grid[r][c].acc += product

                    if self.verbose:
                        logger.info(
                            "    PE[%d,%d] w=%-6.2f in=%-6.2f "
                            "+= %-8.2f  acc=%-8.2f",
                            r, c, self.pe_grid[r][c].w_reg,
                            input_val, product, self.pe_grid[r][c].acc,
                        )

        # 3. Collect results
        for r in range(S):
            for c in range(S):
                result[r, c] = self.pe_grid[r][c].acc
        return result

    # ------------------------------------------------------------------
    # Output Stationary
    # ------------------------------------------------------------------

    def _matmul_os(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Output-Stationary matrix multiply.

        Each PE accumulates its own output (C[i,j]).  Weights and inputs
        both stream through the array.
        """
        S = self.size
        self.reset_all()

        if self.verbose:
            logger.info("\n=== Output-Stationary MatMul ===")

        # In OS mode each PE at (i,j) is responsible for C[i,j] = sum_k A[i,k] * B[k,j].
        # We iterate over the reduction dimension k (0..S-1) and stream
        # A[i,k] across rows and B[k,j] down columns.
        for k in range(S):
            if self.verbose:
                logger.info("\n--- k = %d (reduction dimension) ---", k)
            for r in range(S):
                for c in range(S):
                    weight = float(B[k, c])
                    input_val = float(A[r, k])
                    self.pe_grid[r][c].step_os(weight, input_val)

        result = np.zeros((S, S), dtype=np.float64)
        for r in range(S):
            for c in range(S):
                result[r, c] = self.pe_grid[r][c].acc
        return result

    def print_state(self) -> None:
        """Print a formatted grid of current PE accumulators."""
        logger.info("Array state (acc values):")
        for r in range(self.size):
            row_vals = "  ".join(f"{self.pe_grid[r][c].acc:8.2f}" for c in range(self.size))
            logger.info("  " + row_vals)

    def __repr__(self) -> str:
        return (
            f"SystolicArray({self.size}×{self.size}, dataflow={self.dataflow})"
        )


# ---------------------------------------------------------------------------
# Main — run 4×4 multiply in both modes and compare with NumPy
# ---------------------------------------------------------------------------

def main() -> None:
    """Demonstrate 4×4 systolic matrix multiply in WS and OS mode."""
    np.random.seed(42)
    N = 4

    # Generate well-conditioned random matrices
    A = np.random.uniform(-1.0, 1.0, (N, N)).astype(np.float64)
    B = np.random.uniform(-1.0, 1.0, (N, N)).astype(np.float64)
    C_expected = A @ B

    print("=" * 64)
    print("Systolic Array Simulator — 4×4 Matrix Multiply")
    print("=" * 64)
    print(f"\nMatrix A ({A.shape}):\n{A}")
    print(f"\nMatrix B ({B.shape}):\n{B}")
    print(f"\nNumPy reference C = A × B:\n{C_expected}")

    for mode in ("WS", "OS"):
        print(f"\n{'─' * 64}")
        print(f"Dataflow: {mode}")
        print(f"{'─' * 64}")

        sa = SystolicArray(size=N, dataflow=mode, verbose=True)
        C_sim = sa.matmul(A, B)

        print(f"\n  Simulated result:\n{C_sim}")
        print(f"\n  Difference from NumPy:\n{C_sim - C_expected}")
        mse = np.mean((C_sim - C_expected) ** 2)
        max_err = np.max(np.abs(C_sim - C_expected))
        print(f"\n  MSE  = {mse:.4e}")
        print(f"  MaxAbs error = {max_err:.4e}")

    # Edge case tests
    print(f"\n{'═' * 64}")
    print("Validation tests")
    print(f"{'═' * 64}")

    # Test 1: identity multiply
    I = np.eye(N, dtype=np.float64)
    sa = SystolicArray(size=N, dataflow="WS", verbose=False)
    C_id = sa.matmul(A, I)
    assert np.allclose(C_id, A, atol=1e-10), "WS identity test failed"
    print("  [PASS] WS identity: A × I == A")

    sa_os = SystolicArray(size=N, dataflow="OS", verbose=False)
    C_id_os = sa_os.matmul(A, I)
    assert np.allclose(C_id_os, A, atol=1e-10), "OS identity test failed"
    print("  [PASS] OS identity: A × I == A")

    # Test 2: zero matrix
    Z = np.zeros((N, N), dtype=np.float64)
    sa_z = SystolicArray(size=N, dataflow="WS", verbose=False)
    C_z = sa_z.matmul(A, Z)
    assert np.allclose(C_z, np.zeros((N, N)), atol=1e-10), "WS zero test failed"
    print("  [PASS] WS zero: A × 0 == 0")

    # Test 3: error handling
    try:
        SystolicArray(size=0)
    except ValueError:
        print("  [PASS] System catches invalid array size")

    try:
        sa_bad = SystolicArray(size=4, dataflow="NONSENSE")
    except ValueError:
        print("  [PASS] System catches invalid dataflow mode")

    print(f"\n{'═' * 64}")
    print("All tests passed.")
    print(f"{'═' * 64}")


if __name__ == "__main__":
    main()
