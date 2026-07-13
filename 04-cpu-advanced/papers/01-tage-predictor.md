# Paper Note: TAGE-SC-L Branch Predictors

## Paper Information

- **Title:** TAGE-SC-L Branch Predictors
- **Author:** Andre Seznec (Inria)
- **Published in:** Journal of Instruction-Level Parallelism (JILP), 2014
- **DOI:** 10.5555/2692286.2692287

## Also Referenced

- Seznec, A. & Michaud, P. "A Case for (Partially) Tagged Geometric History Length Branch Prediction." *JILP*, 2006. (Original TAGE proposal)
- Yeh, T.-Y. & Patt, Y. N. "Two-Level Adaptive Training Branch Prediction." *MICRO-24*, 1991.
- Seznec, A. "The L-TAGE Branch Predictor." *JILP*, 2007.

## One-Sentence Contribution

TAGE (Tagged Geometric History Length) achieves near-optimal branch prediction accuracy -- often exceeding 95% for CINT and 90% for CFP -- by combining multiple predictor tables indexed with geometrically increasing history lengths, using tagged entries to resolve conflicts, all while keeping storage under practical limits (e.g., 32 Kbits for the championship-class configuration).

## Background: Why We Need Better Branch Prediction

Modern superscalar processors issue multiple instructions per cycle across deep pipelines (15--25 stages). Every branch -- roughly one every five to six instructions -- threatens to stall the front-end while the outcome resolves. The cost of a misprediction is the pipeline flush penalty multiplied by the issue width: on a 4-wide, 20-stage machine, a single misprediction wastes up to 80 instructions of work.

Early predictors used simple 2-bit saturating counters (Smith, 1981), which capture the bias of a branch (e.g., always-taken or mostly-taken) but fail on branches with periodic or context-dependent behavior. Two-level adaptive predictors (Yeh & Patt, 1991) improved accuracy by tracking the outcomes of recent branches (the *global history*) and using that pattern to index a table of counters. However, these predictors still struggle when different branches interfere in the predictor table, a problem known as *aliasing*.

The key insight behind TAGE is that different branches benefit from different amounts of history. A loop-closing branch may be perfectly predicted with only 4--8 bits of history, while a branch deep inside nested conditionals might need 100+ bits. TAGE addresses both extremes -- and everything in between -- in a single, storage-efficient design.

## Key Concepts

### Tagged Geometric History Lengths

TAGE maintains multiple predictor tables, each associated with a different history length. The lengths grow geometrically: if the shortest table uses L bits of history, the next uses ~2L, then ~4L, and so on. For example, a typical 32-Kbit TAGE configuration might use history lengths of 4, 8, 16, 32, 64, 128, and 256 bits.

The geometric progression is deliberate: it covers a wide range of correlation distances with a small number of tables. Linear growth (e.g., 2, 4, 6, 8, ...) would require many more tables to reach the same maximum history length, consuming more area and access energy.

### TAGE Tables

Each TAGE table is a direct-mapped array of entries. Each entry contains:

1. **A saturating counter** (typically 3 bits): Predicts the branch direction (taken / not taken).
2. **A tag** (typically 8--12 bits): A hash of the branch PC and the global history. The tag verifies that this entry actually corresponds to the current branch-history combination.
3. **A useful bit** (1 bit): Indicates whether the entry has contributed useful predictions recently, used by the replacement policy.

When a branch is predicted, all tables are read in parallel. The prediction is provided by the *longest-history table that produces a tag match*. If no table matches, a base predictor (a simple 2-bit counter indexed by PC) supplies the default prediction. This "longest-match-wins" policy is the heart of TAGE: short-history tables handle common patterns, while long-history tables capture rare but highly correlated contexts.

### Why Longer Histories Improve Prediction Accuracy

Consider a branch deep inside three nested loops. Its outcome may depend on the branch history from hundreds of instructions ago. Two-level predictors with a fixed, short history window cannot capture this correlation. TAGE's longest tables can, because they index using 128 or 256 bits of global history.

Conversely, a short-history table handles branches whose outcome depends only on the last few branches -- for example, the back-edge of a loop that alternates between short and long runs. Using a long history for such branches would introduce noise (uncorrelated history bits) and increase table conflicts. TAGE automatically selects the appropriate length through the tag-match mechanism.

## Resource Efficiency

TAGE's most impressive achievement is its accuracy-to-storage ratio. In the 2014 Championship Branch Prediction (CBP) evaluation, a 32-Kbit TAGE configuration achieved misprediction rates below 4 per 1000 instructions (4 MPKI) on CINT benchmarks -- outperforming much larger predictors:

| Predictor Type          | Storage Budget | MPKI (CINT Avg.) |
|-------------------------|---------------|-------------------|
| 2-bit bimodal           | 4 Kbits       | ~12               |
| Gshare (8 Kbits)        | 8 Kbits       | ~8                |
| Tournament (Alpha 21264)| 16 Kbits      | ~6                |
| **TAGE (32 Kbits)**     | **32 Kbits**  | **~3.5**          |
| Large TAGE (256 Kbits)  | 256 Kbits     | ~2.0              |

The efficiency comes from three design choices:

1. **Tagged entries with geometric histories** -- Tables only store entries for branch-history combinations that actually exhibit correlation. Uncorrelated combinations get the base prediction at near-zero storage cost.
2. **Direct-mapped organization** -- Each table is a simple array, keeping access latency low (single cycle) and area small. No associative lookup or complex indexing.
3. **Useful-bit replacement** -- When a new entry must be allocated, the predictor prefers to evict entries with zero useful bits (i.e., entries that have not recently contributed correct predictions). This prevents thrashing.

### The "-SC-L" Extensions

The full TAGE-SC-L predictor adds optional components:

- **SC (Statistical Corrector)** : A side predictor that corrects the TAGE prediction for very hard-to-predict branches. It uses a large table indexed by a hash of PC and global history, storing confidence-weighted corrections. The SC is only consulted when TAGE's confidence is low.
- **L (Loop predictor)** : A specialized component that detects and predicts loops with constant iteration counts. It overrides TAGE for branches that follow a fixed "take N times, skip once" pattern.

These extensions add ~10% more storage but can reduce mispredictions by an additional 15--25% on loop-heavy workloads.

## My Reflections

### What I Learned

TAGE changed how I think about predictor design. Earlier predictors (bimodal, gshare, tournament) treat all branches uniformly: every branch-history pair maps to a single prediction counter. TAGE's key insight -- that branches correlate with history at different "distances," and that we should let each branch find its own best distance through tagging -- is elegant and practical.

The geometric history progression is a clever engineering trade-off. It's not optimal for any single branch, but it provides good coverage across the entire spectrum. The result is a predictor that is simultaneously simple enough to implement in hardware (single-cycle access via direct-mapped tables) and accurate enough to approach the theoretical limits of history-based prediction.

### Connections to Other Topics

- **Memory hierarchy**: TAGE's tag + data organization resembles a set-associative cache, but the indexing is over (PC, global history) rather than address. The useful-bit replacement policy mirrors pseudo-LRU in caches.
- **Out-of-order execution**: Accurate branch prediction is a prerequisite for wide, deep pipelines. Without TAGE-level accuracy, the misprediction penalty would dominate performance on modern superscalars.
- **Machine learning**: TAGE can be viewed as a form of ensemble learning: multiple weak predictors (the per-table counters) are combined through a priority scheme (longest-match-wins). The SC component adds a meta-learner on top.

### Open Questions

1. **Diminishing returns**: Does doubling the history length from 256 to 512 bits still improve accuracy meaningfully, or have we hit the correlation limit for most branches?
2. **Neural predictors**: Oliinyk et al. (2021) showed that small neural networks can match TAGE accuracy. Will future predictors move toward learned models, or does TAGE's simplicity and verifiability keep it dominant in commercial cores?
3. **Power**: TAGE reads multiple tables in parallel every cycle. With 7--8 tables, this energy cost is non-trivial. Can we design a predictor that activates only the most likely matching table(s) first?

### Relevance Today (2026)

TAGE-based predictors remain the state of the art in commercial processors. ARM's Cortex-X series, AMD's Zen 4/5, and Intel's recent cores all use variants of TAGE for their main branch predictor. The core design has been refined (larger tables, better hash functions, improved SC components) but the fundamental architecture -- geometric histories, tagged entries, longest-match-wins -- has proven remarkably durable.

---

## References

1. Seznec, A. "TAGE-SC-L Branch Predictors." *Journal of Instruction-Level Parallelism*, Vol. 16, 2014, pp. 1--13.
2. Seznec, A. & Michaud, P. "A Case for (Partially) Tagged Geometric History Length Branch Prediction." *JILP*, Vol. 8, 2006.
3. Yeh, T.-Y. & Patt, Y. N. "Two-Level Adaptive Training Branch Prediction." *Proceedings of MICRO-24*, 1991, pp. 51--61.
4. Seznec, A. "The L-TAGE Branch Predictor." *JILP*, Vol. 9, 2007.
5. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of ISCA-8*, 1981, pp. 135--148.
6. Oliinyk, O. et al. "A Small Neural Network-Based Branch Predictor." *Proceedings of IISWC*, 2021.
7. Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 3.
