# 08 — GPU 互联

> 现代高性能计算系统中 GPU 不是孤立的计算单元。CPU-GPU 通信、GPU-GPU 通信的带宽和拓扑直接影响多 GPU 应用的性能。

---

## 1. PCIe 总线

### PCIe 基础知识

PCI Express（PCIe）是 CPU 与 GPU 之间最主要的互连通道。每个 GPU 通过 x16 插槽连接到 CPU 的 PCIe 控制器。

### PCIe 代际带宽

| PCIe 代次 | 编码 | 单通道带宽 (GT/s) | x16 单向带宽 | x16 双向带宽 |
|-----------|------|------------------|-------------|-------------|
| Gen 3 | 128b/130b | 8 | ~16 GB/s | ~32 GB/s |
| Gen 4 | 128b/130b | 16 | ~32 GB/s | ~64 GB/s |
| Gen 5 | 128b/130b | 32 | ~64 GB/s | ~128 GB/s |
| Gen 6 | 128b/130b | 64 | ~128 GB/s | ~256 GB/s |

### CPU-GPU 通信模式

```
CPU ─── PCIe ─── GPU
       |
    DRAM (系统内存)      HBM (GPU 显存)

典型序列：
1. cudaMemcpyHostToDevice: CPU 内存 → PCIe → GPU 显存
2. GPU Kernel 执行
3. cudaMemcpyDeviceToHost: GPU 显存 → PCIe → CPU 内存
```

### PCIe 瓶颈

与 GPU 内部带宽相比，PCIe 的带宽差异巨大：

| GPU | 内部带宽 | PCIe Gen4 x16 | 比值 |
|-----|---------|---------------|------|
| H100 | 3,350 GB/s | 64 GB/s | 52:1 |
| A100 | 2,000 GB/s | 64 GB/s | 31:1 |

**关键结论**：CPU <-> GPU 的数据传输是主要瓶颈之一，设计系统时应尽量减少跨 PCIe 的数据移动。

### Unified Memory（统一内存）

Pascal 及之后架构支持统一内存，允许 CPU 和 GPU 共享虚拟地址空间，由硬件自动管理页面迁移：

```cuda
// 统一内存分配
float *data;
cudaMallocManaged(&data, N * sizeof(float));

// CPU 访问 → 自动页面迁移到系统内存
// GPU 访问 → 自动页面迁移到显存
```

Caveat：频繁的页面错误会导致性能显著下降。统一内存适合访问模式可预测的场景，不适合高性能计算。

---

## 2. NVLink

### NVLink 概述

NVLink 是 NVIDIA 开发的高带宽 GPU-GPU 直连接口。与 PCIe 不同，NVLink 是**点对点**连接，不经过 CPU。

### NVLink 代际演进

| 代次 | 架构 | 每链路单向 | 每链路双向 | 每 GPU 链路数 | 总带宽/GPU |
|------|------|-----------|-----------|--------------|-----------|
| NVLink 1 | Pascal | 20 GB/s | 40 GB/s | 4 | 160 GB/s |
| NVLink 2 | Volta | 25 GB/s | 50 GB/s | 6 | 300 GB/s |
| NVLink 3 | Ampere | 25 GB/s | 50 GB/s | 12 | 600 GB/s |
| NVLink 4 | Hopper | 50 GB/s | 100 GB/s | 18 | 900 GB/s |

### NVLink 拓扑

**NVLink 全互联**（DGX 系统）：

```
DGX H100（8 GPU）NVLink 拓扑：
         ┌─────┐
         │GPU 0│──────┐
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 1│      │
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 2│      │
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 3│      │
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 4│      │
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 5│      │
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 6│      │
         └──┬──┘      │
            │         │
         ┌──▼──┐      │
         │GPU 7│      │
         └──┬──┘      │
            │         │
         ┌──▼─────────▼──┐
         │  NVSwitch ×4  │
         └───────────────┘
```

### NVLink vs PCIe

| 对比维度 | PCIe Gen5 x16 | NVLink 4 (H100) |
|---------|--------------|-----------------|
| 带宽 | 64 GB/s（双向） | 900 GB/s（双向，18 链路） |
| 延迟 | ~5 μs | ~1-2 μs |
| 拓扑 | 树形（CPU为中心） | 全互联（任意 GPU 直接通信） |
| 协议 | 标准 | NVIDIA 专用 |
| 用途 | CPU-GPU 通信 | GPU-GPU 直接通信 |
| 软件接口 | cudaMemcpy | cudaMemcpyPeer / NCCL |

---

## 3. NVSwitch

### NVSwitch 架构

NVSwitch 是 NVIDIA 的全连接交换机芯片，允许 GPU 以**全带宽**互相通信，无需中间跳转：

```
NVSwitch 全互联拓扑（每 GPU 连接到所有 NVSwitch）：
         GPU 0 ──┬── NVSwitch 0 ──┬── GPU 4
         GPU 1 ──┤                ├── GPU 5
         GPU 2 ──┤                ├── GPU 6
         GPU 3 ──┘                └── GPU 7
                  │                │
         GPU 0 ──┬── NVSwitch 1 ──┬── GPU 4
         GPU 1 ──┤                ├── GPU 5
         GPU 2 ──┤                ├── GPU 6
         GPU 3 ──┘                └── GPU 7
```

DGX H100 中每台服务器有 4 个 NVSwitch，每个 GPU 连接到所有 4 个 NVSwitch，提供 900 GB/s 的总 GPU-GPU 带宽。

### NVSwitch 优势

- **全互联**（All-to-All）：任意两个 GPU 间以 NVLink 全带宽通信
- **可扩展**：通过 NVLink 集群互联，可扩展到数百个 GPU
- **低延迟**：交换机内延迟极低（<1 μs）
- **网络无阻塞**：总带宽足以支持所有 GPU 同时全速通信

---

## 4. 多 GPU 训练通信模式

### 数据并行（Data Parallelism）

每个 GPU 持有完整模型副本，处理不同的数据批次：

```
数据并行通信模式：
                  ┌──────┐
         批次 0 ──►│GPU 0 │───┐
         批次 1 ──►│GPU 1 │───┤
         批次 2 ──►│GPU 2 │───┤     梯度 AllReduce
         批次 3 ──►│GPU 3 │───┼──► ┌───────────┐
         批次 4 ──►│GPU 4 │───┤     │梯度聚合    │
         批次 5 ──►│GPU 5 │───┤     │(Ring-AR)  │
         批次 6 ──►│GPU 6 │───┤     └───────────┘
         批次 7 ──►│GPU 7 │───┘
```

- **通信模式**：梯度 AllReduce（Ring AllReduce / Tree AllReduce）
- **通信量**：与模型参数量成正比（~2 × 模型大小的梯度数据）
- **Scaling Law**：理想情况下，N 个 GPU 可获得 ~N 倍的训练吞吐（受通信效率限制）

### 模型并行（Model Parallelism）

将模型的不同层分布到不同 GPU 上：

```
流水线并行（Pipeline Parallelism）：
GPU 0:  层 1-4    → 前向 → GPU 1
GPU 1:  层 5-8    → 前向 → GPU 2
GPU 2:  层 9-12   → 前向 → GPU 3
GPU 3:  层 13-16  → 输出

反向传播方向相反：GPU 3 → GPU 2 → GPU 1 → GPU 0
```

- **通信模式**：激活值传输（前向） + 梯度传输（反向）
- **通信量**：与激活值大小成正比
- **占用**：流水线气泡（bubble）降低效率，通过微批次（micro-batch）优化

### 张量并行（Tensor Parallelism）

将单层的矩阵切分到多个 GPU 上：

```
张量并行（以列切分为例）：
输入 X ──┬── GPU 0: W[:, 0:N/4]  → X · W[:, 0:N/4]  ──┐
          ├── GPU 1: W[:, N/4:N/2] → X · W[:, N/4:N/2] ──┤── AllReduce → Y
          ├── GPU 2: W[:, N/2:3N/4] → X · W[:, N/2:3N/4] ─┤
          └── GPU 3: W[:, 3N/4:N] → X · W[:, 3N/4:N]  ──┘
```

- **通信模式**：AllReduce 或 AllGather
- **通信量**：与激活值大小成正比
- **最优策略**：在单节点内使用张量并行（利用 NVLink 高带宽）

### 通信策略对比

| 策略 | 通信模式 | 通信量 | 适用场景 | 推荐互联 |
|------|---------|-------|---------|---------|
| 数据并行 | AllReduce | 梯度大小 × 2 | 小模型 | NVLink / 高速网络 |
| 流水线并行 | P2P 激活传输 | 激活值大小 | 超大模型 | NVLink |
| 张量并行 | AllReduce | 激活值大小 | 一层过大的模型 | NVLink（要求最高） |
| 序列并行 | AllReduce | 序列维度相关 | 长序列 Transformer | NVLink |

---

## 5. DGX SuperPOD 架构

### NVIDIA 的超级计算机架构

DGX SuperPOD 通过 NVSwitch 和网络将数百个 GPU 组成集群：

```
DGX SuperPOD H100 架构：
DGX H100 × 32 节点（256 GPU）
  │
  ├── 同一节点内：NVLink + NVSwitch（900 GB/s GPU-GPU）
  └── 节点间：InfiniBand NDR 400G（~50 GB/s 单向）
       └── Mellanox QM9700 交换机全互联
```

这一架构优化了：
- **节点内通信**：NVLink/NVSwitch 提供极致的 GPU-GPU 带宽
- **节点间通信**：InfiniBand 提供可扩展的跨节点通信
- **拓扑感知**：NCCL 自动感知拓扑结构，选择最优通信路径

---

## 参考文献

- NVIDIA, *NVLink and NVSwitch Whitepaper*, 2022. Sections: NVLink 4.0 Architecture, NVSwitch 3rd Gen.
- NVIDIA, *DGX SuperPOD: Next Generation Data Center Architecture*, 2023.
- NVIDIA, *DGX H100 System Architecture Whitepaper*, 2022. Section: NVLink Topology.
- NVIDIA, *NCCL (NVIDIA Collective Communications Library) Documentation*, Section: Topology-aware Communication.
- Li, S. et al., "Demystifying the Communication Characteristics for Distributed Transformer Models", *arXiv:2211.01186*, 2022.
- PCI-SIG, *PCI Express Base Specification Revision 5.0*, 2019.
- NVIDIA, *CUDA C++ Programming Guide*, Section 3.2: Multiple Devices, Section 3.2.4: Peer-to-Peer Access.
- NVIDIA, *NVIDIA H100 Tensor Core GPU Architecture*, Section: NVLink and NVSwitch Connectivity.
- Shoeybi, M. et al., "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism", *arXiv:1909.08053*, 2019. Section: Model and Data Parallelism.
