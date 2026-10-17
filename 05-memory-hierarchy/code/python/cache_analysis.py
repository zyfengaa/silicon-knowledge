"""
cache_analysis.py — Cache performance analysis by trace-driven simulation.

Plots hit rate vs working set size for different cache associativities.

Access pattern (deliberately conflict-heavy):
  - The simulated cache is 32 KB with 64 B lines (512 lines).
  - Every access is 64 B apart.  Line i of the working set is mapped to
    set (i % 64) and tag (i // 64), i.e. only 64 of the cache's sets are
    ever used, and successive visits to the same set use a new tag.
  - With this pattern, a set can retain at most `assoc` lines.  Once the
    working set exceeds assoc * 64 lines (= assoc * 4 KB), the per-set
    working set no longer fits and LRU evicts the line that will be
    requested next -> a conflict-miss cliff.
  - Therefore the onset of thrashing moves right as associativity grows:
    1-way at 4 KB, 2-way at 8 KB, 4-way at 16 KB, 8-way at 32 KB.
  - The first pass is compulsory misses, so the maximum observable hit
    rate is 4/5 = 0.80, not 1.0.  When a set thrashes, every pass misses
    and the hit rate falls to 0.0.

This is a synthetic worst case designed to expose conflict misses.  It is
not representative of average application behaviour, where sequential
access and prefetching make higher associativity far less dramatic.

Dependencies: matplotlib, numpy
Run:
  python -I cache_analysis.py

Output:
  - Console summary of hit rates.
  - Saved plot: cache_hitrate_vs_wss.png (next to this script).
  - Interactive plot window only when a display is available.

Reference:
  Hennessy & Patterson, "Computer Architecture: A Quantitative
  Approach", 6th Ed., Chapter 2.
"""

import os
import sys

try:
    import numpy as np
    import matplotlib
except ImportError:
    sys.exit("缺少 numpy/matplotlib，请先安装：pip install numpy matplotlib")

# Avoid blocking/failing in headless environments: use Agg unless we are
# attached to an interactive terminal with a display.
_INTERACTIVE = sys.stdout.isatty() and (
    os.name == 'nt' or bool(os.environ.get('DISPLAY'))
)
if not _INTERACTIVE:
    matplotlib.use('Agg')

import matplotlib.pyplot as plt

# ================================================================
# Cache parameters
# ================================================================

CACHE_SIZE = 32 * 1024       # 32 KB
LINE_SIZE  = 64               # 64 B per line
NUM_LINES  = CACHE_SIZE // LINE_SIZE

ASSOCIATIVITIES = [1, 2, 4, 8]

# Common index space for all associativities: the smallest cache (8-way)
# has NUM_LINES / 8 = 64 sets.  Keeping accesses within these 64 sets
# guarantees that every associativity sees the same set indices, so the
# only variable is how many lines each set can retain.
NUM_CONFLICT_SETS = NUM_LINES // max(ASSOCIATIVITIES)

# Working-set sizes (4 KB - 256 KB, log-spaced)
WS_MIN = 4 * 1024
WS_MAX = 256 * 1024
NUM_POINTS = 40
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
        if num_sets <= 0 or (num_sets & (num_sets - 1)) != 0:
            raise ValueError("number of sets must be a positive power of two")

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
    """Run a conflict-heavy trace of `ws_size` bytes, repeated 5 times.

    Line i of the working set maps to set (i % NUM_CONFLICT_SETS) and to a
    fresh tag for each 64-line group.  Every access touches a distinct
    cache line (one 64 B line), so all reuse is inter-pass reuse.
    Returns the observed hit rate.
    """
    sim = CacheSim(cache_size, line_size, assoc)

    num_lines_ws = max(1, ws_size // line_size)
    repeats = 5

    # Precompute the line addresses once: line i -> (tag * NUM_LINES + set).
    # Since set < NUM_CONFLICT_SETS <= num_sets for every associativity,
    # the cache index equals `set` in all configurations.
    addrs = [
        (((i // NUM_CONFLICT_SETS) * NUM_LINES + (i % NUM_CONFLICT_SETS))
         * line_size) & 0xFFFFFFFF
        for i in range(num_lines_ws)
    ]

    hits = 0
    total = 0
    for _ in range(repeats):
        for addr in addrs:
            if sim.access(addr):
                hits += 1
            total += 1

    return hits / total if total > 0 else 0.0


# ================================================================
# Plotting
# ================================================================

def main():
    print("=== Cache Performance: Hit Rate vs Working Set Size ===")
    print("  Trace: conflict-heavy stride (64 B), 64 active sets, 5 passes")
    print("  Max hit rate is 4/5 = 0.80 (first pass is compulsory misses)")
    print(f"  Cache: {CACHE_SIZE // 1024} KB, Line: {LINE_SIZE} B\n")

    results = {a: [] for a in ASSOCIATIVITIES}
    for ws in working_sets:
        for a in ASSOCIATIVITIES:
            results[a].append(estimate_hit_rate(ws, a))

    # Print numerical summary
    print(f"{'Working Set (KB)':>16}", end="")
    for a in ASSOCIATIVITIES:
        print(f"  Hit Rate ({a}-way)", end="")
    print()

    step = max(1, NUM_POINTS // 12)
    for idx in range(0, NUM_POINTS, step):
        ws = working_sets[idx]
        print(f"{ws // 1024:>16d}", end="")
        for a in ASSOCIATIVITIES:
            print(f"  {results[a][idx]:13.4f}", end="")
        print()

    # ---- Plot ----
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except OSError:
        pass

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
    ax.set_title('Conflict Misses: Hit Rate vs Working Set Size')
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

    if _INTERACTIVE:
        plt.show()


if __name__ == '__main__':
    main()
