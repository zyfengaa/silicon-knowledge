# 04 — Streams 与异步操作

> 让 GPU 同时做多件事：传输数据、执行计算、传输结果。没有 Stream 的 CUDA 程序只用了 GPU 一半的能力。

## 什么是 CUDA Stream

**CUDA Stream** 是一个**有序的操作序列**。在同一个 Stream 中的操作按照提交顺序**串行执行**。不同 Stream 中的操作可以**并发执行**。

```
Stream 0 (Default):  [H2D] → [Kernel A] → [D2H]
Stream 1:            [H2D] → [Kernel B] → [D2H]

时间:  _____________________________________________
Stream 0:     |H2D_A| Kernel_A |D2H_A|
Stream 1:     |H2D_B| Kernel_B |D2H_B|
                      ↓  （如果资源和依赖允许，可以重叠）
Stream 0:     |H2D_A|           |Kernel_A|           |D2H_A|
Stream 1:           |H2D_B|           |Kernel_B|           |D2H_B|
           └──── 时间重叠 ────┘
```

## 默认 Stream (Stream 0)

在没有显式创建 Stream 时，所有操作都在 **Default Stream（Stream 0）** 中执行。

**默认 Stream 的行为取决于 `--default-stream` 编译选项：**

| 编译选项 | 默认 Stream 行为 |
|----------|-----------------|
| `--default-stream legacy` (默认) | 默认 Stream 与所有其他 Stream 同步 |
| `--default-stream per-thread` | 每个线程有自己的默认 Stream，不与其他 Stream 同步 |

```cuda
// 以下操作都在默认 Stream 0 中串行执行
cudaMemcpy(d_a, h_a, size, cudaMemcpyHostToDevice);
vec_add<<<grid, block>>>(d_a, N);
cudaMemcpy(h_a, d_a, size, cudaMemcpyDeviceToHost);
```

## 创建和使用 Stream

### API

```cuda
cudaStream_t stream1, stream2;
cudaStreamCreate(&stream1);   // 创建 Stream
cudaStreamCreate(&stream2);

// 使用 Stream 的 CUDA 操作
kernel<<<grid, block, 0, stream1>>>(d_a, N);
cudaMemcpyAsync(d_b, h_b, size, cudaMemcpyHostToDevice, stream2);

cudaStreamSynchronize(stream1);  // 等待 Stream 1 完成

cudaStreamDestroy(stream1);     // 销毁 Stream
cudaStreamDestroy(stream2);
```

### 关键 API

| 函数 | 用途 |
|------|------|
| `cudaStreamCreate` | 创建新 Stream |
| `cudaStreamDestroy` | 销毁 Stream |
| `cudaStreamSynchronize` | 阻塞 CPU 直到 Stream 所有操作完成 |
| `cudaStreamQuery` | 查询 Stream 状态（完成/未完成） |
| `cudaEventRecord` | 在 Stream 中插入 Event |
| `cudaEventSynchronize` | 等待 Event 完成 |
| `cudaStreamWaitEvent` | 让一个 Stream 等待另一个 Stream 的 Event |

## cudaMemcpyAsync — 异步内存传输

`cudaMemcpyAsync` 是 `cudaMemcpy` 的异步版本，它立即返回，不阻塞 CPU。

```cuda
cudaMemcpyAsync(dst, src, size, cudaMemcpyHostToDevice, stream);
```

### 关键要求：Pinned Memory

**cudaMemcpyAsync 需要 Host 内存是 Pinned（页锁定）的。** 否则会回退到同步行为或报错。

```cuda
// 错误的做法（可能出错或回退到同步）
float *h_a = (float*)malloc(N * sizeof(float));  // Pageable memory
cudaMemcpyAsync(d_a, h_a, size, cudaMemcpyHostToDevice, stream);

// 正确的做法
float *h_a;
cudaHostAlloc((void**)&h_a, N * sizeof(float), cudaHostAllocDefault);
// 或使用 cudaMallocHost
// cudaMallocHost((void**)&h_a, N * sizeof(float));

cudaMemcpyAsync(d_a, h_a, size, cudaMemcpyHostToDevice, stream);
```

**为什么需要 Pinned Memory：**
- Pageable Memory 可能被 OS 换出到磁盘
- GPU DMA 引擎需要物理地址连续的页面
- 使用 Pinned Memory 后，DMA 引擎可以直接在 Host 和 Device 之间传输数据，不需要 CPU 中转

## 重叠模式 (Overlap Pattern)

最常用的 Stream 模式：**H2D → Kernel → D2H** 流水线，通过多个 Stream 实现重叠。

### 单 Stream 基准（无重叠）

```cuda
for (int i = 0; i < N; i++) {
    cudaMemcpy(d_data[i], h_data[i], size, cudaMemcpyHostToDevice);  // H2D
    process_kernel<<<grid, block>>>(d_data[i]);                       // Compute
    cudaMemcpy(h_result[i], d_data[i], size, cudaMemcpyDeviceToHost); // D2H
}
// 总时间 = N × (H2D_time + Compute_time + D2H_time)
// 串行执行，没有重叠
```

```
时间:  ┌─────┐ ┌─────────┐ ┌─────┐
        |H2D_0| |Kernel_0| |D2H_0|
        └─────┘ └─────────┘ └─────┘
                ┌─────┐ ┌─────────┐ ┌─────┐
                |H2D_1| |Kernel_1| |D2H_1|
                └─────┘ └─────────┘ └─────┘
                                          ⋯
```

### 多 Stream 重叠

```cuda
cudaStream_t streams[N];
for (int i = 0; i < N; i++) {
    cudaStreamCreate(&streams[i]);
    
    // 在 Stream i 中提交操作
    cudaMemcpyAsync(d_data[i], h_data[i], size, 
                    cudaMemcpyHostToDevice, streams[i]);
    process_kernel<<<grid, block, 0, streams[i]>>>(d_data[i]);
    cudaMemcpyAsync(h_result[i], d_data[i], size,
                    cudaMemcpyDeviceToHost, streams[i]);
}

for (int i = 0; i < N; i++) {
    cudaStreamSynchronize(streams[i]);
}
```

```
时间:  ┌─────┐ ┌─────────┐ ┌─────┐
       |H2D_0| |Kernel_0| |D2H_0|
       └─────┘                 
              ┌─────┐ ┌─────────┐ ┌─────┐
              |H2D_1| |Kernel_1| |D2H_1|
              └─────┘           └─────┘
                     ┌─────┐ ┌─────────┐ ┌─────┐
                     |H2D_2| |Kernel_2| |D2H_2|
                     └─────┘           └─────┘
```

**理想总时间 ≈ H2D + max(N×compute, N×H2D, N×D2H)**

如果吞吐量平衡，**理论加速为 3 倍**（理想情况下，三个操作完全重叠）。

## 使用 Event 实现 Stream 间同步

Event 允许在不同 Stream 之间设置依赖关系。

```cuda
cudaEvent_t event;
cudaEventCreate(&event);

// Stream A: 计算结果
kernel_A<<<grid, block, 0, streamA>>>(d_a);
cudaEventRecord(event, streamA);  // Stream A 完成后记录 Event

// Stream B: 等待 Stream A 的结果，然后使用
cudaStreamWaitEvent(streamB, event, 0);  // Stream B 等待 event
kernel_B<<<grid, block, 0, streamB>>>(d_a);  // 等 A 完成后

// 测量时间
cudaEvent_t start, stop;
cudaEventCreate(&start);
cudaEventCreate(&stop);

cudaEventRecord(start, stream);
kernel<<<grid, block, 0, stream>>>(d_a);
cudaEventRecord(stop, stream);

cudaEventSynchronize(stop);
float ms;
cudaEventElapsedTime(&ms, start, stop);
```

## Hyper-Q — 32 个 Hardware Work Queue

从 **Kepler (Compute Capability 3.5)** 开始，NVIDIA 引入了 **Hyper-Q**：

- **32 个硬件工作队列**（之前只有 1 个）
- 允许 32 个 Stream 同时在硬件层面上独立调度
- 避免了串行化问题

```
Without Hyper-Q:
  Stream 0 ──→ [1 Queue] ──→ SM
  Stream 1 ──→ [同上]       （需要等待前面操作完成）

With Hyper-Q:
  Stream 0 ──→ [Queue 0] ──→ SM  ← 可以同时
  Stream 1 ──→ [Queue 1] ──→ SM  ← 执行不同操作
  ...
  Stream 31 ──→ [Queue 31] ──→ SM
```

Hyper-Q 使得多个 Stream 可以真正并发执行，而不仅仅是提交后串行化。

## Stream 优先级

CUDA 支持不同优先级的 Stream：

```cuda
int priority_high, priority_low;
cudaDeviceGetStreamPriorityRange(&priority_low, &priority_high);

cudaStream_t high_prio, low_prio;
cudaStreamCreateWithPriority(&high_prio, cudaStreamNonBlocking, priority_high);
cudaStreamCreateWithPriority(&low_prio, cudaStreamNonBlocking, priority_low);
```

高优先级 Stream 中的操作优先于低优先级 Stream 中的操作被调度。

## Stream 的典型使用场景

1. **数据传输与计算重叠**：H2D + Kernel + D2H 流水线
2. **多 GPU 通信**：每个 GPU 对应一个 Stream
3. **优先级调度**：控制计算与数据加载的优先级
4. **并发 MPS**：多进程通过 MPS 共享 GPU 时各自使用 Stream

## 调试 Stream

### 使用 Nsight Systems

Nsight Systems 是最直观的 Stream 分析工具：

```
nsys profile -o timeline ./myapp
```

可以看到：
- 哪些操作在哪些 Stream 上执行
- 操作之间是否有重叠（并行）
- CPU 侧和 GPU 侧的空闲时间段

### 常见问题

| 问题 | 表现 | 原因 |
|------|------|------|
| 没有重叠 | 串行执行 | 使用了 cudaMemcpy 而非 cudaMemcpyAsync |
| 没有重叠 | 串行执行 | Host 内存不是 Pinned Memory |
| 没有重叠 | Kernel 等待传输 | 依赖关系未正确设置 |
| 无效 Stream 错误 | 崩溃 | Stream 未创建或已被销毁 |

## 总结

| 概念 | 要点 |
|------|------|
| CUDA Stream | 有序操作队列，不同 Stream 可并发 |
| Default Stream | Stream 0，默认同步行为 |
| cudaMemcpyAsync | 异步内存传输，需要 Pinned Memory |
| Overlap Pattern | 多个 Stream 实现 H2D / Kernel / D2H 重叠 |
| Event | 跨 Stream 同步和计时 |
| Hyper-Q | 32 硬件队列，多 Stream 真正并发 |
| Pinned Memory | cudaHostAlloc 或 cudaMallocHost |

## 参考文献

- NVIDIA. *CUDA C++ Programming Guide*. "Chapter 3: CUDA Runtime API — Stream." https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#cuda-runtime-api-stream
- NVIDIA. *CUDA C++ Programming Guide*. "Chapter 3: CUDA Runtime API — Event." https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#cuda-runtime-api-event
- NVIDIA. *CUDA C++ Best Practices Guide*. "Chapter 6: Asynchronous and Overlapping Transfers." https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#asynchronous-and-overlapping-transfers-with-computation
- Harris, Mark. "How to Overlap Data Transfers in CUDA." *NVIDIA Developer Blog*, 2012. https://developer.nvidia.com/blog/how-overlap-data-transfers-cuda-cc/
- NVIDIA. "Hyper-Q." *NVIDIA Kepler Architecture Whitepaper*, 2012. https://www.nvidia.com/content/PDF/kepler/NVIDIA-Kepler-GK110-Architecture-Whitepaper.pdf
