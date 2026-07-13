# 片上存储系统与数据流调度

## 存储层次与能耗差异

在深度神经网络加速器的设计中，存储系统是决定能效和性能的核心因素之一。现代计算系统中存在明显的**存储层次**：寄存器（Register File）→ 片上SRAM缓存（On-chip SRAM Buffer）→ 片外DRAM（如HBM、DDR4）。各层级之间的能耗差距极大。

Horowitz (2014) 及后续研究给出了一组被广泛引用的能耗数据（以45nm CMOS工艺、32bit浮点操作为基准）：

| 操作 | 能耗（pJ） | 相对代价 |
|-----|-----------|---------|
| 32bit INT MAC | 3.2 | 1× |
| 32bit SRAM 读（8KB） | 5 | ~1.6× |
| 32bit SRAM 读（32KB） | 10 | ~3× |
| 32bit DRAM 读 | 640 | ~200× |

从表中可以直观看到：**一次DRAM访问的能耗大约是一次SRAM访问的50-100倍**，更是一次MAC运算的200倍。这构成了神经网络加速器设计的基本约束：**减少DRAM访问是降低功耗最有效的途径**。

考虑到数据搬运（data movement）在推理总能耗中占比超过80%（据NVIDIA和Google的多份报告），如何通过片上存储系统最大化数据复用、最小化片外访问，就成为了NPU架构设计的首要问题。

## 片上SRAM缓冲区的作用

片上SRAM缓冲区位于计算阵列和片外DRAM之间，扮演着**数据暂存与重用的枢纽角色**。其作用包括：

1. **输入特征图缓冲**：对于卷积层，输入特征图（Input Feature Map, IFMap）会被多个卷积核反复使用。将IFMap加载到片上缓冲区后，可以在单次访存后完成多次乘累加。
2. **权重缓冲**：权重参数可以被批次内的多个输入样本复用。尤其在批量推理场景中，权重缓冲能将带宽需求降低数个数量级。
3. **部分和（Partial Sum）缓冲**：卷积运算中间累加结果需要暂存。K×K卷积核的结果需要在Psum缓冲中累积K²次再写回DRAM。

不同设计的缓冲区大小差异很大：

- **DianNao**（Chen et al., 2014）：采用44KB的片上SRAM（NBin：输入缓冲16KB，NBout：输出缓冲16KB，SB：权重缓冲2KB，以及额外的NFU内部寄存器）。这一设计证明了即使在小缓冲区下，通过精心设计的数据流也能获得可观能效。
- **Eyeriss**（Chen et al., 2016）：采用108KB的片上SRAM（分为全局缓冲和行缓冲两级），支撑其**行固定（Row-Stationary）**数据流。更大的缓冲区允许更灵活的数据复用策略。
- **TPU v1**（Jouppi et al., 2017）：拥有28MB的统一SRAM缓冲区（称为统一缓冲UF），服务于256×256的脉动阵列。28MB足以容纳ResNet-50的中间激活数据，使整个推理过程无需回写DRAM。

从44KB到28MB的增长反映了设计权衡：更大的缓冲区减少DRAM访问，但增加芯片面积和SRAM泄漏功耗。最优值取决于目标模型的激活尺寸、权重尺寸和批量大小。

## 数据流调度策略

数据流调度（Dataflow Scheduling）决定了计算过程中数据在各个存储层次之间的移动顺序和复用模式。以下是三种经典的数据流：

### 1. 权重复用（Weight Stationary）

权重加载到片上缓冲区后保持不变，输入特征图依次流过。适合权重尺寸适中、而输入特征图按批次变化的场景。脉动阵列（Systolic Array）天然支持权重复用。

### 2. 输入复用（Input Stationary）

输入特征图驻留在片上，权重按需加载。适合输入特征图尺寸小（如深度可分离卷积的逐点卷积）的情况。Eyeriss的设计支持输入复用模式。

### 3. 输出复用（Output Stationary / Row-Stationary）

部分和在片上累加，减少对DRAM的读写压力。**行固定（Row-Stationary）**是Eyeriss提出的核心创新：

- 基本调度单元是**一行卷积窗口**的数据。
- 每个PE处理一组特定的输入行和权重，在本地累加部分和。
- 通过NoC（Network-on-Chip）在不同PE之间传递部分和。

行固定数据流利用卷积的空间局部性：相邻滑动窗口之间存在大量重叠的输入行，通过在PE之间移动而非从DRAM重新读取，可以大幅降低DRAM带宽需求。

### 数据复用层次

Raghunathan等将CNN中的数据复用归纳为三个层次：

1. **卷积复用**：同一卷积核在输入图的多个位置滑动，权重被多次使用。
2. **特征图复用**：同一输入特征图被多个卷积核处理，输入像素被多次读取。
3. **批量复用**：同一权重在同一批次的不同输入样本之间复用。

数据流调度的目标就是最大化这三个层次的复用，使尽可能多的数据访问发生在片上SRAM级别。

## 现代设计中的存储系统

近年来，随着模型规模和计算需求的增长，存储系统设计出现了几个新趋势：

- **多级缓冲层次**：在全局SRAM和PE本地寄存器之间增加中间缓冲（如TPU v2/v3的向量存储器）。
- **存储与计算的紧耦合**：将SRAM分布在计算单元附近（near-memory computing 的片上版本），缩短数据路径。
- **HBM的采用**：从TPU v2开始采用HBM作为主存储器，提供高带宽（600-900 GB/s）但仍需要通过SRAM缓冲来减少频繁访问。
- **模型驱动的缓冲区规划**：在编译器中静态分析模型，为每层分配最优的SRAM分区和调度策略（如TVM中的AutoTVM）。

## 总结

片上SRAM缓冲是NPU存储层次的核心。其设计需要在面积、功耗和DRAM访问频率之间进行精细平衡。数据流调度决定了SRAM的使用效率，而不同的数据流策略（权重复用、输入复用、输出行复用）适用于不同的模型特征。良好的存储系统设计是实现高能效AI推理的关键。

## 参考文献

1. Chen, Y.-H., Krishna, T., Emer, J., & Sze, V. "Eyeriss: An Energy-Efficient Reconfigurable Accelerator for Deep Convolutional Neural Networks." ISCA 2016.
2. Chen, Y.-H., Krishna, T., Emer, J., & Sze, V. "Eyeriss v2: A Flexible Accelerator for Emerging Deep Neural Networks." IEEE Journal of Solid-State Circuits (JSSC), 2018.
3. Chen, T., et al. "DianNao: A Small-Footprint High-Throughput Accelerator for Ubiquitous Machine-Learning." ASPLOS 2014.
4. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." ISCA 2017.
5. Horowitz, M. "Computing's Energy Problem (and what we can do about it)." ISSCC 2014.
6. Sze, V., Chen, Y.-H., Yang, T.-J., & Emer, J. "Efficient Processing of Deep Neural Networks: A Tutorial and Survey." Proceedings of the IEEE, 2017.
7. Rahimian, A., et al. "Improving Energy Efficiency of Convolutional Neural Networks: A Survey." ACM Computing Surveys, 2020.
