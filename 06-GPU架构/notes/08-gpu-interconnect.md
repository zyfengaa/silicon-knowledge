# 08 — 单机与封装内互连

> 现代高性能计算系统中 GPU 不是孤立的计算单元。CPU-GPU 通信、GPU-GPU 通信的带宽和拓扑直接影响多 GPU 应用的性能。本篇聚焦芯片与单机封装内的互连；集群网络与并行策略见兄弟仓库 `why-ai-cluster`。

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
| Gen 6 | PAM4 + FLIT + FEC | 64 | ~128 GB/s | ~256 GB/s |

注：Gen 1-5 使用 128b/130b 编码；Gen 6 改用 PAM4 信号（每符号 2 bit）、固定大小的 FLIT 和 FEC 前向纠错，因此不再使用 128b/130b。

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

### GPU-GPU 通信：P2P 与经过 Root Complex 两条路径

多 GPU 服务器里，GPU 之间走 PCIe 有两条不同路径：

- **P2P（Peer-to-Peer）**：GPU 0 直接访问 GPU 1 的 BAR 空间，不经过 CPU 和系统内存。前提是两块 GPU 位于同一 PCIe 交换机或同一 CPU 根端口下，并且芯片组/BIOS 没有用 ACS（Access Control Services）阻断。
- **非 P2P**：GPU 0 → PCIe → CPU Root Complex → 系统 DDR → CPU Root Complex → PCIe → GPU 1。数据被 CPU 和内存中转，带宽与延迟都明显更差。

`nvidia-smi topo -m` 的输出可以帮助判断：`PIX`/`PXB` 表示同一 PCIe 交换机下的 P2P 路径，`PHB` 表示经过 host bridge，`SYS` 表示跨 NUMA、经过系统内存。启用 IOMMU 或严格的 ACS 策略时，P2P 可能被强制绕到 Root Complex；实际走哪条路径要以拓扑和实测带宽为准，不能只看“都插在 PCIe 上”。

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

需要注意：页面错误和迁移会显著拖慢性能，但统一内存并非"不能用于高性能计算"。在现代系统上，配合显式预取与访问建议（`cudaMemPrefetchAsync`、`cudaMemAdvise`）以及 HMM/ATS 等机制，统一内存已可用于生产环境（例如 Grace Hopper 的 CPU-GPU 一致地址空间）。若不加以管理、任由 GPU 频繁缺页，则性能可能远低于显式拷贝。

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
| NVLink 4 | Hopper | 25 GB/s | 50 GB/s | 18 | 900 GB/s |
| NVLink 5 | Blackwell | 50 GB/s | 100 GB/s | 18 | 1,800 GB/s |

注：NVLink 4 每条链路双向 50 GB/s（每个方向 25 GB/s），18 条链路合计 900 GB/s。NVLink 5 每链路双向 100 GB/s，18 条链路合计 1.8 TB/s。表中"总带宽/GPU"一列均为双向合计。

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
| 带宽 | ~64 GB/s（单向）/ ~128 GB/s（双向） | 900 GB/s（双向，18 链路） |
| 延迟 | ~1-2 μs | ~1-2 μs |
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

DGX H100 中每台服务器有 4 颗 NVSwitch 3。每张 H100 的 18 条 NVLink 4 链路按 **5+4+4+5** 分配到 4 颗交换芯片上，因此任意两张 GPU 之间都有 900 GB/s（双向）的全带宽路径；对应到交换芯片的 GPU 侧端口占用是 40/32/32/40。

为什么需要交换芯片？8 张卡两两直连需要 $C(8,2)=28$ 对连接，而每张卡只有 18 条链路，分给 7 个对端后每对只剩 2 条，带宽远低于全速。NVSwitch 把链路集中起来做交换，才能让 8 卡（以及 NVL72 的 72 卡）在域内保持全带宽。

### NVLink 5 与 GB200 NVL72

Blackwell 世代的 NVLink 5 将每 GPU 的双向带宽提升到 1.8 TB/s。GB200 NVL72 通过 NVSwitch 把机架内的 72 个 Blackwell GPU 全互联，使整个机架在逻辑上像一个大型 GPU 一样通信；这是"纵向扩展（scale-up）"与 InfiniBand 的"横向扩展（scale-out）"的分界。

NVSwitch 的代际差异直接决定了 NVLink 域的规模：

| 项目 | NVSwitch 3（Hopper） | NVSwitch 4（Blackwell） |
|------|---------------------|------------------------|
| 端口数 | 64 | 72 |
| 单端口带宽 | 50 GB/s（双向，NVLink 4） | 100 GB/s（双向，NVLink 5） |
| 单芯片聚合带宽 | 64 × 50 ≈ 3.2 TB/s | 72 × 100 ≈ 7.2 TB/s |
| 典型部署 | DGX H100：4 颗 | GB200/GB300 NVL72：18 颗（9 个托盘） |
| 单 NVLink 域上限 | 8 GPU | 72 GPU |

NVLink 域的上限随代际扩大：H100 为 8 卡，NVL72 为 72 卡，Rubin 规划为 NVL144，Rubin Ultra 为 NVL576。**域内**走 NVLink/NVSwitch，**域间**走 InfiniBand 或以太网。DGX SuperPOD 的 256 卡是 32 个 8 卡节点通过 IB 组成的集群，不是"256 卡 NVLink 全互联"。

开放标准方面，UALink 1.0 定义 **800 Gb/s/端口（100 GB/s 单向）** 的加速器 scale-up 互联，ESUN（Ethernet for Scale-Up Networking）则在 OCP 下探索基于以太网的 scale-up；两者都是 NVLink 之外的选项，生态仍在形成。NVLS（NVLink SHARP）让 NVSwitch 在网内完成归约（AllReduce 的 reduce 阶段），跨机的对应能力是 InfiniBand SHARP（NCCL 中的 CollNet）。

另有两个容易混淆的互连：

- **NVLink-C2C**：Grace CPU 与 Hopper/Blackwell GPU 之间的芯片间一致性互连（Grace Hopper 上为 900 GB/s 双向）。
- **NV-HBI**：Blackwell B200 两个计算 die 之间的高带宽互连（10 TB/s），用于把双 die 组成一颗逻辑 GPU；它不是 GPU 之间的 NVLink。

### NVSwitch 优势

- **全互联**（All-to-All）：任意两个 GPU 间以 NVLink 全带宽通信
- **可扩展**：NVLink 域可从 8 卡扩展到 NVL72 的 72 卡（更大队列属集群组网）
- **低延迟**：交换机内延迟极低（<1 μs）
- **网络无阻塞**：总带宽足以支持所有 GPU 同时全速通信

---

## 4. 从单机互连到集群网络（延伸阅读）

本节只讨论芯片与单机封装内的互连。以下内容属于集群/系统层，统一放在兄弟仓库 `why-ai-cluster`：

- 数据并行/张量并行/流水线并行/序列并行的通信模式与通信量分析
- InfiniBand/RoCEv2、网络拓扑与超订阅比
- DGX SuperPOD 等大规模组网、调度与运维

入口：

- [数据并行 DP](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/01-数据并行DP.md)
- [张量并行 TP](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/02-张量并行TP.md)
- [流水线并行 PP](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/03-流水线并行PP.md)
- [序列并行 SP](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/05-序列并行SP.md)
- [网络拓扑怎么选](https://github.com/zyfengaa/why-ai-cluster/blob/main/03-网络篇/05-网络拓扑怎么选.md)
- [超大集群长什么样](https://github.com/zyfengaa/why-ai-cluster/blob/main/09-前沿与实践篇/01-超大集群长什么样.md)

需要保留的一条硬件事实：DGX SuperPOD 的 256 卡是 32 个 8 卡节点通过 InfiniBand 互联，不是"256 卡 NVLink 全互联"；每个 8 卡节点内部才是 NVLink 域。把两者混为一谈会把跨节点带宽高估一个数量级以上。

---

## 参考文献

- NVIDIA, *NVLink and NVSwitch Whitepaper*, 2022. Sections: NVLink 4.0 Architecture, NVSwitch 3rd Gen.
- NVIDIA, *DGX H100 System Architecture Whitepaper*, 2022. Section: NVLink Topology.
- PCI-SIG, *PCI Express Base Specification Revision 5.0*, 2019.
- NVIDIA, *CUDA C++ Programming Guide*, Section 3.2: Multiple Devices, Section 3.2.4: Peer-to-Peer Access.
- NVIDIA, *NVIDIA H100 Tensor Core GPU Architecture*, Section: NVLink and NVSwitch Connectivity.
- UALink Consortium, *UALink 1.0 Specification*, 2025. — UALink 端口速率与 scale-up 语义.
- NVIDIA, *NVIDIA GB200 NVL72 System Architecture*, 2024. — NVL72 的 NVSwitch 数量与整柜带宽.
- Open Compute Project, *Ethernet for Scale-Up Networking (ESUN)*, 2025. — 基于以太网的 scale-up 工作流.
