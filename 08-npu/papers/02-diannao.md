# DianNao: A Small-Footprint High-Throughput Accelerator for Machine Learning

> **文献信息**
> - 会议：MICRO (International Symposium on Microarchitecture), 2014
> - 作者：Tianshi Chen, Zidong Du, Ninghui Sun, Jia Wang, Chengyong Wu, Yunji Chen, Olivier Temam
> - 机构：中国科学院计算技术研究所、INRIA
> - 引用：Chen T, Du Z, Sun N, et al. DianNao: A small-footprint high-throughput accelerator for ubiquitous machine learning[C]//Proceedings of the 19th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS). ACM, 2014. (注：该文发表于ASPLOS'14，但在MICRO系列中也常被引用，其姊妹篇在MICRO发表)。

---

## 一、动机与背景

2014年前后，机器学习（尤其是深度神经网络）在语音识别、图像理解等领域的应用正从云端向终端设备渗透。然而，当时的CPU和GPU在运行神经网络推理时面临两难：CPU能效不足，且通用计算架构中存在大量非计算开销（指令取指、译码、乱序执行等）；GPU功耗过高，难以用于移动设备或嵌入式场景。此外，学术界已有的神经网络加速器研究大多针对特定网络结构（如全连接网络）或过于简化，缺乏对真实大规模神经网络（包含卷积、池化等多种层类型）的全面支持。

DianNao团队提出的核心问题是：**能否设计一种专用加速器，在极小的芯片面积和功耗预算下，达到与高端GPU相当的神经网络推理性能？** 论文的标题"Small-Footprint High-Throughput"精准概括了这一目标——既要面积小、功耗低，又要吞吐量高。

DianNao是"电脑"（computer）的中文音译，也是该加速器家族（DianNao、DaDianNao、ShiDianNao、PuDianNao）的第一代产品。这一系列工作代表了中国学术机构在神经网络加速器领域的开创性贡献，对后续NPU设计产生了深远影响。

---

## 二、NFU（Neural Functional Unit）架构

DianNao的核心创新是**神经功能单元（Neural Functional Unit, NFU）**，这是一个专门为神经网络层计算量身定制的流水线计算单元。NFU的设计摒弃了传统处理器中的通用计算范式，直接面向神经网络的计算模式。

### NFU的流水线结构

NFU分为三个流水级，每一级对应神经网络层中的一个核心操作：

1. **第一级：乘法器阵列**。接收输入神经元和突触权重，执行逐元素乘法。这一级包含了若干并行乘法器，其数量由设计参数决定（DianNao的原型中为16个）。

2. **第二级：加法树（Adder Tree）**。将第一级的乘法结果累加，生成神经元的加权和。加法树采用二叉树结构，延迟为O(log n)，面积效率高。

3. **第三级：非线性函数单元（Non-linear Unit）**。对加法树的结果应用非线性函数（如sigmoid、tanh、ReLU等）。这一级通过查找表（LUT）或分段线性逼近实现。

NFU的三个流水级可以有效地处理全连接层（单个向量点积）和卷积层（多路乘法并行），同时也支持池化操作（通过旁路乘法器级）。

### 多lane并行计算

DianNao设计了三条并行计算lane，每条lane包含一个NFU。三条lane可以同时处理不同的输入数据，例如：
- 对全连接层：三条lane并行计算三个不同输入神经元的加权和。
- 对卷积层：三条lane并行计算三个不同输出通道的部分和。

设计者通过理论分析表明，三条lane是面积效率（area efficiency）和计算吞吐量的最佳平衡点。增加lane数量虽然能提升吞吐量，但存储器和互连的面积增长更快，导致整体面积效率下降。

---

## 三、存储层次设计

DianNao在存储层次上采用了精心设计的结构，以缓解"存储墙"问题。芯片上集成了**44KB的片上SRAM**，分为三个缓冲区：

1. **NBin（Neural Input Buffer）**：输入神经元缓冲区，大小为16KB，用于缓存当前层的输入特征图数据。由于卷积和全连接层都存在输入复用（同一个输入被多个卷积核使用），NBin的命中率对性能至关重要。

2. **SB（Synapse Buffer）**：突触权重缓冲区，大小为16KB，用于缓存神经网络权重。权重在层内是固定的（weight stationary），因此SB的设计优先级最高——尽量减少从片外DRAM读取权重的次数。

3. **NBout（Neural Output Buffer）**：输出神经元缓冲区，大小为12KB，用于暂存部分和和最终输出结果。部分和在片内累积完成后，批量写回片外DRAM。

### 存储层次的工作流程

一个典型的神经网络层执行过程如下：
1. 从片外DRAM将权重预加载到SB。
2. 从片外DRAM将输入特征图加载到NBin（可分批加载，NBin的大小决定了每个批次能处理的数据量）。
3. NFU从NBin和SB读取数据，进行计算，将部分和写入NBout。
4. 当NBout中累积完成一个完整的输出特征图时，写回DRAM。

这种"double buffering"（双缓冲）机制可以使计算和数据加载重叠，隐藏DRAM访问延迟。论文的实验表明，在大多数层中，DianNao的计算单元利用率达到90%以上，远高于GPU在相同负载下的利用率。

---

## 四、性能评估与对比

DianNao在65nm工艺下进行了综合评估，主要结果如下：

### 性能

- **峰值性能**：在1GHz频率下，DianNao达到452 GOPS（使用16位定点精度）。这是理论峰值，实际应用中的性能取决于存储器带宽和层配置。
- **实际性能**：在代表性神经网络（如卷积神经网络和深度信念网络）上实测，平均达到峰值性能的60%-80%。

### 对比GPU（NVIDIA K20M）

DianNao在以下几个维度上与K20M GPU（当时的高端计算GPU）进行了对比：
- **吞吐量**：DianNao的吞吐量约为K20M的21倍（归一化到相同功耗），但由于K20M的功耗远高于DianNao，这一结果主要反映了能效的优势。
- **面积**：DianNao的核心面积为3.02mm²（不含DRAM控制器等I/O），远小于K20M的约561mm²。
- **功耗**：DianNao的功耗约0.485W，而K20M的TDP为225W。

### 能效优势的来源

DianNao之所以能实现如此高的能效，核心原因在于两点：
1. **消除了指令开销**：NFU直接硬连线实现神经网络计算，没有取指、译码、寄存器重命名等指令开销。
2. **数据本地化**：44KB的片上SRAM使得大部分数据访问不需要到片外DRAM，大幅降低了数据搬运能耗。设计还对数据复用的模式做了针对性优化（如权重的多播）。

---

## 五、DianNao家族的发展

DianNao是"寒武纪"（Cambricon）系列加速器的第一代，后续相继发表了多个变体：

### DaDianNao（MICRO 2014）

DaDianNao是大规模的DianNao，针对服务器端数据中心场景。核心改进包括：
- **分布式存储**：使用eDRAM代替SRAM作为主要存储介质，在相同面积下提供更大的存储容量（片上总存储达36MB）。
- **多节点架构**：支持多个DianNao核心通过片上网络互连，实现大规模的神经网络计算。
- **性能**：在28nm工艺下，DaDianNao达到约5.6 TOPS的峰值性能，功耗约15W。

DaDianNao的本质思路是"用更大的片上存储减少DRAM访问"——训练和推理中的大部分数据停留在大容量的eDRAM中，不再频繁访问片外DRAM。

### ShiDianNao（ISCA 2015）

ShiDianNao是针对视觉应用的极低功耗加速器，目标是直接与CMOS图像传感器集成。核心特征：
- **无DRAM**：整个网络的全部数据都存储在片上SRAM中（总容量约28KB），彻底消除了DRAM访问能耗。
- **近传感器计算（near-sensor processing）**：加速器直接放在传感器旁边甚至在传感器芯片上，最小化数据传输距离。
- **功耗**：在65nm工艺下仅约0.32mW，足以支持电池供电的微型设备。

ShiDianNao展示了当数据完全本地化时，能耗可以比DianNao再降低两个数量级。

### PuDianNao（ASPLOS 2015）

PuDianNao是面向多种机器学习算法的通用加速器（不限于神经网络），支持k-means、SVM、决策树、朴素贝叶斯等传统算法。其核心思想是识别这些算法的共性计算模式（如循环嵌套、归约操作），设计可重配置的计算单元。

---

## 六、思考与启示

1. **专用化的驱动力**：DianNao的成功表明，在计算模式高度统一的领域（如神经网络），专用加速器可以在面积和能效上比通用处理器提升2-3个数量级。

2. **存储是第一位的**：DianNao家族的每一代都是以存储层次设计为核心——从44KB SRAM到36MB eDRAM再到零DRAM——数据搬运的优化始终是关键。

3. **学术与产业的双向影响**：DianNao系列是中科院计算所在AI芯片领域的标志性成果，催生了寒武纪科技（Cambricon Technologies）的创业公司。这些工作在学术论文和商业芯片之间架起了桥梁。

4. **局限性**：DianNao主要针对推理，不支持训练（尤其是反向传播中的梯度计算）；定点精度在训练场景中需要谨慎处理；对新兴网络结构（如Transformer注意力机制）的支持有限。

---

## 参考文献

1. Chen T, Du Z, Sun N, et al. DianNao: A small-footprint high-throughput accelerator for ubiquitous machine-learning[C]//Proceedings of the 19th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS). ACM, 2014: 269-284.

2. Chen Y, Luo T, Liu S, et al. DaDianNao: A machine-learning supercomputer[C]//2014 47th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO). IEEE, 2014: 609-622.

3. Du Z, Fasthuber R, Chen T, et al. ShiDianNao: Shifting vision processing closer to the sensor[C]//Proceedings of the 42nd Annual International Symposium on Computer Architecture (ISCA). ACM, 2015: 92-104.

4. Liu D, Chen T, Liu S, et al. PuDianNao: A polyvalent machine learning accelerator[C]//Proceedings of the 20th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS). ACM, 2015: 369-381.

5. Liu S, Du Z, Tao J, et al. Cambricon: An instruction set architecture for neural networks[C]//2016 ACM/IEEE 43rd Annual International Symposium on Computer Architecture (ISCA). IEEE, 2016: 393-405.

6. Zhang S, Du Z, Zhang L, et al. Cambricon-X: An accelerator for sparse neural networks[C]//2016 49th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO). IEEE, 2016: 1-12.
