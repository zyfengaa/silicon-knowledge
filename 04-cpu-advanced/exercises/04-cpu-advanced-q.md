# Module 04: CPU Advanced -- Exercises

## 04-cpu-advanced-q.md: Questions and Problems

---

## Section 1: Superscalar IPC Calculation

### Question 1.1

A 4-wide superscalar processor can fetch, decode, issue, and commit up to 4 instructions per cycle. However, dependencies between instructions limit the achievable IPC. Given the following dependence profile for a program (assume a perfect branch predictor with no mispredictions):

- 20% of instructions depend on the immediately preceding instruction (a 1-cycle RAW hazard)
- 10% of instructions depend on an instruction 2--3 positions ahead (a 2--3 cycle RAW hazard)
- 5% of instructions are branches (resolved in 1 cycle, perfect prediction)
- Remaining instructions are independent or depend on instructions far enough back to be ready

Assume:
- The processor has enough functional units to sustain 4-wide execution
- Full forwarding/bypassing is implemented (no structural hazards)
- Branches are predicted perfectly and incur no penalty
- An instruction that depends on the immediately preceding instruction must wait 1 cycle before issuing
- An instruction that depends on an instruction 2--3 ahead must wait 2 cycles before issuing

Calculate the **maximum achievable IPC** for this workload. Show your reasoning.

### Question 1.2

Suppose we double the issue width from 4-wide to 8-wide, but the dependence profile remains the same. Does the IPC double? Explain why or why not, and discuss the practical limits of increasing issue width.

---

## Section 2: Out-of-Order Execution Structures

### Question 2.1

Explain the roles of the **Reorder Buffer (ROB)** and **Reservation Stations (RS)** in an out-of-order processor. For each structure, describe:

| Aspect               | Reorder Buffer (ROB)                     | Reservation Stations (RS)               |
|----------------------|------------------------------------------|------------------------------------------|
| **What it stores**   |                                          |                                          |
| **When allocated**   |                                          |                                          |
| **When freed**       |                                          |                                          |
| **Role in misprediction** |                                       |                                          |

### Question 2.2

Consider the following instruction sequence executing on a Tomasulo-style out-of-order processor:

```
FADD f1, f2, f3      # f1 = f2 + f3
FMUL f3, f4, f5      # f3 = f4 * f5  (WAR on f3)
FADD f6, f3, f7      # f6 = f3 + f7  (RAW on f3)
```

a) Identify all true (RAW) and anti (WAR) dependencies.
b) Explain how register renaming eliminates the WAR dependency. Show the renamed register mappings for each instruction.
c) After renaming, which instructions can execute in parallel?

### Question 2.3

On a branch misprediction in an out-of-order processor, both the ROB and RS must be flushed. Why must both structures be cleared, not just one? What state is lost from each, and why can't instructions in the RS survive the misprediction?

---

## Section 3: Branch Prediction Comparison

### Question 3.1

Compare a **2-bit saturating counter** predictor and a **TAGE** predictor across the following dimensions:

| Dimension              | 2-bit Saturating Counter | TAGE |
|------------------------|--------------------------|------|
| Always-taken branch    |                          |      |
| Hard-to-predict branch |                          |      |
| Loop with fixed trip count (e.g., for i in 0..100) | | |
| Storage cost (entries) |                          |      |
| Circuit complexity     |                          |      |

### Question 3.2

Consider a branch with the following repeating pattern of outcomes (T = Taken, N = Not Taken):

```
T T T T N   T T T T N   T T T T N   ...
```

The pattern repeats every 5 branches (4 Taken, 1 Not Taken).

a) Simulate the behavior of a 2-bit saturating counter predictor starting from the "weakly not-taken" state (01). How many mispredictions occur over 100 iterations (500 branches)? Report the final counter state.
b) Explain how TAGE would handle this pattern better. Which history length table is likely to provide the correct prediction? How many mispredictions would TAGE incur after the pattern is learned?

### Question 3.3

Why does TAGE use geometrically increasing history lengths (e.g., 4, 8, 16, 32, 64, 128) rather than linearly increasing lengths (e.g., 2, 4, 6, 8, 10)? Provide two concrete reasons related to branch behavior and hardware cost.

---

## Section 4: SIMD Speedup Calculation

### Question 4.1

Compare **128-bit NEON** and **256-bit AVX2** for single-precision (32-bit) floating-point operations.

a) How many single-precision floats fit in each vector register?
   - 128-bit NEON: _____ floats
   - 256-bit AVX2: _____ floats

b) Calculate the **theoretical speedup** of each SIMD extension over scalar execution for an element-wise vector addition `C[i] = A[i] + B[i]` with no dependencies between iterations. Assume no memory bottlenecks.

| Implementation | Elements per iteration | Theoretical speedup vs. scalar |
|----------------|-----------------------|-------------------------------|
| Scalar         | 1                     | 1.0x (baseline)               |
| 128-bit NEON   |                       |                                |
| 256-bit AVX2   |                       |                                |

### Question 4.2

Now consider a **reduction** operation -- summing all elements of a single-precision array of length N:

```c
float sum = 0.0f;
for (int i = 0; i < N; i++) {
    sum += A[i];
}
```

In a SIMD reduction, the partial results held in each vector lane must be combined at the end (a "horizontal add" or "had" sequence).

a) For NEON (128-bit, 4 floats), how many horizontal-add steps are needed to combine the 4 partial sums into one scalar result? Show the reduction tree.
b) For AVX2 (256-bit, 8 floats), how many horizontal-add steps are needed? Show the reduction tree.
c) Calculate the effective speedup for N = 1024. Assume:
   - Each vector addition (vertical add) takes 1 cycle
   - Each horizontal-add step takes 3 cycles
   - All memory access costs are identical across implementations

| Implementation | Cycles for 1024 vertical adds (1024/lane_width) | Cycles for final horizontal reduction | Total cycles | Speedup vs. scalar |
|----------------|-------------------------------------------------|---------------------------------------|-------------|---------------------|
| Scalar         | 1024                                            | 0                                     | 1024        | 1.0x                |
| NEON (4-lane)  |                                                 |                                       |             |                     |
| AVX2 (8-lane)  |                                                 |                                       |             |                     |

d) The reduction overhead reduces the speedup versus the ideal (no-reduction) case. What fraction of the theoretical speedup is actually achieved for each SIMD implementation?

### Question 4.3

Explain two reasons why a real application might achieve far lower SIMD speedup than the theoretical calculation. For each reason, give a concrete example.

---

## Section 5: False Sharing Analysis

### Question 5.1

Consider the following code running on a dual-core processor with 64-byte cache lines:

```c
struct {
    int x;  // Thread 0 updates this field (10M iterations)
    int y;  // Thread 1 updates this field (10M iterations)
} data;

// Thread 0:
for (int i = 0; i < 10000000; i++) {
    data.x++;
}

// Thread 1:
for (int i = 0; i < 10000000; i++) {
    data.y++;
}
```

a) Identify the problem. Why is this considered **false sharing**? Base your explanation on the memory layout of `data` and the cache line boundaries.

b) Show the struct definition after applying a proper fix using explicit padding. Assume 64-byte cache lines and that `data` is cache-line-aligned.

```c
// Fix: add padding to isolate x and y into separate cache lines
struct {
    int x;
    // padding here:
    ____________________________________
    int y;
} data;
```

c) Calculate the **slowdown factor** caused by false sharing. Assume:
   - Access to local cache data: 50 ns per iteration
   - Cache line transfer between cores (cache-to-cache): 100 ns per transfer
   - Each thread runs 10,000,000 iterations
   - MESI protocol: a write by Thread 0 invalidates Thread 1's copy, forcing a transfer on Thread 1's next access, and vice versa
   - Each iteration incurs exactly one cache miss due to false sharing (one transfer per increment)

Calculate the total execution time per thread with false sharing vs. without false sharing, then compute the slowdown factor.

| Scenario                          | Time per iteration | Total time (10M iterations) |
|-----------------------------------|-------------------:|----------------------------:|
| Without false sharing (ideal)     | 50 ns              |                             |
| With false sharing                |                    |                             |
| **Slowdown factor**               |                    |                     _____x |

### Question 5.2

Would the false sharing problem be less severe if the cache line size were 128 bytes instead of 64 bytes? Explain.

### Question 5.3

List two diagnostic tools or methods that can detect false sharing in a running multithreaded program.

---

## Answer Guidelines

- For IPC calculations (Section 1), compute the effective issue rate by weighting each dependency penalty by its frequency
- For out-of-order questions (Section 2), distinguish the ROB's in-order commit from the RS's out-of-order issue
- For branch prediction (Section 3), simulate the 2-bit counter state transitions step by step; then reason about TAGE's tag-match mechanism
- For SIMD (Section 4), show the horizontal reduction tree explicitly with step counts
- For false sharing (Section 5), compute the cache-line layout to confirm x and y share the same line

---

## References

1. Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapters 3, 4.
2. Seznec, A. "TAGE-SC-L Branch Predictors." *JILP*, Vol. 16, 2014.
3. Tomasulo, R. M. "An Efficient Algorithm for Exploiting Multiple Arithmetic Units." *IBM Journal of Research and Development*, Vol. 11 No. 1, 1967, pp. 25--33.
4. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of ISCA-8*, 1981.
5. Intel Corporation. *Intel 64 and IA-32 Architectures Optimization Reference Manual*. 2023. Sections on cache and false sharing.
6. Bolosky, W. J. & Scott, M. L. "False Sharing and Its Effect on Shared Memory Performance." *USENIX SEDMS*, 1993.
