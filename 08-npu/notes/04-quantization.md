# 神经网络量化：原理、方法与硬件支持

## 1. 为什么需要量化？

### 1.1 模型规模的压缩

现代大规模神经网络——特别是大语言模型——的参数量已达到千亿甚至万亿级别。模型权重通常以FP32格式存储（每个参数4字节），这意味着一个175B参数的GPT-3模型仅权重就需要约700GB的存储空间。通过量化到INT8格式，可以将模型大小压缩4倍至约175GB；若量化到INT4格式，则可再压缩至约87.5GB。这种压缩带来的直接好处是：

1. **降低显存需求**：更多的模型参数可以装入单个加速器，减少跨设备的模型并行开销。
2. **加速推理**：更少的数据搬运意味着更低的I/O延迟。
3. **降低部署成本**：可以使用更少或更低端的硬件来完成推理任务。

### 1.2 带宽瓶颈的缓解

在神经网络推理中，**内存带宽是比计算能力更稀缺的资源**。以A100 GPU为例，其FP16计算能力为312 TFLOPS，而HBM2e内存带宽仅为2 TB/s。这意味着每个加载到寄存器中的FP16数值只有约6.5次计算机会——超过此值，计算核心就会因等待数据而处于空闲状态。将数据从FP32/FP16压缩到INT8，相当于将有效带宽提升了2-4倍，直接缓解了"内存墙"问题。

### 1.3 高效整数运算的优势

现代NPU的核心理念之一就是用**专用的整数算术单元**替代通用的浮点算术单元：

- INT8乘法器的硅面积约为FP32乘法器的 $\frac{1}{18}$（Horowitz, 2014）；
- INT8乘加运算的能耗约为FP32的 $\frac{1}{18}$；
- 在相同的芯片面积预算下，可以部署更多的INT8计算单元，从而实现更高的峰值吞吐。

## 2. 均匀量化（Uniform Quantization）的数学原理

### 2.1 仿射量化（Affine Quantization）

最常见的量化方案是仿射均匀量化（也称为非对称量化）。给定浮点数 $r$，量化后的整数 $q$ 通过以下变换得到：

$$
q = \text{round}\left(\frac{r}{\Delta}\right) + Z
$$

其中 $\Delta$ 是缩放因子（scale），$Z$ 是零点偏移（zero-point）。反量化过程为：

$$
r \approx \Delta \cdot (q - Z)
$$

缩放因子 $\Delta$ 由量化范围决定。对于b-bit量化：

$$
\Delta = \frac{\max(r) - \min(r)}{2^b - 1}
$$

零点的计算方式为：

$$
Z = \text{round}\left(-\frac{\min(r)}{\Delta}\right)
$$

对称量化是仿射量化的特例，其 $Z = 0$，缩放因子为 $\Delta = \frac{2 \cdot \max(|r|)}{2^b - 2}$。对称量化的优点在于计算时无需处理零点偏移，简化了硬件实现。

### 2.2 量化误差分析

量化过程引入的误差可以分解为两部分：

1. **舍入误差**：由 $\text{round}$ 操作引起，最大误差为 $\frac{\Delta}{2}$，均匀分布在 $[-\frac{\Delta}{2}, \frac{\Delta}{2}]$ 区间内。
2. **截断误差**：当浮点值超出量化范围 $[\min(r), \max(r)]$ 时发生——超出范围的值被截断为最近的量化边界值。

对于权重和激活值呈正态分布或拉普拉斯分布的典型场景，**截断误差的影响通常远大于舍入误差**（Zhao et al., 2019）。这是因为分布的尾部（outliers）虽然概率低，但值很大，如果直接使用 $\min(r)$ 和 $\max(r)$ 来确定量化范围，会导致 $\Delta$ 过大，从而大幅增加舍入误差。

## 3. 校准方法（Calibration Methods）

校准是指在使用前确定量化参数（$\Delta$ 和 $Z$）的过程。校准需要通过少量校准数据集（通常为几百到几千个样本）来统计张量的分布特征。

### 3.1 Min-Max校准

**方法**：直接使用校准数据中观察到的最大值和最小值设定量化范围。

$$
\Delta = \frac{r_{\max} - r_{\min}}{2^b - 1}
$$

**优点**：实现简单，计算开销低，保证所有值都在量化范围内（无截断误差）。

**缺点**：对异常值极其敏感。如果校准集中出现一个异常的极大值（统计上的离群点），整个量化范围被迫扩大，导致所有其他值的分辨率大幅下降。在实际部署中，由于校准集通常远小于训练集，Min-Max校准往往会过度估计真实的数据范围。

### 3.2 百分位校准（Percentile Calibration）

**方法**：不使用绝对最大值，而是使用某个百分位数的值作为量化边界。例如，99.9%分位数：

$$
r_{\max} = \text{Percentile}(r, 99.9\%), \quad r_{\min} = \text{Percentile}(r, 0.1\%)
$$

**优点**：对离群点具有鲁棒性。如果最大值是极端离群点，使用99.9%分位数可以将其排除在量化范围之外，从而保留更多精度给主要数据分布。

**缺点**：排除离群点意味着这些离群值会被截断。对于某些对离群值敏感的层（如softmax之前的全连接层输出），截断可能导致准确率显著下降。

### 3.3 KL散度校准（KL Divergence Calibration）

**方法**：选择量化范围使得量化后的分布与原始浮点分布之间的KL散度（Kullback-Leibler Divergence）最小化。KL散度的定义为：

$$
D_{KL}(P \parallel Q) = \sum_{i} P(i) \log \frac{P(i)}{Q(i)}
$$

其中 $P$ 是原始浮点值的分布（直方图），$Q$ 是量化后的分布。KL散度校准通过贪心搜索寻找最优截断阈值 $T$：

$$
T^* = \arg\min_{T} D_{KL}(P_T \parallel Q_T)
$$

**计算步骤**：
1. 将浮点值范围划分为2048个bins，统计直方图；
2. 对于每个候选阈值 $T$（对应直方图中的一个bin），将 $[-T, T]$ 范围外的值全部映射到边界；
3. 将 $[-T, T]$ 内的 $N$ 个bins合并为128个量化区间；
4. 计算原始分布与量化后分布的KL散度；
5. 选择使KL散度最小的阈值 $T$。

**优点**：在理论上最优地平衡了舍入误差和截断误差。TensorRT和许多工业级部署框架都采用KL散度作为默认校准方法。

**缺点**：计算复杂度高（需要扫描多个候选阈值），且依赖于校准数据的代表性。

## 4. 量化感知训练（Quantization-Aware Training, QAT）

### 4.1 基本思想

后训练量化（Post-Training Quantization, PTQ）虽然简便，但在低比特（如4-bit或以下）时往往导致显著的准确率下降。量化感知训练通过将量化噪声**模拟到训练过程中**，使网络权重自适应地调整，从而在高压缩率下保持准确率。

### 4.2 Fake-Quantization操作

QAT的核心是Fake-Quantization操作——在网络前向传播中模拟量化-反量化过程，但在反向传播中保持梯度为浮点数：

$$
\hat{r} = \Delta \cdot \text{round}\left(\frac{\text{clip}(r, \min, \max)}{\Delta}\right)
$$

其中 $\text{clip}$ 函数将值限制在量化范围内。

反向传播时，使用**直通估计器（Straight-Through Estimator, STE）**来近似round函数的梯度：

$$
\frac{\partial \hat{r}}{\partial r} \approx 1 \cdot \mathbb{1}_{\min \leq r \leq \max}
$$

即，在量化范围内将round函数视为恒等映射，在范围外梯度为零。

### 4.3 QAT的训练流程

1. **预训练**：使用FP32训练一个基线模型，达到目标准确率。
2. **注入量化节点**：在每个权重点和激活点之后插入Fake-Quantization节点。
3. **微调**：使用小学习率（约为初始学习率的$\frac{1}{10}$到$\frac{1}{100}$）继续训练若干epoch，让网络适应量化噪声。
4. **冻结量化参数**：停止更新$\Delta$和$Z$。
5. **转换**：从训练图中移除Fake-Quantization节点，导出纯INT8计算图用于推理。

## 5. 浮点量化格式：BF16与FP8

### 5.1 BF16（Brain Floating Point 16）

BF16由Google Brain团队提出，专为深度学习设计。其格式如下：

- 符号位：1 bit
- 指数位：8 bit
- 尾数位：7 bit

BF16的关键特性是**指数位宽与FP32相同（8位）**。这意味着BF16可以表示的数值范围（动态范围）与FP32完全相同：

$$
\text{BF16最小值} = \pm 2^{-126} \approx \pm 1.18 \times 10^{-38}
$$
$$
\text{BF16最大值} = \pm 2^{127} \times (2 - 2^{-7}) \approx \pm 3.39 \times 10^{38}
$$

BF16的精度（约7位有效数字）低于FP16（约10位有效数字）——因为尾数只有7位而非10位。但在深度学习中，**动态范围比精度更重要**。原因在于：

- 梯度在反向传播中可能跨越多个数量级（从$10^{-8}$到$10^2$），需要宽动态范围防止下溢/上溢。
- 训练过程中，学习率和正则化项引入的数值变化需要大的指数空间。

BF16的前向和反向精度已足够支持绝大多数深度学习训练的收敛。据Google的实测报告，BF16训练在BERT、ResNet-50等模型中可以达到与FP32训练几乎完全一致的收敛曲线（Wang et al., 2018）。

### 5.2 FP8（8-bit Floating Point）

FP8是近年来业界标准化的8-bit浮点格式，包含两种变体：

**FP8 E4M3**：
- 符号位：1 bit
- 指数位：4 bit
- 尾数位：3 bit
- 可表示的最大值：$2^{7} \times (2 - 2^{-3}) = 448$
- 最小正常值：$2^{-6} = 1.56 \times 10^{-2}$
- 精度：约1位有效数字

**FP8 E5M2**：
- 符号位：1 bit
- 指数位：5 bit
- 尾数位：2 bit
- 可表示的最大值：$2^{15} \times (2 - 2^{-2}) = 57344$
- 最小正常值：$2^{-14} = 6.10 \times 10^{-5}$
- 精度：约0.6位有效数字

两者的区别体现了**动态范围与精度之间的折中**：

- E4M3具有更高的精度（3位尾数），适合表示权重和激活值（分布相对集中）；
- E5M2具有更大的动态范围（5位指数），适合表示梯度（分布更分散，可能存在离群值）。

NVIDIA的H100 GPU首次在硬件层面原生支持FP8计算，使用E4M3表示前向计算的权重和激活值，使用E5M2表示反向传播的梯度。据NVIDIA的报告，FP8混合精度训练在LLaMA、BERT等模型上可以匹配FP16/BF16的训练精度（Micikevicius et al., 2022）。

### 5.3 量化格式的应用场景总结

| 格式 | 比特数 | 典型范围 | 主要应用 | 硬件支持 |
|------|--------|----------|----------|----------|
| INT8  | 8   | $[-128, 127]$ 或 $[0, 255]$ | 推理 | 几乎所有NPU和现代GPU |
| INT4  | 4   | $[-8, 7]$ 或 $[0, 15]$ | 极致压缩推理 | 部分NPU（如Apple Neural Engine） |
| BF16  | 16  | $\pm 3.4 \times 10^{38}$ | 训练 | TPU v2+, A100+ GPU |
| FP16  | 16  | $\pm 6.55 \times 10^4$ | 训练（早期方案） | Volta+ GPU |
| FP8 E4M3 | 8 | $[-448, 448]$ | 推理和训练前向 | H100+ GPU |
| FP8 E5M2 | 8 | $[-57344, 57344]$ | 训练反向传播 | H100+ GPU |

## 6. 量化对NPU架构设计的影响

NPU架构设计者在量化方面面临以下关键决策：

1. **支持的精度格式**：现代NPU需要同时支持INT8、INT4、BF16等多种格式。不同格式之间的切换需要支持不同位宽的数据路径和多模式MAC单元。
2. **累加器位宽**：INT8乘加操作需要足够宽的累加器防止溢出。业界共识是使用INT32累加器。对于4-bit量化，INT16累加器通常足够。
3. **量化参数的在线更新**：在动态量化（如每token、每channel的量化）中，缩放因子和零点需要在线计算并广播到所有PE，这增加了控制逻辑的复杂性。
4. **混合精度调度**：网络的不同层可能需要不同的量化精度。NPU编译器需要支持逐层或逐操作粒度的精度配置。

## 参考文献

1. Jacob, B., et al. "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference." *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*, 2018.

2. Micikevicius, P., et al. "FP8 Formats for Deep Learning." *arXiv preprint arXiv:2209.05433*, 2022.

3. Wang, S., et al. "Mixed Precision Training of Deep Neural Networks with the Brain Floating Point (BF16) Format." *arXiv preprint arXiv:1808.07596*, 2018.

4. Horowitz, M. "Computing's Energy Problem (and what we can do about it)." *IEEE International Solid-State Circuits Conference (ISSCC) Digest of Technical Papers*, 2014.

5. Zhao, R., et al. "Improving Neural Network Quantization without Retraining using Outlier Channel Elimination." *arXiv preprint arXiv:1907.09605*, 2019.

6. Gholami, A., et al. "A Survey of Quantization Methods for Efficient Neural Network Inference." In *Low-Power Computer Vision*, Chapman and Hall/CRC, 2022.

7. Krishnamoorthi, R. "Quantizing Deep Convolutional Networks for Efficient Inference: A Whitepaper." *arXiv preprint arXiv:1806.08342*, 2018.

8. Banner, R., Hubara, I., Hoffer, E., & Soudry, D. "Scalable Methods for 8-bit Training of Neural Networks." *Advances in Neural Information Processing Systems (NeurIPS)*, 2018.

9. Nagel, M., et al. "A White Paper on Neural Network Quantization." *arXiv preprint arXiv:2106.08295*, 2021.
