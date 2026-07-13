# TPU v3：规模扩展与液冷全面化

## 1. 设计目标

TPU v3 于 2018 年发布，是 TPU v2 的直接后继产品。与 v2 相比，v3 在架构上没有根本性变化，而是采取了**均匀缩放（uniform scaling）** 的策略——在保持相同微架构的前提下，将关键资源指标增加约 2 倍。这种"同类强化"的做法在芯片设计上风险更低，因为 v2 的架构已经过生产验证。

## 2. 核心架构升级

### 2.1 MXU 数量翻倍

TPU v3 对每个核心的矩阵乘法单元进行了倍增。在 v2 中，每个核心拥有 1 个 MXU（128×128 Systolic Array）。在 v3 中，每个核心拥有 **2 个 MXU**。因此，一个芯片（2 个核心）共计 4 个 MXU。

每个 MXU 的规格与 v2 保持一致：128×128 的 BF16 乘法阵列，FP32 累加。因此 v3 单芯片的理论 BF16 计算峰值是 v2 的 2 倍：

$$
\text{TPU v3 单芯片峰值} \approx 2 \times \text{TPU v2 单芯片峰值} \approx 420 \text{ TFLOPS}
$$

这一增长不仅来自 MXU 数量的翻倍，也来自工作频率的小幅提升（从 v2 的 700 MHz 提升至 v3 的 940 MHz 左右）。

### 2.2 HBM 容量与带宽翻倍

TPU v3 的 HBM 配置从 v2 的 16 GB 每芯片（每个核心 8 GB）提升至 **32 GB 每芯片（每个核心 16 GB）**，同时 HBM 带宽也从约 600 GB/s 翻倍至约 1,200 GB/s。

HBM 容量的增加对于训练大模型至关重要。以 Transformer 类模型为例，大模型通常需要存储：

- 模型参数（$W$）
- 优化器状态（如 Adam 的 $m$ 和 $v$ 动量缓冲）
- 中间激活值（用于反向传播）

设模型参数量为 $P$，以 BF16 存储则需要 $2P$ 字节。对于 Adam 优化器，还需要存储梯度 $g$、一阶动量 $m$ 和二阶动量 $v$（各 $2P$ 字节），因此总存储需求为 $8P$（外加激活值的额外开销）。当 $P = 1B$ 时，仅参数和优化器状态就需要约 16 GB 的 HBM 容量。TPU v3 的 32 GB 每芯片有效缓解了大模型训练时的内存瓶颈。

### 2.3 互联网络带宽提升

TPU v3 的芯片间互联带宽也获得了约 2 倍的提升。在 v2 中，每个芯片与相邻芯片之间的单向带宽约为 32 GB/s，v3 将这个数字提升至约 64 GB/s。在 All-Reduce 操作中，通信带宽的提升直接转化为梯度聚合时间的减少。

设 ring All-Reduce 的通信时间为：

$$
T_{\text{allreduce}} = 2 \times (N - 1) \times \alpha + 2 \times \frac{N - 1}{N} \times \frac{S}{B}
$$

其中 $\alpha$ 是单次消息的启动延迟，$N$ 是参与节点数，$S$ 是梯度数据总量，$B$ 是带宽。当 $S$ 很大（大模型）时，带宽 $B$ 成为主导因素。v3 的带宽翻倍使得大模型训练时的通信瓶颈大幅缓解。

## 3. 液冷全面化

TPU v2 中，水冷仅用于完整的 64-chip pod 配置，部分小型部署仍使用风冷。而在 TPU v3 中，由于 MXU 翻倍带来的功耗增长，**液冷成为所有部署的标准配置**。

### 3.1 热设计功耗

TPU v3 单芯片的 TDP 约为 450W，是 v2（约 200–250W）的近两倍。在 64-chip pod 配置下，一个 pod 的总散热需求约为：

$$
P_{\text{pod}} = 64 \times 450 \text{ W} = 28.8 \text{ kW}
$$

这样的热密度已经远超传统数据中心风冷机架的设计上限（典型风冷机架的散热能力约为 10–15 kW），因此水冷成为必然选择。

### 3.2 冷却方案设计

TPU v3 采用了**直接液体冷却（Direct Liquid Cooling, DLC）** 方案。每个芯片上方安装冷板（cold plate），冷却液通过冷板流道带走热量。冷却液温度保持在 25–30°C 的回水温度范围内（高于传统水冷的 18°C），从而提高了冷却系统的能源效率（更高的回水温度意味着冷却塔的工作能耗更低）。

Google 在 TPU v3 的数据中心部署中采用了名为"温水冷却（Warm Water Cooling）"的策略，允许冷却液在高达 40°C 的入口温度下工作，大幅减少或完全消除了对机械冷却设备（如冷水机组）的需求。

## 4. Pod 级架构

TPU v3 的 pod 结构延续了 v2 的设计但规模更大：

- **4×4 chip board**：16 个芯片组成一块板卡，通过板上的高速互联连接
- **64-chip rack**：4 块 4×4 板卡组成一个 64 芯片机架（2D torus 拓扑）
- **1,024-chip superpod**：16 个 64-chip 机架通过中心化光交换机互连，形成一个包含 1,024 个芯片的大型 superpod

1024-chip superpod 的总计算能力约为：

$$
P_{\text{superpod}} = 1024 \times 420 \text{ TFLOPS} = 430 \text{ PFLOPS}
$$

这一算力在 2018 年发布时位居当时 AI 训练集群的前列。

## 5. 性能表现

在典型的大型模型训练任务中，TPU v3 相比 v2 的表现如下：

| 模型 | TPU v2 (64-chip) | TPU v3 (64-chip) | 加速比 |
|-----|-----------------|-----------------|--------|
| ResNet-50 | 11,500 img/s | 23,000 img/s | 2.0× |
| Transformer Big (NMT) | 18.5 M tokens/s | 37.0 M tokens/s | 2.0× |
| BERT-Large | 整体提升至 ~2× | — | ~2.0× |

实际测试表明，TPU v3 在深度学习模型的训练吞吐量上达到了 v2 的约 2 倍，基本实现了均匀缩放的设计目标。值得注意的是，这一接近线性的加速比证明 v3 的存储和互联带宽增长充分支持了计算资源的倍增，未形成新的瓶颈。

## 参考文献

1. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *Proceedings of the 45th Annual International Symposium on Computer Architecture (ISCA)*, 2018, pp. 1–14.
2. Jouppi, N. P., et al. "Ten Lessons from Three Generations Shaped Google's TPUv4i." *Proceedings of the 48th Annual International Symposium on Computer Architecture (ISCA)*, 2021, pp. 1–14.
3. Barroso, L. A., et al. "The Datacenter as a Computer: Designing Warehouse-Scale Machines." *Synthesis Lectures on Computer Architecture*, 3rd ed., Morgan & Claypool, 2018.
4. Pemberton, N., and Somasundaram, S. "Liquid Cooling in Google's Data Centers." *Google Cloud White Paper*, 2019.
