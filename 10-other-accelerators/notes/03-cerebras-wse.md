# 03 — Cerebras Wafer-Scale Engine (WSE)

> Cerebras Systems 的设计理念极为大胆：**不做芯片切割，而是直接把整个晶圆做成一个芯片**。这个"Wafer-Scale Engine"（WSE）是迄今为止面积最大的半导体芯片，专为深度学习训练设计。

---

## 1. 为什么需要 Wafer-Scale？

### 传统方案的痛点

训练大模型时，GPU 集群面临的核心问题：

```
GPU 集群的瓶颈:
1. 显存容量限制：单个 GPU 的 HBM 容量有限（~80GB H100）
2. 显存带宽限制：HBM 带宽虽高但仍是瓶颈
3. 通信开销：All-reduce 等集合通信随节点数增加而恶化
4. 能耗分布：大量功耗花在片间通信和数据搬运上
```

Cerebras 的思路：**把整个模型放在一个芯片上，彻底消除片间通信**。

### Wafer-Scale 的工程挑战

为什么之前没有人做？

| 挑战 | 说明 | Cerebras 的解决方案 |
|------|------|-------------------|
| 良率 | 晶圆上的制造缺陷不可避免 | 冗余设计 + 缺陷容忍路由 |
| 散热 | 整片晶圆功耗~15kW，远超传统散热方案 | 定制水冷系统，直接接触晶圆背面 |
| 封装 | 标准封装无法容纳晶圆级芯片 | 特殊的晶圆级封装 + 74 个连接的电源模块 |
| 互联 | 晶圆尺度上的信号传输延迟大 | 低延迟的晶圆级互联网络 |

---

## 2. WSE-2 架构

Cerebras 于 2021 年发布的第二代 Wafer-Scale Engine (WSE-2) 规格：

| 规格 | WSE-2 |
|------|-------|
| 制造工艺 | TSMC 7nm |
| 芯片面积 | 46,225 mm²（整片晶圆） |
| 晶体管数量 | 2.6 万亿 |
| 核心数量 | 850,000+ |
| 片上 SRAM | 40 GB |
| 片上带宽 | 20 PB/s |
| 核心互联带宽 | 220 PB/s |
| 功耗 | ~15 kW (TDP) |
| Fabric 尺寸 | 7nm, 分布式 SRAM |

作为对比：

| 对比项 | WSE-2 | NVIDIA A100 (×56) |
|--------|-------|-------------------|
| 芯片面积 | 46,225 mm² | 826 mm² × 56 = 46,256 mm² |
| 总 SRAM | 40 GB | 0 (只靠 HBM) |
| 片内带宽 | 20 PB/s | 12.8 TB/s (NVLink) |

一片 WSE-2 的处理能力约等于 56 片 A100 的总芯片面积，但**完全消除了片间通信**。

---

## 3. Cerebras 核心架构

### 3.1 核心（Core）

每个核心是一个专为稀疏线性代数优化的计算单元：

```
每个 Core:
├── 可编程 ALU
│   ├── 浮点运算 (FP16, FP32)
│   ├── 整数运算
│   └── 自定义激活函数
├── 本地 SRAM (48 KB)
├── 数据加载/存储单元
├── 通信接口
└── 冗余逻辑（良率提升）
```

### 3.2 晶圆级互联（Wafer-Scale Fabric）

核心通过 2D 网格互联，每个核心连接到 4 个邻居。关键在于：

```
Fabric 特性:
- 低延迟：邻居间通信延迟 < 1 ns
- 高带宽：每个连接 100+ Gbps
- 冗余路由：绕过缺陷核心，确保良率
- 支持单播、组播、广播
```

### 3.3 缺陷容忍

制造缺陷不可避免（每片晶圆可能有数百个缺陷）：

```
制造 → 测试 → 标记缺陷核心 → 配置互联绕过缺陷 → 正常使用

缺陷核心的邻居自动重路由，使用备用接口绕过
```

这样可以将原本可能产生数万坏点的整片晶圆变成可用芯片。

---

## 4. CS-2 系统

基于 WSE-2 的 Cerebras CS-2 系统：

| 组件 | 规格 |
|------|------|
| WSE-2 | 1 片（850K cores, 40GB SRAM） |
| AI 算力 | > 400 TFLOPS (Rmax) |
| 内存 | 40 GB 片内 SRAM（无需 HBM） |
| 互联 | 1.2 Tbps 片外带宽连接到主机 |
| 主机 | 标准 x86 服务器 |
| 散热 | 定制水冷，液冷板直接接触晶圆 |
| 软件 | Cerebras Software Platform (CSoft) |

### 无需 HBM

WSE-2 有 40GB 片上 SRAM，足以容纳大多数模型：

```
GPT-3 175B: 350GB (BF16) × ZeRO-1 = 350GB  → 仍然超出单颗 WSE-2
BERT-Large: 1.3GB                                      → 完全放入
GPT-2 XL: 6.7GB                                        → 完全放入
ResNet-152: 500MB                                      → 完全放入
```

对于 GPT-3 级别的模型，Cerebras 需要将模型切分到多个 CS-2 系统上。

---

## 5. 编程模型

Cerebras 使用 CSoft（基于 TensorFlow/PyTorch）的编译器自动将模型映射到 WSE：

```
PyTorch 模型 → CSoft Compiler → 核心映射 + 数据流调度 → 配置位流

用户不需要感知底层 850K 核心的存在。
```

关键优化：
1. **数据并行**：在多个核心上复制模型，每个核心处理不同批次数据
2. **流水线并行**：模型不同层在不同核心上
3. **稀疏计算**：利用 WSE 的细粒度核心处理稀疏层

---

## 6. 性能与定位

### 优势

- **避免分布式训练复杂度**：单芯片即可训练大模型
- **超高的片上带宽**：20 PB/s 是任何片外方案无法比拟的
- **高效的稀疏处理**：细粒度核心适合 ReLU 激活带来的稀疏性
- **确定性的调试**：无需处理分布式训练的异步性和一致性

### 劣势

- **单芯片算力上限**：400 TFLOPS 远低于大型 GPU 集群（上万 A100 可达 EFLOPS）
- **成本极高**：定制晶圆、封装、散热的成本难以摊薄
- **并非所有模型都能放入**：超大模型仍需多 CS-2 集群
- **软件生态**：远不如 CUDA 成熟

---

## 参考文献

1. Cerebras Systems. (2021). "Cerebras Wafer-Scale Engine: The Largest Chip Ever Built." *Whitepaper*.
2. Lie, S. (2021). "Wafer-Scale Deep Learning." *Hot Chips 33*.
3. Cerebras Systems. (2021). "Cerebras CS-2 System Architecture." *Whitepaper*.
4. Gianchandani, S. (2022). "Cerebras Wafer-Scale Technology." *IEEE Micro*, 42(3).
5. Willsey, M. (2022). "Training Large AI Models on a Single Wafer-Scale Chip." *MLSys 2022*.
6. Cerebras Systems. (2022). "Andromeda: A Supercomputer Powered by Cerebras CS-2 Systems." *Press Release*.
