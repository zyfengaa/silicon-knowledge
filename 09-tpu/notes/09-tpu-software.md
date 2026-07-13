# TPU 软件栈：XLA 编译器与 JAX 框架

## 概述

TPU 的强大硬件能力离不开其配套的软件栈。与 GPU 使用 CUDA 作为底层编程模型不同，TPU 完全依赖于一个更高层次的编译框架——XLA（Accelerated Linear Algebra, 加速线性代数）。XLA 将来自多种前端框架（JAX、TensorFlow、PyTorch）的计算图编译为可在 TPU 上高效执行的机器指令。JAX 则是与 XLA 深度耦合的数值计算库，提供了 NumPy 兼容的 API 和函数式变换功能，成为目前 TPU 用户的首选编程框架。

## XLA 编译器架构

### 发展背景

XLA 最初是 TensorFlow 的一部分，于 2017 年开源。其核心动机是解决 TensorFlow 图执行模式的性能问题——在传统 TensorFlow 中，每个算子独立调度执行，带来了大量的内核启动开销（kernel launch overhead），并且无法跨算子进行全局优化。XLA 通过将整个计算图编译为单一的可执行程序来消除这些开销。

### HLO 中间表示

XLA 的核心中间表示称为 HLO（High-Level Optimizer, 高级优化器），它是一个基于静态单赋值（SSA, Static Single Assignment）形式的计算图表示。每个 HLO 指令代表一个高层运算操作，包括：

- **乘法/卷积**: `kDot`, `kConvolution`
- **逐元素运算**: `kAdd`, `kMul`, `kMax`, `kExp`
- **归约**: `kReduce`, `kReduceWindow`
- **数据重组**: `kReshape`, `kTranspose`, `kSlice`
- **通信**: `kAllReduce`, `kAllGather`, `kCollectivePermute`

一个典型的 HLO 程序片段如下（以矩阵乘法后接 ReLU 为例）：

```
HloModule matmul_relu

ENTRY main {
  x = f32[1024,768] parameter(0)
  w = f32[768,512] parameter(1)
  dot = f32[1024,512] dot(x, w), lhs_contracting_dims={1},
                                     rhs_contracting_dims={0}
  zero = f32[] constant(0)
  relu = f32[1024,512] maximum(dot, zero)
  ROOT out = f32[1024,512] copy(relu)
}
```

### XLA 编译流程

XLA 的编译过程包含多个阶段（pass），每个阶段对 HLO 图进行特定的优化。典型流程如下：

1. **HLO 构建（HLO Builder）**: 将前端框架（JAX/TensorFlow）的计算图转换为 HLO 表示。

2. **HLO 优化（HLO Optimization Passes）**:
   - **算子融合（Operator Fusion）**: 将连续的运算合并为单一内核，减少数据搬运。例如，矩阵乘法和后续的 ReLU 可以融合为一个 custom-call，中间结果不写回 HBM。
   - **代数简化（Algebraic Simplification）**: 应用恒等变换化简计算，如 $A \times 0 = 0$、$A + 0 = A$、常见的常数折叠（constant folding）等。
   - **死代码消除（Dead Code Elimination）**: 移除不会被使用的计算。
   - **批量归一化优化（BatchNorm Optimization）**: 将 BatchNorm 的推理阶段折叠到前面的卷积或矩阵乘法中。
   - **内存规划器（Memory Planner）**: 在编译时确定每个张量的生命周期和布放位置，实现编译时内存管理。

3. **并行化（Parallelization）**:
   - 通过 GSPMD 将 HLO 计算图按照分片标注（sharding annotations）在多个 TPU 设备之间分配。
   - 自动插入所需的集体通信原语（all-reduce, all-gather, reduce-scatter 等）。

4. **代码生成（Code Generation）**:
   - 将优化后的 HLO 指令逐一映射为 TPU 底层的 CISC 指令。
   - 调度器（scheduler）确定指令的执行顺序，最大化指令级并行度。
   - 生成最终的 TPU 二进制可执行文件。

### 算子融合的数学原理

算子融合是 XLA 最关键的优化之一。考虑一个常见的模式：$Y = \text{ReLU}(AX + B)$，即先进行矩阵乘法，再加偏置，最后应用 ReLU 激活。

在不融合的情况下，计算为：

$$
\begin{aligned}
Z &= AX + B \quad \text{(写入 HBM)}\\
Y &= \max(Z, 0) \quad \text{(从 HBM 读入)}
\end{aligned}
$$

每次 HBM 读写都有巨大的功耗和延迟开销。XLA 将其融合为一个单一操作：

$$
Y = \max(AX + B, 0)
$$

融合后，$AX + B$ 的结果直接留在 MXU 的累加寄存器或向量单元的寄存器文件中，供第二步的 $\max$ 操作使用，整个过程完全在芯片内部完成，没有任何 HBM 访问。

## JAX 框架

### JAX 的设计哲学

JAX 是 Google 开发的一个面向科学计算和机器学习的 Python 库，由 Matt Johnson、Roy Frostig、Dougal Maclaurin 和 Chris Leary 等人创建。JAX 的核心设计理念是：

1. **NumPy 兼容**: JAX 的 API 几乎完全镜像 NumPy 的接口，用户可以用熟悉的 NumPy 语法编写计算代码
2. **函数式纯变换**: JAX 不接受可变状态，所有变换作用于纯函数
3. **XLA 后端**: JAX 依赖 XLA 将其计算图编译并执行

JAX 的核心优势通过"函数变换"（functional transformations）体现，主要包括以下变换：

### jit（即时编译）

`jit` 将 Python 函数编译为 XLA 可执行程序：

```python
import jax
import jax.numpy as jnp

@jax.jit
def forward(x, w):
    return jnp.dot(x, w)

x = jnp.ones((1024, 768))
w = jnp.ones((768, 512))
y = forward(x, w)  # 首次调用时编译，后续直接执行编译后的代码
```

`jit` 的关键优势在于：
- XLA 可以看到整个 `forward` 函数的全局计算图，进行跨算子融合优化
- 函数在首次调用时编译一次，后续调用直接使用缓存的可执行文件
- 避免了 Python 解释器在每次运算之间的开销

### vmap（向量化映射）

`vmap` 自动将批量计算向量化。假设有一个函数处理单个样本：$f: \mathbb{R}^{D} \to \mathbb{R}^{K}$，批量处理 $N$ 个样本时，传统的做法是在批处理维度上写显式循环或手动管理批维度的索引。`vmap` 自动处理这一切：

```python
f = lambda x: jnp.dot(x, w)  # 单样本函数
batch_f = jax.vmap(f)        # 自动向量化为批量函数
output = batch_f(X)          # X: (N, D) -> output: (N, K)
```

`vmap` 并不只是在外部加一个循环，而是通过 XLA 的 HLO 重写在计算图中插入批处理维度，使得循环在编译器的控制流优化中被高效处理。d

### pmap（并行映射）

`pmap` 将计算分布到多个 TPU 设备上。它在语义上类似于 `vmap`，但将批处理维度映射到设备维度（device dimension），每个设备计算一部分数据：

```python
# 在 8 个 TPU 核心上并行
parallel_forward = jax.pmap(forward, axis_name='batch')
output = parallel_forward(x_sharded, w)  # x_sharded 已在 8 个核心上分片
```

`pmap` 自动处理：
- 输入张量的分片和分发
- 梯度计算的自动同步（all-reduce）
- 结果收集与合并

### shard_map

`shard_map` 是 JAX 中较新的并行变换，提供了对 GSPMD 更细粒度的控制：

```python
from jax.sharding import PartitionSpec
from jax.experimental.shard_map import shard_map

mesh = Mesh(np.array(jax.devices()), ('batch',))
@partial(shard_map, mesh=mesh, spec_in=PartitionSpec('batch', None),
         spec_out=PartitionSpec('batch', None))
def sharded_forward(x, w):
    return jnp.dot(x, w)  # GSPMD 自动插入通信操作
```

`shard_map` 的优势在于用户可以精确控制每个维度如何在设备网格上分片，而 GSPMD 自动推导出所需的跨设备通信。

## XLA 与 JAX 的协作流程

JAX 与 XLA 的协作流程如下：

1. **追踪（Tracing）**: JAX 使用抽象张量（abstract tensors）追踪 Python 函数，构建 JAXPR（JAX 的中间表示）无状态函数
2. **HLO 生成**: JAXPR 被转换为 XLA 的 HLO 表示
3. **XLA 优化**: HLO 经过上述的多阶段优化 passes
4. **代码生成**: XLA 为 TPU（或其他后端）生成设备代码
5. **执行**: TPU 执行编译后的程序

这套流程使得用户用高级 Python API 编写的代码，经过一系列自动优化和转换，最终在高性能 TPU 硬件上执行时能够接近理论峰值性能。

## PyTorch/XLA 与 TensorFlow

除 JAX 外，PyTorch 也可以通过 PyTorch/XLA 库使用 TPU。PyTorch/XLA 将 PyTorch 的计算图转换为 XLA HLO，然后利用 XLA 编译到 TPU。TensorFlow 则是 XLA 的原生前端之一，与 XLA 的结合最为紧密。不过，从社区活跃度和 Google 内部投入来看，JAX 已经成为 TPU 的首选编程框架。

## 参考文献

1. XLA Team. "XLA: Optimizing Compiler for Machine Learning." TensorFlow Documentation, 2017. https://www.tensorflow.org/xla
2. Bradbury, J., et al. "JAX: Composable Transformations of Python+NumPy Programs." GitHub, 2018. http://github.com/google/jax
3. Frostig, R., et al. "Compiling Machine Learning Programs via High-Level Differentiable Programming." Program Transformations for Machine Learning Workshop (NeurIPS), 2018.
4. Xu, Y., et al. "GSPMD: General and Scalable Parallelization for ML Computation Graphs." arXiv:2105.04663, 2021.
5. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." ISCA '17, 2017.
6. Sabne, A., et al. "Modeling the XLA Compiler for TPU Performance." Google Research Technical Report, 2020.
7. Paszke, A., et al. "PyTorch: An Imperative Style, High-Performance Deep Learning Library." NeurIPS, 2019.
