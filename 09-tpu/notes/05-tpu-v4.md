# TPU v4：光交换机与可重构拓扑的革命

## 1. 设计背景

TPU v3 通过均匀缩放将单芯片性能推到了约 420 TFLOPS，但这种单纯依赖二维 torus 拓扑的扩展方式在更大规模集群（4,096 芯片）下面临严峻的挑战。在固定拓扑的 2D torus 中，随着芯片数量的增加，节点间的平均跳数（hop count）线性增长，All-Reduce 等集体通信操作的延迟和带宽利用率都会恶化。

TPU v4 于 2021 年发布，是 Google 在 TPU 系列上的第四次迭代。与前代相比，v4 最根本的创新在于**光学电路交换机（Optical Circuit Switch, OCS）** 和**可重构拓扑**的引入，使得芯片间互联拓扑可以在毫秒级的时间内动态重建。

## 2. 核心架构

### 2.1 芯片级架构

TPU v4 每芯片的计算能力约为其前代 TPU v3 的 2 倍以上。在数值精度方面，v4 延续了 BF16 计算，同时增加了对 FP8（8-bit 浮点）的原生加速支持，用于特定训练和推理场景。

TPU v4 的核心依然采用 MXU Systolic Array，但尺寸和数量都得到了扩展。每个芯片中的 MXU 总计算面积更大，使得单芯片 BF16 峰值性能达到约 275 TFLOPS。更重要的是，v4 的**互联带宽**相比 v3 提升了约 1.5 倍，每芯片的双向带宽达到约 1.2 Tb/s。

### 2.2 SparseCore

TPU v4 引入了全新的专用硬件单元——**SparseCore**。SparseCore 专门为处理大规模嵌入查找（embedding lookup）操作而设计，这对于推荐系统和 NLP 模型中的稀疏特征尤为重要。

在传统架构中，嵌入查找是一个带宽密集型操作：模型从巨大的嵌入表中检索与输入特征对应的行向量。当嵌入表的大小远超芯片的片上 SRAM 容量时，每次查找都需要一次高延迟的 HBM 或主存访问。SparseCore 为这一操作提供了专门的数据通路和计算单元，每个 SparseCore 提供约 20 GB/s 的随机访问带宽。

SparseCore 的关键设计特性包括：

- **专用的嵌入表缓存**：可配置的片上存储结构，用于缓存最常用的嵌入行；
- **硬件加速的梯度更新**：在反向传播中，嵌入表的稀疏梯度更新可以就地执行，无需通过通用 MXU 完成；
- **多级哈希索引**：支持嵌入表的快速索引，支持分布式嵌入表分区。

设嵌入表的维度为 $V \times d$（$V$ 为词汇表大小，$d$ 为嵌入维度），在一次推理中输入的 batch 包含 $B$ 个样本，每个样本包含 $K$ 个类别特征，则嵌入查找的总访存量约为：

$$
\text{Memory Access} = B \times K \times d \times s
$$

其中 $s$ 是每个稀疏特征的嵌入表存取字节数。SparseCore 通过专用硬件流水线将这一操作的开销降低到传统方案的约 1/5 到 1/10。

## 3. 光学电路交换机（OCS）——最重大的架构创新

### 3.1 问题定义

在传统的数据中心集群中，芯片互联的物理拓扑是固定的。例如 v2/v3 的 2D torus 在芯片部署完成后就不可改变。这意味着：

- 如果某个训练作业需要全对全（all-to-all）通信模式，而物理拓扑只优化了邻域通信，那么远距离通信需要经过多跳中继，造成延迟增加和带宽损耗；
- 不同大小的训练作业（64-chip、256-chip、1024-chip）在同一个固定拓扑上运行，无法为每种规模优化通信路径（拓扑碎片化问题）。

### 3.2 OCS 的工作原理

TPU v4 在互联网络中引入了基于 MEMS（微机电系统）的光学电路交换机。OCS 的核心原理是通过微小镜面的物理偏转，将光纤输入端口与任意输出端口直接连接。关键参数如下：

| 参数 | 值 |
|-----|----|
| 重配置时间 | ~20–50 毫秒 |
| 端口数 | 每个 OCS 交换机 ~136 端口 × 2 方向 |
| 单端口带宽 | ~100–200 Gb/s（取决于光学收发器） |
| 功耗 | 每端口 <1W（远低于电子交换机的 5–10W/端口） |

与传统电子分组交换机（packet switch）不同，OCS 不解析数据包头部，不做缓冲，不做路由决策——它仅仅建立一条端到端的光学连接。一旦连接建立，数据在两个端口之间以光速传播，带宽完全独占，无需转发逻辑。

### 3.3 可重构拓扑

OCS 的引入使得 TPU v4 的物理拓扑与逻辑拓扑**解耦**：

$$
\text{Logical Topology} = f(\text{Physical Topology}, \text{OCS Configuration})
$$

在训练作业开始时，集群调度器评估作业的大小和通信模式，然后调整 OCS 的镜面角度，为该作业"编织"一个最优的拓扑。例如：

- 对于 256-chip 的数据并行训练：可以构建一个 16×16 的 2D torus，每跳延迟最小；
- 对于 512-chip 的模型并行训练：可以构建一个高带宽的 ring 拓扑以加速 pipeline parallelism；
- 对于 4096-chip 的全员训练：可以分层构建 torus，在 OCS 层面将下层 torus 互联。

重配置过程仅需约 20–50 毫秒，两次训练作业之间的拓扑切换延迟几乎不影响集群的整体利用率。

### 3.4 OCS 的效益

OCS 带来的核心效益包括：

1. **消除拓扑碎片化**：不同规模的训练任务可以分别获得为其定制的互联拓扑，不再受物理布线约束；
2. **减少跳数**：逻辑上相邻的芯片在物理上可以跨机架连接，平均通信延迟降低；
3. **提高带宽利用率**：All-Reduce 等集体通信在专用拓扑上可以更高效地完成；
4. **简化布线**：光纤统一布设到 OCS patch panel，运维人员不需要在每次拓扑变更时物理重新接线；
5. **闪电故障恢复**：OCS 可以在几十毫秒内将被故障链路路由到备用链路，而传统电交换需要数分钟。

## 4. 4,096 芯片 Pod

TPU v4 的 pod 规模从前代的 1,024 芯片提升到了 **4,096 芯片**。这一扩展得益于 OCS 引入的拓扑灵活性——在 1,024 芯片规模下，2D torus 尚可工作，但在 4,096 芯片下，没有 OCS 的纯 torus 拓扑的通信效率将大幅下降。

4096 芯片 pod 的总算力约为：

$$
P_{\text{v4 pod}} = 4096 \times 275 \text{ TFLOPS} \approx 1.1 \text{ EFLOPS}
$$

即突破 1 EFLOPS 的 BF16 算力门槛。

## 5. 与前代的对比

| 特性 | TPU v3 | TPU v4 | 提升倍数 |
|------|--------|--------|---------|
| 单芯片性能 (BF16) | 420 TFLOPS | 275 TFLOPS | — |
| 互联带宽/芯片 | ~800 Gb/s | ~1.2 Tb/s (双向) | ~1.5× |
| Pod 规模 | 1,024 | 4,096 | 4× |
| 拓扑 | 固定 2D/3D torus | OCS 可重构拓扑 | 根本性改变 |
| 稀疏计算 | 无 | SparseCore | 新增 |
| 液冷 | 全液冷 | 全液冷 | 延续 |
| 最大 pod 算力 | ~430 PFLOPS | ~1.1 EFLOPS | ~2.5× |

## 6. 多租户与资源隔离

OCS 的另一个关键优势是天然支持多租户。在传统的固定拓扑集群中，不同用户的训练作业共享同一互联网络，作业间可能产生带宽争用和性能干扰。而 OCS 可以将 pod 物理地划分为若干独立的逻辑子集，每个子集拥有完全隔离的网络带宽。

实验数据表明，在 TPU v4 上，OCS 重配置的开销（包括调度、拓扑计算、镜面偏转和链路训练）不到总训练时间的 0.1%。这意味着可重构拓扑的灵活性几乎以零成本获得。

## 7. 对 AI 基础设施的深远影响

TPU v4 的光学交换机架构不仅是一项芯片级别的创新，更代表了一种**以数据中心为计算机（Datacenter as a Computer）** 的系统级设计思想。Google 首次将光通信从数据中心网络的核心延伸到芯片互联层面，实现了计算、网络、存储三位一体的可重构设计。这一思路直接影响了后续的 TPU v4i 和 v5p 的设计方向，也为整个 AI 基础设施行业树立了新的标杆。

## 参考文献

1. Jouppi, N. P., et al. "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings." *Proceedings of the 50th Annual International Symposium on Computer Architecture (ISCA)*, 2023, pp. 1–14.
2. Jouppi, N. P., et al. "Ten Lessons from Three Generations Shaped Google's TPUv4i." *Proceedings of the 48th Annual International Symposium on Computer Architecture (ISCA)*, 2021, pp. 1–14.
3. Farrington, N., et al. "Hedera: Dynamic Flow Scheduling for Data Center Networks." *Proceedings of the 7th USENIX Symposium on Networked Systems Design and Implementation (NSDI)*, 2010, pp. 281–296.
4. Mellette, W. M., et al. "A Scalable, Partially Configurable Optical Switch for Data Center Networks." *Journal of Lightwave Technology*, vol. 35, no. 2, 2017, pp. 136–144.
5. Poutievski, L., et al. "Jupiter Evolving: Transforming Google's Datacenter Network via Optical Circuit Switches." *Proceedings of the ACM SIGCOMM 2022 Conference*, 2022, pp. 121–135.
