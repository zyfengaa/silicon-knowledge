# 05 — Graphcore IPU (Intelligence Processing Unit)

> Graphcore 的 IPU（Intelligence Processing Unit）采用 **MIMD（Multiple Instruction, Multiple Data）** 架构——将大量独立处理器核通过高速互联网络连接，每个核有自己的本地存储和独立的指令流。配合 Poplar 编译器，IPU 可以高效地执行机器学习计算图。

---

## 1. 设计理念

### CPU/GPU 的问题

```
CPU: 适合串行控制逻辑，但并行度有限
GPU: 适合 SIMT 大规模并行，但控制流效率低
      - 同一个 warp 内的线程必须执行相同的指令
      - 条件分支导致部分线程停等
      - 大量线程共享有限寄存器和 cache
```

### IPU 的方案：MIMD + 分布式存储

每个 IPU 核心可以独立执行不同的指令——这适合机器学习中不同层的异构计算需求：

```
Conv Layer:  core 1-100 → 卷积运算指令
Pooling:     core 101   → 池化运算指令
FC Layer:    core 102-200 → 全连接运算指令
Softmax:     core 201   → softmax 指令
```

所有核心并行执行，互不阻塞。

---

## 2. IPU 架构

### 2.1 GC200 IPU (第二代)

| 规格 | GC200 (MK2) |
|------|-------------|
| 制造工艺 | TSMC 7nm |
| 处理器核心数 | 1,472 |
| 每核心线程槽 | 6 (可同时驻留 6 个线程) |
| 每核心 SRAM | 916 KB |
| 总片上 SRAM | 900 MB |
| 峰值 FP16 TFLOPS | 250 (稀疏) / 125 (稠密) |
| 互联带宽 | 8 TB/s (片内) |
| 片间互联 | 320 Gbps / 芯片 (IPU-Link) |
| TDP | ~185W |

### 2.2 处理核心（Tile）

每个 tile 是一个可以独立执行指令的处理单元：

```
每个 Tile:
├── 处理器流水线
│   ├── 取指/译码
│   ├── 执行单元
│   │   ├── 浮点运算（FP16, FP32）
│   │   ├── 整数运算
│   │   └── 特殊函数（激活函数等）
│   └── 写回
├── 本地 SRAM (916 KB)
│   └── 存储指令和数据
├── 6 线程上下文
│   └── 硬件多线程，由编译器调度
├── 通信接口
│   └── 与相邻 tile 交换数据
└── 同步逻辑
    └── BSP 同步支持
```

### 2.3 互联：IPU-Exchange

Tile 以 2D 网格方式互联，形成高效的片内网络：

```
Tile 网络:
- 每个 tile 连接到 6 个邻居（六边形布局）
- 支持单播、组播、全广播
- 所有 tile 之间的通信延迟在同一个数量级

对比 GPU:
- GPU 的 SM/L1 → L2 → HBM 层次化带宽递减
- IPU 所有 tile 的存储访问延迟相对均匀
```

---

## 3. BSP 执行模型

IPU 采用 **Bulk Synchronous Parallel (BSP)** 执行模型，计算被分为三个阶段的循环：

```
BSP 执行:
┌─────────────────────────────────────────────────┐
│  阶段 1: Compute                                  │
│  所有 tile 并发执行本地计算（从本地 SRAM 读取数据）      │
│                                                   │
│  阶段 2: Exchange                                  │
│  Tile 之间通过互联交换数据                          │
│  每个 tile 发送/接收固定大小的消息                     │
│                                                   │
│  阶段 3: Sync                                      │
│  所有 tile 到达同步屏障                              │
│  确认所有交换完成                                   │
└─────────────────────────────────────────────────┘
```

### BSP 的优点

1. **消除死锁**：通信在严格界限的阶段中进行
2. **编译器可知**：计算和通信的时间都可以静态分析
3. **全局同步**：简化了分布式算法的正确性

### BSP 的代价

1. **同步等待时间**：最快和最慢的 tile 之间的差距会导致空闲
2. **负载均衡要求高**：所有阶段的计算量需要近似均衡

---

## 4. Poplar 编译器

Poplar 是 IPU 的核心软件——它将 ML 计算图映射到 tile 数组上：

```
输入: 计算图 (TensorFlow / PyTorch)
  ↓
计算图分析: 识别算子、张量形状、数据类型
  ↓
图切分: 将计算图分配到 tile 上
  │
  ├── 如何切分算子 → 流水线分
  │   └── 大矩阵乘 → 切分到多个 tile 上
  │
  ├── 如何分配张量 → 存储规划
  │   └── 中间结果存在哪个 tile 的 SRAM 上
  │
  └── 如何安排通信 → 交换调度
      └── 每个 BSP 阶段的数据交换计划
  ↓
代码生成: 为每个 tile 生成独立的二进制代码
  ↓
配置位流 → 加载到 IPU
```

### 自动流水线并行

Poplar 可以将整个模型以流水线方式跨 tile 部署：

```
Layer1 (tile 0-49) → Layer2 (tile 50-99) → Layer3 (tile 100-149)
       ↑ 数据流               ↑                   ↓
       └──────── 同步通信 (Exchange) ──────────────┘
```

每个 tile 在其本地 SRAM 中存储该层所需的参数和中间结果。

---

## 5. IPU vs GPU

| 维度 | IPU GC200 | NVIDIA H100 |
|------|-----------|-------------|
| 处理器数量 | 1,472 独立核心 | 132 SM (16896 CUDA 核心) |
| 存储模型 | 分布式 SRAM (~900MB) | 共享 HBM + cache 层次 |
| 并行模式 | MIMD (各核独立执行) | SIMT (warp 内锁步) |
| 编程模型 | BSP (显式计算/通信/同步) | CUDA (隐式线程调度) |
| 编译器角色 | 核心 - 负责所有调度决策 | 重要但硬件也做调度 |
| 控制流效率 | 高 (每个核独立) | 低 (warp 内分支分歧) |
| 矩阵乘法 (大) | 好 | 极好 (Tensor Core) |
| 稀疏计算 | 好 (每个核独立处理) | 差 (warp 利用不足) |

---

## 6. 适用场景

### 优势场景

- **模型推理**（特别是小批次）：每个 tile 独立处理，无需等待其他 tile
- **稀疏模型**：各 tile 独立处理稀疏激活
- **图神经网路（GNNs）**：GNN 的图结构天然适合 tile 上的分布式处理
- **NLP 推理**：BSP 模型适合 Transformer 的 attention 计算

### 不适用场景

- **大规模稠密矩阵乘**：GPU 的 Tensor Core 仍占优势
- **动态控制流**：BSP 模型对动态图支持有限
- **需要大量 DRAM 的模型**：IPU 全部使用 SRAM，总容量小于 HBM

---

## 参考文献

1. Graphcore. (2020). "Graphcore IPU Architecture: GC200." *Whitepaper*.
2. Jia, Z., et al. (2019). "Graphcore IPU Architecture and Performance Analysis for Machine Learning." *Hot Chips 31*.
3. Graphcore. (2021). "Poplar SDK Programming Guide." *Graphcore Documentation*.
4. Valiant, L. G. (1990). "A Bridging Model for Parallel Computation." *Communications of the ACM*, 33(8).
5. Graphcore. (2022). "Benchmarking the Graphcore IPU." *Technical Report*.
6. Knowles, S. (2022). "Graphcore's Second-Generation IPU." *IEEE Micro*, 42(3).
