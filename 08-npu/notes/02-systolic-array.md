# 脉动阵列（Systolic Array）：NPU的核心计算引擎

## 1. 脉动阵列的基本概念

### 1.1 历史起源

脉动阵列（Systolic Array）的概念由卡内基梅隆大学的H. T. Kung于1982年在其经典论文"Why Systolic Architectures?"中正式提出。Kung类比了人体心脏的脉动供血系统：心脏通过有节律的搏动将血液泵送到全身每个细胞，而脉动阵列则通过有节律的数据流将数据"泵送"到阵列中的每个处理单元（Processing Element, PE）。在这一比喻中，数据扮演"血液"的角色，PE扮演"细胞"的角色，而全局时钟或握手信号则扮演"心跳"的角色。

Kung提出脉动阵列的核心动机是解决**I/O瓶颈问题**。在传统的冯·诺依曼架构中，数据必须在内存和处理器之间反复搬运，而处理器的计算速度远高于内存的访问速度——这就是所谓的"存储墙（Memory Wall）"问题。脉动阵列通过让数据在相邻PE之间直接流动，使得每次从内存读取的数据可以被多个PE重复使用，从而极大地降低了对内存带宽的需求。

### 1.2 脉动阵列的数学本质

脉动阵列的本质可以理解为**空间上的流水线**。在传统的时间流水线中，不同的计算阶段在同一个处理单元上按时间顺序执行；而在空间流水线中，不同的计算阶段被映射到不同的PE上，数据在PE之间流动的同时完成计算。

更形式化地，脉动阵列满足以下特性：

1. **局部通信**：每个PE仅与相邻的PE直接连接（左、右、上、下），不存在全局广播或多跳连接。
2. **规则性**：阵列中所有PE的结构相同或遵循简单的重复模式。
3. **同步性**：所有PE在统一的时钟控制下同步工作（经典脉动阵列）或通过握手信号协调（异步脉动阵列）。
4. **数据流规律**：数据以固定的方向和速率在阵列中流动。

## 2. 一维脉动阵列：向量点积与FIR滤波器

### 2.1 基本结构

一维脉动阵列是将PE排列成一条线性链。每个PE包含一个乘法器和一个累加器（Multiply-Accumulate, MAC）。一维脉动阵列最经典的应用是计算两个向量的点积以及有限冲激响应（FIR）滤波器。

### 2.2 向量点积的计算流

考虑两个长度为 $N$ 的向量 $\mathbf{a} = [a_0, a_1, ..., a_{N-1}]$ 和 $\mathbf{b} = [b_0, b_1, ..., b_{N-1}]$，其点积为：

$$
\mathbf{a} \cdot \mathbf{b} = \sum_{i=0}^{N-1} a_i \cdot b_i
$$

在一维脉动阵列上计算点积的一种典型调度方式如下：

1. **权重预加载**：将向量 $\mathbf{b}$ 的各个元素 $b_i$ 预先加载到对应的PE $i$ 中（权值固定）。
2. **输入流推送**：向量 $\mathbf{a}$ 的元素从阵列的一端依次送入，每个时钟周期前进一个PE。
3. **部分和流动**：部分和寄存器初始化为0，从阵列的另一端流入，每个PE将自身的输入数据与权重相乘后累加到部分和上。

具体而言，在时钟周期 $t$，PE $i$ 执行的计算为：

$$
p_i^{(t)} = p_{i-1}^{(t-1)} + a_{i-t}^{(t)} \cdot b_i
$$

其中 $p_i^{(t)}$ 是PE $i$ 在周期 $t$ 输出的部分和，$a_{i-t}^{(t)}$ 是到达PE $i$ 的输入元素。经过 $N$ 个周期后，阵列末端的PE输出即为完整的点积结果。

### 2.3 FIR滤波器

FIR滤波器的计算与向量点积本质相同：

$$
y_n = \sum_{i=0}^{N-1} h_i \cdot x_{n-i}
$$

其中 $h_i$ 为滤波器系数（对应权重），$x_n$ 为输入序列。一维脉动阵列天然支持这一计算模式——系数 $h_i$ 静止在各自的PE中，输入序列 $x_n$ 流经阵列，输出序列 $y_n$ 在阵列末端产生。

## 3. 二维脉动阵列：矩阵乘法

### 3.1 计算二维矩阵乘法的经典映射

二维脉动阵列将PE排列成 $M \times N$ 的网格。考虑矩阵乘法 $\mathbf{C} = \mathbf{A} \times \mathbf{B}$，其中 $\mathbf{A} \in \mathbb{R}^{M \times K}$，$\mathbf{B} \in \mathbb{R}^{K \times N}$，$\mathbf{C} \in \mathbb{R}^{M \times N}$。

Google TPU v1中采用的就是二维脉动阵列。其计算过程可以直观地描述如下：

令阵列大小为 $256 \times 256$，共65536个PE。矩阵 $\mathbf{A}$ 的元素从阵列左侧流入（每行一个元素），矩阵 $\mathbf{B}$ 的元素从阵列上方流入（每列一个元素）。每个PE $[i,j]$ 的功能是：

1. 接收左侧PE传来的 $a_{ik}$ 值；
2. 接收上方PE传来的 $b_{kj}$ 值；
3. 计算 $a_{ik} \times b_{kj}$ 并累加到内部寄存器；
4. 将 $a_{ik}$ 传递给右侧的PE $[i, j+1]$；
5. 将 $b_{kj}$ 传递给下方的PE $[i+1, j]$。

经过 $K$ 个周期后，每个PE $[i,j]$ 中的累加值即为 $c_{ij} = \sum_{k=0}^{K-1} a_{ik} \cdot b_{kj}$。

### 3.2 处理单元（PE）的内部结构

每个PE的微架构包含以下关键组件：

1. **乘法器（Multiplier）**：执行定点或浮点乘法运算。在INT8精度下，乘法器面积仅约 $400 \ \mu m^2$（7nm工艺），功耗约 $0.2 \ \text{pJ}$。
2. **累加器（Accumulator）**：一个寄存器和一个加法器组成的反馈环路。累加器的位宽通常高于输入数据位宽，以防止溢出——例如，对INT8输入使用INT32累加器。
3. **数据路径多路选择器**：控制数据的流入方向和来源，支持不同的数据流模式。
4. **本地寄存器文件**：在Weight Stationary模式中用于存储权重，或在Input Stationary模式中存储激活值。

## 4. 三种数据流模式及其比较

数据流（Dataflow）决定了在计算过程中哪一类数据保持在PE内部、哪一类数据在PE之间流动。Eyeriss（Chen et al., 2016）系统地分析了三种数据流模式的特点。

### 4.1 权值固定（Weight Stationary, WS）

**工作机制**：每个PE加载一组权重并将其固定在内部寄存器中。输入的激活值（activations）在阵列中流动，部分和也在PE之间传递。

**优点**：
- 权重的数据重用最大化——每个权重只从全局缓冲区加载一次，随后在所有输入数据上重复使用；
- 特别适合卷积层，因为卷积核的权重在整张特征图上共享；
- 由于权重固定，权重的更新（如训练场景）需要额外支持。

**缺点**：
- 输入数据和部分和都需要在PE之间传递，两者同时流动可能导致数据冲突；
- 在深度可分离卷积等结构中，每次仅计算很少的权重通道，WS模式的效率下降。

### 4.2 输入固定（Input Stationary, IS）

**工作机制**：每个PE固定一个输入激活值，权重和部分和在阵列中流动。

**优点**：
- 输入激活值的重用最大化——每个输入激活值只需从DRAM加载一次；
- 对于输入通道数较多但输出通道数较少的情况表现良好；
- 适合ReLU等就地激活函数后的层。

**缺点**：
- 权重需要频繁流动，若权重重用因子低，会导致大量数据搬运能耗；
- 部分和的数据流动路径与权重流动路径重叠，增加了路由复杂度。

### 4.3 输出固定（Output Stationary, OS）

**工作机制**：每个PE固定一个输出像素的部分和（即输出通道上某个空间位置的结果），权重和输入数据都流经PE。

**优点**：
- 部分和的流动最小化——每个输出元素的累加在同一PE内完成，无需将部分和传递给其他PE；
- 减少了部分和寄存器文件的读写次数，从而降低能耗；
- 部分和精度可以保持较高（宽累加器），只在最终写回时才进行精度转换。

**缺点**：
- 权重和输入数据都需要全局分发，对片上互连带宽要求高；
- 输出通道数较少时，OS模式的利用率可能下降。

### 4.4 三种数据流的定量对比

Eyeriss的分析表明（基于65nm工艺），在典型卷积层配置下：

| 数据流模式 | 每次MAC的DRAM访问（字节） | 每次MAC的SRAM访问（字节） | 每次MAC的RF访问（字节） | 相对能耗 |
|-----------|--------------------------|--------------------------|--------------------------|---------|
| WS        | 0.05                     | 1.5                      | 4.0                      | 1.0x    |
| IS        | 0.06                     | 2.0                      | 3.5                      | 1.2x    |
| OS        | 0.07                     | 1.8                      | 3.0                      | 1.1x    |

需要注意的是，上述对比高度依赖于具体的网络层参数和阵列尺寸。实际设计中选择哪种数据流，需要根据目标工作负载的特征进行**设计空间探索（Design Space Exploration）**。Eyeriss架构的一个关键创新就是支持数据流的运行时配置，使其可以根据不同卷积层的特点动态切换。

## 5. 脉动阵列的优缺点总结

### 优势

1. **I/O需求极低**：每个PE只与相邻PE通信，消除了全局总线的带宽瓶颈。
2. **高度规则**：PE阵列的规则结构使其易于VLSI实现，时钟树平衡、布线和功耗分析都相对简单。
3. **可扩展**：阵列尺寸可以随工艺节点迁移自然扩展。
4. **高吞吐**：所有PE在每个时钟周期同时工作，可实现极高的计算吞吐。

### 局限性

1. **负载不均**：在矩阵边界处，部分PE可能因缺少输入数据而空闲（edge idling）。
2. **灵活性受限**：脉动阵列针对规律的数据流优化，处理不规则计算（如稀疏矩阵、动态路由）时效率低。
3. **数据流固定**：一旦芯片设计定型，数据流的方式就基本固定，难以适应新型网络结构的计算需求。
4. **控制简单但数据搬运复杂**：虽然PE的控制逻辑简单，但如何在正确的时间将正确的数据送到正确的PE位置（即数据映射问题）具有较高的编译复杂度。

## 参考文献

1. Kung, H. T. "Why Systolic Architectures?" *IEEE Computer*, 15(1):37-46, 1982.

2. Chen, Y.-H., Krishna, T., Emer, J., & Sze, V. "Eyeriss: An Energy-Efficient Reconfigurable Accelerator for Deep Convolutional Neural Networks." *Proceedings of the 43rd Annual IEEE/ACM International Symposium on Computer Architecture (ISCA)*, 2016.

3. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *Proceedings of the 44th Annual International Symposium on Computer Architecture (ISCA)*, 2017.

4. Kung, H. T., & Leiserson, C. E. "Systolic Arrays (for VLSI)." *Sparse Matrix Proceedings*, SIAM, 1978.

5. Sze, V., Chen, Y.-H., Yang, T.-J., & Emer, J. S. "Efficient Processing of Deep Neural Networks: A Tutorial and Survey." *Proceedings of the IEEE*, 105(12), 2017.

6. Chen, T., et al. "DianNao: A Small-Footprint High-Throughput Accelerator for Ubiquitous Machine-Learning." *Proceedings of the 19th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*, 2014.

7. Horowitz, M. "Computing's Energy Problem (and what we can do about it)." *IEEE International Solid-State Circuits Conference (ISSCC) Digest of Technical Papers*, 2014.
