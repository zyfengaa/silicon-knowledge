# 01 — Roofline 模型

> Roofline 模型是性能分析中最经典的"第一性原理"工具。它将程序的性能瓶颈可视化地分为两类——**计算受限**（compute-bound）和**访存受限**（memory-bound）——并用一张图告诉你：对于一个给定的程序，在特定硬件上的性能上限在哪里。

---

## 1. 核心概念

### 1.1 两个轴

Roofline 模型的定义：

| 轴 | 变量 | 含义 | 单位 |
|----|------|------|------|
| X 轴 | 算术强度 (Arithmetic Intensity, AI) | 每字节访存对应的浮点运算次数 | FLOP/Byte |
| Y 轴 | 性能 (Performance) | 实际达到的浮点运算速率 | GFLOPS |

### 1.2 两个天花板

Roofline 图由两条线构成：

```
性能 (GFLOPS)
    ↑
    │  ┌────────────────────── Peak GFLOPS (计算天花板)
    │  │
    │  │                     ↗  Ridge Point
    │  │                    ↗
    │  │                   ↗ Peak BW × AI (内存天花板)
    │  │                  ↗
    │  │                 ↗
    │  ├────────────────→──→──→──→──→  Arithmetic Intensity (FLOP/Byte)
    │  内存受限区域       计算受限区域
```

**计算天花板（Compute Ceiling）**：处理器的峰值计算能力（GFLOPS 峰值）。

**内存天花板（Memory Ceiling）**：由内存带宽和算术强度共同决定的上限。

```
Memory Ceiling = Peak BW × AI

其中：
- Peak BW: 峰值内存带宽 (GB/s)
- AI: 算术强度 (FLOP/Byte)
```

**脊点（Ridge Point）**：两条天花板的交点。

```
Ridge Point AI = Peak GFLOPS / Peak BW (FLOP/Byte)
```

- **左侧（AI < Ridge）**：程序是 **memory-bound**，性能上限由内存带宽决定
- **右侧（AI > Ridge）**：程序是 **compute-bound**，性能上限由峰值算力决定

---

## 2. 数学定义

程序的**实际性能**由 Arithmetic Intensity 所在区域决定：

```
如果 AI > Ridge_Point:
    Achievable GFLOPS = Peak GFLOPS  (compute-bound)
否则:
    Achievable GFLOPS = Peak BW × AI  (memory-bound)
```

或者更严谨地：

```
Achievable GFLOPS = min(Peak GFLOPS, Peak BW × AI)
```

---

## 3. 两个例子

### 3.1 SAXPY (y = a·x + y)

```
SAXPY 每轮迭代:
- 计算: 1 次乘法 + 1 次加法 = 2 FLOP (FP32)
- 访存: 读 x[i] (4B) + 读 y[i] (4B) + 写 y[i] (4B) = 12B

AI = 2 FLOP / 12 Byte = 0.167 FLOP/Byte

假设硬件: 
Peak GFLOPS = 1000 GFLOPS
Peak BW = 200 GB/s
Ridge Point = 1000 / 200 = 5 FLOP/Byte

AI (0.167) < Ridge (5) → memory-bound
Achievable = 200 × 0.167 = 33.4 GFLOPS = Peak GFLOPS 的 3.3%
```

### 3.2 矩阵乘法 (DGEMM, N=1024)

```
DGEMM (C = A × B):
- 计算: 2 × N³ = 2 × 1024³ ≈ 2.15 GFLOPS (FP64)
- 访存:
  - A: N² = 1M 个元素 × 8B = 8MB (如果全部从 DRAM 读)
  - B: N² = 1M 个元素 × 8B = 8MB
  - C: N² = 1M 个元素 × 8B = 8MB (读 + 写)
  
但由于缓存优化，实际上每 FLOP 对应的访存量远小于此。

如果通过分块（tiling）达到 AI ≈ 20 FLOP/Byte:

AI (20) > Ridge (5) → compute-bound
Achievable ≈ Peak GFLOPS (如果有足够的子块重复利用缓存)
```

---

## 4. 如何画 Roofline 图

### 4.1 确定硬件参数

| 参数 | 来源 |
|------|------|
| Peak GFLOPS | 芯片规格 (时钟 × 核心数 × 每周期 FLOP) |
| Peak BW | 内存规格 (频率 × 位宽 × 通道数) |

### 4.2 绘制步骤

```
1. 画 X 轴 (AI, log scale, 0.1 → 100)
2. 画 Y 轴 (GFLOPS, log scale, 1 → peak)
3. 画水平线 y = Peak GFLOPS (计算天花板)
4. 画斜线 y = Peak BW × AI (内存天花板，从左上到右下)
5. 标记 Ridge Point 的 AI 值
6. 在图上标注实际程序 (计算其 AI, 测量其性能)
```

### 4.3 实际使用

获取程序的 Arithmetic Intensity：

```
工具: Intel Advisor (Roofline 分析模块)
     NVIDIA Nsight Compute (GPU Roofline)
     也可以手动计算 (统计 FLOP 和访存字节数)
```

---

## 5. 实际分析案例

### 5.1 Stencil 计算

```
3D Stencil (7-point):
每格子:
- 计算: 7 次加 + 1 次乘 ≈ 8 FLOP
- 访存: 7 个邻居 + 1 个自身 = 8 × 4B (FP32) = 32B
  (实际因为有时间方向，可能更复杂)

AI ≈ 8 / 32 = 0.25 FLOP/Byte → 典型 memory-bound
```

### 5.2 FFT

```
1D FFT (N=1024, FP32):
- 计算: ~5N log₂(N) ≈ 5×1024×10 = 51200 FLOP
- 访存: 数组通过多次 pass 在内存和 cache 间反复移动
  假设 cache 命中率 90%, 外部访存约 10%
  (简化): ~2×N×4B (输入+输出) + pass 间的回写 ≈ ~2×4KB × passes

AI 高度依赖于 cache 利用率和 N 的大小。
小 FFT: 可放入 cache → compute-bound
大 FFT: cache 溢出 → memory-bound
```

### 5.3 不同操作在 Roofline 上的位置

```
AI (FLOP/Byte):  0.1    0.5    1    5    10    50    100
                  │      │     │    │    │     │     │
SAXPY:            ★  (0.17)
Stencil:               ★  (0.25-0.5)
SpMV:                    ★  (0.5-1)
FFT (大):                  ★  (1-3)
DGEMM (优化):                  ★  ★  (10-50)
DGEMM (理论极限):                ★  ★  ★  (~1000)
```

---

## 6. Roofline 的变种

### 6.1 分层 Roofline

考虑不同级别的存储层次：

```
天花板 1: DRAM bandwidth  → 如果 L2/L1 miss
天花板 2: L2 bandwidth   → 如果 L1 miss
天花板 3: L1 bandwidth   → 如果数据在 L1 中
```

实际上只需要画**最慢的（DRAM）天花板**，因为它是全局瓶颈。

### 6.2 可达到的 Roofline

实际软件有各种开销（循环控制、地址计算），有效峰值通常远低于理论峰值。可达到的 Roofline 引入"实际天花板"：

```
Theoretical Peak GFLOPS → (× 实践系数) → Achievable Peak GFLOPS
                                 0.7-0.9 (稠密), 0.1-0.5 (稀疏)
```

### 6.3 能耗 Roofline

将 Y 轴改为**每瓦性能**（GFLOPS/W），可以分析能效瓶颈。

---

## 7. 局限性

1. **简化的内存模型**：使用单一的 DRAM 带宽，忽略缓存层次的影响
2. **忽略指令开销**：假设所有 FLOP 都是"有用的"
3. **忽略内存延迟**：仅考虑带宽，不考虑延迟
4. **忽略并行开销**：不建模多核/多线程的同步和竞争
5. **AI 计算困难**：精确计算程序的 Arithmetic Intensity 本身并不简单

尽管如此，Roofline 仍然是性能分析的最佳**第一性原理工具**——它让你立即知道"程序卡在哪里"，这是优化的起点。

---

## 参考文献

1. Williams, S., Waterman, A., & Patterson, D. (2009). "Roofline: An Insightful Visual Performance Model for Floating-Point Programs and Multicore Architectures." *Communications of the ACM*, 52(4).
2. Lo, Y. J., et al. (2014). "Roofline Model Toolkit: A Practical Tool for Architecture and Program Analysis." *Workshop on Performance Modeling*.
3. Intel. (2022). "Intel Advisor Roofline Analysis." *Intel Advisor User Guide*.
4. NVIDIA. (2022). "Nsight Compute Roofline Analysis." *Nsight Compute Documentation*.
5. Doerfert, J., et al. (2022). "The Roofline Model: A Comprehensive Review." *arXiv:2206.11997*.
6. Hennessy, J. L., & Patterson, D. A. (2019). *Computer Architecture: A Quantitative Approach* (6th ed.). Morgan Kaufmann.
