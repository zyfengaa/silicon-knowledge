# 论文笔记：NVIDIA CUDA 最佳实践指南

## 贡献

NVIDIA CUDA 最佳实践指南为优化 GPU kernel 提供了一套系统化、以实证为基础的方法论，涵盖占用率调优、内存访问模式、流并发以及分析驱动的迭代改进。

## 背景

使用 CUDA 进行通用 GPU（GPGPU）编程可提供巨大的并行吞吐能力，但朴素实现通常只能达到 GPU 理论峰值性能的一小部分。这一差距之所以出现，是因为 GPU 性能取决于硬件资源（寄存器、共享内存、warp 调度器、内存带宽）与软件配置（网格/线程块维度、内存访问模式、流的使用）之间复杂的相互作用。没有一套有原则的优化框架，开发者就无法可靠地识别瓶颈，也无法预测哪些变换会带来最大的加速。

CUDA 最佳实践指南（随 CUDA 2.0 首次发布，并针对每一代架构持续更新，直至 Hopper/Blackwell）填补了这一空白，它将经过数千个 kernel 和数代 GPU 验证的优化模式编纂成文。它建立在 Patterson 和 Hennessy 开创的定量方法之上，并针对 SIMT（单指令多线程，Single Instruction, Multiple Thread）执行的独特约束进行了调整。

## 核心概念

### 1. 占用率（occupancy）最大化

**占用率（occupancy）** 是活跃 warp 数与每个 SM 所支持的最大 warp 数之比。更高的占用率有助于隐藏延迟，因为当当前 warp 停顿（例如在内存访问上）时，warp 调度器有更多独立的 warp 可供发射。

本指南强调，**占用率本身并不是目标**——它是隐藏延迟的一种手段。其权衡包括：

- **寄存器压力（register pressure）**：每个线程使用更少的寄存器会提高占用率，但可能导致寄存器溢出（register spilling）到本地内存（这会占用缓慢的全局内存带宽）。指南建议使用 `--maxrregcount` 或 `__launch_bounds__` 来控制每个 kernel 的寄存器用量。
- **共享内存（shared memory）用量**：共享内存是每个 SM 上有限的资源（A100 上为 164 KB，H100 上为 228 KB）。每个线程块使用更多共享内存，会减少可同时驻留在某个 SM 上的线程块数量。
- **线程块大小（block size）选择**：线程块大小应是 warp 大小（32）的整数倍，并且要足够大以让 SM 保持忙碌，但也不能大到使寄存器/共享内存限制阻碍占用率。典型大小为每个线程块 128、256 或 512 个线程。

占用率 API（`cudaOccupancyMaxPotentialBlockSize`、`cudaOccupancyMaxActiveBlocksPerMultiprocessor`）允许开发者在运行 kernel 之前，针对给定的 kernel 配置计算理论占用率。

**指南中的关键洞见**：对于内存受限（memory-bound）的 kernel，中等占用率（50-67%）通常足以隐藏 DRAM 延迟；更高的占用率带来的收益会递减。对于具有高指令级并行（instruction-level parallelism，ILP）的计算受限（compute-bound）kernel，更低的占用率也可能足够。

### 2. 内存合并访问（coalescing）模式

全局内存（global memory）带宽是 GPU kernel 中最常见的瓶颈。GPU 内存控制器会将多个线程的访问合并为宽事务（transaction）：L2 缓存行（cache line）为 128 字节，传输以 32 字节扇区（sector）为单位处理。指南指出了关键原则：

> warp 中的相邻线程应访问相邻的内存地址。

具体而言：

- **最优情况**：线程 `i` 访问某个段中的第 `i` 个字（word）。单次 128 字节事务即可服务整个 warp（对于 4 字节数据类型）。可实现 100% 的合并访问效率。
- **跨步访问（strided access）**：线程 `i` 访问第 `i * stride` 个字。如果 stride > 1，内存控制器会发出多个事务。对于 stride = 2，会发出 2 倍数量的事务；对于 stride = 32，每个线程访问的是独立的缓存行段。
- **随机/索引访问（random/indexed access）**：线程 `i` 访问 `array[index[i]]`。只有当 `index[i]` 的值本身连续时，才可能实现合并访问。

指南推荐使用数组结构（structure-of-arrays，SoA）布局而非结构体数组（array-of-structures，AoS）布局，以最大化合并访问：

```
// AoS (bad for coalescing)
struct Particle { float x, y, z; };
Particle particles[N];  // threads access: x y z x y z ...

// SoA (good for coalescing)
struct Particles { float x[N], y[N], z[N]; };
// threads access: x x x ... y y y ... z z z ...
```

### 3. 避免 bank 冲突

共享内存在所有现代 NVIDIA GPU 上被组织为 32 个 bank。连续的 32 位字映射到连续的 bank（第 `i` 个字映射到 bank `i % 32`）。当一个 warp 中的多个线程访问同一个 bank 中的不同地址时，就会发生 **bank 冲突（bank conflict）**，从而将这些访问串行化。

指南指出了三种模式：

| 访问模式 | 是否存在 bank 冲突？ | 有效带宽 |
|---|---|---|
| 所有线程访问同一地址（广播，broadcast） | 否（广播给所有线程） | 100% |
| 线程 i 访问字 i（无冲突） | 否 | 100% |
| 线程 i 访问字 i * 2（步长 2） | 2 路冲突 | 50% |
| 线程 i 访问字 i * 32（步长 32） | 32 路冲突（最坏情况） | ~3% |

**规避策略**：
- 为共享内存数组填充（padding）：使用 `__shared__ float s[32][33]` 而不是 `s[32][32]`，增加一个填充列以改变 bank 映射。
- 对只读数据使用 `__ldg()`（只读缓存，read-only cache），从而完全绕过共享内存。
- 重新组织访问模式，使 warp 内的线程访问不同的 bank。

### 4. 流（stream）的使用与重叠

CUDA 流（stream）支持 kernel、数据传输与主机端工作的并发执行。指南涵盖三个层次的并发：

1. **Kernel 并发（Hyper-Q）**：如果 SM 资源充足，来自不同流的多个 kernel 可以在同一 GPU 上并发运行。该功能随 Kepler GK110（计算能力（Compute Capability）3.5）引入。在 Kepler 及之后架构上，并发硬件工作队列的数量为 32。

2. **数据传输重叠**：将 `cudaMemcpyAsync` 与页锁定内存（pinned memory）配合使用，并且传输与 kernel 位于不同流、GPU 支持双向 DMA（两个拷贝引擎（copy engine））时，数据传输可以与 kernel 执行重叠。

3. **主机—设备并行（host-device parallelism）**：异步操作会立即将控制权交还给 CPU，使主机侧工作可以与 GPU 操作重叠。

**实现重叠的前提条件**：
- 主机内存必须是页锁定内存（通过 `cudaHostAlloc` 或 `cudaMallocHost` 分配）
- 所有操作必须使用非默认流
- GPU 必须具有足够的拷贝引擎（检查 `prop.asyncEngineCount`）

指南提醒，如果跨流的操作共享资源（例如同一块内存分配），**虚假依赖（false dependencies）** 会使这些操作串行化。

### 5. 分析驱动优化（profiling-driven optimization）

指南倡导一种迭代式的“性能分析—分析—优化”（profile-analyze-optimize）循环：

1. **性能分析（Profile）**：使用 NVIDIA Nsight Compute（ncu）或 Nsight Systems（nsys）采集硬件性能计数器。
2. **识别瓶颈**：使用“光速”（Speed of Light）指标（内存利用率与计算利用率）将其分类为内存受限或计算受限。
3. **分析具体指标**：
   - `achieved_occupancy`：warp 是否因活跃 warp 不足而停顿？
   - `gld_efficiency` / `gst_efficiency`：内存访问是否被合并？
   - `shared_efficiency`：是否正在发生 bank 冲突？
   - `stall_memory_dependency`：warp 是否因等待内存而停顿？
   - `stall_short_scoreboard`：warp 是否因寄存器依赖而停顿？
4. **针对瓶颈应用优化**。

指南强调，没有经过性能分析就进行过早优化是一种浪费：“先测量，再猜测。”

## 我的思考

**占用率与 ILP 的权衡**：指南对占用率的细致处理是其最突出的贡献之一。早期的 CUDA 教程（约 2009—2012 年）常常把“最大化占用率”当作绝对规则，导致开发者在 kernel 需要 20 个寄存器时只使用 8 个，从而引发大量寄存器溢出。指南正确地将占用率重新定义为隐藏延迟的工具，而不是最终目标。对于具有高指令级并行的计算 kernel，低占用率（例如 25%）也能实现接近峰值的吞吐量，因为调度器会让每个 warp 忙于执行独立的指令，而不是在 warp 之间切换。

**合并访问是影响最大的单项优化**：根据我的经验，将未合并的访问模式从 10% 的效率修复到 100%，可以带来 5—10 倍的加速——远超任何其他单项优化。指南正确地优先考虑内存访问模式分析。在许多实际应用（粒子模拟、N 体模拟、图布局）中，仅 AoS 到 SoA 的转换所带来的性能收益，就超过所有其他优化收益的总和。

**性能分析基础设施的价值被低估**：指南的分析驱动方法本身是合理的，但在实践中，Nsight Compute 的学习曲线很陡峭。许多开发者完全跳过性能分析，凭猜测进行优化。如果专门用一节来教开发者如何解读五个最重要的指标（内存吞吐量、实际占用率、L1/L2 命中率、计算利用率以及 warp 停顿原因），那将是未来版本中最有影响力的补充。

**流的行为依赖于架构**：流的并发行为在历代 GPU 之间发生了变化。Fermi 使用单一的硬件工作队列，因此来自不同流的 kernel 可能因虚假依赖而串行化；Kepler 引入了 32 个 Hyper-Q 硬件队列，使并发流变得实用。Maxwell/Pascal 及后续架构进一步改进了调度。面向多代 GPU 的开发者必须意识到，流的行为（以及多流带来的收益）差异显著。指南若能补充一张按架构区分的并发能力对照表，将会更有帮助。

**最佳实践能够经受时间考验，但并非完美**：核心原则（合并访问、占用率、避免 bank 冲突）自 CUDA 1.0 以来一直保持稳定。然而，较新的特性（如 CUDA 图（CUDA Graphs，CUDA 10）、异步内存池（asynchronous memory pools，CUDA 11）以及线程块簇（thread block clusters，Hopper，SM 90））引入了原始最佳实践框架尚未完全覆盖的优化策略。补充一份“现代 CUDA 最佳实践”的增补内容将很有价值。

---

## 参考文献

1. NVIDIA. *CUDA C++ Best Practices Guide*. https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ -- 主要参考文档，涵盖 Occupancy、Coalescing、Stream 和 Profiling 各章节
2. NVIDIA. *CUDA C++ Programming Guide*. https://docs.nvidia.com/cuda/cuda-c-programming-guide/ -- 第 3 章 Stream 与 Event，第 5 章 Performance Guidelines
3. NVIDIA. *Nsight Compute Documentation*. https://docs.nvidia.com/nsight-compute/ -- Profiling 指标说明
4. NVIDIA. *CUDA Occupancy Calculator*. https://docs.nvidia.com/cuda/cuda-occupancy-calculator/ -- Occupancy 计算工具
5. Harris, Mark. "How to Access Global Memory Efficiently." NVIDIA Developer Blog, 2013. https://developer.nvidia.com/blog/how-access-global-memory-efficiently-cuda-kernel/ -- Global Memory Coalescing 详解
6. NVIDIA. "CUDA Pro Tip: Increase Performance with Vectorized Memory Access." NVIDIA Developer Blog, 2013. -- Vectorized Memory Access 技巧
7. Kirk, David B., and Wen-mei W. Hwu. *Programming Massively Parallel Processors: A Hands-on Approach*. 3rd ed., Morgan Kaufmann, 2016. -- 第 6 章 Performance Considerations，第 9 章 Advanced Optimizations
