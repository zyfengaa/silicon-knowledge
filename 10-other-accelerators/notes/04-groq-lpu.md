# 04 — Groq LPU (Language Processing Unit)

> Groq 的 Language Processing Unit（LPU）采用了一种与传统 CPU/GPU 截然不同的设计哲学：**完全的确定性执行**。没有乱序执行、没有分支预测、没有缓存一致性——所有指令的时序在编译时就已经确定。

---

## 1. 设计哲学

### 传统处理器的"不确定性"

CPU 和 GPU 为了提升平均性能，引入了大量硬件推测机制：

```
现代 CPU 的不确定性来源:
1. 乱序执行：指令发射顺序与程序顺序不同
2. 分支预测：预测错误后需要冲刷流水线
3. 缓存缺失：访存延迟不可预测
4. 缓存一致性：多个核心共享数据的同步开销
5. 中断和上下文切换

结果：同样的程序，每次执行的指令时序不同。
```

### Groq 的确定性架构

Groq 的观点：对于 AI 推理等计算模式固定的任务，不需要这些硬件动态机制。

```
Groq 设计原则:
1. 编译器调度一切 → 硬件不做任何运行时决策
2. 存储是显式管理的 → 不需要 cache 一致性
3. 互联是确定性的 → 数据到达时间已知
4. 每个功能单元的工作在编译时分配 → 硬件只执行
```

---

## 2. LPU 架构

### 2.1 功能单元（Functional Units）

LPU 由多种功能单元组成，通过高带宽互联网络连接：

```
LPU 核心的资源:
├── 向量处理单元 (Vector Unit)
│   ├── SIMD 计算（FP32, BF16, INT8）
│   └── 支持矩阵乘法
├── 张量处理单元 (Tensor Unit)
│   ├── 矩阵乘累加矩阵（类似 NVIDIA Tensor Core）
│   └── 专为 AI 运算优化
├── 内存单元 (Memory Unit)
│   ├── 分布式 SRAM（~200 MB+）
│   └── 显式 DMA 控制
└── 互联交换机（Switch）
    └── 确定性片上网络
```

### 2.2 片上 SRAM

LPU 拥有 200+ MB 的片上 SRAM，分布在所有功能单元中：

```
对比:
LPU:      ~200 MB 片上 SRAM  → 模型参数和中间结果都可存放
GPU:      ~40 MB L2 cache    → 依赖高带宽 HBM

Groq 的权衡: 用更多芯片面积做 SRAM，替换复杂的分支预测/OOO 逻辑
```

### 2.3 确定性互联

互联网络采用 **Systolic Array** 风格的确定性数据流：

```
时间 t0: 数据从 Memory Unit A 出发
时间 t1: 数据经过 Switch 2
时间 t2: 到达 Tensor Unit C
...
时间 tn: 结果写回 Memory Unit D

所有时间在编译时静态已知。
```

---

## 3. 编译器：Groq Compiler

Groq 编译器的角色远重要于传统编译器——它负责**安排每一纳秒的行为**：

```
模型定义 (PyTorch) → Groq Compiler
                    ↓
输入: 计算图 + 张量形状 + 数据类型
                    ↓
输出: 指令序列 + 数据流时间表
                    ↓
      发送到 LPU: 按时间表执行
```

### 编译器的工作

1. **将计算图映射到功能单元**：决定哪些操作在哪些单元上执行
2. **分配片上 SRAM**：为每个张量分配存储位置
3. **安排数据移动的时间表**：确保数据在正确的时间到达正确的单元
4. **流水线调度**：最大化功能单元利用率
5. **生成控制指令**：每个单元按照精确的周期计数执行操作

---

## 4. 执行模型

LPU 的执行与 CPU/GPU 有本质区别：

```
CPU:    指令流 → 硬件动态调度 → 执行
GPU:    指令流 → Warp 调度器 → 执行
LPU:    时间表 → 每个周期所有单元执行预定的操作

不需要:
- 取指和译码（调度已在编译时完成）
- 分支预测（没有条件分支）
- 乱序执行（顺序由编译器决定）
- 缓存一致性（没有 cache）
```

### 数据流执行

```
时间 t0:  所有 Vector Unit 开始计算 Layer1
时间 t1:  所有 Tensor Unit 开始计算 Layer2
            Vector Unit 结果 → Switch → Tensor Unit
时间 t2:  Tensor Unit 结果写回 Memory Unit
...
```

对比 GPU 的 BSP（Bulk Synchronous Parallel）执行，LPU 的数据流是**连续的**——没有全局同步点。

---

## 5. 性能特征

| 特性 | LPU | NVIDIA H100 |
|------|-----|-------------|
| 时序行为 | 完全确定 | 统计（缓存/调度影响） |
| 峰值 FP32 TFLOPS | ~200 | ~67 |
| 推理延迟 | 极低（ns 级确定性） | 较低（μs 级） |
| 存储层次 | 完全显式 SRAM | HBM + cache 层次 |
| 编译器角色 | 核心（调度一切） | 重要（但硬件也做决策） |
| 推理批次 | 小批次效率极高 | 大批次利用 Tensor Core |
| 功耗 | ~185W (LPU) | ~700W (H100) |

### 关键指标：时延一致性

对于推理场景，**P99 延迟**可能比平均延迟更重要：

```
GPU 推理延迟分布:  10μs (avg), 100μs (P99)   ← 缓存缺失+Warp 调度波动
LPU 推理延迟分布:  1μs (avg), 1.01μs (P99)   ← 完全确定性
```

---

## 6. 适用场景

### 最佳场景

- **超低延迟推理**：需要稳定、可预测的推理时间
- **固定计算图**：模型结构不频繁变化
- **批量大小为 1 的推理**：LPU 的小批次效率很高
- **关键任务系统**：确定性行为有助于故障排查和认证

### 不适用场景

- **训练**：不确定性模型需要动态决策（优化器状态、学习率调度等），LPU 的确定性架构不匹配
- **图搜索/动态分支**：需要运行时决策的算法
- **大规模稀疏模型**：稀疏性会破坏确定性的数据流模式
- **非 AI 通用计算**：如数据库系统

---

## 参考文献

1. Groq. (2020). "Groq Architecture Whitepaper." *Groq Inc.*
2. Jouppi, N. P., et al. (2020). "A Domain-Specific Supercomputer for Training Deep Neural Networks." *ISCA 2020*.
3. Abts, D., et al. (2020). "Think Fast: A Tensor Streaming Processor for Accelerating Deep Learning Workloads." *ISCA 2020*.
4. Groq. (2020). "Groq Compiler: Scheduling for Deterministic Execution." *Hot Chips 32*.
5. Abts, D., et al. (2022). "The Groq Software-Defined Hardware Architecture." *IEEE Micro*, 42(3).
