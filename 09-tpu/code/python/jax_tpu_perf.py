"""
JAX TPU Performance — Linear Regression Training with Timing.

Trains a simple linear model  y = W * x + b  using MSE loss and
JIT-compiled gradient descent.  Collects per-step timing data and
compares against a NumPy CPU reference implementation.

Learning objectives:
  - Writing a JAX training step (forward + backward) under @jit.
  - Using jax.grad for automatic differentiation.
  - Benchmarking TPU vs CPU for a small workload.
  - Understanding compilation overhead vs. steady-state performance.

Requirements:
    pip install jax jaxlib numpy

References:
    - JAX documentation: https://jax.readthedocs.io/
    - JAX training examples: https://jax.readthedocs.io/en/latest/notebooks/neural_network_with_tfds_data.html
    - TensorFlow performance guide: https://www.tensorflow.org/guide/performance/overview
"""

import time
import sys
from typing import Dict, List, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Graceful import
# ---------------------------------------------------------------------------
try:
    import jax
    import jax.numpy as jnp
    from jax import jit, grad
except ImportError:
    print("=" * 65)
    print("  JAX is not installed.  To install, run:")
    print()
    print("      pip install jax jaxlib")
    print()
    print("  For TPU support:")
    print("      pip install jax[tpu] -f https://storage.googleapis.com/jax-releases/libtpu_releases.html")
    print("=" * 65)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------
def generate_data(
    n_samples: int = 65536,
    n_features: int = 64,
    noise_std: float = 0.1,
    seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic linear data:  y = X @ W_true + b_true + noise.

    Returns:
        X_np, y_np, W_true, b_true  as NumPy arrays (used later for comparison).
    """
    rng = np.random.default_rng(seed)
    W_true = rng.normal(0, 1.0, size=(n_features, 1)).astype(np.float32)
    b_true = rng.normal(0, 0.5, size=(1,)).astype(np.float32)

    X = rng.normal(0, 1.0, size=(n_samples, n_features)).astype(np.float32)
    y = X @ W_true + b_true + noise_std * rng.normal(0, 1.0, size=(n_samples, 1)).astype(np.float32)
    return X, y, W_true.flatten(), b_true[0]


# ---------------------------------------------------------------------------
# Model definition (JAX)
# ---------------------------------------------------------------------------
def predict_jax(W: jnp.ndarray, b: jnp.ndarray, X: jnp.ndarray) -> jnp.ndarray:
    """Linear prediction: y_pred = X @ W + b."""
    return X @ W + b


def mse_loss_jax(W: jnp.ndarray, b: jnp.ndarray, X: jnp.ndarray, y: jnp.ndarray) -> jnp.ndarray:
    """Mean Squared Error loss."""
    y_pred = predict_jax(W, b, X)
    return jnp.mean((y_pred - y) ** 2)


# Compute gradients using JAX's automatic differentiation
loss_grad = grad(mse_loss_jax, argnums=(0, 1))  # grad w.r.t. W and b


@jit
def train_step_jit(
    W: jnp.ndarray,
    b: jnp.ndarray,
    X: jnp.ndarray,
    y: jnp.ndarray,
    lr: float,
) -> Tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    """
    One step of SGD — JIT-compiled.

    Returns:
        Updated W, updated b, current loss.
    """
    loss = mse_loss_jax(W, b, X, y)
    dW, db = loss_grad(W, b, X, y)
    W_new = W - lr * dW
    b_new = b - lr * db
    return W_new, b_new, loss


# ---------------------------------------------------------------------------
# NumPy CPU reference (no autograd — manual gradient)
# ---------------------------------------------------------------------------
def mse_loss_np(W: np.ndarray, b: float, X: np.ndarray, y: np.ndarray) -> float:
    y_pred = X @ W + b
    return float(np.mean((y_pred - y) ** 2))


def train_step_np(
    W: np.ndarray,
    b: float,
    X: np.ndarray,
    y: np.ndarray,
    lr: float,
) -> Tuple[np.ndarray, float, float]:
    """
    One step of SGD — NumPy reference (manual gradients).
    """
    y_pred = X @ W + b
    loss = np.mean((y_pred - y) ** 2)

    # dL/dW = (2/N) * X^T (y_pred - y)
    grad_W = (2.0 / X.shape[0]) * X.T @ (y_pred - y)
    # dL/db = (2/N) * sum(y_pred - y)
    grad_b = (2.0 / X.shape[0]) * np.sum(y_pred - y)

    W_new = W - lr * grad_W
    b_new = b - lr * grad_b
    return W_new, b_new, loss


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train_jax(
    X: np.ndarray,
    y: np.ndarray,
    n_steps: int = 1000,
    lr: float = 0.01,
    verbose: bool = True,
) -> Dict[str, List[float]]:
    """
    Train linear regression with JAX (JIT-compiled).

    Returns:
        Dictionary with timing and loss history.
    """
    n_features = X.shape[1]
    # Move data to the default JAX device
    X_jax = jnp.array(X)
    y_jax = jnp.array(y)

    # Initialise parameters
    key = jax.random.PRNGKey(42)
    W = jax.random.normal(key, (n_features, 1)) * 0.01
    b = jnp.zeros((1,))

    # Flatten for convenience
    W = W.flatten()

    times: List[float] = []
    losses: List[float] = []

    # Warm-up step (compiles the train_step)
    W, b, _ = train_step_jit(W, b, X_jax, y_jax, lr)

    for step in range(n_steps):
        t0 = time.perf_counter()
        W, b, loss = train_step_jit(W, b, X_jax, y_jax, lr)
        loss.block_until_ready()
        t1 = time.perf_counter()

        times.append(t1 - t0)
        losses.append(float(loss))

        if verbose and (step + 1) % 200 == 0:
            avg = np.mean(times[-200:]) * 1000
            print(f"    Step {step + 1:5d}  |  loss {losses[-1]:.6f}  |  avg step {avg:.4f} ms")

    stats = {
        "times_ms": [t * 1000 for t in times],
        "losses": losses,
        "final_W": np.array(jax.device_get(W)),
        "final_b": float(jax.device_get(b)),
    }
    return stats


def train_numpy(
    X: np.ndarray,
    y: np.ndarray,
    n_steps: int = 1000,
    lr: float = 0.01,
    verbose: bool = True,
) -> Dict[str, List[float]]:
    """
    Train linear regression with NumPy on CPU.

    Returns:
        Dictionary with timing and loss history.
    """
    n_features = X.shape[1]
    W = np.random.default_rng(42).normal(0, 0.01, size=(n_features,)).astype(np.float32)
    b = 0.0

    # y is (N, 1); flatten for linear algebra convenience
    y_flat = y.flatten()

    times: List[float] = []
    losses: List[float] = []

    for step in range(n_steps):
        t0 = time.perf_counter()
        W, b, loss = train_step_np(W, b, X, y_flat, lr)
        t1 = time.perf_counter()

        times.append(t1 - t0)
        losses.append(loss)

        if verbose and (step + 1) % 200 == 0:
            avg = np.mean(times[-200:]) * 1000
            print(f"    Step {step + 1:5d}  |  loss {loss:.6f}  |  avg step {avg:.4f} ms")

    stats = {
        "times_ms": [t * 1000 for t in times],
        "losses": losses,
        "final_W": W,
        "final_b": b,
    }
    return stats


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------
def print_comparison(
    jax_stats: Dict,
    np_stats: Dict,
    n_steps: int,
    n_samples: int,
    n_features: int,
) -> None:
    """Print a text-format comparison table."""
    jax_avg = np.mean(jax_stats["times_ms"])
    jax_std = np.std(jax_stats["times_ms"])
    np_avg = np.mean(np_stats["times_ms"])
    np_std = np.std(np_stats["times_ms"])

    print()
    print("=" * 72)
    print("  Performance Comparison: JAX (TPU/GPU) vs NumPy (CPU)")
    print("=" * 72)
    print(f"  Dataset:  {n_samples} samples, {n_features} features,")
    print(f"            {n_steps} training steps")
    print()
    print(f"  {'Metric':<35} {'JAX (TPU/GPU)':<18} {'NumPy (CPU)':<18}")
    print(f"  {'-' * 35} {'-' * 18} {'-' * 18}")
    print(f"  {'Total training time (ms)':<35} {sum(jax_stats['times_ms']):<18.2f} {sum(np_stats['times_ms']):<18.2f}")
    print(f"  {'Average step time (ms)':<35} {jax_avg:<18.4f} {np_avg:<18.4f}")
    print(f"  {'Std dev step time (ms)':<35} {jax_std:<18.4f} {np_std:<18.4f}")
    print(f"  {'Final loss':<35} {jax_stats['losses'][-1]:<18.6f} {np_stats['losses'][-1]:<18.6f}")
    print(f"  {'Speed-up (CPU avg / JAX avg)':<35} {np_avg / jax_avg:<18.1f}x")
    print()

    # Print first 5 and last 5 step times for inspection
    print("  Step-time samples (ms):")
    print(f"    JAX first 5:    {', '.join(f'{t:.3f}' for t in jax_stats['times_ms'][:5])}")
    print(f"    JAX last 5:     {', '.join(f'{t:.3f}' for t in jax_stats['times_ms'][-5:])}")
    print(f"    NumPy first 5:  {', '.join(f'{t:.3f}' for t in np_stats['times_ms'][:5])}")
    print(f"    NumPy last 5:   {', '.join(f'{t:.3f}' for t in np_stats['times_ms'][-5:])}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print()
    print("=" * 72)
    print("  JAX TPU Performance — Linear Regression Benchmark")
    print("=" * 72)

    # Hyper-parameters
    N_SAMPLES = 65536
    N_FEATURES = 64
    N_STEPS = 1000
    LR = 0.01

    print(f"\n  Generating synthetic data ({N_SAMPLES} samples, {N_FEATURES} features)...")
    X, y, W_true, b_true = generate_data(
        n_samples=N_SAMPLES, n_features=N_FEATURES, noise_std=0.1, seed=0,
    )
    print(f"  True W[:4]: {W_true[:4]}")
    print(f"  True b:     {b_true:.4f}")
    print()

    # ---- JAX Training ----
    print("  --- JAX (JIT-compiled) Training ---")
    key = jax.random.PRNGKey(42)
    X_jax = jnp.array(X)
    y_jax = jnp.array(y)
    W = jax.random.normal(key, (N_FEATURES, 1)) * 0.01
    b = jnp.zeros((1,))
    W = W.flatten()

    # Warm-up compile
    W, b, _ = train_step_jit(W, b, X_jax, y_jax, LR)

    jax_times = []
    jax_losses = []
    for step in range(N_STEPS):
        t0 = time.perf_counter()
        W, b, loss = train_step_jit(W, b, X_jax, y_jax, LR)
        loss.block_until_ready()
        t1 = time.perf_counter()
        jax_times.append((t1 - t0) * 1000)
        jax_losses.append(float(loss))
        if (step + 1) % 200 == 0:
            avg = np.mean(jax_times[-200:])
            print(f"    Step {step + 1:5d}  |  loss {loss:.6f}  |  avg step {avg:.4f} ms")

    jax_stats = {
        "times_ms": jax_times,
        "losses": jax_losses,
    }
    print()

    # ---- NumPy Training ----
    print("  --- NumPy (CPU) Training ---")
    np_times = []
    np_losses = []
    W_np = np.random.default_rng(42).normal(0, 0.01, size=(N_FEATURES,)).astype(np.float32)
    b_np = 0.0
    y_flat = y.flatten()
    for step in range(N_STEPS):
        t0 = time.perf_counter()
        y_pred = X @ W_np + b_np
        loss_np = float(np.mean((y_pred - y_flat) ** 2))
        grad_W = (2.0 / N_SAMPLES) * X.T @ (y_pred - y_flat)
        grad_b = (2.0 / N_SAMPLES) * np.sum(y_pred - y_flat)
        W_np = W_np - LR * grad_W
        b_np = b_np - LR * grad_b
        t1 = time.perf_counter()
        np_times.append((t1 - t0) * 1000)
        np_losses.append(loss_np)
        if (step + 1) % 200 == 0:
            avg = np.mean(np_times[-200:])
            print(f"    Step {step + 1:5d}  |  loss {loss_np:.6f}  |  avg step {avg:.4f} ms")

    np_stats = {
        "times_ms": np_times,
        "losses": np_losses,
    }
    print()

    # ---- Comparison ----
    print_comparison(jax_stats, np_stats, N_STEPS, N_SAMPLES, N_FEATURES)

    print("=" * 72)
    print("  Benchmark complete.")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()


# ===================================================================
# References
# ===================================================================
# - JAX: https://jax.readthedocs.io/
# - JAX training examples: https://jax.readthedocs.io/en/latest/notebooks/neural_network_with_tfds_data.html
# - TensorFlow performance guide: https://www.tensorflow.org/guide/performance/overview
#
## 参考文献
