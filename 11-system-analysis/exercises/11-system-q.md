# Module 11: System Analysis — Exercises

## Questions

### Question 1: Arithmetic Intensity Calculation

For each of the following operations, calculate the arithmetic intensity (FLOP/Byte). Assume FP32 (4 bytes per value) and all data is read from/written to DRAM (no cache reuse).

a) **SAXPY**: `y[i] = a * x[i] + y[i]`, where `a` is a scalar.

b) **Dot product**: `sum += x[i] * y[i]`.

c) **Matrix-vector multiply (GEMV)**: `y = A * x`, where A is N×N.

d) **Matrix multiply (GEMM)**: `C = A * B`, where all matrices are N×N, and you perform blocking so that A and B are read once and C is written once.

e) **3D Stencil (7-point)**: Each output point depends on 7 neighbor input points. Assume grid size N³.

### Question 2: Classify as Compute-bound or Memory-bound

Using the arithmetic intensities computed in Question 1, classify each operation. Assume the following hardware:

```
Peak GFLOPS: 1000
Peak BW:     200 GB/s
```

For each operation:
- Compute the Ridge Point
- State whether it is compute-bound or memory-bound
- Calculate the achievable GFLOPS

### Question 3: Amdahl and Gustafson

a) A program takes 100 seconds to run on a single core. 80 seconds are spent in a parallelizable section. What is the maximum speedup achievable with 16 cores? With infinite cores?

b) Suppose the same program (80% parallel, 20% serial) runs on a cluster. A user now wants to scale the problem size such that it still completes in roughly the same wall-clock time. According to Gustafson's Law, what speedup would they observe when moving from 1 to 16 cores? Assume the serial fraction remains constant at 20% of the *scaled* problem.

c) For a program with 95% parallel portion, how many cores are needed to achieve at least 10× speedup according to Amdahl? And at least 15×?

d) In practice, scaling efficiency often drops below the theoretical limit due to communication overhead. Derive a modified Amdahl-style formula that accounts for a communication overhead term `C(N)` that grows linearly with `N` (number of processors).

### Question 4: Interpreting Profiling Output

Given the following `perf stat` output for a program:

```
Performance counter stats for './my_program':

   845,678,901,234      cycles
   678,901,234,567      instructions
   123,456,789,012      cache-references
    55,555,555,555      cache-misses
    22,222,222,222      branch-instructions
     4,444,444,444      branch-misses
```

a) Calculate the IPC (instructions per cycle).

b) Calculate the cache miss rate.

c) Calculate the branch misprediction rate.

d) Based on these numbers, what are the likely performance bottlenecks? What should the programmer optimize first?

### Question 5: LLM Training System Analysis

You are training a 70B parameter language model on a cluster of 512 H100 GPUs (each 80GB HBM3, 1979 TFLOPS FP16, 3.35 TB/s memory bandwidth). The model uses Adam optimizer, FP16 (BF16) training.

a) **Memory**: Compute the minimum memory required for model parameters, gradients, and optimizer states. Calculate the memory per GPU when using ZeRO-3.

b) **Compute**: The model trains on 1 trillion tokens. Compute the total FLOPs required for forward and backward passes.

c) **Communication**: Estimate the all-reduce data volume per training step for ZeRO-3, assuming each step uses a batch of 1M tokens. How does the choice of micro-batch size affect communication volume?

d) **Optimization**: Given that the cluster achieves 45% MFU, calculate the expected time to complete training. State your assumptions about the training configuration (batch size, sequence length, etc.).

e) **Bottleneck**: If the profiler shows that GPU idle time (waiting for data) accounts for 35% of total step time, what optimization would you recommend first?

---

## Answers

### Answer 1: Arithmetic Intensity Calculation

Recall: AI = FLOP / Byte (data moved to/from DRAM).

**a) SAXPY** (`y[i] = a*x[i] + y[i]`):

```
Per iteration:
- FLOPs: 1 multiply + 1 add = 2 FLOP
- Data: read x[i] (4B) + read y[i] (4B) + write y[i] (4B) = 12B

AI = 2 / 12 = 0.167 FLOP/Byte
```

**b) Dot product** (`sum += x[i] * y[i]`):

```
Per iteration:
- FLOPs: 1 multiply + 1 add = 2 FLOP
- Data: read x[i] (4B) + read y[i] (4B) = 8B (sum is in register)

AI = 2 / 8 = 0.25 FLOP/Byte
```

**c) Matrix-vector multiply** (`y = A * x`, N×N):

```
For each row of A:
- FLOPs: N multiply + N add = 2N FLOP (total: 2N²)
- Data: read A row (N × 4B) + read x completely (N × 4B) + write y (1 × 4B)
  (Assuming x is cached after first read is unrealistic for large N)
  Strictly: A: N² × 4B, x: N × 4B, y: N × 4B → total ~4N² + 8N bytes

AI ≈ 2N² / (4N² + 8N) ≈ 0.5 FLOP/Byte (for large N)
```

**d) Matrix multiply** (`C = A × B`, N×N with blocking):

```
With perfect tiling (cache blocking):
- FLOPs: 2N³
- Data: A read once (N² × 4B), B read once (N² × 4B), C written once (N² × 4B)

Total data: 12N² bytes (for FP32)

AI = 2N³ / (12N²) = N/6 FLOP/Byte

For N=1024: AI = 1024/6 ≈ 171 FLOP/Byte
For N=4096: AI = 4096/6 ≈ 683 FLOP/Byte

Note: In practice, cache hierarchy makes perfect blocking impossible, so actual AI is lower.
```

**e) 3D Stencil (7-point)**:

```
Per grid point:
- FLOPs: 7 additions = 7 FLOP (simplified)
- Data: read 7 neighbor points + 1 center point = 8 × 4B = 32B

AI = 7 / 32 ≈ 0.219 FLOP/Byte
```

### Answer 2: Classify as Compute- or Memory-bound

```
Ridge Point = Peak GFLOPS / Peak BW = 1000 / 200 = 5.0 FLOP/Byte
```

| Operation | AI (FLOP/Byte) | Bound | Achievable GFLOPS |
|-----------|---------------|-------|-------------------|
| SAXPY | 0.167 | Memory | 0.167 × 200 = 33.4 |
| Dot product | 0.25 | Memory | 0.25 × 200 = 50.0 |
| GEMV | 0.5 | Memory | 0.5 × 200 = 100.0 |
| GEMM (N=1024) | 171 | Compute | 1000 |
| 3D Stencil | 0.219 | Memory | 0.219 × 200 = 43.8 |

### Answer 3: Amdahl and Gustafson

**a) Amdahl's Law**

Parallel portion P = 80/100 = 0.8.

```
S(N) = 1 / ((1-P) + P/N)

N=16:   S = 1 / (0.2 + 0.8/16) = 1 / (0.2 + 0.05) = 1/0.25 = 4.0×
N→∞:    S_max = 1 / (1-P) = 1 / 0.2 = 5.0×
```

**b) Gustafson's Law**

```
S(N) = N - α(N - 1),  α = 0.2 (serial fraction)
S(16) = 16 - 0.2(16-1) = 16 - 3 = 13.0×
```

**c) Core count for target speedup**

```
P = 0.95, Amdahl:
S(N) = 1 / (0.05 + 0.95/N)

For S = 10:
10 = 1 / (0.05 + 0.95/N) → 0.05 + 0.95/N = 0.1 → 0.95/N = 0.05 → N = 19

For S = 15:
15 = 1 / (0.05 + 0.95/N) → 0.05 + 0.95/N = 0.0667 → 0.95/N = 0.0167 → N ≈ 57
```

**d) Amdahl with communication overhead**

```
Let C(N) = k·N be the communication overhead per unit work (linear growth).

Modified formula:
S(N) = 1 / ((1-P) + P/N + C(N))

With C(N) = c·N (c is a constant):

S(N) = 1 / ((1-P) + P/N + c·N)

For large N, the c·N term dominates → speedup can actually DECREASE.
This is a common real-world effect — beyond a certain point, adding more
processors hurts performance due to communication overhead.

Example with P=0.95, c=0.001:
N=10:   S = 1/(0.05+0.095+0.01)   = 1/0.155     ≈ 6.45×
N=100:  S = 1/(0.05+0.0095+0.1)   = 1/0.1595    ≈ 6.27×  ← already decreasing!
N=1000: S = 1/(0.05+0.00095+1.0)  = 1/1.051     ≈ 0.95×  ← slowdown!
```

### Answer 4: Interpreting Profiling Output

**a) IPC**

```
IPC = instructions / cycles = 678,901,234,567 / 845,678,901,234 ≈ 0.80
```

This is relatively low. Modern CPUs can achieve IPC > 2 for well-optimized code.

**b) Cache miss rate**

```
Cache miss rate = cache-misses / cache-references
                = 55,555,555,555 / 123,456,789,012 ≈ 45%
```

This extremely high cache miss rate is the primary bottleneck.

**c) Branch misprediction rate**

```
Branch miss rate = branch-misses / branch-instructions
                 = 4,444,444,444 / 22,222,222,222 ≈ 20%
```

A 20% branch misprediction rate is very high (good code should be < 2%).

**d) Analysis and recommendations**

Primary bottleneck: **Cache misses (45%)**. IPC is only 0.80 primarily because the CPU spends most of its time waiting for data from DRAM.

Secondary issue: **Branch mispredictions (20%)**. The program likely has unpredictable branches.

Optimization priorities:
1. Improve data locality (loop tiling, structure of arrays, cache-friendly algorithms)
2. Prefetch data (hardware prefetch may not be sufficient at 45% miss rate)
3. Reduce branch mispredictions (replace unpredictable branches with arithmetic, use branch hints, or restructure algorithms)

### Answer 5: LLM Training System Analysis

**a) Memory per GPU (ZeRO-3)**

```
Model parameters: 70B × 2 bytes (BF16) = 140 GB
Gradients:        70B × 2 bytes = 140 GB
Optimizer states (Adam):
  Momentum: 70B × 4 bytes (FP32) = 280 GB
  Variance: 70B × 4 bytes (FP32) = 280 GB

Total without partitioning: 140 + 140 + 280 + 280 = 840 GB

With ZeRO-3 partitioning across 512 GPUs:
Per GPU: 840 GB / 512 ≈ 1.64 GB

Additional activation memory (variable, depends on batch size and sequence length):
  For batch=32, seq_len=2048, hidden=8192 (typical 70B config):
  Activation memory ≈ 20-40 GB per GPU (with activation checkpointing)
  Without checkpointing: 80-160 GB per GPU

Total per GPU with ZeRO-3 and activation checkpointing: ~1.64 + 30 ≈ 32 GB
This fits comfortably in H100's 80 GB.
```

**b) Total FLOPs**

```
FLOPs per token = 2 × 6 × N_params
                = 2 × 6 × 70 × 10^9
                = 840 × 10^9 FLOPs/token

Total tokens = 1T = 10^12

Total FLOPs = 840 × 10^9 × 10^12 = 8.4 × 10^23 FLOPs
```

**c) Communication volume**

```
ZeRO-3 communication per step:

For each model layer during forward (parameter all-gather):
  Communication = 2 × param_size per layer × (P-1)/P × N_gpu
  (where the factor of 2 accounts for both forward and backward all-gather)

Simplified estimate:
  Per step, total all-reduce (or reduce-scatter + all-gather) data ≈ 2 × model_size

  Model size (BF16) = 140 GB
  Communication per step ≈ 2 × 140 GB = 280 GB (total across all GPUs)
  
  Per GPU: 280 GB / 512 ≈ 550 MB per step

Micro-batch size does not directly affect communication volume per step
(it affects how many all-reduce operations happen concurrently, but the
total data exchanged per training step remains the same for a given model.
However, larger micro-batches allow better overlap of communication and
computation.)
```

**d) Expected training time**

```
Peak compute of 512 H100s: 512 × 1979 TFLOPS = 1,013,248 TFLOPS ≈ 1.01 EFLOPS

MFU = 45% → Effective compute = 0.45 × 1.01 EFLOPS = 0.455 EFLOPS

Total FLOPs required = 8.4 × 10^23 FLOPs

Time = 8.4e23 / (0.455 × 10^18) = 8.4e23 / 4.55e17 ≈ 1,846,154 seconds
     ≈ 513 hours ≈ 21.4 days

Assumptions:
- 1T tokens, batch size ~2M tokens per step → 500K steps
- Sequence length ~4096, no padding overhead from variable lengths
- Overlap of communication and computation is already accounted for in 45% MFU
- No overhead for checkpointing, evaluation, or restarts
```

**e) Bottleneck optimization**

35% idle time waiting for data suggests the **input pipeline** or **host-to-device transfer** is a major bottleneck.

Recommended optimization: **Prefetching and data pipeline parallelism**
1. Increase `num_workers` in the data loader to overlap data loading with training
2. Use a larger prefetch buffer so data is ready before the GPU needs it
3. If using JAX/TensorFlow, profile the input pipeline with TensorBoard to identify specific delays
4. Consider streaming data from fast NVMe SSDs instead of network storage
5. Use gradient accumulation to reduce the frequency of data transfers

---

## 参考文献

1. Williams, S., Waterman, A., & Patterson, D. (2009). "Roofline: An Insightful Visual Performance Model for Floating-Point Programs." *Communications of the ACM*, 52(4).
2. Amdahl, G. M. (1967). "Validity of the Single Processor Approach to Achieving Large-Scale Computing Capabilities." *AFIPS Spring Joint Computer Conference*.
3. Gustafson, J. L. (1988). "Reevaluating Amdahl's Law." *Communications of the ACM*, 31(5).
4. Rajbhandari, S., et al. (2020). "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models." *SC 2020*.
5. Brown, T. B., et al. (2020). "Language Models are Few-Shot Learners." *NeurIPS 2020* (GPT-3).
6. Gregg, B. (2022). *Systems Performance: Enterprise and the Cloud* (2nd ed.). Addison-Wesley.
7. NVIDIA. (2023). "H100 Tensor Core GPU Architecture." *Whitepaper*.
