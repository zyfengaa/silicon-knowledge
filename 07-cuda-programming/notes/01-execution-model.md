# 01 — CUDA Execution Model

> 理解 GPU 如何把你的 kernel 代码映射到硬件上执行。

## Grid → Block → Thread 的硬件映射

CUDA 采用三级抽象，每一级都有对应的硬件实体：

| 编程抽象 | 硬件实体 | 说明 |
|----------|----------|------|
| Grid      | GPU 设备        | 一个 kernel 启动对应一个 Grid |
| Block     | Streaming Multiprocessor (SM) | 每个 Block 被调度到 **一个 SM** 上执行 |
| Thread    | CUDA Core        | Warp 中的线程在 Core 上执行 |

**关键规则：**
- **一个 Block 只能在一个 SM 上执行**，不会跨 SM
- **一个 SM 可以同时运行多个 Block**（资源允许时）
- Block 内的线程通过 **Shared Memory** 和 **Barrier Synchronization** 协作
- 不同 Block 之间**无法协作**（只能通过 Global Memory 间接通信）

```
Grid (kernel)
├── Block (0,0) → SM 0
│   ├── Thread (0,0,0)
│   ├── Thread (0,0,1)
│   └── ...
├── Block (1,0) → SM 1
│   ├── Thread (0,0,0)
│   └── ...
└── Block (2,0) → SM 0  (多个 Block 可以共享 SM)
```

## Block 调度

SM 内部有一个 **Block Scheduler**，负责将 Block 分配给可用的 SM。调度策略是**贪心的**：只要有空闲 SM，就立即分配下一个 Block。

**多 Block 在同一个 SM 上的条件：**
SM 的资源（寄存器、共享内存、线程数上限）必须能够同时容纳这些 Block。

```
SM 资源池
├── 寄存器: 65536
├── 共享内存: 96 KB
├── 最大线程数: 1536
├── 最大 Block 数: 16
│
├── Block A: 256 threads, 32 reg/thread, 8 KB shared
├── Block B: 256 threads, 32 reg/thread, 8 KB shared
│   (剩余资源: 512 threads, 32768 regs, 80 KB shared → 可容纳更多 Block)
└── ...
```

## Warp — 执行的基本单元

Warp 是 32 个线程的集合，是 GPU 调度和执行的**最小单元**。

- 一个 Block 中的线程被划分为多个 Warp（`ceil(block_size / 32)` 个 Warp）
- Warp 中的所有线程在同一时刻执行**相同的指令**（SIMT 模型）
- **Warp Divergence：** 当 Warp 中的线程走不同的分支时，路径被串行化执行

```
Warp 0:  Thread 0-31   ← 同时执行相同指令
Warp 1:  Thread 32-63
...
```

### Warp Divergence 示例

```cuda
// BAD: 同一个 Warp 中的线程进入不同分支
if (threadIdx.x < 16) {
    // Warp 0 的前 16 个线程执行这条路径
    // 后 16 个线程被阻塞
} else {
    // Warp 0 的后 16 个线程执行这条路径
    // 前 16 个线程被阻塞
}

// GOOD: 分支以 Warp 粒度对齐
if (threadIdx.x < 32) {  // 整个 Warp 走同一条路径
    // ...
}
if (threadIdx.x >= 32) { // 另一个完整的 Warp
    // ...
}
```

## Occupancy

**Occupancy** 是衡量 SM 利用率的核心指标：

```
Occupancy = 活跃 Warp 数 / 最大 Warp 数
```

- **最大 Warp 数**：由 GPU 架构决定（例如 H100 SM 最大 64 Warps）
- **活跃 Warp 数**：受限于 SM 资源（寄存器、共享内存、Block 上限）

### Occupancy 计算

**Step 1：确定 Block 所需的 Warp 数**

```
Warps_per_Block = ceil(Block_Size / Warp_Size)
                = ceil(Block_Size / 32)
```

**Step 2：确定资源限制**

每个线程消耗的资源：
- 寄存器数量（由编译器分配，可通过 `--maxrregcount` 限制）
- 没有共享内存使用时不消耗共享内存

每个 Block 消耗的资源：
- 共享内存（静态 + 动态分配）
- 线程数

**Step 3：计算每个资源的 Block 上限**

```
// 受寄存器限制
Blocks_by_Regs = SM_Registers / (regs_per_thread * threads_per_block)

// 受共享内存限制
Blocks_by_SharedMem = SM_Shared_Mem / (shared_mem_per_block)

// 受最大线程数限制
Blocks_by_Threads = SM_Max_Threads / block_size

// 受最大 Block 数限制
Blocks_by_MaxBlocks = SM_Max_Blocks

// 实际同时运行的 Block 数 = 以上四个的最小值
Active_Blocks = min(Blocks_by_Regs, Blocks_by_SharedMem, 
                    Blocks_by_Threads, Blocks_by_MaxBlocks)
```

**Step 4：计算活跃 Warp 和 Occupancy**

```
Active_Warps = Active_Blocks * Warps_per_Block
Occupancy = Active_Warps / SM_Max_Warps
```

### 示例：32 寄存器/线程，Block Size 256

假设 SM 配置（类似 V100 / A100）：

| 资源 | 值 |
|------|-----|
| SM 寄存器数 | 65536 |
| SM 共享内存 | 96 KB (98304 bytes) |
| SM 最大线程数 | 2048 |
| SM 最大 Warp 数 | 64 |
| SM 最大 Block 数 | 32 |

计算：

```
Warps_per_Block = ceil(256 / 32) = 8

// 寄存器限制
Blocks_by_Regs = 65536 / (32 * 256) = 65536 / 8192 = 8

// 假设没有共享内存
Blocks_by_SharedMem = 98304 / 0 = 无穷大

// 线程数限制
Blocks_by_Threads = 2048 / 256 = 8

// Block 数限制
Blocks_by_MaxBlocks = 32

Active_Blocks = min(8, ∞, 8, 32) = 8
Active_Warps = 8 * 8 = 64
Occupancy = 64 / 64 = 100%
```

**如果将每线程寄存器增加到 64：**

```
Blocks_by_Regs = 65536 / (64 * 256) = 65536 / 16384 = 4
Active_Blocks = min(4, ∞, 8, 32) = 4
Active_Warps = 4 * 8 = 32
Occupancy = 32 / 64 = 50%
```

寄存器使用是影响 Occupancy 的关键因素。编译器会尝试分配更多寄存器来减少 Global Memory 访问，但这会降低 Occupancy。这是一个典型的 **trade-off**。

## 理解 Block 调度的影响

### 高 Occupancy ≠ 高性能

高 Occupancy 意味着 SM 有更多的 Warp 可供切换，有助于：
- **隐藏内存延迟**：当一个 Warp 等待内存访问时，SM 可以切换到其他 Warp
- **提高吞吐量**：更多 Warp 意味着更多的并行指令流

但过高的寄存器压力可能迫使编译器将数据 spill 到 Local Memory（实际上在 Global Memory 中），反而降低性能。

**经验法则：**
- 计算密集型 Kernel → 中等 Occupancy（约 50%）通常足够
- 内存密集型 Kernel → 高 Occupancy（> 75%）有助于隐藏延迟

## 总结

| 概念 | 要点 |
|------|------|
| Grid → Block → Thread | Block 是独立调度单元，Block 内线程可协作 |
| Block → SM | 一个 Block 只能在一个 SM 上，一个 SM 可有多 Block |
| Warp | 32 线程一组，SIMT 执行 |
| Occupancy | 活跃 Warp / 最大 Warp，受寄存器和共享内存限制 |
| 调度隐藏延迟 | SM 通过 Warp 切换隐藏内存延迟 |

## 参考文献

- Kirk, David B., and Wen-mei W. Hwu. *Programming Massively Parallel Processors: A Hands-on Approach*. 3rd ed., Morgan Kaufmann, 2016. (Chapter 3: CUDA Execution Model)
- NVIDIA. *CUDA C++ Programming Guide*. "Chapter 4: Hardware Implementation." https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#hardware-implementation
- NVIDIA. *CUDA Best Practices Guide*. "Chapter 9: Execution Configuration Optimizations." https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#execution-configuration-optimizations
- NVIDIA. *CUDA Occupancy Calculator*. https://docs.nvidia.com/cuda/cuda-occupancy-calculator/index.html
