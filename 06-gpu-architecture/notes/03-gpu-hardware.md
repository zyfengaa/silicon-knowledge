# 03 — GPU 硬件组成

> SM（流式多处理器）是 GPU 的计算核心。理解 SM 的内部结构是理解 GPU 性能的基础。

---

## 1. GPU 整体架构

GPU 由多个 SM（Streaming Multiprocessor）组成，所有 SM 通过高速互联网络连接到 L2 缓存和 HBM 显存控制器。

```
GPU 芯片顶层布局（H100 示例）：
┌─────────────────────────────────────────────────────────┐
│  GPC 0     │  GPC 1     │  GPC 2     │  GPC 3          │
│  ┌───────┐  │  ┌───────┐  │  ┌───────┐  │  ┌───────┐     │
│  │ SM 0  │  │  │ SM 4  │  │  │ SM 8  │  │  │ SM 12 │     │
│  │ SM 1  │  │  │ SM 5  │  │  │ SM 9  │  │  │ SM 13 │     │
│  │ SM 2  │  │  │ SM 6  │  │  │ SM 10 │  │  │ SM 14 │     │
│  │ SM 3  │  │  │ SM 7  │  │  │ SM 11 │  │  │ SM 15 │     │
│  └───────┘  │  └───────┘  │  └───────┘  │  └───────┘     │
├──────────────┴──────────────┴──────────────┴──────────────┤
│                  L2 缓存 (共 50 MB)                        │
├───────────────────────────────────────────────────────────┤
│ HBM3 Ctrl │ HBM3 Ctrl │ HBM3 Ctrl │ HBM3 Ctrl │ HBM3 Ctrl │
└───────────────────────────────────────────────────────────┘
```

**关键结构**：

- **GPC（Graphics Processing Cluster）**：将多个 SM 分组，共享 L1 缓存和光栅化单元
- **SM（Streaming Multiprocessor）**：计算的基本单元，包含执行单元、寄存器和共享内存
- **L2 Cache**：所有 SM 共享的最后一级缓存
- **HBM 控制器**：多个 HBM（High Bandwidth Memory）控制器提供极高带宽

| 架构 | 制造工艺 | 晶体管数 | SM 数量 | CUDA Core/SM | 总计 CUDA Core |
|------|---------|---------|---------|--------------|---------------|
| Turing TU102 | TSMC 12nm | 18.6B | 72 | 64 | 4,608 |
| Ampere GA102 | Samsung 8nm | 28.3B | 84 | 128 | 10,752 |
| Hopper GH100 | TSMC 4N | 80B | 132 | 128 | 16,896 |
| Blackwell GB100 | TSMC 4NP | 208B | 168 | 128 | 21,504 |

---

## 2. SM（流式多处理器）内部结构

SM 是 GPU 的计算核心。不同世代的 SM 结构略有差异，但核心部件保持一致。

### SM 的主要组件

```
H100 SM 内部结构：
┌────────────────────────────────────────────────────────┐
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ Warp Scheduler 0 │  │ Warp Scheduler 1 │           │
│  │  指令缓存         │  │  指令缓存         │           │
│  └────────┬─────────┘  └────────┬─────────┘           │
│           │                     │                     │
│  ┌────────▼──────────────────────▼─────────┐          │
│  │        寄存器文件 (256 KB)               │          │
│  └────────┬──────────────────────┬─────────┘          │
│           │                     │                     │
│  ┌────────▼─────────┐  ┌────────▼─────────┐          │
│  │  FP32 单元 x32   │  │  FP32 单元 x32   │          │
│  │  INT32 单元 x16  │  │  INT32 单元 x16  │          │
│  │  FP64 单元 x2    │  │  FP64 单元 x2    │          │
│  │  Tensor Core x4  │  │  Tensor Core x4  │          │
│  └──────────────────┘  └──────────────────┘          │
│                                                       │
│  ┌────────────┐     ┌────────────┐                    │
│  │ Shared Mem │     │  L1 Cache  │                    │
│  │  (128 KB)  │     │  (128 KB)  │                    │
│  └────────────┘     └────────────┘                    │
│           总共享内存+L1：256 KB（可配置）              │
└────────────────────────────────────────────────────────┘
```

| 组件 | 功能 | H100 SM 规格 |
|------|------|-------------|
| **Warp Scheduler** | 管理 warp 就绪状态，每周期调度发射 | 4 个 |
| **指令缓存** | 缓存 warp 待执行的指令 | 每个调度器独立 |
| **寄存器文件** | 活动线程的寄存器状态 | 256 KB / SM |
| **FP32 单元** | 单精度浮点运算（CUDA Core 核心） | 64 / SM 分区 × 2 = 128 |
| **INT32 单元** | 整数运算 | 32 / SM 分区 × 2 = 64 |
| **FP64 单元** | 双精度浮点运算 | 4 / SM 分区 × 2 = 8 |
| **Tensor Core** | 矩阵乘加加速（第 4 代） | 4 / SM 分区 × 2 = 8 |
| **Shared Memory** | 片上低延迟共享存储 | 128 KB（可配置） |
| **L1 Cache** | 片上数据缓存 | 128 KB（可配置） |

### SM 分区

现代 GPU 的 SM 被划分为多个分区（partition，NVIDIA 内部称 "SM sub-partition" 或 "processing block"），每个分区包含一组独立的执行单元和一个 warp 调度器。

H100 每个 SM 有 4 个分区，每个分区包含：
- 1 个 Warp Scheduler
- 16 个 FP32 单元
- 8 个 INT32 单元
- 2 个 FP64 单元
- 2 个 Tensor Core
- 2 个 LD/ST 单元（用于访存）

---

## 3. CUDA Core（FP32 单元）

CUDA Core 是 NVIDIA 市场营销中最常提到的概念，本质上是一个执行标准单精度浮点运算的 ALU。

**CUDA Core 不是"核心"**：与 CPU 核心不同，CUDA Core 只负责执行简单计算，没有取指、译码、乱序执行等复杂逻辑。多个 CUDA Core 共享一条指令流。

**演进历史**：

| 代次 | 架构 | Core/SM | 功能 |
|------|------|---------|------|
| 1st | Tesla (G80) | 8 | 仅有 FP32 |
| 2nd | Fermi (GF100) | 32 | FP32 + INT32 |
| 3rd | Kepler (GK104) | 192 | FP32 + INT32 |
| 4th | Maxwell (GM204) | 128 | FP32 + INT32 |
| 5th | Pascal (GP104) | 128 | FP32 + INT32 |
| 6th | Volta (GV100) | 64 | FP32 + INT32（分离管线） |
| 7th | Turing (TU102) | 64 | FP32 + INT32（并发执行） |
| 8th | Ampere (GA102) | 128 | FP32 + INT32 + FP64 |
| 9th | Hopper (GH100) | 128 | FP32 + INT32 + FP64 |
| 10th | Blackwell (GB100) | 128 | 改进的 FP32/Tensor Core |

---

## 4. SM 的线程管理能力

SM 需要同时管理大量的 warp 和线程。以下是主要限制：

| 资源 | H100 (GH100) | A100 (GA100) | V100 (GV100) |
|------|-------------|-------------|-------------|
| 最大 warp / SM | 64 | 64 | 64 |
| 最大线程 / SM | 2048 | 2048 | 2048 |
| 最大线程块 / SM | 32 | 32 | 32 |
| 最大线程 / 线程块 | 1024 | 1024 | 1024 |
| 寄存器文件 / SM | 256 KB | 256 KB | 256 KB |
| 共享内存 / SM | 228 KB | 164 KB | 96 KB |

**实际约束**：启动 kernel 时，GPU 会根据线程块大小、每个线程使用的寄存器数、每个块使用的共享内存量来计算实际可以分配到 SM 上的线程块数量。

---

## 5. GPU 的缓存和内存控制器

### L2 缓存

L2 缓存在所有 SM 之间共享，用于缓存全局内存访问。L2 缓存是避免频繁访问 HBM 的关键。

| GPU | L2 缓存大小 | L2 分区 |
|-----|------------|---------|
| H100 | 50 MB | 24 个分区 |
| A100 | 40 MB | 40 个分区 |
| V100 | 6 MB | 32 个分区 |

### 内存控制器

GPU 通过多个 HBM 控制器访问显存，提供远超传统内存的带宽：

| GPU | 显存类型 | 总线宽度 | 带宽 | 容量 |
|-----|---------|---------|------|------|
| H100 SXM | HBM3 | 5120-bit | 3.35 TB/s | 80 GB |
| A100 SXM | HBM2e | 5120-bit | 2.0 TB/s | 80 GB |
| V100 SXM | HBM2 | 4096-bit | 900 GB/s | 32 GB |

---

## 参考文献

- NVIDIA, *H100 GPU Architecture Whitepaper*, 2022. Sections: GPU Architecture Overview, SM Architecture.
- NVIDIA, *A100 GPU Architecture Whitepaper*, 2020. Section: Streaming Multiprocessor.
- NVIDIA, *V100 GPU Architecture Whitepaper*, 2017. Section: SM Architecture.
- Kirk, D. B. & Hwu, W. W., *Programming Massively Parallel Processors: A Hands-on Approach*, 3rd ed., Chapter 4: CUDA Threads and Memory Hierarchy, Morgan Kaufmann, 2016.
- NVIDIA, *CUDA C++ Programming Guide*, Section 2.3: The Streaming Multiprocessor.
- Patterson, D. A. & Hennessy, J. L., *Computer Organization and Design: The Hardware/Software Interface*, 6th ed., Chapter 6, Section 6.4: GPU Architectures, Morgan Kaufmann, 2020.
- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Chapter 4: Vector, SIMD, and GPU Architectures, Section 4.5: NVIDIA GPU Architecture, Morgan Kaufmann, 2018.
