# TPU 核心架构：MXU、HBM、统一内存与指令集

## 概述

TPU（Tensor Processing Unit）的核心架构围绕着一个大规模二维脉动阵列（Systolic Array）——即矩阵乘法单元（MXU, Matrix Multiply Unit）——进行设计。围绕 MXU，TPU 还集成了向量处理单元（Vector Unit）、高带宽内存（HBM）以及由编译器管理的片上存储层次。这套架构的核心哲学是：针对深度学习中占主导地位的矩阵乘法运算进行极致优化，牺牲通用性换取单位功耗和单位面积下的最高吞吐量。

## MXU：脉动阵列矩阵乘法单元

### 基本原理

MXU 的核心是一个二维的乘累加单元阵列（PE, Processing Element），数据以脉动（systolic）方式在阵列中流动。以 TPU v1 为例，其 MXU 大小为 $256 \times 256$，即包含 65,536 个 PE。每个 PE 执行一个乘加操作 $D = D + A \times B$。

矩阵乘法 $C = A \times B$ 的计算过程如下。假设 $A \in \mathbb{R}^{M \times K}$ 和 $B \in \mathbb{R}^{K \times N}$，MXU 将结果按 $256 \times 256$ 的块（tile）分块处理。数据流为：

$$
C_{ij} = \sum_{k=1}^{K} A_{ik} B_{kj}
$$

- **A 矩阵**的行数据从左侧逐行流入阵列
- **B 矩阵**的列数据从上方逐列流入阵列
- 每个 PE 在上方和左方各有一个输入寄存器，一个乘加器，以及一个累加寄存器
- 权重在 PE 内驻留，激活沿行方向传播，部分和沿列方向传播

在 TPU v1 中，一条 MXU 操作指令可以指令阵列执行 $256 \times 256 \times 256$ 的矩阵乘法，即一次性完成 $256^3 = 16,777,216$ 次乘加运算。这充分体现了 TPU 指令集的 CISC 特性——一条指令覆盖上千万次运算。

### TPU v2/v3+ 的 MXU 演进

TPU v2/v3 每个 MXU 仍为 $128 \times 128$（16,384 个 PE），但 v2 每芯片有 2 个 MXU、v3 每芯片有 4 个 MXU。到 TPU v4/v5p，单个 MXU 仍是 $128 \times 128$（16,384 个 PE），变化的是芯片内的数量与组织方式：每芯片包含 **2 个 TensorCore**，每个 TensorCore 集成 **4 个 MXU**，即每芯片 **8 个 MXU、$8 \times 16{,}384 = 131{,}072$ 个 MAC**。单个 MXU 扩大到 $256 \times 256$ 要到 v6e（Trillium）。与此同时，TPU v2 引入了 BF16（Brain Floating Point 16）数据类型的原生支持，相比 v1 的 INT8，BF16 具有更大的动态范围，更适合训练场景（训练时累积精度保持 FP32）。

> MXU 的乘加器位宽在流片时固定，这是 TPU 用 INT8/BF16/FP8 划分代际的根本原因。精度与执行单元的完整关系见 [06-12 精度与硬件](../../06-GPU架构/notes/12-precision-hardware.md)。

从 v2 到 v5p，MXU 的基本结构保持不变，但阵列的利用率（utilization）、时钟频率、数据搬运路径等都得到了持续优化。

### 关于“16 个周期”的口径

一个常见的误读是把 $128^3$ 矩阵乘的芯片级聚合吞吐当成单块阵列的延迟。单个 $128 \times 128$ 的 MXU 每周期执行 $128 \times 128 = 16{,}384$ 次 MAC（输出 tile 的每个元素累加一项），完成 $K=128$ 的归约需要 **128 个周期**。只有把一个芯片的 8 个 MXU 全部用于互不相同的输出块时，整芯片每周期才完成 $131{,}072$ 个 MAC；此时 $128^3 = 2{,}097{,}152$ 次 MAC 在理想情况下才表现为 $2{,}097{,}152 / 131{,}072 = 16$ 个周期的**聚合吞吐**。这 16 个周期是芯片级吞吐的等效值，**不是**单个 $128 \times 128$ 阵列完成一次 $128^3$ 计算所需的延迟（后者为 128 个周期）。

## 向量处理单元（Vector Unit）

TPU 的向量处理单元负责所有非矩阵运算，包括：

- **激活函数**: ReLU, GeLU, Sigmoid 等逐元素运算
- **归一化**: BatchNorm, LayerNorm
- **逐元素运算**: 加法、乘法、减法
- **Reduce 操作**: 求和、最大值、最小值
- **内存搬运**: 统一内存与 MXU 之间的数据传输

向量单元的宽度与对应 MXU 的列数匹配（v1 为 256；v2/v3/v4/v5p 每个 MXU 为 128；v6e 及之后为 256），这使得向量操作和矩阵操作之间能够无缝衔接。例如，完成一次 MXU 矩阵乘法后，结果直接送入向量单元进行 ReLU 激活，整个过程在芯片内部完成，无需经过片外内存。

## 高带宽内存（HBM）

HBM（High Bandwidth Memory, 高带宽内存）是 TPU 的主存储器。HBM 将多个 DRAM 裸晶通过硅通孔（TSV, Through-Silicon Via）垂直堆叠，并放置在靠近计算芯片的同一封装基板上（如 CoWoS 封装技术），从而大幅缩短了内存与计算单元之间的物理距离。

TPU 各代 HBM 配置：

| 代际 | HBM 类型 | 容量 | 带宽 |
|------|----------|------|------|
| v1 (2015) | DDR3 (非 HBM) | 8 GB | ~34 GB/s |
| v2 (2017) | HBM | 16 GB | ~600 GB/s |
| v3 (2018) | HBM | 32 GB | ~900 GB/s |
| v4 (2022) | HBM2e | 32 GB | ~1.2 TB/s |
| v5p (2023) | HBM3 | 95 GiB | ~2,765 GB/s |

巨大的内存带宽对于 TPU 至关重要——MXU 的计算吞吐量极高，必须持续不断地从内存中读取权重和激活值才能保持满负荷运转。以 v4 为例，每个芯片的峰值计算吞吐量约为 275 TFLOPS（BF16），对应的数据搬运需求为每秒 TB 级别，没有 HBM 是无法满足的。

## 编译时内存管理（不是“统一内存/零拷贝”）

TPU 通过 XLA/HLO 编译器在设备 HBM 内做编译时内存管理：编译器在编译阶段计算每个张量的生命周期、访问模式和依赖关系，从而在 HBM 中高效地分配和回收内存。这与 GPU 的运行时分配/显存管理不同，但**并不意味着主机内存与 TPU HBM 是统一的**。与 GPU 类似，主机侧内存和 TPU 侧 HBM 仍然分离，模型和数据需要经 PCIe（v1）或主机接口传输；跨 host/device 的“零拷贝”并不成立。

具体实现上，这种编译时内存管理的优势在于：

1. **减少碎片**: 编译器拥有完整的全局信息，可以打包分配内存，避免运行时的内存碎片问题
2. **减少片上冗余拷贝**: 数据在 MXU 和向量单元之间通过片上互联直接传递，不需要落回 HBM
3. **预取优化**: 编译器可以提前发出内存加载指令，隐藏 HBM 的延迟

## TPU 指令集：CISC 风格

TPU 的指令集架构（ISA）具有鲜明的 CISC（复杂指令集计算机）特征。一条 TPU 指令可以触发数千甚至数万次运算。主要的指令类型包括：

1. **MXU 操作**: 启动一次矩阵乘法（v1 为 $256 \times 256$；v2/v3/v4/v5p 每个 MXU 为 $128 \times 128$，其中 v4/v5p 每芯片 8 个 MXU；v6e 为 $256 \times 256$），将结果写入累加器
2. **向量操作**: 对向量寄存器文件进行操作，如激活、归一化、类型转换
3. **内存操作**: 在片上缓冲/寄存器文件与 HBM 之间搬运数据
4. **控制流**: 条件分支、循环控制

例如，一条典型的卷积层处理流水线为：

```
LOAD_WEIGHTS  weight_ptr -> MXU_Accum        # 将权重加载到 MXU 累加器
LOAD_INPUTS   input_ptr  -> MXU_Input        # 将输入加载到 MXU 输入寄存器
MXU_MATMUL    0, N                              # 执行 N 次矩阵乘法
VECTOR_ACT    MXU_Output -> ReLU              # 对输出应用 ReLU
STORE_OUTPUT  VectorReg -> output_ptr         # 将结果写回 HBM
```

这种指令设计大幅减少了指令获取和解码的开销——每次 MXU 操作执行后，结果直接通过片上通道传递给向量单元，所有中间结果都在芯片内部流动，避免了对 HBM 的带宽消耗。

## MXU 与向量单元的数据流接口

MXU 与向量单元之间通过一组专用的高速 FIFO 缓冲区连接。MXU 运算完成后，其累加寄存器的值通过 Reduce 树汇合并传递到向量单元的输入寄存器文件（Vector Register File, VRF）。向量的结果又可以直接写回到 MXU 的累加寄存器，形成计算流水线。这种紧耦合设计使得卷积和 Transformer 中的密集计算模式能在芯片内部高效完成。实际利用率随模型形状、batch size、内存带宽和编译质量变化；在部分 dense GEMM/卷积层可以接近峰值，但不应笼统声称“通常超过 80%”。

## 参考文献

1. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." Proceedings of the 44th Annual International Symposium on Computer Architecture (ISCA '17), ACM, 2017.
2. Jouppi, N. P., et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." Communications of the ACM, Vol. 63 No. 7, 2020 (originally ISCA '18).
3. Norm Jouppi. "Google's Tensor Processing Units: From ASICs to Supercomputers." Hot Chips 33, 2021.
4. Jouppi, N. P., et al. "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings." Proceedings of the 50th Annual International Symposium on Computer Architecture (ISCA '23), 2023.
5. Lee, J., et al. "HBM: High-Bandwidth Memory." IEEE Micro, 2015.
6. Google Cloud. "Cloud TPU System Architecture." Google Cloud Documentation, 2024. https://cloud.google.com/tpu/docs/system-architecture
