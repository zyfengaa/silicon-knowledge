"""
JAX TPU Basics — Demonstrates core JAX features on TPU (with CPU fallback).

This script covers:
  1. Device detection (TPU / CPU / GPU)
  2. jit — Just-In-Time compilation with XLA
  3. vmap — Automatic vectorisation (SIMD within a device)
  4. pmap — Parallel map across multiple devices (SPMD)
  5. Benchmark: matmul with / without jit

Requirements:
    pip install jax jaxlib

References:
    - JAX documentation: https://jax.readthedocs.io/
    - XLA documentation: https://www.tensorflow.org/xla
    - TPU quickstart: https://cloud.google.com/tpu/docs/jax-quickstart
"""

import time
import sys
from typing import Tuple

# ---------------------------------------------------------------------------
# Graceful import — if JAX is missing we print instructions and exit.
# ---------------------------------------------------------------------------
try:
    import jax
    import jax.numpy as jnp
    from jax import jit, vmap, pmap
except ImportError:
    print("=" * 65)
    print("  JAX is not installed.  To install, run:")
    print()
    print("      pip install jax jaxlib")
    print()
    print("  For TPU support (Colab / Cloud TPU VM):")
    print("      pip install jax[tpu] -f https://storage.googleapis.com/jax-releases/libtpu_releases.html")
    print("=" * 65)
    sys.exit(0)


# ===================================================================
# 1.  Device Detection
# ===================================================================
def detect_devices() -> None:
    """
    Print the number and type of available accelerators.

    JAX exposes devices through ``jax.devices()``.  On a Cloud TPU VM this
    will typically return 4 or 8 TPU chips; on Colab it may return 1 TPU;
    otherwise we fall back to CPU or GPU.
    """
    devices = jax.devices()
    print(f"[Device Detection]  Found {len(devices)} device(s):")
    for i, dev in enumerate(devices):
        print(f"    [{i}] {dev}")

    # Show the default backend platform
    platform = jax.default_backend()
    print(f"[Platform]         jax.default_backend() = {platform}")
    print()


# ===================================================================
# 2.  jit — Just-In-Time compilation
# ===================================================================
@jit
def matmul_jit(x: jnp.ndarray, y: jnp.ndarray) -> jnp.ndarray:
    """JIT-compiled matrix multiplication."""
    return jnp.dot(x, y)


def matmul_no_jit(x: jnp.ndarray, y: jnp.ndarray) -> jnp.ndarray:
    """Eager (non-compiled) matrix multiplication for comparison."""
    return jnp.dot(x, y)


def demo_jit(size: int = 2048) -> None:
    """
    Demonstrate and benchmark JIT compilation.

    The first call to a ``@jit``-decorated function triggers XLA compilation.
    Subsequent calls reuse the cached executable and are significantly faster.
    """
    print("=" * 60)
    print("  2.  JIT Compilation Demo")
    print("=" * 60)

    # Create random matrices on the default device
    key = jax.random.PRNGKey(42)
    x = jax.random.normal(key, (size, size), dtype=jnp.float32)
    y = jax.random.normal(key + 1, (size, size), dtype=jnp.float32)

    # Warm-up / compile (timing irrelevant)
    _ = matmul_jit(x, y)

    # --- Benchmark: with JIT ---
    n_runs = 10
    t_jit = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        _ = matmul_jit(x, y).block_until_ready()
        t1 = time.perf_counter()
        t_jit.append(t1 - t0)

    avg_jit = (sum(t_jit) / len(t_jit)) * 1000  # ms

    # --- Benchmark: without JIT ---
    t_eager = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        _ = matmul_no_jit(x, y).block_until_ready()
        t1 = time.perf_counter()
        t_eager.append(t1 - t0)

    avg_eager = (sum(t_eager) / len(t_eager)) * 1000  # ms

    print(f"  Matrix size:                {size} x {size}")
    print(f"  Runs per mode:              {n_runs}")
    print(f"  Avg. time (with JIT):       {avg_jit:.3f} ms")
    print(f"  Avg. time (without JIT):    {avg_eager:.3f} ms")
    print(f"  Speed-up (eager / jit):     {avg_eager / avg_jit:.1f}x")
    print()


# ===================================================================
# 3.  vmap — Automatic vectorisation
# ===================================================================
def single_row_operation(row: jnp.ndarray, weight: jnp.ndarray) -> jnp.ndarray:
    """
    Compute the dot product of a single row with a weight matrix.

    When we ``vmap`` this function over the leading axis of a batch of rows,
    JAX automatically generates the batched (vectorised) computation graph.
    """
    return jnp.dot(row, weight)


def demo_vmap(batch_size: int = 128, feat_dim: int = 64) -> None:
    """
    Demonstrate ``vmap``: turn a per-row function into a batched one.
    """
    print("=" * 60)
    print("  3.  vmap — Automatic Vectorisation")
    print("=" * 60)

    key = jax.random.PRNGKey(99)
    batch = jax.random.normal(key, (batch_size, feat_dim))
    weight = jax.random.normal(key + 1, (feat_dim, feat_dim))

    # Manually loop over rows (slow, for illustration)
    t0 = time.perf_counter()
    results_loop = jnp.array(
        [single_row_operation(batch[i], weight) for i in range(batch_size)]
    )
    # Force computation
    results_loop.block_until_ready()
    t_loop = time.perf_counter() - t0

    # vmap — automatic batching
    batched_fn = vmap(single_row_operation)
    t0 = time.perf_counter()
    results_vmap = batched_fn(batch, weight).block_until_ready()
    t_vmap = time.perf_counter() - t0

    # Verify correctness
    diff = jnp.max(jnp.abs(results_loop - results_vmap))
    print(f"  Batch size:                 {batch_size}")
    print(f"  Feature dim:                {feat_dim}")
    print(f"  Loop time:                  {t_loop * 1000:.3f} ms")
    print(f"  vmap time:                  {t_vmap * 1000:.3f} ms")
    print(f"  Speed-up:                   {t_loop / t_vmap:.1f}x")
    print(f"  Max diff (correctness):     {diff:.2e}")
    print()

    # JIT + vmap combine naturally
    @jit
    def fast_batched_fn(x, w):
        return vmap(single_row_operation)(x, w)

    t0 = time.perf_counter()
    _ = fast_batched_fn(batch, weight).block_until_ready()
    _ = fast_batched_fn(batch, weight).block_until_ready()  # compiled
    t1 = time.perf_counter()
    print(f"  vmap + jit time:            {(t1 - t0) * 1000:.3f} ms (2nd call)")
    print()


# ===================================================================
# 4.  pmap — Parallel map across devices (SPMD)
# ===================================================================
def element_wise_square(x: jnp.ndarray) -> jnp.ndarray:
    """Simple element-wise operation to illustrate SPMD."""
    return x ** 2 + 2 * x + 1


def demo_pmap(size: int = 4096) -> None:
    """
    Demonstrate ``pmap``: replicate data across devices and run in parallel.

    ``pmap`` compiles the function with XLA's SPMD partitioner so that each
    device executes the same program on a different shard of the input.
    """
    print("=" * 60)
    print("  4.  pmap — Parallel Map (SPMD)")
    print("=" * 60)

    devices = jax.devices()
    n_devices = len(devices)
    print(f"  Devices available:          {n_devices}")

    if n_devices == 1:
        print("  Skipping pmap demo (only 1 device).")
        print()
        return

    # Create data and split along first axis
    key = jax.random.PRNGKey(7)
    data = jax.random.normal(key, (n_devices, size))

    # pmap: shard data across devices automatically
    pmap_square = pmap(element_wise_square)

    # Warm-up compile
    _ = pmap_square(data)

    t0 = time.perf_counter()
    result = pmap_square(data)
    # block on all devices
    result.block_until_ready()
    t_pmap = time.perf_counter() - t0

    # Verify by checking on the first device
    single_device = jax.devices()[0]
    local_result = jax.device_get(jax.device_put(result[0], device=single_device))
    local_input = jax.device_get(jax.device_put(data[0], device=single_device))
    expected = element_wise_square(local_input)
    diff = jnp.max(jnp.abs(local_result - expected))
    print(f"  Data shard per device:      {size} elements")
    print(f"  pmap time:                  {t_pmap * 1000:.3f} ms")
    print(f"  Max diff (correctness):     {diff:.2e}")
    print()


# ===================================================================
# 5.  Main
# ===================================================================
def main():
    print()
    print("=" * 60)
    print("  JAX TPU Basics — JIT / vmap / pmap / Benchmark")
    print("=" * 60)
    print()

    detect_devices()
    demo_jit(size=2048)
    demo_vmap(batch_size=128, feat_dim=64)
    demo_pmap(size=4096)

    print("=" * 60)
    print("  All demonstrations completed successfully.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()


# ===================================================================
# References
# ===================================================================
# - JAX: https://jax.readthedocs.io/
# - XLA: https://www.tensorflow.org/xla
# - TPU quickstart: https://cloud.google.com/tpu/docs/jax-quickstart
#
## 参考文献
