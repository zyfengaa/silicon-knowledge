# Module 05: Memory Hierarchy -- Exercises

## 05-memory-q.md: Questions and Problems

---

## Section 1: Tag / Index / Offset Calculation

### Question 1

Calculate the tag, index, and offset bits for address `0xABCD1234` in two different cache configurations, both with 64 B lines.

a) **Direct-mapped cache, 32 KB total size.** Show the bit breakdown (which bits form the offset, which form the index, and which form the tag). Extract the actual field values from the address.

b) **4-way set-associative cache, 32 KB total size.** Again show the bit breakdown and extracted field values.

c) How many sets does each configuration have? How does associativity change the index field width compared to the direct-mapped case?

### Question 2

Classify each miss in the following access sequence as **compulsory (cold)**, **conflict**, or **capacity**. Assume:

- Cache: 4 sets, 1-way (direct-mapped), 2-word lines (8 bytes per line)
- Addresses are given in **word addresses** (each address refers to a 4-byte word)
- Cache starts empty (cold)

Access sequence (word addresses): `0, 8, 0, 16, 8, 0, 24, 32, 0, 8`

For each access, determine:

a) The set it maps to
b) Whether it is a hit or miss
c) The miss type (compulsory, conflict, or capacity)
d) Explain your reasoning for each classification

---

## Section 2: AMAT and Multi-Level Caches

### Question 3

A system has the following memory hierarchy parameters:

| Level | Hit Time | Miss Rate (local) |
|-------|----------|-------------------|
| L1    | 1 cycle  | 5%                |
| L2    | 10 cycles| 20%               |
| Main memory | 100 cycles | -- (assume 100% miss penalty) |

a) Compute the **AMAT** for the full hierarchy (L1 + L2 + main memory). Show your work.

b) Compute the **AMAT** if L2 is removed (i.e., only L1 + main memory, with L1's miss going directly to main memory at 100 cycles).

c) Compare the two AMAT values. By what factor does the L2 cache improve the average access time?

d) If we had the option to add an L3 cache (hit time = 30 cycles, local miss rate = 25%) between L2 and main memory instead of relying only on L2, calculate the new AMAT. Is the L3 worthwhile given the cost and complexity?

---

## Section 3: Write Policies

### Question 4

Compare **write-through** and **write-back** policies for the following access pattern:

A program performs sequential writes to addresses within a **32-byte block**, repeated 4 times:

```
Write addr 0x00, Write addr 0x04, Write addr 0x08, ..., Write addr 0x1C
(8 writes per iteration, 4 iterations = 32 writes total)
```

Assume:

- Cache line size = 32 bytes (one line holds the entire block)
- The cache starts empty (cold)
- **Write-through**: every write goes to memory immediately; no write-allocate (write misses go directly to memory without loading the line into cache)
- **Write-back**: write-allocate (load line on miss), only evicted dirty lines are written to memory
- No other accesses interfere (the block stays in cache for write-back)

a) For **write-through**, count the total number of memory writes (including those caused by cache line fills on misses, if any). How many of these writes are to the 32-byte block vs. elsewhere?

b) For **write-back**, count the total number of memory writes (including the write-back on eviction and any line fills on misses).

c) Assume the write-through policy uses a **write buffer** that batches writes. How does this change the performance picture compared to write-back? Under what conditions would write-through still be preferred?

---

## Section 4: TLB Reach

### Question 5

Consider a TLB (Translation Lookaside Buffer) that is fully associative with **64 entries**.

a) **TLB reach with 4 KB pages**: What is the total virtual address range (in bytes) that the TLB can cover without a page walk?

b) **TLB reach with 2 MB pages**: What is the reach with the same 64 entries?

c) How many TLB entries would be needed to cover **512 GB** of virtual address space with 4 KB pages?

d) A modern database server has a working set of approximately 200 GB. Discuss the practical implications of TLB reach for this workload. How would 2 MB pages (or 1 GB pages) change the situation?

e) Some recent processors (e.g., Intel Ice Lake, AMD Zen 3+) include a **second-level TLB (L2 TLB)** that holds thousands of entries. Explain why this helps and what design trade-off it represents.

---

## Section 5: Applied Problems

You may answer these in free-form text or with calculated values where applicable. Show your reasoning for any calculations.

---

## Reference Formulas

- Cache capacity = number of sets x associativity x line size
- Index bits = log2(number of sets)
- Offset bits = log2(line size)
- Tag bits = address width - index bits - offset bits
- AMAT = Hit Time + Miss Rate x Miss Penalty
- TLB reach = number of entries x page size

---

## Answer Guidelines

- For Question 1, express the address in binary and draw lines separating the tag, index, and offset fields. Then compute the numeric values.
- For Question 2, consider whether each miss would still occur in a fully-associative cache (capacity) or is caused by conflict with another address (conflict), or whether it is the first-ever access (compulsory).
- For Questions 3-5, show all formulas and intermediate steps.

---

## References

1. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 2 (Memory Hierarchy Design).
2. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 5 (Large and Fast -- Exploiting Memory Hierarchy).
3. Hill, M. D., & Smith, A. J. "Evaluating Associativity in CPU Caches." *IEEE Transactions on Computers*, Vol. 38 No. 12, 1989.
4. Intel Corporation. *Intel 64 and IA-32 Architectures Optimization Reference Manual*. Sections on TLB organisation and page sizes.
