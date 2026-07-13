# TPU Profiling：Google Cloud TPU 性能分析工具链

## 为什么讲这个

Tensor Processing Unit（TPU）是 Google 为深度学习工作负载专门设计的 ASIC（Application-Specific Integrated Circuit）。与 GPU 不同，TPU 采用**脉动阵列（Systolic Array）** 架构和**单指令多数据（SIMD）** 执行模型，其编程和 profiling 方式与传统 GPU 有根本差异。TPU 上的程序不是通过 CUDA 或 OpenCL 编写的，而是通过 XLA（Accelerated Linear Algebra）编译器从 TensorFlow、JAX 或 PyTorch 的计算图编译而来。因此，TPU 的 profiling 工具链也围绕 XLA 编译过程和 TPU 硬件计数器构建，形成了一套独特的分析体系。

## TPU 架构概述

### TPU v4 和 v5p 的架构特征

以 TPU v4 为例，每个 TPU 芯片包含：

| 组件 | 规格 |
|------|------|
| 矩阵乘法单元（MXU） | 128×128 脉动阵列 |
| 标量处理单元（VPU） | 用于 element-wise 和 reduce 操作 |
| HBM 容量 | 32 GB（v4）/ 95 GB（v5p） |
| HBM 带宽 | 1,200 GB/s（v4）/ 1,600 GB/s（v5p） |
| 片间互联 | 4D Torus 拓扑（每芯片 6 条链路） |
| 计算精度 | BF16（MXU）/ FP32（累加器） |

TPU 的 MXU 执行矩阵乘法的方式与 NVIDIA Tensor Core 类似，但规模更大：一个 TPU v4 芯片包含 4 个 MXU，每个周期可完成 128×128×128 = 2,097,152 次乘加操作。

### TPU Pod

多个 TPU 芯片通过 4D Torus 互联组成 TPU Pod。例如，TPU v4 Pod 包含 4,096 个芯片，总算力超过 1 exaFLOP（BF16）。TPU 的互联拓扑使得跨芯片通信的延迟和带宽可预测，这是 GPU 集群中常见的 RDMA 网络所不具备的优势。

## XLA 编译与 HLO

### XLA 的编译流程

TPU 上的所有程序都必须经过 XLA 编译器。XLA 的编译过程分为多个 pass，每个 pass 对计算图进行优化：

```
TensorFlow/PyTorch/JAX 计算图
        │
        ▼
  HLO (High-Level Optimizer) IR
        │  ├── 算子融合（Fusion）
        │  ├── 布局约束（Layout Assignment）
        │  ├── 缓冲区分析（Buffer Analysis）
        │  └── 代数简化（Algebraic Simplification）
        ▼
  LHLO (Low-Level HLO) IR
        │  ├── 内存调度
        │  └── 指令调度
        ▼
  TPU 可执行代码
```

XLA 编译器将高层计算图逐步 lower 为 TPU 可执行的指令序列。与 GPU 的即时编译（JIT）不同，TPU 的编译在首次执行时发生，编译时间可能较长（对于大模型可达数十分钟）。

### HLO 统计信息

查看 XLA 的编译统计是 profiling 的第一步。通过环境变量可以获取 XLA 的编译信息：

```bash
# 启用 XLA 编译日志
export XLA_FLAGS="--xla_dump_to=/tmp/xla_dump --xla_dump_hlo_as_text"
```

HLO dump 提供了每步编译的中间表示，从中可以观察：

1. **融合模式**：哪些算子被融合为一个 kernel？如果融合不当（如不必要的大融合导致寄存器溢出），会降低性能。
2. **布局转换**：数据在内存中的布局（NHWC vs NCHW）是否合理？不必要的转置会增加数据传输。
3. **重计算（Rematerialization）**：编译器是否引入了额外的重计算来节省内存？这增加了计算开销。
4. **操作数**：每个 HLO 指令的输入输出张量形状，以及它们是否对齐到 TPU 的块结构（通常是 128 的倍数）。

关键指标：

```
HloModule my_model, entry_computation_layout={...}
  HLO 指令数: 2,456
  Fusion 指令数: 423
  融合比例: 82.7%
  最大融合组大小: 127 个操作
```

高的融合比例（> 80%）通常说明 XLA 的算子融合效果好，中间结果的 DRAM 读写最小化。

### 获取 XLA 统计

```python
# JAX 中启用 XLA 统计
import jax

# 编译时统计
xla_computation = jax.jit(lambda x: x @ x).lower(jax.numpy.ones((128, 128)))
hlo_text = xla_computation.as_text()
print(hlo_text[:2000])

# 运行时 HLO 统计（需要设置环境变量）
# os.environ["XLA_FLAGS"] = "--xla_dump_to=/tmp/xla_dump"
```

## TensorBoard TPU Profiler

TensorBoard TPU Profiler 是 Google Cloud TPU 的主要 profiling 工具，提供了与 Nsight Systems 类似的时间线视图，但专为 TPU 的编译执行模型设计。

### 启动 Profiler

```python
# JAX 中使用 TensorBoard profiler
import tensorflow as tf

# 启动 profiling
tf.profiler.experimental.start('/tmp/tb_logs')

# 运行训练步骤
for step in range(10):
    train_step(data)

# 停止 profiling
tf.profiler.experimental.stop()
```

或者使用命令行：

```bash
capture_tpu_profile --tpu=$TPU_NAME \
    --logdir=/tmp/tb_logs \
    --duration_ms=1000
```

### Trace Viewer（追踪查看器）

Trace Viewer 提供类似 Nsight Systems 的时间线视图：

```
时间 →
───────────────────────────────────────────────────────
TPU Core 0:
  ┌──────MatMul──────┐  ┌─────FusedConv────┐  ┌─Reshape┐
  └──────────────────┘  └──────────────────┘  └────────┘

TPU Core 1:
                       ┌──────MatMul──────┐  ┌─────FusedConv────┐
                       └──────────────────┘  └──────────────────┘

Kernel Launch (CPU):
  ┌────┐┌────┐┌────┐┌────┐┌────┐
```

关键观察点：

1. **TPU Core 之间的负载是否均衡？** 如果某个 core 的空闲时间明显多于其他 core，说明数据并行或模型并行的负载分配不均。
2. **CPU 端是否形成瓶颈？** 如果 CPU kernel launch 之间有明显间隙，且 TPU 处于空闲等待状态，说明 CPU 端的 JAX/TensorFlow 运行时无法及时向 TPU 提交工作。
3. **步间时间（Inter-step Time）**：在 training loop 中，相邻两个训练步之间的时间差是否稳定？如果步间时间波动大，可能有输入数据管线的瓶颈或 host 端计算开销。

### 输入管线分析（Input Pipeline Analysis）

TPU 的输入处理必须在 CPU 端完成并通过高速网络传输到 TPU。如果 CPU 输入预处理跟不上 TPU 的计算速度，TPU 就会空闲等待数据。

TensorBoard Profiler 的 Input Pipeline Analyzer 显示：

```
Input Pipeline Analysis:
  Step 0: 15.2ms (100%)    <- 数据加载时间
  Step 1: 12.8ms (84%)
  Step 2: 13.1ms (86%)
  ...
  平均加载时间: 13.5ms
  TPU 步时间:   10.0ms    <- 数据加载慢于 TPU 计算
  → TPU 空闲率: 26.0%    <- TPU 有 26% 的时间在等数据
```

如果数据加载时间 > TPU 步时间，需要优化数据管线：
- 使用 `tf.data.Dataset.prefetch()` 预取数据
- 使用 JAX 的 `jax.numpy.vectorize_map` 并行数据加载
- 增加数据加载的 worker 数量
- 减小数据预处理的计算量（如使用 TFRecord 格式、提前完成数据增强）

### TFLOPS/TOPS 利用率

TensorBoard Profiler 报告 TPU 的 TFLOPS 利用率：

```
TPU TFLOPS Utilization:
  Theoretical Peak:    275 TFLOPS (BF16)
  Achieved:           192 TFLOPS
  Utilization:         69.8%
```

69.8% 的 TFLOPS 利用率对于 TPU 来说是中等偏上。影响利用率的主要因素包括：

1. **矩阵大小是否对齐**：TPU 的 MXU 是 128×128，如果矩阵维度不是 128 的倍数，会导致 padding 开销。例如，维度 129 需要 padding 到 256（因 MXU 打包方式），增加 2× 的计算量。
2. **注意力计算中的非 MatMul 操作**：Transformer 中的 softmax、layer norm 等操作在 VPU（标量处理单元）上执行，VPU 的吞吐远低于 MXU。如果模型中 softmax 或 layer norm 计算频繁，整体 TFLOPS 利用率会被拉低。
3. **激活函数开销**：ReLU、GELU 等激活函数在 VPU 上执行，也会降低整体利用率。

## JAX Profiling

JAX 提供了 `jax.profiler` 模块，专门用于 TPU 和 GPU 的 profiling。

### 基本用法

```python
import jax
import jax.numpy as jnp

@jax.jit
def train_step(params, x, y):
    pred = params @ x
    loss = jnp.mean((pred - y) ** 2)
    grad = jax.grad(lambda p: jnp.mean((p @ x - y) ** 2))(params)
    return loss, grad

# 启动 trace
with jax.profiler.trace("/tmp/jax_trace"):
    params = jnp.ones((128, 64))
    x = jnp.ones((64, 32))
    y = jnp.ones((128, 32))
    for step in range(100):
        loss, grads = train_step(params, x, y)
```

`jax.profiler.trace()` 会记录整个 with 块内的执行过程，包括：
- XLA 编译事件（只在第一次运行时触发）
- TPU kernel 执行时间
- 数据传输时间
- CPU 端 JAX 运行时开销

### Device Memory Profiling

```python
# 查看设备内存使用情况
import jax
print(jax.devices()[0].memory_stats())
# 输出: {'bytes_in_use': 2147483648, 'bytes_limit': 34359738368, ...}
```

### 手动标注

使用 `jax.profiler.TraceAnnotation` 可以在 profiling 结果中标记代码区域：

```python
with jax.profiler.TraceAnnotation("forward_pass"):
    pred = model(params, x)
with jax.profiler.TraceAnnotation("backward_pass"):
    grad = grad_fn(params, x, y)
```

## TPU 性能优化案例分析

### 案例：Transformer 训练性能分析

考虑一个 Transformer 模型在 TPU v4 Pod 上的训练：

**症状**：TFLOPS 利用率仅为 45%，低于预期的 70%+。

**分析步骤**：

1. **XLA HLO 统计**：发现融合比例仅为 65%，大量独立的 element-wise 操作（layer norm、dropout、softmax 的各个子操作）没有被融合。

2. **TensorBoard Trace Viewer**：观察到每个 step 中有大量的短时间 kernel（< 5μs），说明 XLA 产生了大量微型 kernel。

3. **输入管线分析**：显示数据传输平均耗时 8ms，而 TPU 计算耗时 12ms，数据加载不是瓶颈。

4. **内存分析**：发现模型中存在一个 4096×4096 的矩阵维度，不是 128 的倍数，导致 MXU 需要 padding。

**优化措施**：

1. **对齐维度**：将模型的 hidden dimension 从 4096 改为 4096（已经是 128 的倍数）。但发现 attention head 的维度是 128，而 12 个 head 的总维度并不对齐，将 head 数调整为 16 使总维度变为 2048。

2. **手动融合**：使用 `jax.lax.fori_loop` 替代 Python for 循环，使 XLA 能更好地融合循环内的操作。

3. **减少 HBM 访问**：使用 rematerialization（梯度检查点）减少激活值的显存占用，使 batch size 从 32 增加到 64。

**优化后**：TFLOPS 利用率从 45% 提升到 72%，训练速度提升 1.6 倍。

### 常见性能陷阱

| 问题 | 表现 | 原因 | 解决方法 |
|------|------|------|---------|
| 低 MXU 利用率 | TFLOPS 利用率 < 50% | 矩阵维度不对齐、element-wise 操作过多 | pad 对齐、fuse operations |
| 高通信开销 | Step time 随 TPU 数量超线性增长 | All-reduce 通信效率低 | 使用 `pjit` 优化通信模式、减小通信粒度 |
| 编译时间过长 | 首次 step 耗时数分钟 | XLA 编译在大模型上需要大量时间 | 使用 persistent compilation cache、预热 |
| 数据加载瓶颈 | TPU 空闲等待 | CPU 输入管线处理不足 | 增加 prefetch、使用 TFRecord 格式 |
| 梯度爆炸/消失 | Loss 不收敛 | 精度导致 | 使用混合精度、gradient scaling |

## Cloud TPU Monitoring

Google Cloud 的 Monitoring Dashboard 提供了集群级别的性能指标：

- **TPU 利用率**（每分钟）
- **HBM 使用率**
- **ICI 带宽利用率**
- **队列深度**：pending 的 TPU 执行请求数
- **错误率**：硬件错误和超时事件

## 总结

TPU Profiling 与 GPU Profiling 有本质差异：
- TPU 的编程模型是基于编译器（XLA）的，因此分析的起点是 **HLO 编译统计**，看编译器生成了什么样的代码
- TPU 的计算核心是 **MXU（脉动阵列）**，利用率取决于矩阵维度对齐和算子融合效率
- TPU 的 profiling 工具链以 **TensorBoard Profiler** 和 **JAX profiler** 为主，配合 Google Cloud Monitoring 做集群级监控
- 关键指标包括：TFLOPS 利用率、融合比例、输入管线吞吐、ICI 通信效率

## 参考文献

1. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *Proceedings of the 44th Annual International Symposium on Computer Architecture (ISCA)*, 2017. — TPU v1 的原始论文，详细介绍了 TPU 架构和性能分析方法
2. Jouppi, N. P., et al. "Ten Lessons From Three Generations Shaped Google's TPU." *Proceedings of the 48th Annual International Symposium on Computer Architecture (ISCA)*, 2021. — TPU v1 到 v4 的设计演化和经验总结
3. Google Cloud. "Cloud TPU Profiler User Guide." *Google Cloud Documentation*, 2024. — TensorBoard TPU Profiler 的官方使用指南
4. Google Cloud. "Optimizing TPU Performance." *Google Cloud Documentation*, 2024. — TPU 性能优化的官方最佳实践
5. Google Cloud. "XLA Architecture." *XLA Documentation*, 2024. — XLA 编译器的架构文档和 pass 说明
6. Frost, J., et al. "JAX Profiling Guide." *JAX Documentation*, 2024. — JAX 的 profiling API 文档
7. Bradbury, J., et al. "JAX: Composable Transformations of Python+NumPy Programs." *GitHub*, 2024. — JAX 框架的原始论文和 API 说明
8. Yazdanbakhsh, A., et al. "An Analysis of the Performance of TPU v4 for Deep Learning Workloads." *arXiv:2206.11997*, 2022. — TPU v4 上深度学习工作负载的详细性能分析
