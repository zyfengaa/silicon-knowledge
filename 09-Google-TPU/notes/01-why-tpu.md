# 为什么需要 TPU？——从数据中心工作负载到专用 ASIC 的演进

## 1. 背景：Google 数据中心的计算瓶颈

在 2013–2014 年期间，Google 已经将深度神经网络（DNN）大规模部署到其核心产品中，包括语音搜索、Street View 文字识别、RankBrain 搜索排序、以及 YouTube 视频推荐。这些模型在推理阶段的运算量巨大，而当时可用的通用 CPU 和 GPU 在能效和吞吐量上均难以满足 Google 的规模化需求。

Google 对自身数据中心的生产工作负载进行了详细分析，得出了一个关键结论：**推理阶段中 95% 的运算操作是矩阵乘法（matmul）或卷积（convolution）**。这一发现直接决定了 TPU 的设计哲学——既然绝大多数运算都属于同一类高度规则化的数值计算，那么完全可以通过定制硬件来极致地优化这一小类操作，而非继续使用为通用计算设计的处理器。

## 2. CPU 和 GPU 的局限性

### 2.1 CPU 的根本问题

CPU 在设计上需要兼顾通用性和低延迟，芯片面积中很大一部分被控制逻辑（分支预测、乱序执行、缓存一致性协议等）占据。对于神经网络推理而言，这些功能几乎完全冗余。一个典型的 CPU 核心的 ALU（算术逻辑单元）面积占比不到 20%，其余部分被取指、译码、重排序缓冲、分支预测器、缓存标签等占据。

### 2.2 GPU 虽然强，但仍不够

当时最先进的 GPU（如 NVIDIA K80）虽然拥有数千个 CUDA core 且适合并行计算，但 GPU 本质上仍然是一个**通用并行处理器**。它保留了图形管线、复杂的线程调度器、以及为图形渲染设计的 cache 层次结构。在推理场景中，GPU 的利用率往往受到以下几个因素的制约：

- **Thread block 调度开销**：GPU 需要将计算划分为线程块，调度到 SM 上，每个 warp 的 divergence 问题仍会增加效率损失；
- **显存带宽受限**：虽然 GPU 使用 HBM，但在 batch 较小时，计算单元因访存延迟而空转的情况依然严重；
- **能效比不足**：GPU 为了支持各种并行模式（归约、扫描、排序）而保留的大量灵活性，在 AI 推理场景中成了不必要的功耗开销。

Google 的内部测算显示：对于其生产级 DNN 模型，**GPU 的吞吐量比实际需求低 10–30 倍**，且 TCO（总体拥有成本）远高于可接受水平。

## 3. 专用 ASIC 的设计选择

### 3.1 舍弃一切非必要功能

TPU 的设计原则极其明确：既然 95% 的运算是 matmul 和 conv，那就做一个**专门执行矩阵乘法的机器**。具体而言，TPU 的设计中：

- **没有图形管线**（rasterizer、ROP、纹理单元等）；
- **没有分支预测器**——CISC 指令本身不包含分支；
- **没有乱序执行**——指令按顺序发射和完成；
- **没有传统的通用 cache 层级**——代之以软件管理的片上 SRAM；
- **没有线程调度器**——Systolic Array 由 host 驱动，数据流由编译器静态安排。

### 3.2 确定性执行模型

与 GPU 的 no-op 指令填充策略不同，TPU 不依赖硬件动态调度来隐藏延迟。所有访存和计算的时序由编译器在编译时确定，硬件严格按照预定顺序执行。这消除了动态调度带来的能耗和面积开销，使得芯片上几乎所有晶体管都服务于实际的计算和访存。

这种**确定性执行**模型带来的好处是显著的：芯片的功耗更加可预测，面积利用率高达 70% 以上（对比 CPU 的典型约 20%），能效比提升了一个数量级。

## 4. 能效分析

从理论层面来看，一次算术运算的能耗比一次 DRAM 访存低两个数量级。对于常规的冯·诺依曼架构，大量的能耗浪费在数据搬运上。TPU 的**软件管理片上 SRAM** 策略（28MB 位于计算阵列旁）大幅减少了芯片与 DRAM 之间的数据搬运量，从而显著降低了每 TOPS（Tera Operations Per Second）的能耗。

设一次 $8$-bit 乘加运算的能耗为 $E_{\text{MAC}}$，一次 DRAM 访存的能耗为 $E_{\text{DRAM}}$，在典型工艺节点下：

$$
E_{\text{DRAM}} \approx 200 \times E_{\text{MAC}}
$$

因此，减少 DRAM 访存次数对于降低总能耗至关重要。TPU 的设计通过最大化片上数据复用，将权重数据一次性加载到 SRAM 中，然后由 Systolic Array 反复使用，有效降低了片外数据搬运的开销。

## 5. 商业与技术决策的闭环

TPU 的诞生并非一次纯学术探索，而是由明确的商业需求驱动。Google 的推理工作负载的增长率极高，以语音识别为例，2012 到 2014 年间 Google 的语音搜索量增长了 100 倍以上。如果继续使用 CPU/GPU 集群来承载这些推理工作，将导致数据中心规模急剧膨胀，功耗和冷却成本不可持续。

TPU 项目于 2013 年启动，目标是 2015 年完成部署。从设计到 tape-out 仅用了约 15 个月的时间——这一速度在 ASIC 项目中极为罕见。Google 团队采取了高度激进的设计策略：大量使用自动化布局布线工具，限制设计复杂度，专注于单一的矩阵乘法数据类型（INT8），以最快速度交付可用的推理加速器。

从最终结果来看，TPU v1 在 2015 年部署后，将 Google 推理集群的 TCO 降低了大约一个数量级，证明了**领域专用架构（Domain-Specific Architecture）** 在特定工作负载下的巨大优势，也为后续可训练 TPU（v2/v3/v4）的发展奠定了理论和工程基础。

## 参考文献

1. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *Proceedings of the 44th Annual International Symposium on Computer Architecture (ISCA)*, 2017, pp. 1–12.
2. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *Communications of the ACM*, vol. 63, no. 7, 2020, pp. 67–78.
3. Hennessy, J. L., and Patterson, D. A. "A New Golden Age for Computer Architecture: Domain-Specific Hardware/Software Co-Design, Enhanced Security, Open Instruction Sets, and Agile Chip Development." *Proceedings of the 2018 ACM/IEEE 45th Annual International Symposium on Computer Architecture (ISCA)*, 2018, pp. 27–29.
4. Gray, S., et al. "A Configurable Parallel Hardware Architecture for Efficient Convolutional Neural Network Inference." *Proceedings of the 2017 ACM/SIGDA International Symposium on Field-Programmable Gate Arrays*, 2017, pp. 231–240.
