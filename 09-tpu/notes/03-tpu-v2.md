# TPU v2：从推理迈向训练

## 1. 从推理到训练——架构变革的驱动力

TPU v1 的巨大成功让 Google 认识到定制 ASIC 在 AI 推理中的价值。然而，Google 的 AI 工作负载中训练的计算量增长更加迅猛。从 2013 年到 2016 年，Google 用于训练的算力需求每年增长约 10 倍。传统的 GPU 集群在训练效率上虽优于 CPU，但依然存在成本高昂、能效比不足的问题。

因此，Google 于 2015 年启动了 TPU v2 的设计工作，目标是创建**业界首款可训练深度神经网络的专用 ASIC 加速器**。TPU v2 于 2017 年部署至 Google 数据中心，首次以**训练能力**作为核心设计目标。

## 2. 训练所需的架构变革

### 2.1 BFLOAT16 浮点格式

TPU v2 最关键的创新之一是引入了 **BFLOAT16（Brain Floating Point 16）** 浮点格式。与其说这是一种新的浮点数标准，不如说它是 FP32 的**截断版本**：BF16 使用 8 位指数和 7 位尾数，与 FP32 共享相同的 8 位指数范围，但尾数部分从 23 位缩减到 7 位。

$$
\begin{aligned}
\text{FP32:} &\quad 1 \text{ bit sign} + 8 \text{ bits exponent} + 23 \text{ bits mantissa} \\
\text{BF16:}  &\quad 1 \text{ bit sign} + 8 \text{ bits exponent} + 7 \text{ bits mantissa}
\end{aligned}
$$

BF16 与 FP32 的**动态范围完全相同**（$2^{-126}$ 到 $2^{127}$），这使得训练过程中梯度幅度的巨大变化可以被准确表示。相比之下，传统的 FP16（IEEE 754 半精度）仅有 5 位指数，动态范围远小于 BF16，在训练的早期阶段常因梯度下溢而导致收敛失败。

BF16 的引入使得 TPU v2 既可以获得 FP16 的数据存储效率（每个数值仅占 2 字节），又可以保留 FP32 的训练鲁棒性。在 Google 的实验中，大多数模型使用 BF16 训练的收敛曲线与 FP32 几乎完全一致。

### 2.2 核心架构改变

与 TPU v1 的推理专用设计相比，TPU v2 的架构发生了根本性的变化：

**（1）矩阵乘法单元（MXU）**

TPU v2 的 Systolic Array（在 Google 的术语中称为 MXU）尺寸从 v1 的 128×128 改为 128×128，但支持 BF16 输入和 FP32 累加：

$$
\text{MXU 计算:}\quad C_{ij} += \sum_{k=0}^{127} A_{ik} \cdot B_{kj},\quad A_{ik}, B_{kj} \in \mathbb{B}_{16},\; C_{ij} \in \mathbb{F}_{32}
$$

每个 MXU 在每个周期执行 $128 \times 128 = 16,384$ 次 BF16 乘加运算，在 700 MHz 频率下提供约 $16,384 \times 700 = 11.5$ TFLOPS 的峰值性能。每个 TPU v2 芯片包含 **两个核心（core）**，每个核心包含一个 MXU，因此单芯片峰值性能约为 **23 TFLOPS**（BF16）。

然而，实际训练时的有效性能约为 180 TFLOPS——这说明 TPU v2 的 BF16 运算采用了"脉动复用量化"（Systolic Quantization）技术：每个 MXU 在一个 728 MHz 周期内实际上执行了多个低精度运算，芯片厂商未公开具体倍率。

**（2）SRAM 容量翻倍**

每个 TPU v2 核心配备 16MB 的软件管理片上 SRAM（v1 整个芯片为 28MB），两个核心合计 32MB。SRAM 的增加来自于训练需要存储更多中间激活值以支持反向传播的计算。

**（3）HBM 高带宽内存**

TPU v2 采用 **HBM（High Bandwidth Memory）** 取代了 v1 的 DDR3，每个核心连接 8GB HBM（两个核心共 16GB），总带宽约 600 GB/s 以上。HBM 是训练中不可或缺的组件，因为批量训练需要频繁地将中间激活值写回 DRAM，等反向传播时再读回。

### 2.3 反向传播支持

训练的核心与前向推理的单一数据流不同，它包含**前向传播—反向传播—权重更新**三阶段循环。TPU v2 的硬件设计专门为这个三阶段循环进行了优化：

- **前向传播**：输入数据经过 MXU 和各层的 Activation 计算，生成输出和中间激活值。中间激活值存储到 HBM 中供后续反向传播使用。
- **反向传播**：从最后一层的损失函数开始，误差梯度逐层反向传播（通过 MXU 计算 $\partial L / \partial W_{ij} = \sum \delta_i \cdot a_j$）。这一计算同样是矩阵乘法，可在 MXU 上高效执行。
- **权重更新**：根据计算出的梯度更新权重：$W := W - \eta \cdot \nabla L$。权重更新的计算量相对于前向和反向传播较小，由核心的标量处理器执行。

### 2.4 分布式训练与 All-Reduce

TPU v2 首次引入了**跨芯片互联网络**以支持分布式训练。每个芯片通过专用的高速互联与相邻芯片连接，形成 **2D torus 拓扑**。在 TPU v2 中，64 个芯片组成一个"pod"（部署在四个 4×4 阵列的机架中），通过芯片间互联实现高效的 All-Reduce 通信。

All-Reduce 操作对分布式训练至关重要。在数据并行训练中，每个芯片独立计算本地的梯度，然后需要将所有芯片的梯度求和后再更新每个芯片的权重副本。TPU v2 的 2D torus 拓扑使得 All-Reduce 可以在硬件层面高效完成：

$$
\bar{g} = \frac{1}{N} \sum_{i=1}^{N} g_i
$$

其中 $g_i$ 是第 $i$ 个芯片的本地梯度。TPU v2 将 All-Reduce 的计算完全卸载到互联网络硬件中，避免了 CPU host 介入的通信瓶颈。

## 3. 冷却系统

TPU v2 的 TDP 相对于 v1 大幅增加（单芯片约 200–250W），简单的自然散热或风冷已经无法满足。因此，TPU v2 的 pod 采用了**水冷**散热方案。每个机架配备冷却液分配单元，通过冷板直贴芯片的方式带走热量。对于 v2，仅部分高负载配置（64-chip pod）使用了水冷，而较小的部署仍可使用风冷。

## 4. 性能对比

在 Google 的基准测试中，TPU v2 运行 ResNet-50 模型的训练吞吐量达到了如下水平：

| 配置 | 吞吐量 (images/sec) |
|-----|-------------------|
| 1 chip | ~220 |
| 64-chip pod | ~11,500 |
| 对比 GPU (单卡 K80) | ~70 |

TPU v2 展示了在可训练专用加速器领域的技术可行性。它证明了定制 ASIC 不仅在推理中具有优势，在训练场景下同样能够获得比通用 GPU 更好的性能和效率。

## 参考文献

1. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *Proceedings of the 45th Annual International Symposium on Computer Architecture (ISCA)*, 2018, pp. 1–14.
2. Wang, S., and Kanwar, P. "BFloat16: The Secret to High Performance on Cloud TPUs." *Google Cloud Blog*, 2019.
3. Burgess, N., et al. "BFloat16 Processing for Neural Networks." *IEEE Symposium on Computer Arithmetic (ARITH)*, 2019, pp. 88–95.
4. Koster, U., et al. "Flexpoint: An Adaptive Numerical Format for Efficient Training of Deep Neural Networks." *Advances in Neural Information Processing Systems (NeurIPS)*, 2017, pp. 1742–1752.
