"""
cache_analysis.py — Cache performance analysis visualisation.

Plots hit rate vs working set size for different cache associativities.
Demonstrates that higher associativity handles larger working sets more
gracefully before performance degrades (thrashing).

Simulation model:
  - Cache size: 32 KB, line size: 64 B.
  - For a given working set and associativity, the access pattern is a
    sequential scan of the working set, repeated several times.
  - When the working set fits in the cache, hit rate is near 1.0.
  - As the working set exceeds the cache, capacity misses cause the
    hit rate to drop.  Higher associativity mitigates conflict misses,
    so the onset of thrashing shifts right.

Dependencies: matplotlib, numpy
Run:
  python3 cache_analysis.py

Output:
  - Console summary of hit rates.
  - Saved plot: cache_hitrate_vs_wss.png
  - Interactive plot window.

Reference:
  Hennessy & Patterson, "Computer Architecture: A Quantitative
  Approach", 6th Ed., Chapter 2.
"""

import numpy as np
import matplotlib.pyplot as plt

# ================================================================
# Cache parameters
# ================================================================

CACHE_SIZE = 32 * 1024       # 32 KB
LINE_SIZE  = 64               # 64 B per line
NUM_LINES  = CACHE_SIZE // LINE_SIZE

ASSOCIATIVITIES = [1, 2, 4, 8]

# Working-set sizes (4 KB – 32 MB, log-spaced)
WS_MIN = 4 * 1024
WS_MAX = 32 * 1024 * 1024
NUM_POINTS = 60
working_sets = np.logspace(np.log10(WS_MIN),
                           np.log10(WS_MAX),
                           NUM_POINTS).astype(int)


# ================================================================
# Simple cache simulator
# ================================================================

class CacheSim:
    """Minimal LRU cache simulator for hit-rate estimation."""

    def __init__(self, cache_size, line_size, assoc):
        num_lines = cache_size // line_size
        num_sets  = num_lines // assoc
        self.assoc      = assoc
        self.num_sets   = num_sets
        self.line_bits  = int(np.log2(line_size))
        self.index_bits = int(np.log2(num_sets))

        # Per-set storage: each set holds `assoc` (tag, valid, lru) triples
        self.tags  = np.zeros((num_sets, assoc), dtype=np.int64)
        self.valid = np.zeros((num_sets, assoc), dtype=bool)
        self.lru   = np.zeros((num_sets, assoc), dtype=np.int64)
        self.clock = 0

    def access(self, addr):
        """Simulate one access; return True on hit, False on miss."""
        mask = (1 << self.index_bits) - 1
        idx  = (addr >> self.line_bits) & mask
        tag  = addr >> (self.line_bits + self.index_bits)

        # Search for hit
        for way in range(self.assoc):
            if self.valid[idx, way] and self.tags[idx, way] == tag:
                self.lru[idx, way] = self.clock
                self.clock += 1
                return True

        # Miss — find LRU (or empty) victim
        victim = 0
        for way in range(self.assoc):
            if not self.valid[idx, way]:
                victim = way
                break
            if self.lru[idx, way] < self.lru[idx, victim]:
                victim = way

        self.tags[idx, victim]  = tag
        self.valid[idx, victim] = True
        self.lru[idx, victim]   = self.clock
        self.clock += 1
        return False


def estimate_hit_rate(ws_size, assoc,
                      cache_size=CACHE_SIZE, line_size=LINE_SIZE):
    """Run a sequential scan of `ws_size` bytes, repeated 5 times,
    and return the observed hit rate."""

    sim = CacheSim(cache_size, line_size, assoc)

    # Generate addresses: every 4 bytes (word-aligned)
    num_words = ws_size // 4
    repeats   = 5

    hits = 0
    total = 0
    for _ in range(repeats):
        for w in range(num_words):
            addr = (w * 4) & 0xFFFFFFFF
            if sim.access(addr):
                hits += 1
            total += 1

    return hits / total if total > 0 else 0.0


# ================================================================
# Plotting
# ================================================================

def main():
    print("=== Cache Performance: Hit Rate vs Working Set Size ===\n")
    print(f"  Cache: {CACHE_SIZE // 1024} KB, Line: {LINE_SIZE} B\n")
    print(f"{'Working Set (KB)':>16}", end="")
    for a in ASSOCIATIVITIES:
        print(f"  Hit Rate ({a}-way)", end="")
    print()

    # Collect data for each associativity
    results = {}
    for a in ASSOCIATIVITIES:
        results[a] = []
    for ws in working_sets:
        for a in ASSOCIATIVITIES:
            hr = estimate_hit_rate(ws, a)
            results[a].append(hr)

    # Print numerical summary (every 5th row)
    for idx in range(0, NUM_POINTS, max(1, NUM_POINTS // 12)):
        ws = working_sets[idx]
        print(f"{ws // 1024:>16d}", end="")
        for a in ASSOCIATIVITIES:
            print(f"  {results[a][idx]:13.4f}", end="")
        print()

    # ---- Plot ----
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    markers = ['o', 's', '^', 'D']
    for idx, a in enumerate(ASSOCIATIVITIES):
        ax.plot(working_sets / 1024, results[a],
                marker=markers[idx], markersize=4, linewidth=1.5,
                label=f'{a}-way')

    # Vertical line indicating cache capacity
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
    plt.savefig('cache_hitrate_vs_wss.png', dpi=150)
    print(f"\nPlot saved to cache_hitrate_vs_wss.png")
    plt.show()


if __name__ == '__main__':
    main()
