# 综合实践项目

> 学完理论知识之后，动手做项目来巩固和检验。

---

每个项目都要求综合运用多个模块的知识。建议按照编号顺序完成。

| 项目 | 主题 | 综合模块 | 难度 |
|------|------|---------|------|
| 01 | **RISC-V 流水线模拟器** | 模块 02, 03 | ⭐⭐ |
| 02 | **多级缓存模拟器** | 模块 05 | ⭐⭐ |
| 03 | **高性能 Softmax CUDA Kernel** | 模块 06, 07 | ⭐⭐⭐ |
| 04 | **脉动阵列矩阵乘模拟器** | 模块 08 | ⭐⭐ |
| 05 | **模拟 TPU MXU 的矩阵单元** | 模块 08, 09 | ⭐⭐⭐ |
| 06 | **真实程序的 Roofline 分析** | 模块 11 | ⭐⭐ |

---

## 项目 01 — RISC-V 流水线模拟器

用 C++ 或 Python 实现一个支持 5 段流水线的 RISC-V 模拟器。

**要求**：
- 支持 RV32I 核心指令集
- 实现 5 段流水线（IF/ID/EX/MEM/WB）
- 实现数据转发（forwarding）
- 实现简单分支预测（2-bit 饱和计数器）
- 输出每周期各流水级的状态
- 统计总 CPI

**扩展**：增加 load-use 停顿检测、实现更高级的分支预测器。

**参考**：Patterson & Hennessy 第 4 章。

---

## 项目 02 — 多级缓存模拟器

用 C++ 或 Python 模拟 L1 + L2 + L3 三级缓存的行为。

**要求**：
- 每级缓存可独立配置大小、关联度、行大小
- 支持 Write-back + Write-allocate
- 支持 LRU 和随机替换策略
- 读取内存访问 trace 文件并统计各级命中率
- 输出去往 DRAM 的访问次数

**扩展**：实现 MESI 一致性协议。

**参考**：Hennessy & Patterson 第 2 章。

---

## 项目 03 — 高性能 Softmax CUDA Kernel

手写一个高度优化的 Softmax CUDA kernel。

**要求**：
- 实现安全的 online softmax 算法（两趟 reduction）
- 使用 shared memory 减少全局访存
- 使用 warp-level primitive（`__shfl_xor_sync`）
- 与 cuDNN 版本做性能对比
- 用 Nsight Compute 分析 occupancy 和瓶颈

**扩展**：实现 fused attention 中的 softmax + masked 版本。

**参考**：NVIDIA FlashAttention 论文中的 softmax 实现。

---

## 项目 04 — 脉动阵列 GEMM 模拟器

用 Python 实现二维脉动阵列的矩阵乘模拟器。

**要求**：
- 支持 Weight Stationary 和 Output Stationary 两种数据流
- 显示每个 PE 在每拍中的输入和输出值
- 统计总的计算拍数和 PE 利用率
- 对比理论峰值和实际吞吐

**扩展**：增加 input stationary 数据流实现。

**参考**：Kung 1982 脉动阵列论文 + Eyeriss 论文。

---

## 项目 05 — 模拟 TPU MXU 的矩阵乘单元

用 C++ 实现一个类似于 TPU MXU 的脉动阵列矩阵乘单元。

**要求**：
- 支持 BF16 输入、FP32 累加
- 可配置阵列大小（128×128、64×64 等）
- 从 HBM（Python dict 模拟）读取矩阵数据
- 实现指令队列驱动执行

**扩展**：增加 SparseCore 风格的稀疏支持。

**参考**：TPU v1/v2 论文。

---

## 项目 06 — 真实程序的 Roofline 分析

选择 2-3 个有代表性的计算程序，做完整的 Roofline 分析。

**程序建议**：
1. 朴素矩阵乘 vs 优化矩阵乘（OpenBLAS/MKL）
2. 手写 SIMD 向量加法 vs 循环版本
3. 简单的 CNN 推理（可选：CPU vs GPU）

**要求**：
- 用 `perf stat` 收集指令数、缓存 miss 数、浮点操作数
- 计算实际算力（FLOPS）和计算强度（FLOP/Byte）
- 绘制 Roofline 图并标注各程序的位置
- 分析每个程序的瓶颈类型
- 提出优化建议并验证

**扩展**：对比同一程序在 CPU 和 GPU 上的 Roofline。

**参考**：Williams et al. "Roofline" (CACM 2009)。
