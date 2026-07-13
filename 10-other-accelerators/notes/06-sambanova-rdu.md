# 06 — SambaNova Reconfigurable Dataflow Unit (RDU)

> SambaNova 的 RDU（Reconfigurable Dataflow Unit）代表了一条不同于 GPU 和 FPGA 的"第三条路"：**编译器在运行时配置硬件的计算和数据流拓扑**。这种方法称为"软件定义的硬件"——硬件没有固定的功能，它的功能由编译器在每个任务开始时决定。

---

## 1. 核心概念：可重构数据流

### 传统方案的局限性

```
GPU:  硬件固定（SM/Tensor Core），软件通过指令序列编程
      问题：无法为不规则的稀疏计算优化数据流
FPGA: 硬件可重构，但编程模型是 RTL
      问题：编译时间长（小时级），不适合动态变化

SambaNova 的答案: 编译器快速重配置硬件数据通路
```

### 数据流架构

在 RDU 中，计算不是由一条条指令驱动的，而是由**数据在计算单元之间的流动**驱动的：

```
传统:  指令 → 取指 → 译码 → 执行 → 写回
         ↓
       每个周期从指令存储器读取指令

RDU:   数据 → PCE0 → PCE1 → PCE2 → PCE3 → 输出
         ↓
       编译器配置每个 PCE 的功能和连接
       数据在配置好的通路中流动，不需要指令
```

---

## 2. RDU 架构

### 2.1 硬件组成

RDU 的核心是大量可编程计算引擎（Pattern Compute Engines，PCE）：

```
RDU 芯片:
├── 多个 PCE 集群
│   ├── PCE (Pattern Compute Engine)
│   │   ├── 可重构 ALU 阵列
│   │   ├── 本地存储
│   │   └── 数据流控制逻辑
│   └── ...
├── 数据存储
│   ├── 分布式 SRAM
│   └── HBM 接口
├── 片上互联
│   └── 编译器可配置的数据通路
└── 主机接口
    └── PCIe
```

### 2.2 与 FPGA 的区别

| 特性 | RDU | FPGA |
|------|-----|------|
| 可重构粒度 | 粗粒度（PCE 级） | 细粒度（LUT 级） |
| 重构速度 | 毫秒级 | 秒到分钟级 |
| 编程方式 | 编译器（类 Python/ML 框架） | HDL / HLS |
| 最小编程单元 | 数据流模式 | 逻辑门 |
| 编译器角色 | 运行时配置硬件拓扑 | 生成配置位流 |

RDU 在 FPGA 的灵活性和 GPU 的易用性之间取得了平衡。

---

## 3. SN10 RDU (第二代)

| 规格 | SN10 RDU |
|------|----------|
| 制造工艺 | TSMC 7nm |
| PCE 数量 | 中等规模（确切数字未公开） |
| 片上存储 | 大容量分布式 SRAM |
| 峰值性能 | > 1 PetaOps (稀疏 INT8) |
| 外部存储 | HBM2 / HBM2E |
| 互联 | 片间高速链接 |
| 软件栈 | SambaFlow |

---

## 4. 编程模型：SambaFlow

SambaNova 的软件栈 SambaFlow 使开发者可以用熟悉的 ML 框架编程，编译器自动映射到 RDU：

```
PyTorch 模型 → SambaFlow 编译器
                  ↓
1. 计算图分析
2. 数据流模式提取
3. 资源分配（PCE 映射）
4. 数据通路配置
5. 存储规划
                  ↓
配置位流 → 加载到 RDU
```

### 数据流优化

编译器可以进行传统 GPU 无法做到的优化：

```python
# PyTorch 代码
x = torch.nn.Linear(4096, 4096)(x)
x = torch.nn.GELU(x)
x = torch.nn.Linear(4096, 4096)(x)

# GPU 执行:
# MatMul → AddBias → GELU → MatMul → AddBias
# 每一步需要回写 HBM，再读入

# RDU 执行 (编译器自动实现):
# MatMul → AddBias → GELU → MatMul → AddBias
# 在 PCE 流水线中连续完成，不需要回写 DRAM
```

这种**算子融合**在 GPU 上需要手动编写融合 kernel，而 RDU 编译器自动完成。

---

## 5. RDU vs GPU: 关键差异

### 5.1 计算图映射

```
GPU: 
模型层 1 → 启动 CUDA kernel A → 回写 HBM
模型层 2 → 启动 CUDA kernel B → 回写 HBM
模型层 3 → 启动 CUDA kernel C → 回写 HBM

每层之间的数据通过 HBM 传递，有显著的访存开销

RDU:
模型层 1, 2, 3 → 编译器创建连续数据流
                  PCE A → PCE B → PCE C
                  数据在 PCE 间直接流动，不经过外部存储
```

### 5.2 稀疏性处理

RDU 的粗粒度可重构性使其可以动态调整数据通路以匹配稀疏模式：

```
稀疏矩阵 × 稠密向量:
GPU: 转换为稠密矩阵 → 计算 → 浪费大量算力在零值上
RDU: 编译器构建稀疏数据通路 → 只计算非零元素
```

### 5.3 编译器优化空间

RDU 的编译器可以进行全局优化：

| 优化 | GPU | RDU |
|------|-----|-----|
| 算子融合 | 需手动编写 | 自动 |
| 数据布局优化 | 需手动指定 | 自动 |
| 内存规划 | 运行时管理 | 编译时确定 |
| 流水线深度 | 固定 | 编译器可调 |
| 稀疏优化 | 困难 | 数据流支持 |

---

## 6. 适用场景

### 最佳场景

- **大语言模型推理**：长序列、大 batch 的数据流模式
- **稀疏 ML 模型**：需要处理不规则的激活模式
- **多模型推理管線**：编译器可以跨模型做全局优化
- **需要灵活性的场景**：模型更新频率高，需要快速硬件适配

### 挑战

- **软件生态**：远不如 CUDA 成熟
- **峰值算力**：在稠密矩阵乘上可能不及 GPU Tensor Core
- **训练扩展性**：在多节点训练中的表现需要验证
- **编译器依赖**：优化质量完全取决于编译器

---

## 参考文献

1. SambaNova Systems. (2021). "SambaNova Reconfigurable Dataflow Unit." *Whitepaper*.
2. SambaNova Systems. (2022). "Software-Defined Hardware for AI." *Hot Chips 34*.
3. Prabhakar, R., et al. (2020). "SambaNova SN10 RDU: A Reconfigurable Dataflow Architecture for AI." *IEEE Micro*, 41(5).
4. Olukotun, K. (2022). "Dataflow Architectures for Machine Learning." *ISCA 2022 Keynote*.
5. SambaNova Systems. (2022). "SambaFlow: A Compiler-Driven Software Stack for the RDU." *Technical Report*.
