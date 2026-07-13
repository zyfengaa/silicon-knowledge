# Module 06: GPU Architecture -- Exercises

## 06-gpu-q.md: Questions and Problems

---

## Section 1: SIMT vs SIMD

### Question 1.1

Explain the key difference between SIMT and SIMD. Give a concrete example of code that works efficiently in SIMT but would be difficult or impossible in SIMD.

### Question 1.2

Consider the following CUDA kernel:

```cuda
__global__ void kernel(float *data, int *keys, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        float val = data[idx];
        // indirect indexed access based on runtime data
        float result = data[keys[idx]] + val;
        data[idx] = result;
    }
}
```

Explain why this kernel is trivial in SIMT (CUDA) but would be extremely difficult or inefficient in SIMD (e.g., AVX). What specific hardware features enable this in GPU?

### Question 1.3

In SIMD, the programmer must ensure data is contiguous and aligned. In SIMT, coalescing is a performance optimization but not a correctness requirement. Explain the architectural reasons behind this difference.

---

## Section 2: Warp Divergence

### Question 2.1

Show an if/else condition that causes warp divergence. Given the following code:

```cuda
if (threadIdx.x < 16) {
    // Path A: 10 instructions
    result = a * b + c * d;
} else {
    // Path B: 15 instructions
    result = expf(a) + logf(b);
}
```

Assume 50% of threads take Path A and 50% take Path B. Calculate:
a) How many cycles does the warp take to execute this divergent branch?
b) What is the utilization (active threads / total threads) during each path?
c) What is the overall utilization across both paths?
d) If both paths were 12 instructions each with predication (all threads execute all instructions), how many cycles would it take? Which approach is better?

### Question 2.2

Which of the following conditions cause warp divergence? For each, explain why or why not:

```cuda
// (a)
if (threadIdx.x % 2 == 0) { ... } else { ... }

// (b)
if (blockIdx.x > 0) { ... } else { ... }

// (c)
if (data[threadIdx.x] > 0.0f) { ... } else { ... }

// (d)
switch (threadIdx.x / 8) {
    case 0: ... break;
    case 1: ... break;
    case 2: ... break;
    case 3: ... break;
}
```

### Question 2.3

Describe three programming strategies to avoid or mitigate warp divergence. For each strategy, provide a code example.

---

## Section 3: Coalescing Analysis

### Question 3.1

Given a thread block of 128 threads, each reading a float (4 bytes), analyze the following three access patterns. Identify which are coalesced and which are not, and explain why.

```cuda
// Pattern (a)
float val = array[threadIdx.x];

// Pattern (b)
float val = array[threadIdx.x * 2];

// Pattern (c)
float val = array[blockIdx.x * blockDim.x + threadIdx.x];
```

For each pattern, calculate:
- The address range accessed by a single warp (32 threads)
- How many 128-byte cache line transactions are generated
- The bandwidth utilization (useful bytes / total bytes transferred)

### Question 3.2

Assume a GPU with 128-byte cache lines. A warp of 32 threads reads 4-byte floats with stride S. Fill in the following table:

| Stride S | Address range per warp (bytes) | Cache lines fetched | BW utilization |
|----------|-------------------------------|--------------------|----------------|
| 1        |                               |                    |                |
| 2        |                               |                    |                |
| 4        |                               |                    |                |
| 8        |                               |                    |                |

### Question 3.3

Explain how shared memory tiling (as used in tiled matrix multiplication) improves global memory coalescing. Why does the naive global memory kernel in matrix multiply have poor coalescing for one of the two input matrices?

---

## Section 4: Bank Conflict Detection

### Question 4.1

Given shared memory with 32 banks (each 4 bytes wide), analyze which of the following access patterns cause bank conflicts. Show the bank mapping (bank = (address / 4) % 32) for each.

```cuda
__shared__ float shmem[1024];

// Pattern (a) — no conflict scenario
float a = shmem[threadIdx.x];

// Pattern (b) — stride-2
float b = shmem[threadIdx.x * 2];

// Pattern (c) — prime stride
float c = shmem[threadIdx.x * 33];
```

For each pattern, determine:
- How many unique banks are accessed by the first warp (32 threads)
- How many ways of bank conflict exist
- The effective bandwidth multiplier (ideal = 32, worst = 1)

### Question 4.2

Consider a 2D shared memory array declared as `__shared__ float s_data[32][32]`. A warp of 32 threads (threadIdx.x spanning 0-31, threadIdx.y fixed) accesses the array as follows:

```cuda
// Mode 1: row-major
float v1 = s_data[threadIdx.x][threadIdx.y];

// Mode 2: column-major
float v2 = s_data[threadIdx.x][threadIdx.y];
```

Wait -- both look the same. Let's be more precise. Thread (tx, ty) does:

```cuda
// Mode 1: conflict-free
float val = s_data[tx][ty];  // tx = threadIdx.x, ty = threadIdx.y

// Mode 2: bank conflict
float val = s_data[ty][tx];  // swap: tx = threadIdx.x, ty = threadIdx.y
```

Assuming a 2D block of `dim3 block(32, 32)`:
- For Mode 1, analyze the access pattern when `ty` varies within a warp (warp = threads with same tx, varying ty). Hint: are consecutive ty values in the same bank?
- For Mode 2, analyze when `tx` varies within a warp (warp = threads with same tx, varying ty). Show the bank mapping.
- How would you fix Mode 2 using padding?

### Question 4.3

Explain what "broadcast" is in the context of shared memory bank conflicts. When multiple threads in a warp read the exact same address, how does the hardware handle this? How is this different from multiple threads reading different addresses that map to the same bank?

---

## Section 5: Tensor Core Programming

### Question 5.1

Describe three types of matrix operations that benefit from Tensor Cores. For each operation, specify:
- The operation dimensions (M, N, K)
- The precision requirements
- The typical application domain

### Question 5.2

What are the precision requirements for Tensor Core operations? List at least three precision modes supported across different Tensor Core generations (Volta through Hopper). For each mode, state:
- Input precision
- Accumulation precision
- Compute throughput relative to FP32 (approximate)

### Question 5.3

When would you NOT want to use Tensor Cores despite their higher peak throughput? Describe at least three scenarios and explain why Tensor Cores are suboptimal in each case.

### Question 5.4

The WMMA (Warp Matrix Multiply-Accumulate) API requires specific tile sizes (e.g., 16x16x16). Explain:
- Why the tile size is constrained to specific values (what hardware limitation drives this?)
- How a matrix of arbitrary dimensions (e.g., N=1000) can be computed using Tensor Cores
- Why the thread block must contain at least one warp (32 threads)

### Question 5.5

Compare Tensor Cores to a systolic array (as used in Google TPU). For each architecture, describe:
- Data flow model
- Precision flexibility
- Programmability
- When one is preferred over the other

---

## Answer Guidelines

- For divergence calculations (Section 2), clearly show the number of active threads per path
- For coalescing analysis (Section 3), compute the address ranges explicitly
- For bank conflict analysis (Section 4), show the bank calculation for at least one thread index
- For Tensor Core questions (Section 5), reference specific NVIDIA architecture whitepapers

---

## References

1. NVIDIA. *CUDA C++ Programming Guide*. 2024. — Chapter 4: Hardware Implementation (SIMT Model), Chapter 9: WMMA API.
2. Kirk, D. B., & Hwu, W. W. *Programming Massively Parallel Processors: A Hands-on Approach*. 4th Edition. Morgan Kaufmann, 2022. — Chapters 4-6.
3. NVIDIA. *NVIDIA A100 Tensor Core GPU Architecture Whitepaper*. 2020.
4. NVIDIA. *NVIDIA H100 Tensor Core GPU Architecture Whitepaper*. 2022.
5. Harris, M. "How to Access Global Memory Efficiently." *NVIDIA Developer Blog*, 2013.
6. NVIDIA. "CUDA Pro Tip: Use Shared Memory to Reduce Global Memory Accesses." *NVIDIA Developer Blog*, 2014.
7. NVIDIA. *CUDA C++ Best Practices Guide*. 2024. — Chapter 9: Memory Optimizations.
