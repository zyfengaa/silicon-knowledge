# 07 — 近存计算与存内计算 (PIM)

> 在传统 Von Neumann 架构中，数据需要在处理器和内存之间频繁搬运。随着算力的提升，**数据搬运的能耗和延迟**已成为系统性能的主要瓶颈。近存计算（Near-Memory Computing）和存内计算（Processing-In-Memory, PIM）试图从根本上解决这个问题。

---

## 1. Von Neumann 瓶颈

### 1.1 能耗墙

数据移动消耗的能量远高于计算本身：

| 操作 | 能耗 (相对值) | 能耗 (pJ, 45nm) |
|------|-------------|-----------------|
| 32-bit 整数加法 | 1× | 0.9 pJ |
| 32-bit 浮点乘法 | 4× | 3.2 pJ |
| 读 32-bit 寄存器文件 | 2× | 1.7 pJ |
| 读 32-bit SRAM (8KB) | 10× | 8.2 pJ |
| 读 32-bit SRAM (32KB) | 20× | ~15 pJ |
| 读 32-bit DRAM (片外) | 200× | ~180 pJ |

**核心发现**：从 DRAM 读取一个 32-bit 数据的能耗，大约是加法运算的 200 倍。

### 1.2 性能墙

```
Von Neumann 瓶颈:
CPU/GPU 计算    ← 等待 →   DRAM 提供数据
       ↑                        ↑
    ~10 TFLOPS              ~1 TB/s 带宽
       ↑                        ↑
   需求 >10x 数据            数据无法及时供给

结果: 大多数程序是 memory-bound，而非 compute-bound。
```

### 1.3 解决思路

```
传统方案:
- 更宽的 DRAM 接口 (HBM 1024-bit)
- 更大的 cache (数十 MB)
- 多线程隐藏延迟 (GPU warp)
- 预取 (HW prefetcher)

这些都是在"维持 Von Neumann 架构"前提下的优化。
近存/存内计算: 直接改变架构, 把计算放到数据所在的位置。
```

---

## 2. 近存计算 (Near-Memory Computing)

### 2.1 概念

在逻辑上靠近 DRAM 的位置添加计算能力（通常在内存的**逻辑层**或**缓冲区**中）：

```
传统:  CPU ↔ Memory Bus ↔ DRAM  (距离远, 能耗高)
近存:  CPU ↔ Memory Bus ↔ DRAM + 逻辑层 (计算单元)
                           ↑
                      在内存芯片上集成简单计算逻辑
```

### 2.2 技术路径

| 级别 | 位置 | 延迟改善 | 集成度 |
|------|------|---------|-------|
| DIMM 级 | 内存条上的 FPGA / ASIC | 中等 | 低 |
| 3D 堆叠 | 逻辑层位于 HBM 基底 | 好 | 中 |
| Bank 级 | 每 bank 加 ALU | 很好 | 高 |

### 2.3 Samsung HBM-PIM

Samsung 的 HBM-PIM（Processing-In-Memory）是目前最成熟的 PIM 产品之一：

```
HBM-PIM 架构:
┌─────────────────────────────────────┐
│   DRAM Core Layer (多个)              │
│   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │
│   │Bank0│ │Bank1│ │Bank2│ │Bank3│ │
│   │+PCU │ │+PCU │ │+PCU │ │+PCU │ │
│   └─────┘ └─────┘ └─────┘ └─────┘ │
└─────────────────────────────────────┘
↓ TSV / μbump
┌─────────────────────────────────────┐
│   Base Logic Layer                   │
│   HBM 控制器 + 逻辑运算               │
│   (传统 HBM 无此层)                   │
└─────────────────────────────────────┘
```

PCU (Programmable Computing Unit) 在每个 bank 中集成：

```
每个 PCU:
- 8-bit ALU（定点运算）
- 本地寄存器
- 可以直接访问 bank 的行缓冲
```

性能提升：

| 指标 | 传统 HBM | HBM-PIM | 提升 |
|------|---------|---------|------|
| 内存带宽利用率 | 10-30% | 70-90% | 3-4× |
| 每瓦性能 (memory-bound ops) | 1× | ~2.5× | 2.5× |
| 能耗节省 | — | — | ~60% |

典型受益操作：

```
Element-wise add:   A[i] + B[i]  → 在 bank 内完成, 不出 chip
ReLU:               max(A[i], 0) → 在 bank 内完成
GEMV:               A × x        → 部分结果在 bank 内累加
```

---

## 3. UPMEM

法国创业公司 UPMEM 将完整的处理器核心集成到 DRAM 芯片中：

```
UPMEM DRAM:
┌─────────────────────────────┐
│  DRAM Array (64 MB)          │
│  ┌─────┐ ┌─────┐ ┌─────┐   │
│  │Bank │ │Bank │ │Bank │...│
│  └──┬──┘ └──┬──┘ └──┬──┘   │
│     │       │       │       │
│  ┌──┴──┐ ┌──┴──┐ ┌──┴──┐   │
│  │DPU  │ │DPU  │ │DPU  │...│   ← 每个 Bank 配一个 DPU
│  │32MB │ │32MB │ │32MB │   │
│  └─────┘ └─────┘ └─────┘   │
└─────────────────────────────┘

DPU (DRAM Processing Unit):
- 32-bit RISC 处理器
- ~400 MHz
- 8 硬件线程 (隐藏 DRAM 延迟)
- 24 条指令 ISA
- 本地指令存储器
- 可直接访问相连 DRAM bank
```

对比 HBM-PIM：

| 特性 | Samsung HBM-PIM | UPMEM |
|------|----------------|-------|
| 处理单元 | 简单 8-bit ALU | 完整 32-bit RISC |
| 灵活性 | 有限（特定运算） | 高（可编程） |
| 开发方式 | 硬件算子 | C 语言编程 |
| 适用场景 | 加速特定 memory-bound 核 | 数据密集型应用 |
| 每芯片 DPU 数 | 视 bank 数而定 | 256 / 芯片 |
| 发布时间 | 2021 | 2019 |

---

## 4. 计算在内存中 (Processing Using Memory)

除了 PIM，还有一类更激进的方法——**直接利用内存阵列的物理特性进行计算**：

### 4.1 RowClone

利用 DRAM 行复制操作——将一个行的内容复制到另一个行：

```
DRAM Activate (打开行 A → 行缓冲)
DRAM Activate (打开行 B → 行缓冲 + 写回)
→ 相当于在内存中完成了 memcpy

利用 DRAM 的电荷共享机制实现批量数据复制
```

### 4.2 模拟存内计算 (Analog IMC)

利用非易失性存储器（如 RRAM, PCM, NOR Flash）阵列的特性做矩阵乘法：

```
Crossbar Array:
  ┌───┬───┬───┐
  │ W11 W12 W13 │  ← 权重存储为器件的电导值
  │ W21 W22 W23 │
  │ W31 W32 W33 │
  └───┴───┴───┘
   ↓   ↓   ↓
 输入 V1 V2 V3 (电压)

输出: I_i = Σ V_j × G_ij  (基尔霍夫电流定律)

→ 在模拟域完成向量-矩阵乘法, O(1) 时间复杂度！
```

代表企业：**Mythic**（使用 NOR Flash 阵列做 analog AI 推理）。

---

## 5. 挑战

PIM 技术面临的主要挑战：

| 挑战 | 说明 |
|------|------|
| **计算能力有限** | DRAM 工艺不适合高性能计算，晶体管驱动能力差 |
| **散热** | DRAM 中集成计算单元增加功耗，散热困难 |
| **地址映射** | 哪些数据放在"有计算能力"的 bank 上？ |
| **编程模型** | 需要新的编程模型来利用 PIM 能力 |
| **兼容性** | 需要与现有系统兼容，集成难度大 |
| **带宽利用率** | 并非所有程序都能受益（只有 memory-bound 程序） |

---

## 6. 总结与展望

```
Von Neumann 瓶颈 → 近存/存内计算

趋势:
- 3D 堆叠技术 (HBM) 使逻辑层和 DRAM 层的集成成为可能
- 随着数据量增大，PIM 的价值越来越明显
- 初期：简单 ALU 加速特定操作 (HBM-PIM)
- 中期：可编程核心做数据预处理 (UPMEM)
- 远期：大規模存算一体，彻底颠覆 Von Neumann 架构
```

---

## 参考文献

1. Mutlu, O. (2021). "Processing-in-Memory: A Workload-Driven Perspective." *IBM Research*.
2. Lee, S., et al. (2021). "A 1.2V 8.4Gb/s HBM-PIM with 2.5x System Efficiency Improvement." *ISSCC 2021*.
3. Kwon, Y., et al. (2021). "A 20nm 6GB HBM-PIM with Programmable ALUs." *ISCA 2021*.
4. Devaux, F. (2019). "The True Processing-in-Memory Accelerator." *Hot Chips 31*.
5. Seshadri, V., et al. (2013). "RowClone: Fast and Efficient In-DRAM Copy and Initialization." *MICRO 2013*.
6. Horowitz, M. (2014). "Computing's Energy Problem (and What We Can Do About It)." *ISSCC 2014*.
7. Mutlu, O., et al. (2020). "A Modern Primer on Processing in Memory." *arXiv:2012.03112*.
