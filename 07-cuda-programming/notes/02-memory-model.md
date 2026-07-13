# 02 — CUDA Memory Model

> GPU 编程就是管理数据搬运。理解从 Global Memory 到 Register 的每一级，才能写出高效的 CUDA 代码。

## 主机与设备：两级存储

CUDA 编程模型将系统分为 **Host（CPU）** 和 **Device（GPU）**，各自拥有独立的 DRAM：

| 存储位置 | 名称 | 特点 |
|----------|------|------|
| CPU (Host) | Host Memory (CPU DRAM) | 容量大，延迟 ~100ns |
| GPU (Device) | Device Memory (VRAM) | 带宽高（H100 SXM: 3.35 TB/s），延迟 ~200-800 cycles |

数据默认只能在各自的域内访问。需要通过 **显式拷贝** 或 **Unified Memory** 来跨域访问。

```
┌─────────────────────────────────┐
│            Host (CPU)           │
│  ┌───────────────────────────┐  │
│  │     Host Memory (DRAM)    │  │
│  │   可被 CPU 直接访问        │  │
│  └───────┬───────────────────┘  │
│          │ PCIe / NVLink        │
│          ▼                      │
│  ┌───────────────────────────┐  │
│  │   Device Memory (VRAM)    │  │
│  │   GPU 内核可直接访问        │  │
│  └───────────────────────────┘  │
│          Device (GPU)           │
└─────────────────────────────────┘
```

## 显式内存管理

CUDA 提供了最底层的内存管理 API。开发者负责所有的分配、拷贝和释放。

### cudaMalloc — 在 Device 上分配内存

```cuda
float *d_a;
cudaMalloc((void**)&d_a, N * sizeof(float));
```

- 在 GPU VRAM 上分配 N 个 float
- 返回的设备指针只能被 GPU 上的 kernel 使用
- 不能直接在 CPU 上解引用

### cudaMemcpy — 在 Host 和 Device 之间拷贝数据

```cuda
cudaMemcpy(d_a, h_a, N * sizeof(float), cudaMemcpyHostToDevice);  // H2D
cudaMemcpy(h_a, d_a, N * sizeof(float), cudaMemcpyDeviceToHost);  // D2H
```

- **同步操作**：cudaMemcpy 会阻塞 CPU，直到数据传输完成
- 通过 PCIe（~32 GB/s）或 NVLink（H100: 900 GB/s）传输

### cudaFree — 释放 Device 内存

```cuda
cudaFree(d_a);
```

### 典型编程模式

```cuda
// 1. 分配
float *h_a = (float*)malloc(N * sizeof(float));
float *d_a;
cudaMalloc(&d_a, N * sizeof(float));

// 2. 初始化 Host 数据
for (int i = 0; i < N; i++) h_a[i] = i;

// 3. Host → Device 拷贝
cudaMemcpy(d_a, h_a, N * sizeof(float), cudaMemcpyHostToDevice);

// 4. 执行 Kernel
vec_add<<<grid, block>>>(d_a, N);

// 5. Device → Host 拷贝
cudaMemcpy(h_a, d_a, N * sizeof(float), cudaMemcpyDeviceToHost);

// 6. 释放
cudaFree(d_a);
free(h_a);
```

### 错误检查

所有 CUDA API 调用应检查返回值：

```cuda
#define CUDA_CHECK(call) do {                      \
    cudaError_t err = call;                        \
    if (err != cudaSuccess) {                      \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", \
                __FILE__, __LINE__,                \
                cudaGetErrorString(err));          \
        exit(1);                                   \
    }                                              \
} while(0)

CUDA_CHECK(cudaMalloc(&d_a, N * sizeof(float)));
```

## 内存层次结构

CUDA 提供了多级内存，每一级有不同的速度、容量和可见性：

| 内存类型 | 位置 | 作用域 | 延迟 | 容量 | 典型用途 |
|----------|------|--------|------|------|----------|
| Global Memory | VRAM | 所有线程 + Host | ~200-800 cycles | 最大（GB 级） | 输入/输出数据 |
| Shared Memory | SM 上（SRAM） | Block 内所有线程 | ~30 cycles | 小（~48-228 KB/SM） | 协作、缓存 |
| Registers | SM 上 | 线程私有 | 0-1 cycle | 有限（~256/SM） | 中间计算结果 |
| Local Memory | VRAM | 线程私有 | ~200-800 cycles | 无上限 | 寄存器溢出 |
| Constant Memory | VRAM (缓存) | 所有线程 | ~1 cycle (命中时) | 64 KB | 只读常量 |
| Texture Memory | VRAM (缓存) | 所有线程 | ~1 cycle (命中时) | 无上限 | 只读、空间局部性 |

```
Thread
  ├── Registers       ← 最快，线程私有
  ├── Local Memory    ← 在 VRAM 中，慢（寄存器溢出用）
  │
  └── Block
       ├── Shared Memory  ← 片上 SRAM，Block 内共享
       │
       └── Grid
            ├── Global Memory    ← 可被所有线程 + Host 读写
            ├── Constant Memory  ← 只读，有缓存
            └── Texture Memory   ← 只读，有缓存
```

### Global Memory

- 所有线程都可读写
- 延迟最高（200-800 cycles）
- 通过 **Coalesced Access**（对齐合并访问）达到最佳带宽

```cuda
// Coalesced: 相邻线程访问相邻地址（达到峰值带宽）
float value = arr[threadIdx.x];  // Thread 0 → arr[0], Thread 1 → arr[1], ...

// Non-coalesced: 跳跃访问（带宽大幅下降）
float value = arr[threadIdx.x * 16];  // 线程之间隔 16 个元素
```

### Shared Memory

- 片上 SRAM，延迟极低（~30 cycles）
- 同一个 Block 内的所有线程共享
- 分为 **32 Banks**，每个 Bank 每周期可提供一个 32-bit 值

```cuda
__shared__ float cache[256]; // 在 SM 上分配

// 将 Global Memory 数据加载到 Shared Memory
// 每个线程加载一个元素
cache[threadIdx.x] = global_arr[blockIdx.x * blockDim.x + threadIdx.x];

// 同步，确保所有线程的共享内存写完成
__syncthreads();

// 现在从 Shared Memory 读取，延迟远低于 Global Memory
```

**Bank Conflict：** 当多个线程访问同一个 Bank 的不同地址时，访问被串行化。无 Bank Conflict 时，一个 warp 的 Shared Memory 读取只需一次内存操作。

### Registers

- 线程私有，速度最快（0-1 cycle）
- 编译器自动决定变量的寄存器分配
- 如果寄存器不够，变量被 **Spill** 到 Local Memory（实际上在 Global Memory）

```cuda
// 局部变量通常在寄存器中（除非溢出）
int tid = threadIdx.x;
float sum = 0.0f;
for (int i = 0; i < N; i++) {
    sum += data[i];  // sum 很可能在寄存器中
}
```

## Unified Memory (cudaMallocManaged)

Unified Memory 提供了一种 **单一指针** 编程模型，系统自动在 Host 和 Device 之间迁移数据。

```cuda
float *x;
cudaMallocManaged(&x, N * sizeof(float));

// CPU 可以访问 x（触发页面迁移到 Host）
for (int i = 0; i < N; i++) x[i] = i;

// Kernel 可以访问 x（触发页面迁移到 Device）
vec_add<<<grid, block>>>(x, N);

// CPU 可以读取结果（再次触发迁移到 Host）
printf("x[0] = %f\n", x[0]);

cudaFree(x);
```

### Unified Memory 的工作原理

1. **Page Fault 驱动迁移**：访问 Unified Memory 指针时，如果页面不在当前处理器的内存中，触发 Page Fault
2. **自动迁移**：驱动程序将页面迁移到访问方的内存
3. **逐页迁移**：迁移以 4 KB 或 64 KB 页面为单位

```
初始状态: 所有页面在 Host
CPU 访问 x[0..N-1] → 页面在 Host，可以直接访问
GPU 运行 kernel 访问 x[0..N-1] → 触发 Page Fault
    ↓
Driver 将页面从 Host → Device 迁移
    ↓
Kernel 继续执行（等待迁移完成）
```

### Unified Memory 的优缺点

**优点：**
- 简化编程：不需要显式的 cudaMemcpy
- 容易将现有 CPU 代码移植到 GPU
- 对复杂数据结构（链表、树等）尤其方便

**缺点：**
- **Page Fault 开销**：首次访问会导致显著的性能损失
- **细粒度迁移效率低**：不适合频繁在小块数据上来回迁移
- **缺少手动优化**：开发者无法控制数据传输的时机

### 性能对比

| 操作 | 显式管理 | Unified Memory |
|------|----------|----------------|
| 一次性大块拷贝 | 快（直接 DMA） | 类似（触发批量迁移） |
| 多次小数据访问 | 快（开发者控制） | 慢（每次可能有 Page Fault） |
| 复杂数据结构 | 困难（需要手动序列化） | 方便（零拷贝语义） |
| 代码可读性 | 需要显式 cudaMemcpy | 简洁 |

### 何时使用 Unified Memory

**适合：**
- 原型开发 / 快速迭代
- 数据一次性从 Host 拷贝到 Device，计算后拷回
- 稀疏访问模式（不是所有数据都需要）

**不适合：**
- 性能关键的生产环境代码
- 需要在 Host 和 Device 之间高频来回访问
- 追求极限带宽的应用

## Memory 操作的性能建议

1. **使用 cudaMemcpyAsync**（配合 Stream）实现数据传输和计算重叠
2. **使用 Pinned Memory**（cudaHostAlloc）加速 Host-Device 传输
3. **保证 Global Memory 的 Coalesced Access**
4. **使用 Shared Memory 减少 Global Memory 访问**
5. **减少不必要的 cudaMalloc/cudaFree**（复用已分配的缓冲区）

```cuda
// Pinned Memory: 分配固定内存（不可交换到磁盘）
float *h_a;
cudaHostAlloc((void**)&h_a, N * sizeof(float), cudaHostAllocDefault);
// 或者使用 POSIX 函数: mlock(h_a, N * sizeof(float));
```

Pinned Memory 提升了 H2D/D2H 传输带宽（允许 GPU DMA 直接访问），但占用系统物理内存（不可交换）。

## 总结

| 概念 | 要点 |
|------|------|
| Host vs Device | 独立内存域，需要通过拷贝或 UM 交换数据 |
| 显式管理 | cudaMalloc / cudaMemcpy / cudaFree |
| 内存层次 | Register < Shared < Global（速度递增 -> 递减） |
| Coalesced Access | 对齐的连续访问是达到峰值带宽的关键 |
| Shared Memory | 片上 SRAM，Block 内协作的利器 |
| Unified Memory | 方便但可能牺牲性能 |

## 参考文献

- NVIDIA. *CUDA C++ Programming Guide*. "Chapter 5: Memory Hierarchy." https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#memory-hierarchy
- NVIDIA. *CUDA C++ Best Practices Guide*. "Chapter 8: Memory Optimizations." https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#memory-optimizations
- NVIDIA. *CUDA C++ Programming Guide*. "Chapter 9: Unified Memory Programming." https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#um-unified-memory-programming
- Harris, Mark. "How to Access Global Memory Efficiently in CUDA." *NVIDIA Developer Blog*, 2013. https://developer.nvidia.com/blog/how-access-global-memory-efficiently-cuda-c-kernels/
- Garland, Michael. "Unified Memory in CUDA 6." *NVIDIA Developer Blog*, 2013. https://developer.nvidia.com/blog/unified-memory-in-cuda-6/
