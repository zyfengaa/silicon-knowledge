# 读书笔记：SIMT 执行模型

> **文献信息**
> - **主要来源：** NVIDIA. *CUDA C++ Programming Guide*. 2024. — Chapter 4: Hardware Implementation
> - **教材：** Kirk, D. B., & Hwu, W. W. *Programming Massively Parallel Processors: A Hands-on Approach*. 4th Edition. Morgan Kaufmann, 2022. — Chapter 4: GPU Execution Model

---

## 一句话贡献

SIMT（Single Instruction, Multiple Thread）模型将多线程的程序设计便利性与 SIMD 的硬件效率结合起来，使数千个轻量级线程以锁步组（warp）的形式在 SIMD 类数据通路上执行。

---

## 背景：为什么 GPU 使用 SIMT

### 纯 SIMD 的问题

传统 SIMD（如 SSE、AVX、NEON）要求程序员：

- 在代码中显式感知向量宽度（打包/解包）
- 访问模式必须是步长 1 才能高效
- 分支必须用 predication 或掩码执行来处理
- 不同向量宽度需要不同的代码路径

这使得 SIMD 编程容易出错且不可移植。程序员以标量思维思考，却必须以向量方式编写代码。

### 纯 MIMD 的问题

纯 MIMD（如多核 CPU）允许每个线程独立执行不同指令，但：

- 每个核需要自己的指令获取、译码和控制逻辑
- 每线程的硬件开销高（寄存器文件、程序计数器、控制状态）
- 扩展到数千个线程不现实（面积和功耗）

### SIMT 的折中方案

SIMT 在两者间取折中：程序员编写单个线程的标量代码，但硬件将 32 个线程分组为一个 **warp**，共享单个指令获取单元。这带来了：

- **程序员生产力：** 无需向量 intrinsic，编写普通标量代码即可
- **硬件效率：** 一个指令单元服务 32 个线程
- **可扩展性：** 每个 GPU 可支持数千个线程

---

## 核心概念

### 1. SIMT 与 SIMD 的关键区别

| 维度 | SIMD（如 SSE/AVX） | SIMT（CUDA） |
|--------|----------------------|-------------|
| **编程模型** | 显式向量操作 | 标量每线程代码 |
| **向量宽度** | ISA 层固定（4/8/16） | 硬件管理（32 线程/warp） |
| **控制流** | 仅 Predication | 每 warp 掩码 |
| **内存模型** | Gather/scatter 或连续 | 每线程任意模式；coalescing 为性能优化 |
| **线程身份** | 隐式（元素索引） | 显式（threadIdx, blockIdx） |
| **同步** | 向量内不适用 | 显式 __syncthreads() |

**关键洞察：** 在 SIMD 中，程序员显式管理并行性。在 SIMT 中，硬件管理并行性——程序员只需编写线程。

### 2. Warp 执行

- **warp** 是 CUDA 中 32 个连续线程的分组，它们一起执行
- warp 内的所有线程在同一时间执行 **同一条指令**（操作不同的数据）
- 每个线程有自己的程序计数器和寄存器状态
- warp 调度器在每个周期选择一个 warp 发射指令

```
Warp 0: Threads 0-31  ->  共享指令获取  ->  32 个 ALU 通道
Warp 1: Threads 32-63 ->  共享指令获取  ->  32 个 ALU 通道
```

### 3. Warp Divergence（warp 发散）

当同一 warp 中的线程走不同的控制流路径时，warp 发生 **发散**：

```cuda
if (threadIdx.x < 16) {
    // 路径 A：线程 0-15
} else {
    // 路径 B：线程 16-31
}
```

**执行方式：** 两条路径串行执行——GPU 先执行路径 A（线程 0-15 活跃，线程 16-31 被掩码），然后执行路径 B（线程 16-31 活跃，线程 0-31 被掩码）。

**性能影响：** warp 需要 cycles(path_A) + cycles(path_B) 而不是 max(cycles(path_A), cycles(path_B))。

**避免方法：** 重组数据使发散决策发生在 block 级别而非 warp 级别；对小分支使用 predication。

### 4. Convergence（汇合）

在发散分支之后，所有线程必须在 **汇合点**（if/else 之后的指令）重新汇合。硬件通过 **活跃掩码**（active mask）跟踪哪些线程活跃，并在汇合点恢复完整掩码。

### 5. SIMT 栈

现代 GPU 使用 **SIMT 栈** 管理发散：

- 每个 warp 有一个硬件栈
- 在发散分支处：为每条路径压入新掩码
- 在汇合点：弹出恢复之前的掩码
- 支持嵌套发散（nested divergence）

---

## 硬件映射：从 Grid 到执行

### 执行层次

```
Grid            ->  多个线程块（thread blocks）
Thread Block    ->  多个 warp（blockDim.x / warpSize）
Warp            ->  32 个线程，同一条指令
```

### 流多处理器（SM）架构

每个 SM 包含：

- **Warp 调度器：** 每 SM 2-4 个（Fermi: 2, Maxwell: 4, Volta: 4）
- **CUDA 核心 / ALU：** 每 SM 32-128 个
- **寄存器文件：** 每 SM 64K-256K 个寄存器（在 warp 间分配）
- **共享内存：** 每 SM 16-128 KB
- **Warp 上下文：** 约 64 个 warp 的状态（支持快速切换）

### 指令发射

Warp 调度器选择一个就绪的 warp 并发射一个或两个指令：

- Maxwell 以上：两个独立的 warp 调度器，每个每周期发射一条指令
- Volta 以上：四个调度器，每个每周期发射一条指令（独立线程调度）
- 每个调度器从 16-32 个 warp 中选择以隐藏延迟

### 延迟隐藏

与 CPU（使用缓存隐藏内存延迟）不同，GPU 使用 **线程级并行**：

- 当一个 warp 因内存访问而停顿，调度器切换到另一个就绪的 warp
- 每 SM 64 个 warp，最多 64*32 = 2048 个线程可隐藏内存延迟
- 寄存器文件包含所有活跃 warp 的状态，实现零周期上下文切换

---

## 我的反思

1. **SIMT 是一个出色的抽象层。** 它让程序员编写直观的标量代码，同时硬件实现 SIMD 效率。这可能是 CUDA 被广泛采用的最大原因——你不需要是向量化专家就能编写高效的 GPU 代码。

2. **发散的代价取决于具体场景。** 如果大部分线程走较短路径，则较短的发散路径代价不大。此外，跨 warp 的发散不影响性能——只有 warp 内部的发散才有代价。

3. **Warp 是 GPU 优化的基本单元。** Warp 决定了 coalescing（32 个线程一起访问内存）、同步（warp 内隐式同步）和 occupancy（活跃 warp 数量）。理解 warp 行为是 GPU 优化的基础。

4. **Volta 的独立线程调度改变了游戏规则。** Volta 之前的 GPU 中，warp 内的线程严格锁步执行。Volta 引入了独立线程调度，允许 warp 内的线程更灵活地发散，并启用了更多编译器优化。代价是需要更显式的同步。

5. **SIMT 与 SIMD 是工程权衡，不是根本性的架构差异。** NVIDIA 为 GPU 选择了 SIMT；Intel 为 CPU 选择了 SIMD；向量机（Cray、NEC SX 系列）选择了向量长度无关的 SIMD。每种选择针对不同的工作负载特性和程序员期望进行了优化。

---

## 参考文献

1. NVIDIA. *CUDA C++ Programming Guide*. 2024. — Chapter 4: Hardware Implementation. 关于 SIMT 模型和 warp 执行的权威参考。
2. Kirk, D. B., & Hwu, W. W. *Programming Massively Parallel Processors: A Hands-on Approach*. 4th Edition. Morgan Kaufmann, 2022. — Chapter 4: Execution Model. 清晰的带有图示的教学解释。
3. Lindholm, E., Nickolls, J., Oberman, S., & Montrym, J. "NVIDIA Tesla: A Unified Graphics and Computing Architecture." *IEEE Micro*, Vol. 28, No. 2, 2008. — Tesla 架构中 SIMT 模型的原始描述。
4. Nickolls, J., & Dally, W. J. "The GPU Computing Era." *IEEE Micro*, 2010. — GPU 计算演进概述，包括 SIMT 与 SIMD 的权衡。
5. Fung, W. L., et al. "Dynamic Warp Formation and Management for GPU Workloads." *PACT'09*. — 关于通过动态重组减少发散开销的研究。
6. Harris, M. "CUDA Pro Tip: Optimize for Warp Execution." *NVIDIA Developer Blog*, 2013. — 关于 warp 执行优化的实践技巧。
