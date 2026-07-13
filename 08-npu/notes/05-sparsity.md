# 深度神经网络中的权重稀疏性

## 概述

深度神经网络（DNN）在计算机视觉、自然语言处理等领域的成功伴随着巨大的计算和存储开销。模型压缩中的一个重要方向是利用权重稀疏性——即将部分权重设为0——来减少存储需求和计算量。然而，不同的稀疏化方式对硬件加速的影响差异巨大，需要仔细设计才能在真实芯片上获得吞吐提升。

## 非结构化剪枝

非结构化剪枝（Unstructured Pruning）是最直接的思路：训练完成后，将绝对值低于某个阈值的权重置零。这种方法由 Han 等人在 "Deep Compression"（2016）中系统提出，流程分为三步：训练 → 剪枝 → 再训练（fine-tune）。剪枝后的权重矩阵中，零元素的位置是**不规则且随机**的，不存在任何可预测的模式。

从数学上看，对于一个权重矩阵 $W \in \mathbb{R}^{m \times n}$，剪枝操作定义如下：

$$
W_{ij} = \begin{cases}
W_{ij}, & |W_{ij}| > \tau \\
0, & |W_{ij}| \leq \tau
\end{cases}
$$

其中 $\tau$ 是预设的阈值。实际中通常通过指定**稀疏度**（sparsity ratio，例如90%）来选择 $\tau$。

非结构化剪枝可以对每个权重独立决定是否保留，因此在相同精度损失下能达到最高的压缩率。然而，这种不规则性给硬件带来了严重挑战：

- **不规则的内存访问**：非零元素的位置不定，无法连续读取，需要复杂的索引机制（如坐标列表 COO、压缩稀疏行 CSR 格式）。
- **控制开销巨大**：乘累加（MAC）阵列的每个计算单元都需要判断当前数据是否为0，导致面积和功耗增加。
- **负载不均衡**：不同处理单元分到的非零权重数量可能相差悬殊，部分单元空闲等待。

在实际芯片上，非结构化稀疏性很难转化为真实的速度提升——即使90%的权重是0，由于上述开销，加速比可能只有2-3倍。

## N:M 结构化剪枝

为了兼顾压缩率和硬件友好性，研究者提出了结构化剪枝方法，其中 **N:M 模式**（每M个连续权重中恰好有N个非零）是最成功的实践之一。

NVIDIA Ampere 架构（GA100 GPU）原生支持 **2:4 结构化稀疏**：即每4个连续权重中恰好有2个非零。训练时先进行结构化感知训练（structure-aware training）：

1. 训练完整模型
2. 每4个权重为一组，保留绝对值最大的2个
3. 再训练恢复精度

推理时，硬件知道每4个权重中只有2个非零，因此可以设计**定制的数据路径**。具体而言，2:4稀疏的权重矩阵 $W_s \in \mathbb{R}^{m \times n}$（此时 $n$ 必须是4的倍数）可以通过压缩比2×的格式存储：

- 非零值数组：尺寸为 $m \times (n/2)$
- 索引元数据：每组4个位置用2bit编码，总大小为 $m \times (n/4) \times 2$ bit

与密集矩阵乘法的计算量 $O(mnk)$ 相比，2:4稀疏矩阵乘法的计算量为 $O(m(n/2)k)$，即减半。

## 零跳过（Zero-Skipping）

零跳过是一种在计算时动态跳过零值操作数的技术。其核心思想是：检测到乘累加器的输入为0时，直接跳过该次乘法并累加0。这听起来简单，但在硬件实现中存在以下问题：

- **检测开销**：每个乘法器前面都需要一个比较器来检测输入是否为0。在大型MAC阵列中，这会增加面积。
- **功耗不对称**：跳过操作节省动态功耗，但比较器本身消耗静态功耗，需要在设计中权衡。
- **数据路径复杂性**：非零值需要从稀疏存储格式中解包，额外的多路选择器会增加延迟。

实践中，零跳过多用于**激活值稀疏性**（由于ReLU产生的大量0激活）而非权重稀疏性，因为激活值的0通常是随机的，而权重剪枝倾向于产生结构化模式。

## Sparse Tensor Core

NVIDIA Ampere 架构中的 **Sparse Tensor Core** 是首个大规模支持结构化稀疏性的商业硬件单元。其工作原理可概括为：

1. **压缩存储**：权重在加载到寄存器时已经以2:4压缩格式存放。每个4元素组中只保留2个值及其2bit索引。
2. **解压与重排**：Tensor Core内部将压缩的权重组恢复为4元素向量，但只取非零部分进行计算。
3. **计算映射**：Sparse Tensor Core对非零权重和对应的激活值执行FP16/TF32矩阵乘法，得到2×的吞吐提升。

从数学上看，Sparse Tensor Core 计算的是：

$$
C = A \times \text{decompress}(W_s)
$$

其中 $W_s$ 是以2:4格式存储的稀疏权重。由于 $W_s$ 的压缩带来了2×的存储带宽节省和2×的乘法器有效利用率，理论上可以达到2×的吞吐提升。实际测量表明，在满足2:4稀疏条件的模型中（通过训练或剪枝后微调达到），Sparse Tensor Core 的加速比非常接近理论值2×。

## 其他稀疏硬件设计

除Ampere外，学术界和工业界还探索了多种稀疏加速方案：

- **Cambricon-X**（2016）：利用索引模块处理非结构化稀疏权重，为每个非零值配备索引标签。
- **EIE**（Han et al., 2016）：专为稀疏全连接层设计的加速器，采用压缩稀疏列格式（CSC）存储权重。
- **Sparse CNN 优化**：通过位掩码（bitmask）标记非零位置，在脉动阵列中跳过零值计算。

这些方案在特定场景下能取得可观加速，但由于灵活性不足或开销过大，尚未像Sparse Tensor Core那样被广泛采纳。

## 总结

权重稀疏性是神经网络加速中的重要研究方向。非结构化剪枝可以最大化压缩比，但硬件加速困难；结构化剪枝（尤其是N:M模式）在精度可接受的前提下提供了明确的硬件友好路径。Sparse Tensor Core的成功表明，算法与硬件协同设计是稀疏加速的关键——硬件提供对特定稀疏模式的原生支持，算法则通过训练和剪枝适配该模式。

## 参考文献

1. Han, S., Mao, H., & Dally, W. J. "Deep Compression: Compressing Deep Neural Networks with Pruning, Trained Quantization and Huffman Coding." ICLR 2016.
2. NVIDIA. "NVIDIA A100 Tensor Core GPU Architecture." Whitepaper, 2020.
3. Han, S., et al. "EIE: Efficient Inference Engine on Compressed Sparse Neural Network." ISCA 2016.
4. Zhu, M., et al. "Sparse Tensor Core: Algorithm and Hardware Co-Design for Efficient Sparse Neural Networks." SC 2020.
5. Zhang, S., et al. "Cambricon-X: An Accelerator for Sparse Neural Networks." MICRO 2016.
6. Gale, T., et al. "The State of Sparsity in Deep Neural Networks." arXiv:1902.09574, 2019.
7. Mishra, A., et al. "Accelerating Sparse Deep Neural Networks." arXiv:2104.08378, 2021.
