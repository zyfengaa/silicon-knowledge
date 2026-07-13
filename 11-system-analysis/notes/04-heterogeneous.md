# 04 — 异构计算系统

> 异构计算（Heterogeneous Computing）是当代高性能计算和 AI 系统的基本架构模式。它不再试图用单一类型的处理器解决所有问题，而是将 CPU、GPU、NPU、FPGA 等不同类型的计算单元组合在一起，各司其职。

---

## 1. 为什么需要异构

### 1.1 单一架构的局限

| 架构 | 擅长 | 不擅长 |
|------|------|--------|
| CPU | 控制流、分支、串行逻辑 | 大规模并行计算 |
| GPU | 稠密矩阵运算、大规模并行 | 控制流分歧、小批量推理 |
| FPGA | 低延迟流水线、定制数据通路 | 高浮点算力、复杂控制 |
| ASIC/NPU | 特定领域的极致能效 | 灵活性、通用性 |

没有一种架构在所有维度上都最优。

### 1.2 异构的核心思想

```
CPU for what CPUs are good at:
- 控制流 (if/else, loops)
- 系统调度 (线程/进程管理)
- 数据结构操作 (链表、树)
- I/O 管理 (文件、网络)
- 无法并行化的串行部分

GPU/NPU for what accelerators are good at:
- 大规模矩阵运算
- 数据并行处理
- 计算密集型 kernel
```

---

## 2. 典型异构系统架构

### 2.1 CPU + GPU 系统

最经典的异构组合：

```
节点架构:
┌──────────────────────────────────┐
│          CPU Socket               │
│  ┌──────┐  ┌──────┐  ┌──────┐   │
│  │ Core │  │ Core │  │ Core │   │
│  │  L1  │  │  L1  │  │  L1  │   │
│  └──┬───┘  └──┬───┘  └──┬───┘   │
│     └──── L3 Cache ─────┘       │
│              │                   │
│      PCIe / NVLink              │
│              │                   │
│  ┌───────────┴───────────┐       │
│  │   GPU (显存 40-80GB)   │       │
│  │   SM × 132 (H100)      │       │
│  └───────────────────────┘       │
└──────────────────────────────────┘
```

### 2.2 内存模型挑战

异构系统中最大的挑战是**内存模型**：

```
同一地址空间 (Unified Memory):       
CPU 和 GPU 共享同一个虚拟地址空间
但物理地址可能在不同设备上
数据按需迁移 (page migration)

独立地址空间 (Discrete):            
CPU 内存和 GPU 显存完全独立
需要显式的 cudaMemcpy 传输
程序员必须管理数据移动

CPU + GPU 共享内存 (APU 模式):
AMD APU, NVIDIA Grace Hopper
物理上共享同一个内存控制器
无需显式拷贝，但带宽可能受限
```

### 2.3 数据移动开销

```
CPU → GPU 数据传输延迟:
PCIe Gen4 x16: ~25 GB/s 单向
PCIe Gen5 x16: ~50 GB/s 单向
NVLink 4.0:    ~450 GB/s 双向 (H100)

即使使用 NVLink，与 DRAM 带宽 (TB/s 级) 相比仍有差距。

例: 训练中每个 batch 传输输入/输出数据:
batch_size = 1024, 每个样本 1MB
每 batch 传输: 2 × 1024MB = 2GB
PCIe 延迟: 2GB / 25GB/s = 80ms (每步)

→ 如果每步计算只花 10ms，数据传输就是瓶颈。
→ 因此需要双缓冲/流处理来重叠计算和传输。
```

---

## 3. 异构编程模型

### 3.1 CUDA

NVIDIA 的专有编程模型，支持 CPU ↔ GPU 异构：

```cpp
// CPU 端 (host)
void host_function() {
    float *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, N * sizeof(float));
    cudaMalloc(&d_b, N * sizeof(float));
    cudaMalloc(&d_c, N * sizeof(float));
    
    // CPU → GPU 传输
    cudaMemcpy(d_a, h_a, N * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, N * sizeof(float), cudaMemcpyHostToDevice);
    
    // GPU kernel 启动
    vec_add<<<blocks, threads>>>(d_c, d_a, d_b, N);
    
    // GPU → CPU 传输
    cudaMemcpy(h_c, d_c, N * sizeof(float), cudaMemcpyDeviceToHost);
}
```

### 3.2 OpenCL

开放标准，面向 CPU / GPU / FPGA / DSP 的统一编程：

```
OpenCL 抽象:
┌─────────────────────────────────────┐
│  Host (CPU)                         │
│  管理 Context, Command Queue, Kernel │
├─────────────────────────────────────┤
│  Device (GPU / CPU / FPGA)          │
│  ┌─────────────────────────────────┐│
│  │  Compute Unit (CU) × N          ││
│  │  ┌───────────────────────────┐  ││
│  │  │  Processing Element (PE)  │  ││
│  │  │  Kernel 实例执行代码       │  ││
│  │  └───────────────────────────┘  ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

优势：跨平台便携性。劣势：抽象层带来额外开销，性能不如 CUDA。

### 3.3 SYCL

C++ 对 OpenCL 的高级抽象：

```cpp
// SYCL 示例
sycl::queue q;
auto data = sycl::malloc_device<int>(N, q);
q.submit([&](sycl::handler &h) {
    h.parallel_for(sycl::range(N), [=](sycl::id<1> i) {
        data[i] = data[i] * 2;
    });
}).wait();
```

利用 C++ 模板和 lambda，在语法层面更接近主机代码。

### 3.4 Intel oneAPI

Intel 的统一异构编程框架：

```
oneAPI 组件栈:
┌─────────────────────────────┐
│  oneDPL (parallel STL)      │
│  oneMKL (BLAS)              │
│  oneDNN (深度学习)          │
│  oneCCL (集合通信)          │
├─────────────────────────────┤
│  DPC++ (Data Parallel C++)  │
│  = SYCL + extensions        │
├─────────────────────────────┤
│  Level Zero (底层驱动 API)  │
├─────────────────────────────┤
│  CPU │ GPU │ FPGA           │
└─────────────────────────────┘
```

### 3.5 对比

| 模型 | 厂商/标准 | 支持设备 | 性能 | 开发效率 |
|------|----------|---------|------|---------|
| CUDA | NVIDIA | NVIDIA GPU | 最高 | 高 |
| OpenCL | Khronos | CPU/GPU/FPGA/... | 中 | 中 |
| SYCL | Khronos | CPU/GPU/FPGA/... | 高 | 高 |
| oneAPI DPC++ | Intel | Intel CPU/GPU/FPGA | 高 | 高 |
| ROCm/HIP | AMD | AMD GPU | 高 | 中 |
| Metal | Apple | Apple GPU | 高 | 高 |

---

## 4. 异构系统中的关键问题

### 4.1 内存一致性与数据移动

```
问题 1: 数据在哪里?
- CPU 内存? GPU 显存? 统一内存的哪个部分?
- 如何避免不必要的拷贝?

问题 2: 何时移动?
- 可以在计算时预取下一个 batch
- 可以保留常用数据在设备端

问题 3: 谁负责?
- 程序员 (CUDA 显式 cudaMemcpy)
- 运行时 (Unified Memory 自动迁移)
- 编译器 (自动插入拷贝指令)
```

### 4.2 负载均衡

```
问题: CPU 快还是 GPU 快?

不仅取决于硬件峰值性能，还取决于:
1. 数据大小 (GPU 启动开销 ~10μs)
2. 控制流复杂度 (GPU 分支效率低)
3. 数据局部性 (GPU 需要线程级并行)

解决方案: 运行时自动调度
- 维护历史性能数据
- 对于每个 kernel，尝试几次后决定在哪运行
- 动态调整
```

### 4.3 任务依赖与流水线

```
CPU 和 GPU 任务可以重叠:
时间 →
CPU:   [准备数据] [后处理]  [准备数据] [后处理]
GPU:       [计算 A]    [计算 B]    [计算 C]
───────────────────────────────────────────→

通过 CUDA Stream / OpenCL Command Queue 实现
```

---

## 5. 实际系统示例

### 5.1 NVIDIA DGX H100

```
DGX H100 节点:
├── 2× Intel Xeon Platinum CPU
├── 8× H100 GPU
│   └── 通过 NVLink 4.0 全互联 (900 GB/s 双向)
├── 2TB CPU 内存 (DDR5)
├── 80GB × 8 = 640GB GPU 显存 (HBM3)
└── 30TB NVMe SSD
```

### 5.2 Apple M2 Ultra

```
Apple M2 Ultra SoC:
├── 24 CPU 核心 (16 高性能 + 8 高效)
│   └── 共享 L2 cache
├── 76 GPU 核心
│   └── 统一内存架构 (UMA)
├── 32 Neural Engine 核心
├── 192GB 统一内存
│   └── CPU/GPU/NPU 共享带宽 800 GB/s
└── Media Engine (编解码专用)
```

统一内存模型是 Apple SoC 的核心优势——CPU 和 GPU 共享物理内存，无需数据拷贝。

---

## 参考文献

1. NVIDIA. (2022). "CUDA C++ Programming Guide." *NVIDIA Developer Documentation*.
2. Khronos OpenCL Working Group. (2021). "The OpenCL Specification Version 3.0."
3. Khronos SYCL Working Group. (2021). "SYCL Specification 2020."
4. Intel. (2022). "oneAPI Programming Guide." *Intel Corporation*.
5. AMD. (2022). "ROCm Documentation." *AMD Developer*.
6. Apple. (2023). "Apple M2 Ultra Architecture." *Apple Inc.*
7. NVIDIA. (2022). "DGX H100 Architecture Whitepaper." *NVIDIA Corporation*.
8. Mittal, S., & Vetter, J. S. (2015). "A Survey of CPU-GPU Heterogeneous Computing Techniques." *ACM Computing Surveys*, 47(4).
