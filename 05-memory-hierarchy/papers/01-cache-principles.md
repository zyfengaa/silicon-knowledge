# Paper Note: Cache Design Principles

## Paper Information

This note synthesises the treatment of cache memory from the following sources:

- **Textbook:** Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 2: Memory Hierarchy Design.
- **Textbook:** Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 5: Large and Fast -- Exploiting Memory Hierarchy.

## One-Sentence Contribution

Caches exploit temporal and spatial locality to bridge the growing latency gap between fast processors and slow main memory, and their effectiveness is governed by a small set of design parameters -- size, associativity, line size, replacement policy, and write policy -- that form a well-understood set of trade-offs.

## Background: Why Caches Are Needed

Processor clock speeds have improved by roughly 50% per year historically, while DRAM access latency has improved by only about 7% per year. This growing gap, known as the **memory wall**, means that a single main-memory access can cost hundreds of processor cycles. A modern out-of-order core may issue tens to hundreds of instructions during the time a single cache miss takes to resolve.

Caches sit between the CPU and main memory, storing recently used data and instructions so that future accesses can be served from a fast, on-chip storage. The key insight is **locality**:

- **Temporal locality**: If a location is accessed, it is likely to be accessed again soon (e.g., loop counters, stack frames).
- **Spatial locality**: If a location is accessed, nearby locations are likely to be accessed soon (e.g., array traversal, sequential instruction fetch).

## Key Concepts

### 1. Direct-Mapped Cache

The simplest organisation: each memory address maps to exactly one cache line. The address is split into tag, index, and offset. The index selects a line; the tag is compared to verify that the line holds the desired block.

**Advantage**: Simple, fast (single comparator), low power. **Disadvantage**: High conflict miss rate -- if two frequently accessed addresses map to the same line, they repeatedly evict each other (thrashing).

### 2. Set-Associative Cache

Each set contains N ways (lines). A memory address maps to exactly one set, but may occupy any of the N lines within that set. N-way set-associative caches reduce conflict misses compared to direct-mapped, at the cost of extra comparators and slightly higher access latency.

- 1-way = direct-mapped
- N-way where N = total lines = fully associative

Real caches are typically 2- to 16-way set-associative. L1 caches tend toward lower associativity (faster), while last-level caches (LLC) tend toward higher associativity (better hit rate).

### 3. Replacement Policy

When a miss occurs and the set is full, a line must be evicted. Common policies:

- **LRU (Least Recently Used)**: Replace the line accessed furthest in the past. Optimal for many workloads but expensive to implement for high associativity (requires per-access update of state).
- **Pseudo-LRU (Tree-PLRU)**: Approximates LRU with a binary tree of bits. Used in many real processors (e.g., Intel Sandy Bridge LLC).
- **Random/NR U**: Simple but less predictable. Used in some high-associativity caches where exact LRU is too expensive.

### 4. Write Policies

Two primary strategies for handling writes:

- **Write-Through**: Every write updates both cache and memory. Simple and ensures memory always has the latest value, but generates heavy memory traffic. Usually paired with a **write buffer** to avoid stalling the CPU on every write.

- **Write-Back**: Only the cache line is updated on a write; the line is marked **dirty**. When the line is evicted, its contents are written back to memory. More efficient for repeated writes to the same location, but more complex (coherence protocols for multi-core).

Each write policy has an associated **write-allocate** (fetch the line into cache on a write miss) or **no-write-allocate** (write directly to memory without caching) sub-policy.

## The Three C's of Cache Misses

Hill and Smith (1989) classified misses into three categories, universally known as the **Three C's**:

| Category     | Cause                                                                 | Can be reduced by                                  |
|--------------|-----------------------------------------------------------------------|----------------------------------------------------|
| Compulsory   | First access to a block -- the cache is empty                         | Larger block size (spatial locality); prefetching  |
| Capacity     | Working set exceeds cache size; blocks are evicted and later re-fetched | Larger cache                                      |
| Conflict     | Multiple blocks map to the same set, evicting each other             | Higher associativity; better placement function    |

A fourth "C" -- **Coherence** -- is sometimes added for multi-processor systems, where cache lines are invalidated by writes from other cores.

### Practical Observations

- Compulsory misses are typically a small fraction of total misses in well-tuned applications.
- Capacity misses dominate for large working sets and are addressed by increasing cache size.
- Conflict misses are the most sensitive to cache organisation -- doubling associativity often eliminates most conflict misses for regular access patterns.
- The relationship between miss rate and cache size follows a power law: doubling cache size typically reduces miss rate by roughly 30-50%, though this varies widely by workload.

## Performance Impact

### Average Memory Access Time (AMAT)

The fundamental performance model is:

```
AMAT = Hit Time + Miss Rate * Miss Penalty
```

For a multi-level hierarchy:

```
AMAT = L1_HitTime
       + L1_MissRate * (L2_HitTime
                        + L2_MissRate * (L3_HitTime
                                         + L3_MissRate * MemPenalty))
```

**Key insight**: Reducing miss rate is valuable, but the product of miss rate and miss penalty means that even small miss rates can be costly if the miss penalty is large (e.g., 100+ cycles for DRAM).

### The Miss Penalty Wall

As processors become faster, the miss penalty in terms of lost instructions grows. A 4 GHz core with 4-wide issue may lose 400+ instructions of potential work on a single L3 miss. This has driven:

- Larger L2/L3 caches (up to tens of MB)
- Hardware prefetchers that predict and fetch blocks before they are demanded
- Out-of-order execution to overlap miss latency with other work
- Simultaneous multithreading (SMT) to switch to another thread during a miss

### Bandwidth vs Latency

Modern optimisations increasingly focus on bandwidth (how many bytes per cycle can be moved) as much as latency. A well-designed cache hierarchy provides:

- **Low latency** for frequent accesses (L1: 1-4 cycles)
- **High bandwidth** for bulk data movement (L2/L3: tens of bytes/cycle)
- **Large capacity** for working sets that exceed L1 (LLC: MB-scale)

## My Reflections

1. **Cache-oblivious vs cache-aware programming**: The tiling (blocking) optimisation described in the textbooks is cache-aware -- the programmer selects a tile size based on known cache parameters. Cache-oblivious algorithms (e.g., recursive divide-and-conquer) achieve good cache behaviour without knowing cache size, but often have higher overhead. Both approaches are fascinating examples of how architecture influences algorithm design.

2. **Associativity is not free**: While higher associativity reduces conflict misses, it increases access latency (more tag comparisons) and power consumption. In practice, L1 caches often use 2-8 ways with careful layout to minimise latency impact, while LLCs use 16-32 ways where latency matters less. This is a concrete example of the quantitative approach Patterson and Hennessy advocate: measure, then design.

3. **The rise of ML-driven prefetching**: Recent research (e.g., from the 2022-2025 ISCA/MICRO proceedings) explores using neural networks for cache prefetching and replacement. While the textbook LRU is still the baseline taught, many real processors now use adaptive policies that learn from access patterns (e.g., Intel's Adaptive Replacement Cache in some Xeon generations).

4. **The TLB as a special cache**: The Translation Lookaside Buffer is conceptually just another cache, but with all-or-nothing performance implications -- a TLB miss can cost hundreds to thousands of cycles because it may require walking multi-level page tables in memory. The move to larger page sizes (2 MB, 1 GB) in modern OSes is driven directly by TLB reach concerns, especially for large-memory applications like databases and AI inference servers.

---

## References

1. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 2 (Memory Hierarchy Design). -- Core coverage of cache fundamentals, AMAT, and the Three C's.
2. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 5 (Large and Fast -- Exploiting Memory Hierarchy). -- Accessible introduction to cache organisation.
3. Hill, M. D., & Smith, A. J. "Evaluating Associativity in CPU Caches." *IEEE Transactions on Computers*, Vol. 38 No. 12, 1989, pp. 1612--1630. -- The paper that introduced the Three C's miss classification.
4. Smith, A. J. "Cache Memories." *ACM Computing Surveys*, Vol. 14 No. 3, 1982, pp. 473--530. -- Classic survey of early cache design.
5. Drepper, U. "What Every Programmer Should Know About Memory." Red Hat, 2007. -- Practical programmer-oriented guide to the memory hierarchy.
6. Jacob, B., Ng, S. W., & Wang, D. T. *Memory Systems: Cache, DRAM, Disk*. Morgan Kaufmann, 2007. -- Comprehensive reference on memory-system design.
7. Intel Corporation. *Intel 64 and IA-32 Architectures Optimization Reference Manual*. -- Hardware-specific cache organisation and tuning guidance.
