# TPU v4 论文精读笔记

**论文**: TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings (Jouppi et al., ISCA'23)

---

## 1. 研究背景与动机

TPU v2/v3 使用固定的 2D Torus 拓扑互联，这种设计对于 all-reduce 通信模式效率很高，但具有根本性的局限。固定拓扑意味着计算资源的分配方式固化——一旦芯片之间的物理连接确定，多租户隔离、容错性和作业调度的灵活性都会受到严重制约。一个典型例子是：如果 256 芯片 Pod 中的 4 个芯片被分配给一个租户，剩余的 252 个芯片无法高效地组成一个完整的连续拓扑给另一个租户使用，因为 torus 拓扑中断了。

随着 Google 的模型规模持续增长——从 TPU v3 时代的数十亿参数发展到 v4 时代的数千亿甚至万亿参数模型（如 PaLM、Gemini）——Google 需要一种能够在更大规模下（数千芯片）实现高效且灵活的互联方案的超级计算机架构。

## 2. 光学可重构互联（OCS）

TPU v4 最革命性的创新是引入了光学电路交换机（Optical Circuit Switch, OCS），实现了互联拓扑的动态可重构。

OCS 的工作原理基于 MEMS（微机电系统）反射镜阵列。每个 OCS 交换机在输入光纤和输出光纤之间使用数百个微镜面来路由光信号。当需要改变拓扑时，微镜面重新调整角度，光信号被引导到不同的输出光纤上。这种切换的延迟在**毫秒量级**（MEMS 开关约 ≤5 ms，含控制与链路训练的整体重配置约 10 ms）——比电交换机的纳秒级延迟慢几个数量级，但对于训练作业调度来说完全足够，因为在作业级别，拓扑调整的频率很低（每次调度变化一次）。

OCS 带来的核心优势有三个。

**第一，灵活的资源分配**：TPU v4 的 4096 个芯片通过 OCS 互联，可以动态地划分为任意大小的子集群。例如，一个训练 PaLM 模型的大型作业可以独占 2048 个芯片形成 3D Torus，而其他团队可以在剩余的芯片上运行实验。作业完成后，OCS 可以重新配置拓扑，将资源分配给新的作业。Google 将这种能力称为"芯片虚拟化"——物理芯片不变，但逻辑拓扑可以根据需求调整。

**第二，多租户隔离**：在大型数据中心中，不同团队同时训练多个模型是常态。OCS 允许为不同的租户创建完全隔离的光学子网（optical sub-network）。一个租户的流量完全限制在其分配的光纤和芯片之间，不会影响其他租户的性能。这避免了传统以太网或 InfiniBand 网络中常见的"噪声邻居"问题。

**第三，容错性**：当某个芯片或光纤链路故障时，OCS 可以快速绕过故障组件，重新配置剩余的拓扑，将故障芯片排除出去而不影响整个系统的可用性。

## 3. SparseCore 架构

TPU v4 引入了 SparseCore，这是一个专门处理嵌入查找（embedding lookup）操作的加速器。在推荐系统、搜索排序等大型模型中，嵌入查找是计算瓶颈之一，也是最稀疏的操作——通常需要从巨大的嵌入表中随机读取特定索引对应的稠密向量。

SparseCore 的设计目标是：在模型训练过程中，高效地处理嵌入表和聚合操作。每个 TPU v4 芯片包含多个 SparseCore，每个 SparseCore 具有本地存储和计算能力，可以直接从 HBM 中读取嵌入向量并进行累加。这避免了嵌入操作在 MXU 上运行时出现的极度低效问题（因为 MXU 专为稠密矩阵乘法优化，对随机访存模式几乎无能为力）。

SparseCore 是业界较早对嵌入查找进行硬件加速的设计之一，是 TPU v4 区别于 GPU 和其他 AI 加速器的重要特征。

## 4. 芯片与 Pod 架构

TPU v4 的单个芯片相比 v3 有了全面升级。每个芯片的 BF16 峰值约 **275 TFLOPS**、INT8 约 **275 TOPS**；每芯片包含 **2 个 TensorCore × 4 个 MXU = 8 个 $128 \times 128$ 的 MXU（共 131,072 个 MAC）**。注意 v4/v5p 的单个 MXU 仍为 $128 \times 128$，并非 $128 \times 256$；单个 MXU 升级到 $256 \times 256$ 发生在 v6e（Trillium）。按约 1.05 GHz 估算，$131{,}072 \times 2 \times 1.05\,\text{GHz} \approx 275$ TFLOPS，与标称值一致。每个芯片配备 32 GiB HBM2e（v3 为 32 GB，但带宽更高，约 1.2 TB/s）。更重要的是，TPU v4 对 HBM 的利用率进行了优化，通过更高效的片上缓存层次降低了对 HBM 带宽的依赖。v4 **不支持 FP64**，也没有原生 FP8。

一个完整的 TPU v4 Pod 包含 4096 个芯片，通过 OCS 网络以 3D Torus 拓扑互联；其 BF16 峰值算力约为 $4096 \times 275 \text{ TFLOPS} \approx 1.1$ EFLOPS。不应把该 Pod 描述为 FP64/Linpack 超级计算机或 100+ POPS 的系统。

## 5. 性能结果

论文中报告了多项性能数据。在 NLP 模型训练方面，Google 官方宣称 TPU v4 相比 v3 实现了约 2–3 倍的速度提升；在推荐系统模型上，由于 SparseCore 的帮助，提速更为显著。对于 Transformer 类模型，TPU v4 的强项在于其大规模并行能力：4096 芯片 Pod 在部分负载上可以接近线性扩展，但实际效率随模型、并行策略和通信模式变化，不宜笼统写死为 90% 以上。

与 NVIDIA A100 GPU 相比，TPU v4 在某些特定基准上表现更优——特别是 Google 自家的大规模稀疏和稠密混合模型。但 A100 在通用性和生态系统方面仍然具有优势。

## 6. OCS 的深入分析

OCS 的价值不仅体现在上述实用性上，它还代表了一种计算机系统设计范式的转变。传统的超级计算机采用固定拓扑——如 IBM Blue Gene 的 3D Torus、Cray XC 的 Dragonfly、以及 TPU v2/v3 的 2D Torus——一旦部署完成，拓扑就固定不变。这种设计在面对多样化工作负载时的适应性很差。

OCS 在逻辑上将"计算拓扑"这一概念从物理层解耦出来。基础设施管理者可以像管理计算资源一样管理互联资源。Google 在论文中展示了通过 OCS 动态调整拓扑的能力；重配置时间取决于规模与链路训练，通常在毫秒到秒量级，而不是"即时完成"。

从能耗角度看，OCS 也优于电交换：光交换机的能耗与端口数相关，而电交换机的能耗随带宽增长；在 TPU v4 的规模下，这种差异有助于降低互联功耗（具体节省量取决于端口速率、链路利用率和部署规模，公开资料未给出可直接引用的统一数值）。

## 7. 批判性分析

TPU v4 并非完美。OCS 虽然实现了拓扑可重构，但 MEMS 镜面的切换延迟约为毫秒级（开关 ≤5 ms，整体约 10 ms），远高于电交换机的亚微秒级延迟。这意味着 OCS 不适合需要频繁通信模式切换的工作负载。

SparseCore 虽然是创新设计，但其应用范围相对狭窄。只有推荐系统、搜索排序等包含大规模嵌入表的模型能从 SparseCore 获益，对于纯 Transformer 类模型，SparseCore 的作用微乎其微。

此外，TPU v4 依然完全依赖 XLA 编译器栈，对生态系统的兼容性不如 NVIDIA 的 CUDA。PyTorch 用户仍然需要通过 PyTorch/XLA 来使用 TPU，这带来了额外的调试和优化负担。

最后，TPU v4 的成本问题不容忽视。液冷、OCS 光纤网络、大规模 HBM 的采用使得 TPU v4 Pod 的造价极高。Google 目前仅通过 Google Cloud TPU 服务对外提供 v4 的使用权限，而不对外销售硬件。

## 8. 学术贡献与影响

TPU v4 的工作发表于 ISCA'23。它与 TPU v1 共同构成了计算机体系结构历史上极具影响力的系列工作之一。如果 v1 证明了专用加速器的价值，v4 则证明了可重构互联在大规模并行计算中的战略意义。

TPU v5p 作为 v4 的后续演进版本，进一步扩展了 OCS 网络的规模，并将单芯片 BF16/FP8 性能提升到 459 TFLOPS（约为 v4 的 1.7 倍）。可以预见，OCS 技术将继续在超大规模 AI 超级计算机中扮演重要角色。

## 参考文献

1. Jouppi, N. P., et al. "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings." ISCA'23.
2. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *Communications of the ACM*, 63(7), 2020.
3. Farrington, N., and Porter, G. "Optical Data Center Networks." ACM SIGCOMM'13.
4. Google Cloud Blog. "TPU v4: A New Generation of Custom Machine Learning Hardware." 2022.
5. Top 500 List. "November 2022." https://www.top500.org/.
