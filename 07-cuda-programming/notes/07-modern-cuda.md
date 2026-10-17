# 07 — 现代 CUDA 特性

> 这一篇把散落在各章中的现代特性集中起来：异步拷贝流水线、TMA、CUDA Graphs、统一内存进阶、内存一致性模型和流序内存分配。掌握它们是写出接近峰值性能 kernel 的前提。

---

## 1. 异步拷贝与流水线（Ampere `cp.async`）

Ampere（compute capability 8.0）引入 `cp.async`：从全局内存直接拷贝到共享内存，**不经过寄存器**，并允许计算与拷贝重叠。

```cuda
#include <cuda_pipeline.h>

__shared__ float tile[STAGES][TILE];

// 预取前 STAGES-1 个 stage
for (int s = 0; s < STAGES - 1; ++s) {
    __pipeline_memcpy_async(&tile[s][threadIdx.x],
                            &gmem[(s * TILE) + threadIdx.x],
                            sizeof(float));
    __pipeline_commit();          // 提交当前 stage
}

for (int t = 0; t < num_tiles; ++t) {
    // 等待最早提交的 stage 完成，保留后面的在途
    __pipeline_wait_prior(STAGES - 2);
    __syncthreads();

    // 计算 tile[t % STAGES]
    compute(tile[t % STAGES]);

    // 预取下一个 stage
    int next = t + STAGES - 1;
    if (next < num_tiles) {
        __pipeline_memcpy_async(&tile[next % STAGES][threadIdx.x],
                                &gmem[next * TILE + threadIdx.x],
                                sizeof(float));
        __pipeline_commit();
    }
    __syncthreads();
}
__pipeline_wait_prior(0);
```

要点：

- `cp.async` 的粒度是 4/8/16 字节；16 字节（`float4`）最有效。
- `__pipeline_commit()` 把已发起的拷贝组成一个 group；`__pipeline_wait_prior(N)` 等待除最近 N 个 group 外的所有 group。
- 多 stage（双缓冲/三缓冲）才能把访存延迟藏到计算后面。
- Ampere 的 `cp.async` 每个线程都可以发起；Hopper 的 TMA 则用一条指令搬运整块多维张量，二者是演进关系。

C++ 风格的等价接口：

```cuda
#include <cuda/barrier>
#include <cuda/pipeline>
#include <cooperative_groups.h>
namespace cg = cooperative_groups;

auto block = cg::this_thread_block();

// 每个线程持有自己的 pipeline 对象
cuda::pipeline<cuda::thread_scope_block> pipe = cuda::make_pipeline();

pipe.producer_acquire();
cuda::memcpy_async(block, smem, gmem, cuda::aligned_size_t<16>(bytes), pipe);
pipe.producer_commit();
pipe.consumer_wait();
```

### Hopper TMA（简述）

Hopper 的 TMA 把"发地址、算索引"的工作交给专用引擎：

- 主机侧用 `cuTensorMapEncodeTiled` 创建张量描述符；
- kernel 中用 `cp.async.bulk.tensor`（或 `cuda::memcpy_async` 的 TMA 路径）发起 1D–5D 拷贝；
- 用 `mbarrier` 等待完成，可与 warp specialization 配合。

TMA 的收益是**指令数大幅减少**（不再需要每线程计算地址），并支持 multicast 到多个 CTA。细节见 06 模块的《Hopper 与 Blackwell》。

---

## 2. CUDA Graphs

固定拓扑的重复执行适合用图表示。捕获方式：

```cuda
cudaGraph_t graph;
cudaGraphExec_t exec;

cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal);
for (int i = 0; i < layers; ++i) {
    layer_forward<<<grid, block, 0, stream>>>(d_x, d_w[i]);
}
cudaStreamEndCapture(stream, &graph);
cudaGraphInstantiate(&exec, graph, NULL, NULL, 0);   // CUDA 11 的五参数签名
// CUDA 12 起使用：cudaGraphInstantiate(&exec, graph, 0);

for (int iter = 0; iter < 1000; ++iter) {
    cudaGraphLaunch(exec, stream);
}
```

注意：

- 捕获期间不能使用同步 API（如 `cudaDeviceSynchronize`）或默认 stream 的隐式同步操作。
- 图一旦实例化，参数可通过 `cudaGraphExecKernelNodeSetParams` 更新，而不必重新捕获。
- 对动态形状，可配合 `cudaGraphExecUpdate` 或条件节点（CUDA 12.3+）。

CUDA Graphs 主要消除 **CPU 端启动开销**，对短 kernel、层数多的推理/训练循环效果明显；它不会降低单个 kernel 的 GPU 执行时间。

---

## 3. 统一内存进阶

基础用法见 02 篇。生产环境通常需要显式控制迁移：

```cuda
// kernel 前预取到 GPU
cudaMemPrefetchAsync(x, bytes, device, stream);

// 只读共享：允许其他设备直接远程访问，避免反复迁移
cudaMemAdvise(x, bytes, cudaMemAdviseSetReadMostly, device);

// 指定首选位置
cudaMemAdvise(x, bytes, cudaMemAdviseSetPreferredLocation, device);

// 允许某设备建立映射（不迁移）
cudaMemAdvise(x, bytes, cudaMemAdviseSetAccessedBy, device);
```

现代系统上的相关机制：

- **访问计数器**：Pascal 及之后，GPU 通过页表访问位判断"谁在用这块内存"，从而做出更合理的迁移/复制决策。
- **HMM（Heterogeneous Memory Management）**：让 CPU 与 GPU 共享同一套页表，支持按需迁移和原子操作。
- **ATS（Address Translation Services）**：PCIe 设备通过 IOMMU 直接使用 CPU 页表，减少锁页和暂存拷贝。
- **Grace Hopper**：CPU 与 GPU 通过 NVLink-C2C 连接，提供一致的地址空间和 900 GB/s 双向带宽。

实践建议：对性能敏感的代码，仍应优先使用显式拷贝 + pinned memory + 双缓冲；统一内存适合复杂数据结构、稀疏访问和快速原型。

---

## 4. 内存一致性模型

CUDA 采用**弱一致性（weak consistency）**模型：没有同步时，一个线程的写不保证按程序顺序被其他线程看到。

### 常用同步原语

| 原语 | 作用域 | 语义 |
|------|--------|------|
| `__threadfence_block()` | Block | 保证本线程此前的写对本 block 线程可见 |
| `__threadfence()` | Device | 保证对本 GPU 所有线程可见（设备范围） |
| `__threadfence_system()` | System | 设备 + 主机 + 其他 peer GPU |
| `atomicAdd` 等 | 视函数而定 | 原子读改写，但单独使用不构成完整的内存屏障（除 `_system` 版本外） |

### 典型的 flag 握手

```cuda
__device__ int data_ready = 0;
__device__ int payload = 0;

// 生产者
payload = 42;
__threadfence();          // 确保 payload 的写先于 flag 可见
atomicExch(&data_ready, 1);

// 消费者
while (atomicAdd(&data_ready, 0) == 0) { /* spin */ }
__threadfence();          // 或使用 acquire 语义
int v = payload;          // 保证读到 42
```

### C++ 原子与内存序

`<cuda/atomic>` 提供 `cuda::atomic_ref` / `cuda::atomic`，可指定作用域和内存序：

```cuda
#include <cuda/atomic>

cuda::atomic_ref<int, cuda::thread_scope_device> flag(data_ready);
flag.store(1, cuda::memory_order_release);

// 消费者
while (flag.load(cuda::memory_order_acquire) == 0) {}
```

- `release` 保证此前的写不会被重排到 store 之后；
- `acquire` 保证后续读不会被重排到 load 之前；
- `thread_scope_device` 对应一个 GPU，`thread_scope_system` 对应 CPU + 所有 GPU。

### 常见错误

- 用 `volatile` 代替原子/屏障：`volatile` 只阻止编译器优化，不提供跨线程顺序保证。
- 在 block 内用 `__threadfence()`：开销过大，`__threadfence_block()` 已足够。
- 忘记 `__syncthreads()`：共享内存的写需要 block 级同步才能被其他线程看到。

---

## 5. 流序内存分配（cudaMallocAsync）

CUDA 11.2 引入流序分配器，把分配/释放变成 stream 上的异步操作：

```cuda
void *p;
cudaMallocAsync(&p, bytes, stream);
kernel<<<grid, block, 0, stream>>>(p);
cudaFreeAsync(p, stream);
```

- 底层是 per-device memory pool，分配通常从池中取块，避免 `cudaMalloc` 的全局同步。
- 池的行为可配置：

```cuda
cudaMemPool_t pool;
cudaDeviceGetMemPool(&pool, device);
cudaMemPoolSetAttribute(pool, cudaMemPoolReuseFollowEventDependencies, &enable);
```

- 适合动态生命周期、频繁分配的场景；也可与 CUDA Graphs 结合。

---

## 6. 选型建议

| 需求 | 推荐 |
|------|------|
| 稳定的重复 kernel 序列 | CUDA Graphs |
| 全局→共享的大块/多维搬运 | TMA（Hopper+）；Ampere 用 `cp.async` |
| 复杂指针结构、稀疏访问 | 统一内存（配合 prefetch/advise） |
| 高频小块分配 | `cudaMallocAsync` + memory pool |
| 跨线程/跨设备通信 | `cuda::atomic` + 明确的内存序和 scope |

---

## 参考文献

- NVIDIA, *CUDA C++ Programming Guide*: Asynchronous Data Copies, CUDA Graphs, Unified Memory Programming, Memory Model.
- NVIDIA, *CUDA C++ Best Practices Guide*: Memory Optimizations, Execution Configuration.
- NVIDIA, *PTX ISA*: `cp.async`, `mbarrier`, `cp.async.bulk`, memory consistency model.
- NVIDIA, *CUTLASS Documentation*: pipelined GEMM on Ampere/Hopper.
- Harris, M. & Garland, M., NVIDIA Developer Blog: CUDA Graphs 与 Unified Memory 系列文章.
