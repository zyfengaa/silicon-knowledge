# TPU v1：2015 年部署的推理专用加速器

## 1. 概述

TPU v1（第一代张量处理单元）是 Google 于 2015 年部署到其数据中心的专用 ASIC 推理加速器。它被设计为 PCIe Gen3 ×16 协处理器，插在现有服务器的 PCIe 插槽上，配合 host CPU 完成推理服务。TPU v1 不支持训练——它只做推理，且只支持 INT8 精度。

## 2. 核心架构

### 2.1 Systolic Array

TPU v1 的核心是 **256×256 的二维脉动阵列（Systolic Array）**，包含总计 65,536 个 8-bit 乘加单元（MAC）。每一个 MAC 单元在单个时钟周期内完成一次 $8 \times 8 \rightarrow 32$ 的乘加运算，即：

$$
a_{ij} = \sum_k w_{ik} \cdot x_{kj}
$$

该阵列采用**权重固定（Weight Stationary）** 的数据流方式：权重从 SRAM 预加载到每个 MAC 单元的本地寄存器中并驻留，输入激活值沿行方向（自左向右）脉动传播，部分和沿列方向（自上而下）累加。这种设计最大限度地提高了权重的复用率——在计算一个 $256 \times 256$ 的矩阵乘法时，每个权重被重复使用 256 次，大幅降低了对片外带宽的需求。

设矩阵乘法的两个矩阵分别为 $W \in \mathbb{Z}_8^{M \times K}$ 和 $X \in \mathbb{Z}_8^{K \times N}$，Systolic Array 的计算效率在 $M = K = N = 256$ 时达到峰值。对于非 $256$ 倍数的维度，硬件通过 padding 或分块处理来适配阵列尺寸。

### 2.2 片上存储体系

TPU v1 配备了总计 **28MB 的片上 SRAM**，分为两个主要部分：

- **统一缓冲器（Unified Buffer, UB）**：24MB，用于存储输入激活值和部分和。UB 是一个软件管理的 SRAM 缓冲区，编译器显式控制数据的装载和卸载。UB 与 Systolic Array 之间通过专用的数据通路连接，带宽足以在每个周期为阵列所有列提供新的输入数据。
- **权重 FIFO**：4MB，用于存储权重矩阵。由于采用权重固定数据流，权重只需要在矩阵乘法开始时一次性加载到阵列中，后续计算中权重在阵列内部循环，不再需要从片外读取。

### 2.3 指令集架构

TPU v1 采用**类 CISC（复杂指令集计算机）** 的指令集设计，核心指令只有 **5 条**。与 GPU 的数千条并发线程执行模型截然不同，TPU v1 的控制器一次只发射一条 CISC 指令，每条指令包含一个或多个操作。5 条核心指令是：

| 指令类型 | 功能描述 |
|---------|--------|
| `Read_Host_Memory` | 从主机内存读取输入数据 |
| `Read_Weights` | 从权重 FIFO 读取权重 |
| `MatrixMultiply` | 执行 Systolic Array 矩阵乘法（卷积也由该指令表达） |
| `Activate` | 应用非线性激活函数（ReLU、Sigmoid 等） |
| `Write_Host_Memory` | 将结果写回主机内存 |
- 每条指令可以运行数百到数千个时钟周期，从而降低指令获取和译码的带宽开销。

### 2.4 外部存储接口

TPU v1 板载 **8GB DDR3 DRAM**，通过两个 DDR3 通道与芯片连接。对于 2015 年的标准，DDR3 的带宽（约 34 GB/s）远低于同时代 K80 使用的 GDDR5（约 480 GB/s），但 TPU v1 的 Systolic Array 设计使得它在推理场景中并不完全依赖高带宽——因为权重数据在片上被高度复用。

## 3. 性能表现

### 3.1 与 GPU 的对比

在 Google 的生产级 DNN 推理工作负载上，TPU v1 相比同时代的 GPU（如 NVIDIA K80）展现了显著的性能优势：

- **推理吞吐量**：TPU v1 在 INT8 精度下可达 92 TOPS（Tera Operations Per Second）；K80 的 FP32 峰值约 8.7 TFLOPS（双 GPU，2×4.37 TFLOPS）。按论文实测，TPU v1 相对 K80 的推理速度提升为 **15–30 倍**，相对 Haswell CPU 为 **30–80 倍**。
- **能效比**：TPU v1 的 TDP 约 75W（自然散热），而 K80 的 TDP 为 300W。因此，TPU v1 的每瓦性能（TOPS/W）比 K80/CPU 高出约 **30–80 倍**（不到两个数量级）。

### 3.2 生产环境表现

在 Google 的 RankBrain（搜索排序）和语音识别生产模型中，TPU v1 展示了以下性能数据：

| 模型类型 | 延迟 (TPU v1) | 延迟 (K80 GPU) | 吞吐量提升 |
|---------|--------------|---------------|-----------|
| MLP（RankBrain） | 0.4 ms | 7.2 ms | ~15× |
| LSTM（语音） | 0.6 ms | 20.3 ms | ~30× |
| CNN（图像） | 1.2 ms | 15.8 ms | ~13× |

值得注意的是，TPU v1 的加速比在小批次（batch size = 1）时最为显著，因为在推理场景中，低延迟往往是用户可见的关键指标，而 GPU 在小批次下的计算资源利用率较低。

## 4. 部署规模与影响

截至 2017 年，Google 已经在全球多个数据中心中部署了约 2,000 块 TPU v1 芯片。它们承载了 Google 搜索、RankBrain 排序、街景文字识别、以及 Google Play 和 YouTube 的推荐系统等大量生产流量。根据 Google 的估算，TPU v1 的使用使其推理计算的总拥有成本降低了约 10 倍。

## 5. 局限性

TPU v1 的主要局限性在于其**不支持训练**。训练需要：

1. **更高的数值精度**：反向传播的梯度幅度变化范围极大，INT8 的精度和动态范围不足以支持训练收敛；
2. **保存中间激活值**：反向传播需要前向传播时所有中间层的激活值来计算梯度，这对存储和带宽提出了更高要求；
3. **跨芯片同步**：分布式训练需要 All-Reduce 等跨节点通信原语，TPU v1 的 PCIe 拓扑未针对此优化。

这些局限性直接催生了 TPU v2 的设计——一个既能推理又能训练的新一代架构。

## 参考文献

1. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *Proceedings of the 44th Annual International Symposium on Computer Architecture (ISCA)*, 2017, pp. 1–12.
2. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *Communications of the ACM*, vol. 63, no. 7, 2020, pp. 67–78.
3. Norrie, T., et al. "The Design Process for Google's Training Chips." *IEEE Micro*, vol. 41, no. 2, 2021, pp. 56–63.
4. Patterson, D. A., et al. "A Case for Intelligent RAM." *IEEE Micro*, vol. 17, no. 2, 1997, pp. 34–44.
