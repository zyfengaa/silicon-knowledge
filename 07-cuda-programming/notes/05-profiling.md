# 05 — Profiling：Nsight Systems 与 Nsight Compute

> 不要猜测瓶颈在哪里——用 Profiler 去测量。Nsight Systems 看全局，Nsight Compute 看细节。

## 概览

| 工具 | 作用 | 分析粒度 | 类似工具 |
|------|------|---------|---------|
| **Nsight Systems** (nsys) | 应用级时间线 | API 调用、Memcpy、Kernel、CPU 活动 | Intel VTune, perf |
| **Nsight Compute** (ncu) | Kernel 级分析 | Occupancy、Memory/Compute 利用率、瓶颈 | rocprof |

**工作流程：**
1. 用 `nsys` 看全景 → 发现宏观问题（传输重叠？Kernel 启动开销？）
2. 用 `ncu` 深入具体 Kernel → 分析瓶颈（计算饱和？内存受限？）
3. 优化后回到步骤 1 → 确认优化效果

## Nsight Systems (nsys)

### 基本使用

```bash
# 基本的 timeline 收集
nsys profile -o timeline ./my_cuda_app

# 指定 GPU 和 CPU 活动跟踪
nsys profile --trace=cuda,nvtx,osrt -o timeline ./my_cuda_app

# 生成报告（GUI 或命令行）
nsys stats -o timeline_stats timeline.nsys-rep
```

### 分析关键指标

#### 1. API 调用 (CUDA API Trace)

```
Time           Duration   API Name
5219.673 ms    0.154 ms   cudaMalloc
5239.857 ms    1.243 ms   cudaMemcpy (H2D)  ← 传输时间
5243.201 ms    0.832 ms   vector_add         ← Kernel 执行时间
5245.311 ms    1.101 ms   cudaMemcpy (D2H)  ← 回传时间
```

**关注点：**
- 是否有不必要的 `cudaMalloc`/`cudaFree`（复用缓冲区可以消除）
- Memcpy 和 Kernel 之间是否有空白间隔（重叠时机丢失）

#### 2. Kernel Duration

Kernel 时间线视图展示了每个 Kernel 的执行时间跨度。重点关注：
- **最长的 Kernel**：决定应用瓶颈
- **Kernel 之间的间隔**：是否有可以隐藏的延迟

#### 3. Memcpy Throughput

```
Memcpy Statistics:
  H2D: 128 MB at 24.1 GB/s (peak: 32 GB/s)  ← 利用率 75%
  D2H: 128 MB at 23.8 GB/s (peak: 32 GB/s)
```

**关注点：**
- 传输带宽是否接近峰值
- H2D/D2H 传输是否与 Kernel 重叠
- 是否使用了 Pinned Memory（否则带宽很低）

#### 4. Synchronization

```
cudaDeviceSynchronize  -  12.5 ms  ← 强制等待，可能造成 CPU 空闲
cudaStreamSynchronize  -   3.2 ms  ← Stream 级别等待
```

**关注点：**
- 不必要的 synchronize（每个 kernel 后都加同步是最常见的性能问题）

### Nsight Systems 的时间线视图

```
            Time (ms)
            0       10      20      30      40      50
Stream 0:   [H2D────][Kernel─][D2H───]
Stream 1:           [H2D────][Kernel─][D2H───]
Stream 2:                   [H2D────][Kernel─][D2H───]
Stream 3:                           [H2D────][Kernel─][D2H───]
            ↑                                  ↑
            H2D/Kernel/D2H 完美串联            H2D 与 Kernel 重叠良好
```

**理想的 Timeline：** H2D、Kernel、D2H 在三个不同的 Stream 上完全重叠。

### 可视化 Nsight Systems 报告

Nsight Systems GUI 可以：
- 展开每个 Stream 查看操作细节
- 放大到每个 Kernel/Memcpy 的时间
- 测量选择区间的耗时
- 查看 CPU 栈跟踪（定位启动 Kernel 的代码）

## Nsight Compute (ncu)

### 基本使用

```bash
# 基本的 kernel 分析
ncu --set full -o ncu_report ./my_cuda_app

# 分析特定 kernel（按名字）
ncu --kernel-name "vec_add" --set full -o vec_report ./my_cuda_app

# 简短分析（快速检查）
ncu --set basic -o quick_report ./my_cuda_app

# 逐行分析（需要编译时加 -lineinfo）
nvcc -lineinfo -o myapp myapp.cu
ncu --set full --source-include ./myapp
```

### 分析关键指标

#### 1. Occupancy 报告

```
Section: Occupancy
─────────────────────────────────────────────────
Achieved Occupancy       0.532   ← 理论 100%，实际只达到 53%
Theoretical Occupancy    0.750   ← 资源限制导致的 75%
Block Limit SM           8       ← 寄存器是限制因素
Registers Per Thread     56      ← 每线程 56 个寄存器
```

**解读：**
- **Achieved Occupancy < Theoretical Occupancy** → 存在 Block 启动延迟或负载不均
- **Theoretical Occupancy 低** → 减少寄存器或共享内存可以提升
- 高 Occupancy 不总是好事——如果寄存器溢出，性能反而下降

#### 2. Memory vs Compute Utilization

```
Section: Memory
─────────────────────────────────────────────────
Memory Throughput        1.20 TB/s  (35.8% of peak)  ← 带宽利用率低
L1/TEX Hit Rate          68.5%
L2 Hit Rate              49.2%

Section: Compute (Speed of Light)
─────────────────────────────────────────────────
Compute Utilization      82.1%      ← 计算单元繁忙
Memory Utilization       35.8%      ← 内存未充分利用
            ↓
Kernel is COMPUTE BOUND （计算利用率远高于内存）
```

**瓶颈判断：**

| 情况 | 瓶颈 |
|------|------|
| Compute >> Memory | 计算受限 (Compute Bound) |
| Memory >> Compute | 内存受限 (Memory Bound) |
| Both high | 均衡，可能接近峰值 |
| Both low | 延迟受限或 Occupancy 不足 |

#### 3. Speed of Light 分析

```
Speed of Light (Roofline Analysis):
  Roofline Peak Compute:  60.0 TFLOPS
  Roofline Peak Memory:   3.35 TB/s
  Achieved FLOPS:         45.2 TFLOPS  (75.3% of peak)
  Achieved Bandwidth:     1.20 TB/s    (35.8% of peak)
  
  Arithmetic Intensity:    37.6 FLOPS/byte  ← 计算密集
  Compute Bound:           Yes (ridge point: 17.9)
```

**解读：**
- **Arithmetic Intensity**（运算强度）= 计算量 / 数据量
- 高于 Ridge Point → 计算受限
- 低于 Ridge Point → 内存受限

#### 4. Source-Level 分析

逐行分析可以指出哪一行代码消耗了最多的时间：

```
Line   Source                        Durations
  42   float sum = 0.0f;             0.3%    
  43   for (int i = 0; i < N; i++)  
  44       sum += data[tid * N + i];  82.5%   ← 瓶颈在这里
  45   result[tid] = sum;             0.1%
```

## 实际 Profiling 方法论

### Step 1: 全局排查 (nsys)

```bash
nsys profile -o app_profile ./myapp
```

**检查清单：**
- [ ] Memcpy 和 Kernel 是否有重叠
- [ ] 是否有不必要的 CPU-GPU 同步
- [ ] Kernel 启动开销是否明显
- [ ] 是否频繁 cudaMalloc/cudaFree
- [ ] 是否存在 GPU 空闲时间段

### Step 2: 定位热点 Kernel (nsys)

从 nsys 报告中找到消耗时间最长的 Kernel：

```
Kernel            Duration    % of GPU Time
matmul_kernel     120.3 ms    78.2%
softmax_kernel     22.1 ms    14.4%
vec_add_kernel     11.4 ms     7.4%
```

### Step 3: Kernel 级分析 (ncu)

```bash
ncu --kernel-name "matmul_kernel" --set full -o matmul_report ./myapp
```

**检查清单：**
- [ ] Occupancy 是否接近理论值
- [ ] Memory 访问是否是 Coalesced
- [ ] 是否有 Bank Conflict
- [ ] 计算 / 内存利用率百分比
- [ ] 是否存在分支分歧 (Divergence)
- [ ] 寄存器使用是否合理

### Step 4: 针对性优化

| 发现问题 | 优化方法 |
|----------|----------|
| 计算受限 | 使用更快的数学函数（__fmaf），减少冗余计算 |
| 内存受限 | 使用 Shared Memory，确保 Coalesced Access |
| Occupancy 低 | 调整 Block Size，减少寄存器/共享内存 |
| Warp Divergence | 重构分支逻辑，使用 Warp 级函数 |
| Bank Conflict | 调整数据布局 / padding |
| 传输未重叠 | 使用 Stream 和 Pinned Memory |

### Step 5: 验证优化

```bash
nsys profile -o opt_profile ./myapp_opt
ncu --kernel-name "matmul_kernel" --set full -o matmul_opt ./myapp_opt
```

对比优化前后的报告，确认：
- Kernel 耗时是否减少
- Occupancy 是否提升
- Memory/Compute 利用率是否改善
- 整体应用延迟是否降低

## 常见 Profiling 误区

| 误区 | 正解 |
|------|------|
| "Occupancy 一定要 100%" | 高 Occupancy 有助于隐藏延迟，但不是绝对指标 |
| "先优化 Occupancy" | 先找瓶颈类型（计算/内存），再做针对性优化 |
| "只看 ncu 就够" | ncu 只看内核级，全局问题（Stream 重叠）需用 nsys |
| "Profiling 会影响结果" | Nsight Tools 有最小侵入性，但不完全为零（ncu 会插入额外指令） |
| "不用考虑第一次 kernel 启动" | CUDA 第一次 kernel 启动有初始化开销—建议先跑 warmup |

## 总结

| 工具 | 用途 | 关键命令 |
|------|------|---------|
| nsys | 全局时间线、API 追踪、Stream 可视化 | `nsys profile -o out ./app` |
| ncu | Kernel 级分析、瓶颈识别 | `ncu --set full -o out ./app` |
| Roofline | 计算 vs 内存瓶颈判断 | `ncu --set roofline` |

## 参考文献

- NVIDIA. *NVIDIA Nsight Systems User Guide*. https://docs.nvidia.com/nsight-systems/
- NVIDIA. *NVIDIA Nsight Compute User Guide*. https://docs.nvidia.com/nsight-compute/
- NVIDIA. *Nsight Compute Kernel Profiling*. "Profiling Guide." https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html
- NVIDIA. *CUDA C++ Best Practices Guide*. "Chapter 11: Profiling and Timing." https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#profiling-and-timing
- Williams, Samuel, Andrew Waterman, and David Patterson. "Roofline: An Insightful Visual Performance Model for Multicore Architectures." *Communications of the ACM*, vol. 52, no. 4, 2009, pp. 65-76.
