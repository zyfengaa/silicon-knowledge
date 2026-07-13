# Paper Note: NVIDIA CUDA Best Practices Guide

## Contribution

The NVIDIA CUDA Best Practices Guide provides a systematic, empirically grounded methodology for optimizing GPU kernels, covering occupancy tuning, memory access patterns, stream concurrency, and profiling-driven iterative refinement.

## Background

General-purpose GPU (GPGPU) programming with CUDA offers immense parallel throughput, but naive implementations routinely achieve only a fraction of a GPU's theoretical peak performance. The gap arises because GPU performance depends on a complex interplay of hardware resources (registers, shared memory, warp schedulers, memory bandwidth) and software configuration (grid/block dimensions, memory access patterns, stream usage). Without a principled optimization framework, developers cannot reliably identify bottlenecks or predict which transformations will yield the largest speedup.

The CUDA Best Practices Guide (first released with CUDA 2.0 and updated for each architecture generation through Hopper/Blackwell) fills this gap by codifying optimization patterns validated across thousands of kernels and GPU generations. It builds on the quantitative approach pioneered by Patterson and Hennessy, adapted to the unique constraints of SIMT (Single Instruction, Multiple Thread) execution.

## Key Concepts

### 1. Occupancy Maximization

**Occupancy** is the ratio of active warps to the maximum warps supported per SM. Higher occupancy helps hide latency by giving the warp scheduler more independent warps to issue when the current warp stalls (e.g., on a memory access).

The guide emphasizes that **occupancy is not a goal in itself** -- it is a means to hide latency. The tradeoffs:

- **Register pressure**: Using fewer registers per thread increases occupancy but may cause register spilling to local memory (which uses slow global memory bandwidth). The guide recommends using `--maxrregcount` or `__launch_bounds__` to control register usage per kernel.
- **Shared memory usage**: Shared memory is a limited per-SM resource (164 KB on A100, 228 KB on H100). Using more shared memory per block reduces the number of blocks that can reside simultaneously on an SM.
- **Block size selection**: Block size should be a multiple of the warp size (32) and large enough to keep the SM busy, but not so large that register/shared memory limits block occupancy. Typical sizes: 128, 256, or 512 threads per block.

The occupancy API (`cudaOccupancyMaxPotentialBlockSize`, `cudaOccupancyMaxActiveBlocksPerMultiprocessor`) allows developers to compute the theoretical occupancy for a given kernel configuration before running the kernel.

**Key insight from the guide**: For memory-bound kernels, moderate occupancy (50-67%) is often sufficient to hide DRAM latency; higher occupancy provides diminishing returns. For compute-bound kernels with high instruction-level parallelism (ILP), even lower occupancy may suffice.

### 2. Memory Coalescing Patterns

Global memory bandwidth is the most common bottleneck in GPU kernels. The GPU memory controller coalesces multiple thread accesses into a single wide transaction (32 bytes, 128 bytes, or a cache line of 512 bytes on modern architectures). The guide identifies the key principle:

> Adjacent threads in a warp should access adjacent memory addresses.

Concretely:

- **Optimal**: Thread `i` accesses word `i` of a segment. A single 128-byte transaction serves the entire warp (for 4-byte data types). Achieves 100% coalescing efficiency.
- **Strided access**: Thread `i` accesses word `i * stride`. If stride > 1, the memory controller issues multiple transactions. For stride = 2, it issues 2x the transactions; for stride = 32, each thread accesses a separate cache line segment.
- **Random/indexed access**: Thread `i` accesses `array[index[i]]`. Coalescing is only possible if `index[i]` values are themselves contiguous.

The guide recommends structure-of-arrays (SoA) layout over array-of-structures (AoS) to maximize coalescing:

```
// AoS (bad for coalescing)
struct Particle { float x, y, z; };
Particle particles[N];  // threads access: x y z x y z ...

// SoA (good for coalescing)
struct Particles { float x[N], y[N], z[N]; };
// threads access: x x x ... y y y ... z z z ...
```

### 3. Bank Conflict Avoidance

Shared memory is organized into 32 banks (on all modern NVIDIA GPUs). Successive 32-bit words map to successive banks (word `i` maps to bank `i % 32`). When multiple threads in a warp access different addresses in the same bank, a **bank conflict** occurs, serializing those accesses.

The guide identifies three patterns:

| Access Pattern | Bank Conflict? | Effective Bandwidth |
|---|---|---|
| All threads access same address (broadcast) | No (broadcast to all) | 100% |
| Thread i accesses word i (no conflict) | No | 100% |
| Thread i accesses word i * 2 (stride-2) | 2-way conflict | 50% |
| Thread i accesses word i * 32 (stride-32) | 32-way conflict (worst case) | ~3% |

**Avoidance strategies**:
- Pad shared memory arrays: `__shared__ float s[32][33]` instead of `s[32][32]` adds a padding column to shift the bank mapping.
- Use `__ldg()` (read-only cache) for read-only data to bypass shared memory entirely.
- Restructure access patterns so that threads within a warp access distinct banks.

### 4. Stream Usage and Overlap

CUDA streams enable concurrent execution of kernels, data transfers, and host-side work. The guide covers three levels of concurrency:

1. **Kernel concurrency (Hyper-Q)**: Multiple kernels from different streams can run concurrently on the same GPU if sufficient SM resources exist. Introduced with Kepler GK110 (Compute Capability 3.5). The number of concurrent hardware work queues is 32 on Kepler+.

2. **Data transfer overlap**: `cudaMemcpyAsync` with pinned memory can overlap data transfers with kernel execution if the transfers and kernels are on different streams and the GPU supports bidirectional DMA (two copy engines).

3. **Host-device parallelism**: Asynchronous operations return control to the CPU immediately, allowing host work to overlap with GPU operations.

**Prerequisites for overlap**:
- Host memory must be pinned (`cudaHostAlloc` or `cudaMallocHost`)
- All operations must use the non-default stream
- GPU must have sufficient copy engines (check `prop.asyncEngineCount`)

The guide cautions that **false dependencies** can serialize operations across streams if they share resources (e.g., the same memory allocation).

### 5. Profiling-Driven Optimization

The guide advocates an iterative "profile-analyze-optimize" cycle:

1. **Profile**: Use NVIDIA Nsight Compute (ncu) or Nsight Systems (nsys) to collect hardware performance counters.
2. **Identify bottleneck**: Classify as memory-bound or compute-bound using the "Speed of Light" metrics (memory utilization vs. compute utilization).
3. **Analyze specific metrics**:
   - `achieved_occupancy`: Are warps being stalled due to insufficient active warps?
   - `gld_efficiency` / `gst_efficiency`: Are memory accesses coalesced?
   - `shared_efficiency`: Are bank conflicts occurring?
   - `stall_memory_dependency`: Are warps stalled waiting on memory?
   - `stall_short_scoreboard`: Are warps stalled on register dependencies?
4. **Apply targeted optimization** based on the bottleneck.

The guide emphasizes that premature optimization without profiling is wasteful: "measure, don't guess."

## My Reflections

**Occupancy vs. ILP tradeoff**: The guide's nuanced treatment of occupancy is one of its strongest contributions. Early CUDA tutorials (circa 2009-2012) often treated "maximize occupancy" as an absolute rule, leading developers to use just 8 registers per thread when the kernel needed 20, causing massive register spilling. The guide correctly reframes occupancy as a tool for latency hiding, not an end goal. For compute kernels with high instruction-level parallelism, low occupancy (e.g., 25%) can achieve near-peak throughput because the scheduler keeps each warp busy with independent instructions rather than switching between warps.

**Coalescing is the single most impactful optimization**: In my experience, fixing a non-coalesced access pattern from 10% efficiency to 100% efficiency yields a 5-10x speedup -- far more than any other single optimization. The guide rightly prioritizes memory access pattern analysis. The AoS-to-SoA transformation alone accounts for more performance wins than all other optimizations combined in many real-world applications (particle simulations, N-body, graph layout).

**Profiling infrastructure is undervalued**: The guide's profiling-driven approach is sound, but in practice, the learning curve for Nsight Compute is steep. Many developers skip profiling entirely and guess at optimizations. A dedicated section teaching developers how to read the five most important metrics (gld_efficiency, achieved_occupancy, shared_efficiency, L1 hit rate, compute utilization) would be the most impactful addition to a future edition.

**Streams are architecture-dependent**: The concurrency behavior of streams has changed across GPU generations. Fermi had 16 hardware work queues (not exposed for concurrency), Kepler introduced 32 Hyper-Q queues, and Maxwell/Pascal refined the scheduling. Developers targeting multiple GPU generations must be aware that stream behavior (and the benefit of multiple streams) varies significantly. The guide could benefit from an architecture-specific concurrency matrix.

**Best practices age well, but not perfectly**: The core principles (coalescing, occupancy, bank conflict avoidance) have been stable since CUDA 1.0. However, newer features like CUDA Graphs (CUDA 10), asynchronous memory pools (CUDA 11), and thread block clusters (Hopper, SM 90) introduce optimization strategies that the original best practices framework does not fully cover. A supplement covering "best practices for modern CUDA" would be valuable.

---

## References

1. NVIDIA. *CUDA C++ Best Practices Guide*. https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ -- 主要参考文档，涵盖 Occupancy、Coalescing、Stream 和 Profiling 各章节
2. NVIDIA. *CUDA C++ Programming Guide*. https://docs.nvidia.com/cuda/cuda-c-programming-guide/ -- 第 3 章 Stream 与 Event，第 5 章 Performance Guidelines
3. NVIDIA. *Nsight Compute Documentation*. https://docs.nvidia.com/nsight-compute/ -- Profiling 指标说明
4. NVIDIA. *CUDA Occupancy Calculator*. https://docs.nvidia.com/cuda/cuda-occupancy-calculator/ -- Occupancy 计算工具
5. Harris, Mark. "How to Access Global Memory Efficiently." NVIDIA Developer Blog, 2013. https://developer.nvidia.com/blog/how-access-global-memory-efficiently-cuda-kernel/ -- Global Memory Coalescing 详解
6. NVIDIA. "CUDA Pro Tip: Vectorized Memory Access." NVIDIA Developer Blog, 2015. -- Vectorized Memory Access 技巧
7. Kirk, David B., and Wen-mei W. Hwu. *Programming Massively Parallel Processors: A Hands-on Approach*. 3rd ed., Morgan Kaufmann, 2016. -- 第 6 章 Performance Considerations，第 9 章 Advanced Optimizations
