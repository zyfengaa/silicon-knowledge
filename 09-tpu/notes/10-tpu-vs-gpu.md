# TPU vs GPU：架构、精度、内存、互联与可编程性对比

## 概述

Google TPU 和 NVIDIA GPU 是当今 AI 加速器市场中最具影响力的两类计算平台。虽然两者都专门针对深度学习工作负载进行了优化，但在核心架构设计理念、数据精度支持、内存层级、芯片互联、可编程性以及部署方式上存在根本性差异。本章将系统性地对比这两类加速器，帮助读者理解各自的优劣和适用场景。

## 全面对比表

| 对比维度 | TPU (Google) | GPU (NVIDIA) |
|---------|-------------|-------------|
| **核心架构** | 脉动阵列（Systolic Array）— 确定性数据流 | SIMT（单指令多线程）— 大量并行线程 |
| **计算粒度** | CISC 指令，一条指令覆盖数千次运算 | SIMT warp（32线程），细粒度调度 |
| **代表性计算单元** | MXU ($128 \times 256$ PE 阵列) | Tensor Core ($4 \times 4$ 矩阵 $+$ 累计) |
| **原生精度** | BF16, INT8, FP32（仅累加） | FP16, BF16, TF32, FP32, FP64, INT8, FP8 |
| **峰值 FLOPS (单芯片)** | 约 275 TFLOPS (BF16, v4) | H100: 约 1979 TFLOPS (FP8) |
| **内存类型** | HBM（统一内存，编译时管理） | HBM/GDDR（需显式管理） |
| **内存容量 (单芯片)** | 32-64 GB (HBM2e, v4/v5p) | 80 GB (H100 SXM, HBM3) |
| **内存带宽 (单芯片)** | 约 1.2-1.6 TB/s | 约 3.35 TB/s (H100, HBM3) |
| **芯片间互联** | OCS 可重构 Torus (v4+) | NVLink + NVSwitch |
| **互联拓扑** | 3D Torus（可动态重构） | NVLink 全互联 / Dragonfly+ |
| **互联带宽 (单向)** | 约 200 GB/s/链路 (v4) | NVLink 4: 每链路 450 GB/s (双向 900 GB/s) |
| **Pod 规模** | 8960 芯片 (v5p) | 576 GPU (DGX GH200 SuperPod) |
| **编程模型** | XLA/JAX/TensorFlow | CUDA/CuDNN/TensorRT/XLA |
| **编程灵活性** | 低 — 只能通过 XLA 编译 | 高 — 完整 CUDA 编程模型 |
| **显式内存管理** | 不需要（统一内存由 XLA 管理） | 需要（cudaMemcpy 等） |
| **生态丰富度** | 有限 — 主要面向 TPU | 极丰富 — ML, HPC, 图形, 仿真 |
| **云部署** | 仅 Google Cloud | AWS, GCP, Azure, 私有云, 本地 |
| **硬件获得方式** | 仅云租用 | 购买 + 云租用 |

## 架构差异详解

### 脉动阵列 vs SIMT

TPU 的 MXU 是脉动阵列（systolic array），其核心特点是**确定性数据流**——数据按照预定路径在 PE 阵列中流水线传播，没有分支预测、乱序执行或缓存一致性等通用处理器特性。这种设计使得计算效率（compute utilization）极高，但牺牲了编程灵活性。

GPU 使用 SIMT（Single Instruction, Multiple Threads，单指令多线程）架构——成百上千个线程以 32 个为一组（warp）执行同一条指令，但各个线程可以处理不同的数据元素（通过寄存器值不同区分）。GPU 的 Tensor Core 本质上是一个 $4 \times 4$ 的微型脉动阵列，专门用于矩阵乘法。GPU 的灵活性在于它可以在矩阵计算、卷积、以及其他通用计算之间快速切换。

关键的数学差异在于：TPU 的 MXU 在单条指令下一次性完成 $128 \times 256$ 庞大计算块，而 GPU Tensor Core 每次处理 $4 \times 4$ 或 $16 \times 8$ 的小块。TPU 的方式减少了指令开销，但 GPU 的方式更灵活，可以更容易地处理不规则的计算形状。

### 数据精度

精度支持是一个重要的对比维度：

TPU 从 v2 开始就引入了 BF16（Brain Floating Point 16）作为原生精度。BF16 的指数位与 FP32 相同（8 位），尾数位为 7 位，因此动态范围与 FP32 一致但精度较低。对于深度学习训练来说，BF16 的较大动态范围使得其稳定性优于 FP16，这正是 TPU 选择 BF16 的关键原因。

NVIDIA GPU 除了支持 FP16 和 BF16 外，从 Hopper 架构开始还引入了 FP8（E4M3 和 E5M2 两种格式），进一步提升了计算吞吐量。FP8 相比 BF16 虽然可用精度更低，但在推理和一些训练的中间阶段已经足够。H100 在 FP8 的峰值计算性能达到 1979 TFLOPS——这显著高于 TPU v4 的 275 TFLOPS（BF16）。

### 内存架构

TPU 的统一内存（Unified Memory）架构是其区别于 GPU 的一大特色。在 TPU 中，XLA 编译器在编译时就知道每个张量的生命周期、访问模式和大小，因此可以精确地分配 HBM 空间并规划数据的搬移。这不仅消除了运行时内存管理的开销，还使得计算单元之间可以通过片上通道直接传递数据，避免内存访问。

相比之下，GPU 需要用户（或框架）显式调用 `cudaMemcpy` 在 CPU 和 GPU 之间搬运数据。虽然 NVIDIA 也提供了统一内存（Unified Memory）API，但其实现依赖于 page fault 和缺页中断，性能开销较大。在实际训练中，大多数高性能 GPU 代码仍然使用显式的内存管理。

### 互联与可扩展性

TPU 的 OCS 可重构 3D Torus 和 GPU 的 NVLink+NVSwitch 代表了两种不同的互联哲学：

- **TPU OCS Torus**: 采用光路交换，拓扑可动态重构，实现了极高的芯片间直连带宽，适合大规模同步训练。缺点是拓扑重构的微秒级延迟在每次拓扑修改时会发生，但这对长周期的训练任务影响不大。

- **GPU NVLink+NVSwitch**: 采用电子交换网络，NVSwitch 作为中心交换机，实现全互联拓扑——每个 GPU 可以直接访问网络中任何其他 GPU 的 HBM（NVLink 地址映射）。NVSwitch 的延迟更低（亚微秒级），全互联拓扑使得集体通信效率更高，但电子交换的功耗和端口密度限制了其扩展规模。

## 何时选择 TPU？

TPU 在以下场景具有显著优势：

1. **大规模单一模型训练**: 如果训练的是一个单一的大模型（如 LLM 或大型 ViT），需要上千个加速器进行同步训练，TPU 的 OCS Torus 和 GSPMD 自动并行化使得开发和运维成本较低。
2. **Google Cloud 生态**: 如果已经深度使用 GCP 生态（BigQuery、GCS、Vertex AI），TPU 与这些服务的集成度极高。
3. **JAX 工作流**: JAX/XLA 的函数式编程模型在复杂模型变换（如 vmap 用于数据并行、pmap 用于设备并行）方面具有独特优势。
4. **稳定的计算模式**: 当模型的计算模式主要由规则的大型矩阵乘法组成时，TPU 的脉动阵列可以达到极高的计算效率。

## 何时选择 GPU？

GPU 在以下场景具有显著优势：

1. **灵活性与多任务**: 需要在同一硬件上运行推理、训练、数据预处理等多种工作负载，GPU 的 SIMT 架构和 CUDA 生态可以更好地适应混合工作模式。
2. **混合精度实验**: 需要尝试不同浮点格式（FP8、FP16、BF16、INT8 等）组合的优化策略，GPU 的精度支持更丰富。
3. **多供应商策略**: 不想被单一云供应商绑定，GPU 在 AWS、Azure、GCP 和本地部署都有支持。
4. **高度定制化的通信模式**: 当需要自定义通信拓扑或使用自定义的并行策略（如 2D/3D 模型并行中的特殊分片方案）时，CUDA 支持的 NCCL 通信库提供了更底层的控制能力。
5. **非 ML 工作负载**: 需要运行 HPC 仿真、渲染、科学计算等非深度学习任务。

## TCO 分析

总拥有成本（TCO, Total Cost of Ownership）的比较需要考虑以下因素：

- **硬件成本**: TPU 仅以云服务形式提供，没有硬件购买选项，因此没有资本支出（CapEx），只有运营支出（OpEx）。GPU 可以选择购买（高 CapEx + 较低 OpEx）或云租用（OpEx 模式）。
- **单位 FLOPS 成本**: Google 宣称 TPU 在每 FLOPS 成本上优于同代的 GPU，但具体价格取决于租赁时长和承诺使用量（CUD, Committed Use Discount）。
- **开发成本**: TPU 的软件栈集成度更高（XLA 自动优化），可以减少手动优化的人力投入。GPU 的 CUDA 编程虽然底层灵活性强，但需要更多工程时间来优化性能。
- **运营成本**: TPU 的编译时内存管理减少了运行时监控需求。GPU 的多任务灵活性可能降低资源碎片化（fragmentation），提高整体利用率。
- **总体判断**: 对于大规模、持续运行的单一模型训练任务，TPU 通常具有更低的 TCO。对于多样化的工作负载组合或需要灵活部署环境的场景，GPU 的通用性带来的 TCO 优势更为明显。

## 结论

TPU 和 GPU 并非"孰优孰劣"的关系，而是面向不同的设计目标和应用场景的两种不同优化路径。TPU 追求在可控的 ML 计算模式下的极致性能和能效，GPU 追求通用性和生态完备性。对于实际团队来说，选择哪一平台应综合考虑模型规模、训练频率、部署环境、团队技术栈和预算约束等因素。在实际生产环境中，两者共存互补也已经成为一种常见的策略。

## 参考文献

1. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." ISCA '17, ACM, 2017.
2. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." Communications of the ACM, Vol. 63 No. 7, 2020.
3. Jouppi, N. P., et al. "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings." ISCA '23, 2023.
4. NVIDIA Corporation. "NVIDIA H100 Tensor Core GPU Architecture." NVIDIA Whitepaper, 2022. https://www.nvidia.com/en-us/data-center/h100/
5. NVIDIA Corporation. "NVIDIA DGX SuperPod Architecture." NVIDIA Technical Whitepaper, 2023.
6. Markidis, S., et al. "NVIDIA Tensor Core Programmability, Performance & Precision." IEEE International Parallel and Distributed Processing Symposium (IPDPS), 2018.
7. Wang, Y., et al. "A Comparative Analysis of TPU and GPU Architectures for Deep Learning." arXiv:2208.07416, 2022.
8. Google Cloud. "Cloud TPU Pricing." Google Cloud Official Site, 2024. https://cloud.google.com/tpu/pricing
