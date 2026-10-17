# TPU v5p (2023)：第五代训练加速器

## 概述

TPU v5p 是 Google 于 2023 年 12 月正式发布的第五代张量处理单元（Tensor Processing Unit）。v5p 的定位是面向大规模大语言模型（LLM）训练与推理，在其前代 v4 的基础之上进行了升级，包括矩阵乘法单元（MXU）增强、高带宽内存（HBM）扩容、片间互联带宽提升，以及 Pod 规模的进一步扩展。Google 官方宣称，在特定 LLM 训练配置下，单个 v5p Pod 相比 v4 Pod 可获得约 2× 的性能提升；具体倍数随模型和并行策略变化，不宜当作普适结论。

## 核心规格与性能指标

TPU v5p 的关键硬件规格如下：

| 指标 | TPU v4 | TPU v5p | 提升倍数 |
|------|--------|---------|----------|
| 矩阵乘法性能 (BF16/FP8) | 275 TFLOPS | 459 TFLOPS | ~1.7× |
| HBM 容量 | 32 GiB | 95 GiB | ~3× |
| HBM 带宽 | ~1.2 TB/s | 2,765 GB/s | ~2.3× |
| 片间互联带宽 | ~600 GB/s 双向 | 1,200 GB/s 双向 | 2× |
| Pod 规模 | 4,096 芯片 | 8,960 芯片 | 2.2× |
| 总 FLOPS (Pod) | ~1.1 EFLOPS | ~4.5 EFLOPS | ~4× |

具体来说，v5p 的 MXU 组织与 v4 相同：每个芯片包含 **2 个 TensorCore，每个 TensorCore 4 个 $128 \times 128$ 的 MXU**，即每芯片 **8 个 MXU、131,072 个 MAC**。**v5p 的单个 MXU 仍是 $128 \times 128$，不是 $128 \times 256$**；相对 v4 的提升主要来自更高时钟频率（约 1.75 GHz）和系统级改进。按此估算，$131{,}072 \times 2 \times 1.75\,\text{GHz} \approx 459$ TFLOPS，与标称 BF16/FP8 吞吐量一致。每个 v5p 芯片配备 **95 GiB 的 HBM3**（不是 HBM2e），比 v4 的 32 GiB 大幅增加；官方规格为 2,765 GB/s。每芯片包含 2 个 TensorCore 和 4 个 SparseCore。这对于训练参数规模达到数千亿甚至万亿级别的 LLM 至关重要。

片间互联带宽方面，v5p 通过改进的光学电路交换（OCS）技术和更高速的 SerDes 接口，将每个芯片的双向互联带宽提升至 **1,200 GB/s**，约为 v4（约 600 GB/s 双向）的 2 倍，而不是 4 倍。这使得在大规模分布式训练场景下的梯度同步开销大幅降低。

## 增强的 MXU 架构

v5p 的 MXU 延续了 Google 标志性的脉动阵列（systolic array）设计，但针对大型矩阵乘法运算进行了优化。每个 v5p 芯片包含 2 个 TensorCore，每个 TensorCore 内含 4 个 $128 \times 128$ 的 MXU（每芯片共 8 个 MXU）；MXU 是二维脉动阵列，支持 BF16/FP8 输入与 FP32 累加。脉动阵列的基本工作原理为：

设矩阵 $A \in \mathbb{R}^{M \times K}$ 与矩阵 $B \in \mathbb{R}^{K \times N}$ 相乘得到矩阵 $C \in \mathbb{R}^{M \times N}$，其中 $C_{ij} = \sum_{k=1}^{K} A_{ik} B_{kj}$。在脉动阵列中，$A$ 的行数据从左侧流入，$B$ 的列数据从上方流入，每个处理单元（PE）负责执行一次乘加运算 $C_{ij} = C_{ij} + A_{ik} \cdot B_{kj}$，数据在阵列内部以流水线方式传播。这种设计充分利用了数据局部性，最大限度地减少了寄存器与内存之间的数据搬运。

v5p 的 MXU 相比 v4 的改进包括更高的时钟频率（约 1.75 GHz 对约 1.05 GHz）以及优化的数据流控制逻辑，使得有效计算效率（utilization）进一步提升；单个 MXU 的阵列维度并未从 $128 \times 128$ 扩大。

## Pod 架构与规模扩展

TPU v5p Pod 支持最多 8960 个芯片的规模，通过高密度光学电路开关（OCS）互连。与 v4 的 3D 可重构 Torus 拓扑一脉相承，v5p 的互联架构支持灵活的网络拓扑配置，可以根据用户的工作负载需求动态调整芯片之间的连接模式。这一能力对于训练 GPT-4 级别的大模型极为关键——模型并行度、数据并行度与流水线并行度可以在更大的芯片池中获得更优的组合。

总浮点运算能力方面，单个 v5p Pod 的峰值性能达到约 4.5 exaFLOPS（BF16），足以支撑数万亿参数规模的模型训练。Google 官方数据显示，在训练类似 GPT-3（1750 亿参数）规模的大模型时，v5p Pod 相比 v4 Pod 可以将训练时间缩短 50%-75%。

## 大语言模型训练性能

Google 在发布 v5p 时公布了多项基准测试结果。在 LLM 训练方面，Google 官方博客宣称的特定配置下提升如下（属于厂商口径，实际结果随模型、并行策略和软件版本变化）：

- **GPT-3 175B 规模**: 端到端训练吞吐量提升 2.5×-3×
- **MoE (Mixture-of-Experts) 模型**: 由于 v5p 更高的 HBM 带宽和更大的芯片间带宽，专家并行场景下的通信瓶颈显著缓解，性能提升可达 3.5×-4×
- **长序列 Transformer**: 借助更大容量的 HBM，长序列训练时的显存压力大幅降低，支持更长的上下文窗口

这些性能提升来自硬件改进与软件优化的协同。XLA 编译器在 v5p 上支持更激进的算子融合策略（fusion），GSPMD 自动并行化框架也针对 v5p 的拓扑结构进行了调优。

## v5p 在 Google Cloud 上的应用

TPU v5p 以 Google Cloud TPU v5p 的形式提供，用户可以通过 Cloud TPU API 申请资源。与以往代际一样，v5p 完全与 Google 的软件栈集成，包括 JAX、TensorFlow 和 PyTorch（通过 XLA 编译后端）。Google 推出了一种新的资源分配模型——"多切片"（Multi-slice）——允许用户将多个 TPU Pod 组合在一起，构建超大规模的虚拟集群以训练极大规模的模型。

从成本效益角度分析，v5p 在每美元性能（price/performance）方面的提升较 v4 高达 2× 以上。这使得在同等预算下，用户可以训练更大的模型或以更短的时间完成训练。

## 后续代际（2024–2026）

v5p 之后，Google 继续按“训练/推理分线”迭代，因此 v5p 已不是最新一代：

- **TPU v5e**：面向推理与性价比的版本，Pod 规模 256 芯片；单芯片算力与 HBM 容量低于 v5p，适合成本敏感的推理/微调负载。
- **TPU v6e（Trillium）**：2024 年发布，官方公布单芯片 BF16 约 918 TFLOPS、32 GB HBM，Pod 规模 256 芯片，并引入第三代 SparseCore。
- **TPU v7（Ironwood）**：2025 年发布并逐步开放，官方公布单芯片 FP8 约 4,614 TFLOPS、192 GB HBM3E，Pod 规模 9,216 芯片、约 42.5 FP8 EFLOPS，面向大规模 LLM 训练与推理。

阅读本模块时，应以 v5p 规格表为“第五代”基线，并结合上述代际的官方文档更新。

## 未来展望

TPU v5p 是 Google 第五代训练加速器的重要节点，但 AI 模型的规模仍在高速增长。随着 MoE 架构的广泛采用和万亿参数级别模型的涌现，后续 TPU（v6e/v7 及之后）更加注重 HBM 容量、互联带宽与 FP8/低精度格式的平衡。

## 参考文献

1. Google Cloud TPU v5p Documentation. "TPU v5p AI Accelerators for Large Language Models." Google Cloud Official Documentation, 2023. https://cloud.google.com/tpu/docs/v5p
2. Jouppi, N. P., et al. "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings." Proceedings of the 50th Annual International Symposium on Computer Architecture (ISCA '23), 2023.
3. Google Cloud Blog. "Introducing Cloud TPU v5p: The Most Powerful, Scalable AI Accelerator." 2023. https://cloud.google.com/blog/products/ai-machine-learning/introducing-cloud-tpu-v5p
4. Google Cloud. "TPU v6e (Trillium) Documentation." https://cloud.google.com/tpu/docs/v6e
5. Google Cloud Blog. "Introducing Ironwood, Our Seventh-Generation TPU." 2025.
6. Dean, J., et al. "Large Scale Distributed Deep Networks." Advances in Neural Information Processing Systems (NeurIPS), 2012.
