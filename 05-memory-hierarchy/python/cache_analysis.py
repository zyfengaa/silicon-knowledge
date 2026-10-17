"""
cache_analysis.py — Cache performance analysis visualisation.

Plots hit rate vs working set size for different cache associativities.
Demonstrates that higher associativity handles larger working sets more
gracefully before performance degrades (thrashing).

Model:
  - Cache size: 32 KB, line size: 64 B.
  - For each working set size and associativity, the hit rate is
    estimated via a simple analytical (logistic-family) model:
      * Working sets that fit in cache enjoy near-100 % hit rates.
      * As the working set exceeds capacity, the hit rate falls.
      * Higher associativity is modelled as a modest increase in
        effective capacity.
  - This is an illustrative parametric model, NOT a trace-driven or
    cycle-accurate simulation.  The associativity factor is a heuristic
    (1-way = 1.0, 2-way ~1.3, 4-way ~1.6, 8-way ~1.9), not a measurement.
    For a trace-driven experiment that actually exhibits conflict misses,
    see code/python/cache_analysis.py.

Dependencies: matplotlib, numpy
Run:
  python3 cache_analysis.py

Output:
  - Console summary of hit rates
  - Saved plot: cache_hitrate_vs_wss.png

Reference:
  Hennessy & Patterson, "Computer Architecture: A Quantitative
  Approach", 6th Ed., Chapter 2 (Memory Hierarchy Design).
  Hill, M. D. & Smith, A. J. "Evaluating Associativity in CPU Caches."
  IEEE Trans. Computers, 1989.
"""

import os
import sys

try:
    import matplotlib
    import numpy as np
except ImportError:
    sys.exit("缺少 numpy/matplotlib，请先安装：pip install numpy matplotlib")

# Use non-interactive Agg backend when no display is available
if not os.environ.get('DISPLAY'):
    matplotlib.use('Agg')

import matplotlib.pyplot as plt

# ================================================================
# Cache parameters
# ================================================================

CACHE_SIZE = 32 * 1024        # 32 KB
LINE_SIZE  = 64

ASSOCIATIVITIES = [1, 2, 4, 8]

# Working-set sizes (4 KB – 32 MB, log-spaced)
WS_MIN = 4 * 1024
WS_MAX = 32 * 1024 * 1024
NUM_POINTS = 60
working_sets = np.logspace(np.log10(WS_MIN),
                           np.log10(WS_MAX),
                           NUM_POINTS).astype(int)


# ================================================================
# Analytical hit-rate model
# ================================================================

def hit_rate_analytical(ws_size, assoc, cache_size=CACHE_SIZE):
    """Return an estimated hit rate for a given working set and associativity.

    The model is a logistic-family curve whose inflection point
    (the working-set size where hit rate drops to 50 %) shifts
    rightward with higher associativity.  This captures, qualitatively,
    the key trade-off: more ways reduce conflict misses, letting the cache
    handle larger working sets before thrashing.  It is a heuristic
    illustration, not a measured trace.

    The base inflection point is at ws_size == cache_size for a
    direct-mapped (1-way) cache.  Higher associativity multiplies
    the effective capacity by a heuristic factor (see below); this
    factor is chosen for illustration and is not fitted to measurements.
    """
    ratio = ws_size / cache_size

    if ratio <= 1.0:
        # Working set fits: residual compulsory misses only
        return 0.99

    # Capacity factor: how much the associativity extends effective reach
    # 1-way = 1.0, 2-way ~1.3, 4-way ~1.6, 8-way ~1.9
    cap_factor = 1.0 + 0.3 * np.log2(assoc)

    # Logistic decay: the hit rate falls from ~0.99 to near 0 as
    # ratio increases.  The `cap_factor` shifts the curve rightward.
    # The steepness parameter (4.0) gives a realistic transition width.
    exponent = 4.0 * (ratio / cap_factor - 1.5)
    # Clamp to avoid overflow in np.exp for large ratios
    exponent = np.clip(exponent, -700, 700)
    hr = 0.99 / (1.0 + np.exp(exponent))

    return hr


# ================================================================
# Plotting
# ================================================================

def main():
    print("=== Cache Performance: Hit Rate vs Working Set Size ===\n")
    print(f"  Cache: {CACHE_SIZE // 1024} KB, Line: {LINE_SIZE} B")
    print(f"  Model: illustrative parametric (logistic-family), not a trace simulation")
    print(f"  Assumption: higher associativity extends effective capacity\n")

    # Compute data for each associativity
    results = {}
    for a in ASSOCIATIVITIES:
        results[a] = [hit_rate_analytical(ws, a) for ws in working_sets]

    # Print numerical summary
    print(f"{'WSS (KB)':>10}", end="")
    for a in ASSOCIATIVITIES:
        print(f"  {a}-way", end="")
    print()
    skip = max(1, NUM_POINTS // 8)
    for idx in range(0, NUM_POINTS, skip):
        print(f"{working_sets[idx] // 1024:>10d}", end="")
        for a in ASSOCIATIVITIES:
            print(f"  {results[a][idx]:.4f}", end="")
        print()

    # ---- Plot ----
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    markers = ['o', 's', '^', 'D']
    for idx, a in enumerate(ASSOCIATIVITIES):
        ax.plot(working_sets / 1024, results[a],
                marker=markers[idx], markersize=3, linewidth=1.5,
                label=f'{a}-way')

    # Vertical line at cache capacity
    ax.axvline(x=CACHE_SIZE / 1024, color='gray', linestyle='--',
               alpha=0.6, label=f'Cache size ({CACHE_SIZE // 1024} KB)')

    ax.set_xlabel('Working Set Size (KB)')
    ax.set_ylabel('Hit Rate')
    ax.set_title('Cache Performance: Hit Rate vs Working Set Size')
    ax.set_xscale('log')
    ax.set_xlim(left=WS_MIN / 1024, right=WS_MAX / 1024)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(title='Associativity')
    ax.grid(True, alpha=0.3, which='both')

    plt.tight_layout()
    outdir = os.path.dirname(os.path.abspath(__file__))
    outpath = os.path.join(outdir, 'cache_hitrate_vs_wss.png')
    plt.savefig(outpath, dpi=150)
    print(f"\nPlot saved to {outpath}")

    if os.environ.get('DISPLAY'):
        plt.show()


if __name__ == '__main__':
    main()
