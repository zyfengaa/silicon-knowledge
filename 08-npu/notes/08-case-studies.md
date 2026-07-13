# 神经网络处理器案例分析

## 引言

自2014年以来，学术界和工业界涌现了大量专用神经网络处理器（NPU）的设计。本章详细分析五款有代表性的NPU：DianNao系列、Eyeriss、Apple ANE、Qualcomm Hexagon和华为Ascend DaVinci。每款芯片代表了不同的设计哲学和应用场景。

## DianNao系列

DianNao由中国科学院计算技术研究所陈云霁、陈天石团队于ASPLOS 2014提出，是早期且影响力最大的深度学习加速器之一。

### 核心架构

DianNao的核心计算单元是**神经功能单元（Neural Functional Unit, NFU）**。NFU被设计为专门处理向量MAC（乘累加）操作的结构：

1. **乘法器树（Multiplier Tree）**：NFU包含一个 $N \times N$ 的乘法器阵列，每个时钟周期可以完成 $N^2$ 次乘法。
2. **加法器树（Adder Tree）**：乘法结果通过多级加法器累加，产生部分和。
3. **非线性函数单元**：支持ReLU、Sigmoid等激活函数。

NFU的计算过程可以表示为：

$$
\text{NFU}(x, w) = f\left(\sum_{i=1}^{N} \sum_{j=1}^{N} x_i \cdot w_j\right)
$$

### 存储系统

DianNao采用三级存储：

- **NBin（输入缓冲）**：16KB，缓存输入神经元。
- **NBout（输出缓冲）**：16KB，缓存输出神经元。
- **SB（突触权重缓冲）**：2KB × 6 banks。

另有64KB的**主存储**（Local Memory）。DianNao的设计团队认识到，权重和激活值的高效缓冲是降低能耗的关键——通过最大化片上数据的复用，将DRAM访问次数减少了一个数量级。

### 性能与影响

DianNao的完整设计（包括其多核变体DaDianNao和面向低功耗的ShiDianNao）证明了专用加速器可以在极小的面积和功耗下获得比GPU更高的能效。DaDianNao进一步采用eDRAM替代SRAM，在相同面积下提供更大的片上存储。

## Eyeriss

Eyeriss由MIT的Vivienne Sze、Yu-Hsin Chen团队提出（ISCA 2016），是继DianNao之后最具代表性的加速器设计之一。

### 行固定数据流

Eyeriss的核心创新是**行固定（Row-Stationary, RS）数据流**。其基本思想是将卷积计算调度到单个PE上处理**一行卷积窗口**。每个PE拥有自己的寄存器文件（RF），用于缓存权重、输入像素和部分和。

RS数据流的关键优势在于利用卷积的三个层次数据复用：

1. **权重复用**：同一卷积核在多PE间被重复使用。
2. **输入复用**：相邻卷积窗口的输入像素存在大量重合，通过PE之间的数据传递（而非从DRAM重新读取）实现复用。
3. **部分和累加**：部分和持续在PE本地累加，直到完成整个卷积窗口的计算才写回DRAM。

### 片上网络（NoC）

Eyeriss采用**层次化的片上网络（Network-on-Chip）**来管理PE之间的数据流动：

- **全局总线（Global Bus）**：管理全局缓冲（Global Buffer）到各列PE的数据分发。
- **行间总线（Inter-Row Bus）**：相邻行PE之间的数据传递通道，支持输入像素的行间漂移。

NoC的拓扑结构直接支持RS数据流的数据移动模式，避免了全局全互联的高功耗。

### 存储系统

Eyeriss的片上存储包括：

- **全局缓冲**：108KB SRAM（Eyeriss v1），在Eyeriss v2中扩展至512KB。
- **PE本地寄存器**：每个PE内的RF用于缓存当前计算所需的最小数据集。

Eyeriss v2（JSSC 2018）针对深度可分离卷积（Depthwise Separable Convolution）进行了优化，支持更灵活的数据流配置，并增加了对稀疏性的支持。

## Apple ANE（Apple Neural Engine）

Apple自A11 Bionic芯片（2017）起集成Neural Engine，到M系列芯片时已发展为16核心的高性能NPU。

### 架构特点

Apple ANE的设计哲学是**紧密集成在SoC中，与CPU和GPU共享统一内存**：

- **16核设计**：每个核心包含独立的计算单元和本地SRAM，核心间通过NoC连接。
- **INT8推理**：ANE主要支持INT8量化推理（A12及之后），单次推理的能效远高于GPU。
- **与Core ML深度绑定**：Apple的Core ML框架将模型自动转换为ANE可执行的格式，支持核心分配、内存预加载和算子拆分。

### 性能演进

| 芯片 | 核心数 | 峰值算力（TOPS） |
|------|-------|----------------|
| A11 | 2 | 0.6 |
| A12 | 8 | 5 |
| A14 | 16 | 11 |
| M1 | 16 | 11 |
| M2 Ultra | 32 | 31.6 |
| M4 | 16 | 38 |

ANE的显著特点是**每瓦性能（Performance per Watt）**极高。在M系列芯片中，ANE处理AI任务的能效是GPU的3-5倍，使其可以在设备端流畅运行复杂模型而不显著影响电池续航。

### 集成优势

ANE与Apple生态系统的深度集成体现在：

- 统一内存模型：ANE可以直接访问CPU/GPU的内存空间，无需显式拷贝。
- Metal Performance Shaders：统一后端调度。
- 安全隔区（Secure Enclave）集成：ANE可以处理Face ID等涉及隐私的推理任务。

## Qualcomm Hexagon DSP与HVX

Qualcomm Hexagon DSP最初设计为通用数字信号处理器，但自Snapdragon 820（2016）开始集成HVX（Hexagon Vector eXtensions）后，逐渐发展为专用的AI加速单元。

### HVX架构

HVX是Hexagon DSP的向量处理扩展，其核心技术参数如下：

- **1024bit向量长度**：每个时钟周期可并行处理32个32bit整数、64个16bit整数或128个8bit整数的运算。
- **标量+向量混合架构**：Hexagon有一个标量处理器（负责控制流和地址计算）和一个向量处理器（负责数据密集型计算）。两者并行工作，标量线程为向量线程预取数据。

HVX的向量加法指令可以形式化为：

$$
\vec{v}_{\text{out}} = \vec{v}_{a} + \vec{v}_{b}
$$

其中 $\vec{v}$ 是1024bit向量寄存器，当数据类型为INT8时，一次加法可处理128个元素。

### Snapdragon NPU

从Snapdragon 855开始，Qualcomm在Hexagon DSP基础上进一步集成了专用的AI加速单元（即Snapdragon NPU），具备：

- 专用的卷积引擎和激活引擎。
- HVX负责向量操作，NPU负责密集矩阵乘。
- 统一的Qualcomm Neural Processing SDK，支持TensorFlow、PyTorch、ONNX等框架。

### 应用场景

Hexagon HVX广泛应用于Android手机的**设备端推理**。其优势在于：

- 作为DSP功耗远低于GPU。
- 可以处理流媒体、相机拍照、语音识别等实时任务。
- 支持异构调度，根据任务特性灵活选择CPU/DSP/NPU/GPU。

## 华为Ascend DaVinci（达芬奇）架构

华为Ascend系列AI处理器（310/910）采用自研的**DaVinci架构**，是中国芯片公司在大算力AI加速器方向最重要的成果之一。

### 3D Cube引擎

DaVinci架构最独特的创新是**3D Cube计算单元**。传统矩阵乘硬件的核心是2D脉动阵列，而DaVinci提出了一种 $M \times N \times K$ 的立方体计算结构。

对于一个 $M \times K$ 的权重矩阵 $W$ 与一个 $K \times N$ 的输入矩阵 $A$ 的乘法：

$$
C_{M \times N} = W_{M \times K} \times A_{K \times N}
$$

在每个时钟周期，3D Cube引擎可以完成 $M \times N \times K$ 次乘法累加操作（假设 $M, N, K$ 分别为Cube的维度参数）。

在Ascend 910上，单个Cube引擎的规格为 $16 \times 16 \times 16$，即每个周期可完成4096次FP16 MAC操作。加上超频和并行机制，Ascend 910的峰值FP16算力可达256 TFLOPS。

### 整体架构

DaVinci架构的完整计算单元由三部分组成：

1. **Cube Unit**：负责密集矩阵乘，是算力的主要来源。
2. **Vector Unit**：处理向量级运算（激活函数、BatchNorm等），由多个SIMD处理器组成。
3. **Scalar Unit**：处理标量运算和控制流。

三种计算单元共享统一的寄存器文件和L1缓冲，实现了细粒度的指令级并行。

### 软件生态

Ascend平台配合**CANN（Compute Architecture for Neural Networks）**软件栈：

- **GE（图引擎）**：负责计算图优化和算子融合。
- **TBE（Tensor Boost Engine）**：自定义算子开发框架，支持DSL编写算子。
- **框架适配**：TensorFlow、PyTorch、MindSpore等框架通过CANN实现Ascend后端。

## 对比总结

| 芯片 | 计算单元 | 片上存储 | 数据流 | 目标场景 |
|------|---------|---------|-------|---------|
| DianNao | NFU | 44KB + 64KB | NBin/SB/out | 高能效推理 |
| Eyeriss | 168 PE | 108KB | Row-Stationary | 灵活CNN推理 |
| Apple ANE | 16核 | 共享SoC内存 | Core ML调度 | 设备端推理 |
| Hexagon HVX | 1024bit向量 | L1/L2 DSP | 标量+向量 | 嵌入式推理 |
| DaVinci | 3D Cube+Vec+Scalar | SRAM多层 | 3D Cube | 云端训练+推理 |

## 参考文献

1. Chen, T., et al. "DianNao: A Small-Footprint High-Throughput Accelerator for Ubiquitous Machine-Learning." ASPLOS 2014.
2. Chen, Y.-H., Krishna, T., Emer, J., & Sze, V. "Eyeriss: An Energy-Efficient Reconfigurable Accelerator for Deep Convolutional Neural Networks." ISCA 2016.
3. Chen, Y.-H., et al. "Eyeriss v2: A Flexible Accelerator for Emerging Deep Neural Networks." IEEE Journal of Solid-State Circuits (JSSC), 2018.
4. Apple Inc. "Apple Neural Engine." Apple Developer Documentation, 2020.
5. Qualcomm. "Qualcomm Hexagon DSP and HVX Architecture." Qualcomm Developer Network, 2017.
6. Liao, H., et al. "DaVinci: A Scalable Architecture for Neural Network Computing." IEEE Hot Chips Symposium, 2019.
7. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." ISCA 2017.
8. Sze, V., Chen, Y.-H., Yang, T.-J., & Emer, J. "Efficient Processing of Deep Neural Networks: A Tutorial and Survey." Proceedings of the IEEE, 2017.
9. Chen, Y., et al. "DaDianNao: A Machine-Learning Supercomputer." MICRO 2014.
10. Du, Z., et al. "ShiDianNao: Shifting Vision Processing Closer to the Sensor." ISCA 2015.
