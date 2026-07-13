# 07 — CUDA Programming & Optimization: Exercises

> 通过以下问题验证你对 CUDA Occupancy 计算、Stream 并发、Pinned Memory、Profiling 指标解读和优化优先级排序的理解。

---

## 问题 1: Occupancy 计算

考虑一个 GPU 的以下规格：

| 规格 | 值 |
|------|-----|
| SM 寄存器数 | 65536 |
| 最大线程 / SM | 1024 |
| 最大 Block / SM | 32 |
| Warp 大小 | 32 |

Kernel 使用的资源：

- **场景 A**: 每线程 32 个寄存器，0 bytes 共享内存，256 线程 / block
- **场景 B**: 每线程 64 个寄存器，0 bytes 共享内存，256 线程 / block
- **场景 C**: 每线程 128 个寄存器，0 bytes 共享内存，256 线程 / block

对于每个场景，计算：

1. 每个 Block 需要多少个 Warp？
2. 受寄存器限制，SM 上最多能驻留多少个 Block？
3. 受最大线程数限制，SM 上最多能驻留多少个 Block？
4. 受最大 Block 数限制，SM 上最多能驻留多少个 Block？
5. 在该 SM 上可以同时活跃的 Block 数（取上述限制的最小值）
6. 活跃 Warp 数
7. 理论 Occupancy（活跃 Warp 数 / 最大 Warp 数），其中最大 Warp 数 = 1024 / 32 = 32
8. 哪个资源是限制因素？

## 问题 2: Stream 并发条件

**Part A**: 解释来自不同 Stream 的 Kernel 能够并发执行需要满足哪些条件。至少列出 4 个条件。

**Part B**: 哪些硬件资源会限制 Stream 之间的并发程度？请列举至少 3 个因素。

**Part C**: 同一个 Stream 上的不同 Kernel 能否并发执行（重叠）？为什么？如果使用 CUDA Graphs，情况是否有变化？

## 问题 3: Pinned Memory 机制

**Part A**: 解释为什么使用 `cudaMemcpy` 在 Host 和 Device 之间传输数据时，使用 Pinned Memory（通过 `cudaHostAlloc` 或 `cudaMallocHost` 分配）比 Pageable Memory（通过 `malloc` 分配）更快。

**Part B**: 过多分配 Pinned Memory 有什么缺点？操作系统层面会发生什么问题？

**Part C**: 从 OS 机制层面描述 Pinned Memory 加速传输的原理。描述以下关键点：
- Page fault 的作用
- DMA（Direct Memory Access）如何在不占用 CPU 的情况下完成传输
- 为什么 Pageable Memory 在 `cudaMemcpy` 中需要额外的中间拷贝步骤

## 问题 4: Profiling 指标解读

你通过 Nsight Systems 或 nvprof 对某个 CUDA Kernel 进行 Profiling，得到以下指标：

| 指标 | 值 |
|------|-----|
| achieved_occupancy | 0.45 |
| gld_efficiency | 0.25 |
| shared_efficiency | 0.9 |
| stall_memory_dependency | 45% |

**Questions:**

1. 诊断该 Kernel 的性能瓶颈是什么？请结合具体指标说明。
2. 提出至少两个具体的优化方案来缓解这个瓶颈。对于每个方案，解释它如何影响上述指标中的一个或多个。
3. 如果将该 Kernel 改为使用 __ldg()（Read-Only Cache）加载只读数据，预计哪个指标会改善？为什么？

## 问题 5: 优化优先级排序

对于一个 CUDA Kernel，它在不同的 Tile 大小下分别表现为 Memory-Bound 和 Compute-Bound。以下是可能的优化技术：

- Coalescing（合并访问）
- Occupancy 最大化
- Shared Memory Tiling（共享内存分块）
- Loop Unrolling（循环展开）
- Instruction-Level Parallelism（指令级并行）
- Bank Conflict 消除

**Tasks:**

1. 将这些优化技术按照从最有效到最无效的顺序排列（针对一个既可能 Memory-Bound 又可能 Compute-Bound 的通用 Kernel）。假设你从完全没有优化的 Naive 版本开始。

2. 对于每个优化技术，简要说明：
   - 它主要针对 Memory-Bound 还是 Compute-Bound 场景？
   - 为什么它的优先级在这个位置？

3. 如果通过 Profiling 发现 Kernel 已经是 Memory-Bound（Memory Utilization > 90%，Compute Utilization < 30%），你的优化优先级顺序会如何变化？

---

## 参考文献

1. NVIDIA. *CUDA C++ Programming Guide*. https://docs.nvidia.com/cuda/cuda-c-programming-guide/ -- Ch.3 Stream, Ch.5 Performance Guidelines
2. NVIDIA. *CUDA C++ Best Practices Guide*. https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ -- Occupancy, Memory Optimizations, Streams
3. NVIDIA. *CUDA Occupancy Calculator*. https://docs.nvidia.com/cuda/cuda-occupancy-calculator/
4. NVIDIA. *Nsight Compute Documentation*. https://docs.nvidia.com/nsight-compute/ -- Profiling Metrics
5. Kirk, David B., and Wen-mei W. Hwu. *Programming Massively Parallel Processors*. 3rd ed., Morgan Kaufmann, 2016. -- Ch.6 Performance Considerations, Ch.9 Advanced Optimizations
6. Harris, Mark. "How to Access Global Memory Efficiently." NVIDIA Developer Blog, 2013.
