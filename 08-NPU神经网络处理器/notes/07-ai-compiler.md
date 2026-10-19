# AI编译器：从模型图到机器码

## 引言

随着深度学习模型结构的日益复杂（Transformer、MoE、Diffusion等），手工编写高性能算子已经无法满足多样化的硬件需求。AI编译器应运而生，其核心使命是：**将高级神经网络模型定义自动转换为高效的目标代码**，适配不同的硬件目标（GPU、NPU、TPU等）。

## AI编译器的通用流水线

现代AI编译器通常遵循一条通用的编译流水线（Pipeline），分为四个主要阶段：

### 1. 高层图中间表示（High-Level Graph IR）

输入的模型（如PyTorch的`torch.nn.Module`或TensorFlow的GraphDef）首先被转换为**计算图**，图的节点为算子（Conv2D、ReLU、Add等），边为数据依赖关系。高层IR保留了原始模型的张量形状和数据类型信息，方便进行全局优化。

此阶段的主要优化包括：
- **算子融合（Operator Fusion）**：将多个连续算子合并为一个内核，减少中间结果的DRAM读写。典型例子是将 Convolution + BatchNorm + ReLU 融合为一个算子。
- **常量折叠（Constant Folding）**：对编译时可静态确定的常量表达式预先求值。
- **死代码消除（DCE）**：移除计算图中不影响最终输出的节点。
- **公共子表达式消除（CSE）**：重用相同的计算结果。

### 2. 算子降低（Operator Lowering）

高层算子被分解为更细粒度的操作，以暴露底层硬件的优化机会。例如，一个卷积算子可以被降低为：

$$
\text{Conv2D}(X, W) \rightarrow \text{im2col}(X) \rightarrow \text{GEMM}(X_{\text{col}}, W_{\text{col}})
$$

即通过 im2col 将卷积转换为通用矩阵乘法（GEMM）。这种降低虽然增加了操作数，但可以复用高度优化的 BLAS 库。

对于专用硬件（如TPU或NPU），降低过程还包括：
- 将浮点运算替换为量化 INT8/TF32 运算。
- 将算子拆分为多个硬件支持的原语（如矩阵乘 + 向量加法）。

### 3. 内存规划（Memory Planning）

给定计算顺序后，编译器需要决定每个张量在内存中的位置和生命周期。这类似于传统编译器中的寄存器分配。关键任务包括：

- **张量生存期分析**：确定每个中间张量从创建到最后一次使用之间的运算范围。
- **内存别名**：当两个张量的生存期不重叠时，可以复用同一块内存空间。
- **片内/片外决策**：对于有片上SRAM的NPU，编译器需要判断哪些张量应常驻在片上，哪些应放在片外DRAM。

内存规划的目标是最大化片上复用，最小化片外数据搬运。以一个卷积层为例：

$$
\text{DRAM\_bytes} = \text{bytes\_ifmap} + \text{bytes\_weight} + \text{bytes\_psum\_write} + \text{bytes\_psum\_read}
$$

优秀的内存规划可以消除 $\text{bytes\_psum\_write}$ 和 $\text{bytes\_psum\_read}$，即部分和全程在片上累加完成，不写回DRAM。

### 4. 代码生成（Code Generation）

最后一个阶段将已调度和优化的IR转换为目标硬件的可执行代码。对于GPU，这通常是PTX/CUDA代码；对于CPU，是LLVM IR或原生指令；对于专用NPU，则是设备厂商的自定义指令集（ISA）。

## 主流AI编译器

### TVM：端到端深度学习编译器

由华盛顿大学陈天奇等人开发，发表于OSDI 2018。TVM的核心创新包括：

**Relay IR**：TVM的高层图IR。Relay是一种函数式中间表示，支持控制流、递归、ADT（代数数据类型）等高级特性。这使得Transformer中的dynamic shapes和递归结构可以被优雅表示。

**AutoTVM（基于模板的调优）**：用户为常见算子编写计算描述（compute expression）和调度模板（schedule template）。AutoTVM通过机器学习搜索最优调度参数（如 tile size、unroll factor）。搜索算法包括模拟退火、XGBoost预测等。

**AutoScheduler / Ansor**：TVM的下一代自动调度器，无需手动编写调度模板。Ansor通过分层搜索（先搜索高层结构，再搜索底层参数）和遗传算法，自动生成高性能调度。在多个Benchmark上超越了手写调度和AutoTVM。

优化示例——算子融合：

```
# 未融合：存在中间写回
%1 = nn.conv2d(%data, %weight)  # 写回DRAM
%2 = nn.relu(%1)                 # 从DRAM读取
# 融合后：无中间写回
%2 = fused_conv2d_relu(%data, %weight)
```

### MLIR：多级中间表示框架

MLIR（Multi-Level Intermediate Representation）由Chris Lattner等人在Google提出（CGO 2021），解决了传统编译器缺少针对深度学习优化的IR层级问题。

MLIR的核心概念是**方言（Dialect）**，每个方言定义了一组操作、类型和约束。不同方言对应不同抽象层级：

- **`tosa` (Tensor Operator Set Architecture)**：高层张量运算方言，类似Relay IR。
- **`linalg`**：线性代数方言，表示矩阵运算。
- **`affine`**：仿射循环方言，支持多面体模型优化。
- **`scf` (Structured Control Flow)**：结构化控制流方言。
- **`gpu`**：GPU相关方言。
- **`llvm`**：LLVM IR方言。

**渐进式降低（Progressive Lowering）**是MLIR的精髓：模型从高层方言开始，经过多次部分降低（部分算子从tosa下降到linalg，再从linalg下降到affine等），最终到达LLVM方言。在每一层，编译器都可以应用该层特有的优化。

数学描述：假设 $O_{\text{high}}$ 是高层操作集合，$O_{\text{low}}$ 是低层操作集合，降低函数 $\mathcal{L}: O_{\text{high}} \rightarrow O_{\text{low}}$ 需要保持语义等价性：

$$
\forall x, \text{eval}_{\text{high}}(o_{\text{high}}, x) = \text{eval}_{\text{low}}(\mathcal{L}(o_{\text{high}}), x)
$$

MLIR的模块化设计使其适合作为不同前端（TensorFlow, PyTorch）和后端（GPU, TPU, NPU）的公共编译器基础设施。

### XLA：加速线性代数编译器

XLA（Accelerated Linear Algebra）是Google为其深度学习框架JAX和TensorFlow开发的编译器。其流水线为：

1. **HLO（High Level Optimizer）IR**：从框架前端将模型转换为HLO计算图。
2. **并行化**：将计算图分配到多个加速器设备。
3. **后端特定优化**：
   - 对于GPU：将HLO降低为LLVM IR，再编译为PTX。
   - 对于TPU：将HLO降低为TPU指令（Core IR）。
4. **布局优化**：改变张量的内存布局（如NCHW ↔ NHWC）以匹配硬件的访存模式。

XLA的核心优化包括：

- **Buffer Assignment**：与TVM类似，XLA的Buffer Assignment决定张量的内存分配。
- **Layout Assignment**：为每层的输入输出选择最优内存布局。
- **算子融合**：XLA的fusion pass将较小的HLO运算合并为"Fused Computation"，减少kernel launch开销。

从编译器角度看，XLA、TVM和MLIR本质上都在解决相同的问题——将高层计算图映射到硬件，但采取了不同的IR设计和优化策略。

## IR优化的典型案例：算子融合

算子融合是最具代表性的AI编译器优化之一，体现了数据搬运优化的核心思想。

考虑一个典型pattern：`Conv2D → BatchNorm → ReLU`

未融合时，每一层的输出都需要写回DRAM，下一层再读取：

$$
\begin{aligned}
&Z = \text{Conv2D}(X, W) &&\text{(写回 DRAM)}\\
&Y_{\text{bn}} = \gamma \frac{Z - \mu}{\sigma + \epsilon} + \beta &&\text{(读取 Z, 写回 Y\_bn)}\\
&Y = \max(0, Y_{\text{bn}}) &&\text{(读取 Y\_bn, 写回 Y)}
\end{aligned}
$$

融合后，三条操作在一个kernel中完成，中间结果仅在寄存器或片上SRAM中传递：

$$
Y = \max\left(0, \gamma \frac{\text{Conv2D}(X, W) - \mu}{\sigma + \epsilon} + \beta\right)
$$

## 总结

AI编译器是将深度学习模型高效映射到硬件的关键基础设施。TVM通过AutoTVM和AutoScheduler实现了自动化的调度搜索；MLIR通过多级方言实现了灵活的渐进式降低；XLA通过HLO和专门的Buffer/Layout Assignment服务于Google的TPU生态。三者在基本思想上高度一致——通过高层图优化、算子降低、内存规划和代码生成，最大化硬件利用率和能效。

## 参考文献

1. Chen, T., et al. "TVM: An Automated End-to-End Optimizing Compiler for Deep Learning." OSDI 2018.
2. Lattner, C., et al. "MLIR: A Compiler Infrastructure for the End of Moore's Law." CGO 2021.
3. Zheng, L., et al. "Ansor: Generating High-Performance Tensor Programs for Deep Learning." OSDI 2020.
4. Sabne, A. "XLA: Compiling Machine Learning for Production." Google Technical Report, 2020.
5. Roesch, J., et al. "Relay: A New IR for Machine Learning Frameworks." MAPL 2018.
6. Tillet, P., Kung, H.-T., & Cox, D. "Triton: An Intermediate Language and Compiler for Tiled Neural Network Computations." PLDI 2019.
7. Rotem, N., et al. "Glow: Graph Lowering Compiler Techniques for Neural Networks." arXiv:1805.00907, 2018.
8. Vasilache, N., et al. "Tensor Comprehensions: Framework-Agnostic High-Performance Machine Learning Abstractions." arXiv:1802.04730, 2018.
