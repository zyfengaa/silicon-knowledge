# GPU Profiling：Nsight 工具链深度分析

## 为什么讲这个

GPU 作为异构计算的核心加速器，其性能分析比 CPU 复杂得多。GPU 上动辄数千个线程并发执行，加上多级缓存、多种内存类型（全局/共享/本地/寄存器）、异步执行模型以及 CPU-GPU 数据传输，一个性能问题的成因可能涉及多个子系统。NVIDIA 的 Nsight 工具链提供了端到端的 GPU 性能分析能力：Nsight Systems（nsys）用于宏观的系统级时间线分析，Nsight Compute（ncu）用于微观的 kernel 级瓶颈诊断。掌握这些工具的使用，是 GPU 程序员从"能跑"到"能跑得快"的必经之路。

## Nsight Systems（nsys）：系统时间线分析

### 功能和定位

Nsight Systems 是一个**系统级性能分析器**，它在时间轴上展示整个应用的执行过程，聚焦于以下关键信息：

1. **Kernel 启动和执行时间**：每个 CUDA kernel 的启动延迟和执行耗时
2. **数据传输**：Host-to-Device（H2D）和 Device-to-Host（D2H）的传输时间
3. **API 调用**：CUDA API 的调用序列和时间
4. **CPU 活动**：CPU 端的计算和控制流
5. **同步事件**：cudaDeviceSynchronize、cudaStreamSynchronize 等同步点

### 基本用法

```bash
# 基本 profiling 命令
nsys profile -o output_profile ./my_cuda_app

# 关注 GPU kernel 和内存操作
nsys profile --trace=cuda,cublas,cudnn,nvtx -o output ./my_cuda_app

# 增加采样细节
nsys profile -t cuda,osrt --stats=true -o output ./my_cuda_app

# 限制 profiling 范围（仅分析感兴趣的区域）
nsys profile --duration=10 -o output ./my_cuda_app

# 查看结果
nsys-ui output.qdrep   # GUI 界面
nsys stats output.qdrep  # 命令行统计
```

### 输出解读

Nsight Systems 的时间线视图（在 nsys-ui 中查看）通常显示为：

```
时间 →
───────────────────────────────────────────────────────
CPU Thread:
  ┌───memcpy H2D (5.2ms)───┐
  │                         │  ┌───kernel_A (3.1ms)───┐
  │                         │  │                      │  ┌─memcpy D2H (2.0ms)─┐
  └─────────────────────────┘  └──────────────────────┘  └────────────────────┘

GPU Stream (Stream 0):
                               ┌───kernel_A (3.1ms)───┐
                               └──────────────────────┘
```

关键观察角度：

**是否存在 CPU-GPU 串行化**：如果时间线上 CPU 提交工作在等待 GPU 完成前一次提交（中间有空隙），说明 CPU 和 GPU 没有充分重叠工作。理想情况下，CPU 应持续向 GPU 提交 kernel 请求。

**数据传输是否隐藏**：H2D 和 D2H 传输是否与 kernel 执行重叠？如果不重叠，且数据传输时间可观，则需要使用 CUDA Stream 和异步传输来重叠。

**Kernel 启动开销**：每个 kernel 有一小段灰色部分（启动延迟）。如果 kernel 本身很小（如 < 5μs），启动开销可能占主导，这时应考虑 kernel fusion。

### 典型瓶颈模式

| 时间线模式 | 瓶颈 | 解决方案 |
|-----------|------|---------|
| 频繁的 H2D/D2H | PCIe 带宽受限 | 双缓冲、数据预取、使用 Unified Memory |
| kernel 间长间隔 | CPU 提交过慢 | 使用 MPS（Multi-Process Service）、减少 CPU 端同步 |
| 小 kernel 频繁启动 | kernel 启动开销 | 融合 kernel、使用 Persistent Kernel |
| GPU 利用率低 | 负载不足 | 增大 batch size、调整 grid/block 大小 |

## Nsight Compute（ncu）：Kernel 级深度分析

### 功能和定位

Nsight Compute 是一个**kernel 级性能分析器**，对每个 CUDA kernel 提供详细的硬件指标分析。它直接访问 GPU 的性能计数器，可以回答以下问题：

1. **这个 kernel 是 compute-bound 还是 memory-bound？**
2. **occupancy（占用率）是否足够高？**
3. **L1/L2 cache 命中率如何？**
4. **是否有 bank conflict 或 shared memory 瓶颈？**
5. **指令吞吐是否达到峰值？**

### 基本用法

```bash
# 基本分析
ncu -o output_profile ./my_cuda_app

# 分析特定 kernel
ncu --kernel-name "my_kernel" -o output ./my_cuda_app

# 完整指标集（速度较慢，但信息最全）
ncu --set full -o output ./my_cuda_app

# 针对 roofline 的分析
ncu --set roofline -o output ./my_cuda_app

# 命令行模式（无 GUI）
ncu --set basic --print-detail=all ./my_cuda_app

# 交互式分析
ncu --page details ./my_cuda_app
```

### 关键指标解读

#### Occupancy（占用率）

Occupancy 是每个 SM（Streaming Multiprocessor）中活跃 warp 数与最大 warp 数的比率：

```
Theoretical Occupancy: 100.0%
Achieved Occupancy:    75.3%   (48 active warps per SM)
```

- **Theoretical Occupancy**：基于 kernel 的资源需求（寄存器数、shared memory 量）计算的理论最大值
- **Achieved Occupancy**：实际运行中达到的平均占用率（可能低于理论值，因为指令依赖等原因）
- 高 occupancy（> 80%）通常有利于隐藏内存延迟，但不一定能最大化吞吐

**Occupancy 与性能的关系并非单调递增**：对于计算密集的 kernel（如矩阵乘法），高 occupancy 意味着更多线程竞争计算资源，反而可能降低单线程性能；对于内存密集的 kernel，高 occupancy 有助于隐藏延迟。

#### Memory Throughput（内存吞吐）

```
Memory Throughput:
  L1/TEX Cache Throughput:  4,320 GB/s (73.1% peak)
  L2 Cache Throughput:      1,850 GB/s (52.4% peak)
  HBM Memory Throughput:    1,200 GB/s (65.0% peak)
```

- HBM 吞吐为 65% peak 说明内存压力较大
- 如果 HBM 吞吐高但 L2 吞吐低，说明数据局部性好（L2 命中率高），数据主要在 L1 和 HBM 之间流动
- 如果 L2 吞吐接近峰值但 HBM 吞吐低，说明 L2 提供了有效的缓存过滤

#### Compute Throughput（计算吞吐）

```
Compute Throughput:
  SM Throughput:           85.2% (FP32)
  Tensor Core Throughput:  92.1% (FP16)
```

- Tensor Core 达到 92% 说明 kernel 充分利用了 Tensor Core
- SM 的 FP32 吞吐 85% 说明还剩 15% 的优化空间（可能是指令延迟、数据依赖或 warp stall 导致）

#### Speed-of-Light 分析

ncu 的 Speed-of-Light 页面将 kernel 性能分解为若干个"限制因素"的百分比：

```
Speed Of Light (24 SM, 2048 FP32 Cores):
  Memory:  45.6%
  Compute: 54.4%
```

- 如果 Memory 百分比明显高于 Compute -> **memory-bound**
- 如果 Compute 百分比明显高于 Memory -> **compute-bound**
- 两者接近 -> 平衡状态

#### Stall 分析

```
Warp Stall Reasons:
  Long Scoreboard         52.3%   <- 等待内存访问完成（等待加载数据）
  Short Scoreboard         5.2%
  Not Predicated Off      12.4%
  Wait                    10.1%
  Other                   20.0%
```

- **Long Scoreboard** 占比高说明 warp 因等待从全局或本地内存加载数据而停顿，是 memory-bound 的典型表现
- **Short Scoreboard** 通常是等待 shared memory 或寄存器操作
- **Not Predicated Off** 是 warp 在执行 if/else 等分支时另一部分线程被屏蔽的开销

### 使用 ncu 的典型工作流

#### 步骤 1：基本分析（定位热点）

```bash
ncu --set basic ./my_app
```

查看哪些 kernel 占用了最多时间。对于时间最长的 kernel，进入步骤 2。

#### 步骤 2：Roofline 分析

```bash
ncu --set roofline --kernel-name "matmul_kernel" ./my_app
```

判断 kernel 是 memory-bound 还是 compute-bound。

#### 步骤 3：详细分析

```bash
ncu --set full --kernel-name "matmul_kernel" ./my_app
```

如果 memory-bound：
- 检查 L1/L2 命中率
- 检查 global memory access pattern（coalescing）
- 检查 shared memory bank conflict

如果 compute-bound：
- 检查指令 issue rate
- 检查 Tensor Core 利用率
- 检查 occupancy 是否过高导致计算资源竞争

### 实际案例：矩阵乘法分析

```cpp
// naive_matmul.cu
__global__ void matmul_naive(float *A, float *B, float *C, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    float sum = 0.0f;
    for (int k = 0; k < N; k++)
        sum += A[row * N + k] * B[k * N + col];
    C[row * N + col] = sum;
}
```

ncu 分析结果：

```
Speed Of Light:
  Memory:  78.3%    <- 内存受限
  Compute: 21.7%

Memory Throughput:
  HBM: 1,500 GB/s (81% peak)

Occupancy:
  Achieved: 95.2%   <- occupancy 很高，说明对内存延迟不敏感

L1 Hit Rate: 45.3%  <- 较低的 L1 命中率
L2 Hit Rate: 72.1%
```

**诊断**：naive 矩阵乘法的 B 矩阵是按列访问的，导致每次访问的 cache line 只有 1 个元素被使用（cache line 浪费），L1 命中率低。kernel 是明显的 memory-bound。

**优化**：使用 shared memory 分块，每块加载 A 和 B 的子块到 shared memory，然后在 shared memory 中计算：

```cpp
// tiled_matmul.cu (使用 shared memory tiling)
#define TILE_SIZE 16
__global__ void matmul_tiled(float *A, float *B, float *C, int N) {
    __shared__ float As[TILE_SIZE][TILE_SIZE];
    __shared__ float Bs[TILE_SIZE][TILE_SIZE];
    int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + threadIdx.x;
    float sum = 0.0f;
    for (int t = 0; t < N / TILE_SIZE; t++) {
        As[threadIdx.y][threadIdx.x] = A[row * N + t * TILE_SIZE + threadIdx.x];
        Bs[threadIdx.y][threadIdx.x] = B[(t * TILE_SIZE + threadIdx.y) * N + col];
        __syncthreads();
        for (int k = 0; k < TILE_SIZE; k++)
            sum += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        __syncthreads();
    }
    C[row * N + col] = sum;
}
```

优化后的 ncu 结果：

```
Speed Of Light:
  Memory:  32.1%
  Compute: 68.5%    <- 变为计算受限

HBM Throughput: 520 GB/s (28% peak)  <- HBM 压力大幅下降（数据重用在 shared memory）
L1 Hit Rate: 89.7%                   <- L1 命中率大幅提升
```

**从 memory-bound 变为 compute-bound**，是优化成功的标志。此时瓶颈已经转移到计算单元，进一步优化需关注 Tensor Core 使用和指令级并行。

## NVIDIA Nsight 与其他 GPU Profiling 工具

### AMD ROCprof

对于 AMD GPU，使用 ROCprofiler（rocprof）：

```bash
rocprof --stats ./my_hip_app
rocprof --trace ./my_hip_app
```

rocprof 的输出包含 kernel 耗时、内存传输、occupancy 和 cache 命中率等指标。AMD 的 rocprof 架构与 ncu 对应，但指标集和命名有所不同。例如，AMD 使用 Wavefront（64 线程，相当于 NVIDIA 的 warp）作为调度单元单位，occupancy 的计算也基于 Wavefront 而非 warp。

### Google PAI Profiler（TPU）

Google Cloud TPU 的 profiling 工具链在笔记 07 中详细讨论。其核心区别是 TPU 使用 XLA 编译器和 TensorBoard profiler，与 GPU profiling 的工具链完全不同。

## 总结

GPU Profiling 的核心流程可以归纳为"三步走"：

1. **Nsight Systems（宏观）**：查看整体时间线，识别数据传输和 kernel 执行是否重叠，确认 bottleneck 发生在哪一层
2. **Nsight Compute Roofline（中观）**：对热点 kernel 判断是 memory-bound 还是 compute-bound
3. **Nsight Compute Full（微观）**：钻取具体指标（occupancy、cache 命中率、stall 原因、bank conflict 等），定位根因

通过三个层次的分析，大多数 GPU kernel 性能问题都可以被系统性地诊断和解决。

## 参考文献

1. NVIDIA Corporation. "Nsight Compute User Guide." *NVIDIA Developer Documentation*, 2024. — ncu 的完整用户指南和指标说明
2. NVIDIA Corporation. "Nsight Systems User Guide." *NVIDIA Developer Documentation*, 2024. — nsys 的完整用户指南
3. NVIDIA Corporation. "CUDA C++ Best Practices Guide." *NVIDIA Developer Documentation*, 2024. — 第 9-10 章讨论了 profiling 和性能优化
4. NVIDIA Corporation. "CUDA Occupancy Calculator." *NVIDIA Developer Tools*, 2024. — occupancy 的计算方法和限制因素分析
5. AMD Corporation. "ROCProfiler User Guide." *AMD ROCm Documentation*, 2024. — AMD GPU 的 profiling 工具文档
6. Jia, Z., Maggioni, M., Staiger, B., & Scarpazza, D. P. "Dissecting the NVIDIA Volta GPU Architecture via Microbenchmarking." *arXiv:1804.06826*, 2018. — 通过微基准测试深入分析 GPU 微架构的经典论文
