# 03 — 将大矩阵乘映射到固定尺寸脉动阵列

## 问题定义

实际的神经网络矩阵尺寸远大于硬件脉动阵列的物理尺寸。例如，Google TPU v1 拥有 128×128 的脉动阵列，但需要计算的矩阵可能是 1024×1024 甚至更大。如何将大矩阵乘高效地映射到固定尺寸的阵列上，是 NPU 架构设计中的核心问题。

## Tiling（分块）策略

给定矩阵乘 $C = A \times B$，其中 $A \in \mathbb{R}^{M \times K}$，$B \in \mathbb{R}^{K \times N}$，输出 $C \in \mathbb{R}^{M \times N}$。

若脉动阵列的尺寸为 $S_r \times S_c$，我们将输出矩阵 $C$ 划分为大小为 $S_r \times S_c$ 的 tile：

$$
C_{ij} = \sum_{t=0}^{K/S_t - 1} A_{i,t} \times B_{t,j}
$$

其中 $i \in [0, M/S_r)$，$j \in [0, N/S_c)$，$t \in [0, K/S_t)$。

### 分块维度选择

- **$S_r$ 和 $S_c$**：由脉动阵列的物理尺寸决定。TPU v1 使用 128×128，即每块覆盖 128 行和 128 列的输出。
- **$S_t$**：即 K 维度上的分块大小，取决于片上缓冲区容量。更大的 S_t 意味着更少的 DRAM 访问，但需要更大的缓冲区。

### 分块执行流程

1. **权重预加载阶段**：将 $A_{i,t}$ 的分块加载到脉动阵列的每个 PE 中
2. **计算阶段**：从左侧输入 $B_{t,j}$ 的对应分块，PE 沿垂直方向传递部分和
3. **累积阶段**：累加不同 t 分块的结果，必要时将中间结果写回 DRAM
4. **输出阶段**：完整的 $C_{ij}$ 计算完成后，输出到 DRAM

## 示例：128×128 阵列处理 1024×1024 矩阵乘

假设 $M=N=K=1024$，脉动阵列为 $S_r=S_c=128$，$S_t=128$：

- 输出矩阵 $C$ 被划分为 $(1024/128) \times (1024/128) = 8 \times 8 = 64$ 个 tile
- 每个 tile 需要 K/S_t = 1024/128 = 8 轮累积
- 总计算轮次：64 × 8 = 512
- 每轮每个 PE 执行一次乘加

### PE 利用率分析

在每次分块计算中：

- 所有 $S_r \times S_c = 16384$ 个 PE 均被使用
- 当 $M$ 不是 $S_r$ 的整数倍时，边缘 PE 会出现空闲
- 当 $N$ 不是 $S_c$ 的整数倍时，部分输出统计会被浪费
- 最优情况下 $M \% S_r = 0$ 且 $N \% S_c = 0$

## 权重预加载和计算阶段的详细流程

### 权重固定（WS）模式下的映射

1. **预加载**：将 $A_{ij}$ 的分块写入 PE 的权重寄存器（每个 PE 一个权重）
2. **输入流**：从左侧逐列输入 $B$ 矩阵的分块
3. **部分和传递**：PE 将乘加结果（部分和）传递给下方的 PE
4. **输出收集**：阵列下方的累加器收集最终结果

### 边界条件处理

当矩阵尺寸不是阵列尺寸的整数倍时：

- 在边缘行/列使用掩码，禁用参与无效计算的 PE
- 或者在预加载阶段写入零权重，使得无效 PE 输出零

## 内存层次与数据移动调度

分块策略直接影响 DRAM 访问次数：

- 每个权重元素被复用 $S_c$ 次（被同一行的所有 PE 共享）
- 每个输入元素被复用 $S_r$ 次（通过所有行的 PE 传递）
- 最优分块使数据重用最大化

TPU v1 的 28MB 统一缓冲区（Unified Buffer）可以容纳整个 128×128 脉动阵列的权重和中间激活，使得大多数推理模型可以在不上 DRAM 的情况下完成计算。

## 参考文献

- Jouppi, N. et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *ISCA'17*.
- Chen, Y.H. et al. "Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow for Convolutional Neural Networks." *ISCA'16*.
- Kung, H.T. "Why Systolic Architectures?" *IEEE Computer*, 1982.
- Sze, V. et al. "Efficient Processing of Deep Neural Networks: A Tutorial and Survey." *Proceedings of the IEEE*, 2017.
