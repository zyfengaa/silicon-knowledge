# 06 — 内存优化

> 内存访问模式对 GPU 性能有决定性影响。合并访问（Coalescing）和 Bank Conflict 是 GPU 内存优化的两个核心概念。

---

## 1. 内存合并访问（Memory Coalescing）

### 什么是合并访问

当 warp（32 个线程）同时发出全局内存访问请求时，硬件将这些请求合并为尽可能少的**缓存行事务**。如果访问模式满足合并条件，一次内存事务可满足多个线程的需求。

**不合并 vs 合并**：

```
不合并访问（每次 4 字节 x 32 = 32 次事务）：
线程:   T0  T1  T2  T3  ...  T31
地址:   [0] [N] [2N][3N] ...  [31N]  ← 每次地址跳 N（跨步访问）
        └── 每次独立事务 ────┘

合并访问（1-2 次 128 字节事务）：
线程:   T0  T1  T2  T3  ...  T31
地址:   [0] [4] [8] [12] ...  [124]  ← 连续 128 字节
        └──────── 合并为 1-2 次事务 ────────┘
```

### 合并访问的条件

**基本要求**：

1. **warp 内线程访问连续地址**
2. **起始地址对齐到 128 字节**（L2 缓存行大小）
3. **每个线程读取 4/8/16 字节**（32-bit/64-bit/128-bit）

**详细条件**（取决于计算能力）：

| 计算能力 | 缓存行大小 | 合并条件 |
|---------|-----------|---------|
| 1.x | 64-128 B | 半 warp 内连续 |
| 2.0+ | 128 B | warp 内连续 + 对齐 |
| 6.0+ | 128 B | warp 内连续 + 对齐，更灵活 |

### 示例：合并访问

```cuda
// ✅ 合并访问：warp 内连续，对齐
__global__ void coalesced_kernel(float *out, const float *in, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        out[idx] = in[idx];  // 连续访问：T0 → in[0], T1 → in[1], ...
    }
}
```

**访问模式**（warp 0）：
```
T0 → in[0]     (地址偏移 0)
T1 → in[1]     (地址偏移 4)
T2 → in[2]     (地址偏移 8)
...
T31 → in[31]   (地址偏移 124)

单次 128 字节缓存行事务 → 满足所有 32 个线程
```

### 示例：非合并访问

```cuda
// ❌ 非合并访问：跨步访问
__global__ void strided_kernel(float *out, const float *in, int N, int stride) {
    int idx = (blockIdx.x * blockDim.x + threadIdx.x) * stride;
    if (idx < N) {
        out[idx] = in[idx];  // 跨步访问：T0 → in[0], T1 → in[2], ...
    }
}
```

**访问模式**（stride=2, warp 0）：
```
T0 → in[0]      (地址偏移 0)
T1 → in[2]      (地址偏移 8)
T2 → in[4]      (地址偏移 16)
...
T31 → in[62]    (地址偏移 248)

需要 2 次 128 字节事务（实际仅使用 50% 数据）
```

### 实际带宽对比

| 访问模式 | 有效带宽利用率 | 原因 |
|---------|--------------|------|
| 连续 + 对齐 | ~100% | 每字节都被使用 |
| stride=2 | ~50% | 50% 数据未使用 |
| stride=4 | ~25% | 75% 数据未使用 |
| stride=8 | ~12.5% | 87.5% 数据未使用 |
| stride=16 | ~6.25% | 93.75% 数据未使用 |
| 随机访问 | ~1% | 几乎无缓存复用 |

### 常见非合并访问场景

**场景 1：矩阵按列访问**
```cuda
// 行优先存储，列优先访问
// matrix[col * N + row] → T0=0, T1=N, T2=2N, ...
// stride = N，极大概率非合并
float val = matrix[row * N + col];  // 行优先：✅
float val = matrix[col * N + row];  // 行优先列访问：❌
```

**场景 2：结构体数组（AoS）**
```cuda
// AoS: struct { float x, y, z; } points[N];
// T0 → points[0].x, T1 → points[1].x, ...
// 地址：0, 12, 24, ... → stride=12，非合并 ❌

// SoA: float x[N], y[N], z[N];
// T0 → x[0], T1 → x[1], T2 → x[2], ...
// 地址：0, 4, 8, ... → 连续，合并 ✅
```

**优化方法**：将 AoS 转为 SoA（Array of Structures → Structure of Arrays）

---

## 2. Bank Conflict（存储体冲突）

### 共享内存结构

共享内存由 **32 个存储体（Bank）** 组成，每个 Bank 的宽度为 **4 字节**（32 位）。相邻的 32 位字分布在相邻的 Bank 中：

```
Bank 的映射关系：
地址 0-3     → Bank 0
地址 4-7     → Bank 1
地址 8-11    → Bank 2
...
地址 124-127 → Bank 31
地址 128-131 → Bank 0  (循环)
地址 132-135 → Bank 1  (循环)
...

Bank 地址计算：bank = (address / 4) % 32
```

每个 Bank 在每个周期可以处理一次访问。如果 warp 内多个线程在同一个周期内访问**同一个 Bank 的不同地址**，这些访问会被**串行化**（即产生 Bank Conflict）。

```
无冲突：32 个线程 → 32 个不同 Bank → 1 个周期
┌─────────────────────────────────┐
│ T0→Bank0  T1→Bank1 ... T31→Bank31│
└─────────────────────────────────┘
         ↓
    1 个周期完成

2 路冲突：2 个线程争用同一 Bank → 2 个周期
┌─────────────────────────────────┐
│ T0→Bank0  T1→Bank1              │
│ T16→Bank0(冲突!)  T17→Bank1(冲突!)│
└─────────────────────────────────┘
         ↓
    2 个周期完成
```

### Bank Conflict 的代价

```
冲突路数    有效带宽
   1       100%
   2        50%
   4        25%
   8       12.5%
  16        6.25%
  32        3.125%
```

当 32 个线程都访问同一个 Bank 时，带宽降至 1/32 —— 但这种极端情况可以通过**广播**机制部分缓解（所有线程读取同一地址时，硬件可广播）。

### 示例：无冲突访问

```cuda
__shared__ float s_data[256];

// ✅ 无 Bank Conflict：每个线程访问连续地址
// T0 → s_data[0], T1 → s_data[1], ..., T31 → s_data[31]
// Bank 分布：0, 1, 2, ..., 31 → 全不冲突
float val = s_data[threadIdx.x];
```

### 示例：有冲突访问

```cuda
__shared__ float s_data[256];

// ❌ 2 路 Bank Conflict：步长为 2
// T0 → s_data[0]  (Bank 0)
// T1 → s_data[2]  (Bank 2)
// ...
// T31 → s_data[62] (Bank 62 % 32 = 30)
// 冲突情况：N 和 N+32 映射到同一 Bank
// 实际：24 个不同 Bank 被访问，其中 8 个 Bank 有 2 路冲突
float val = s_data[threadIdx.x * 2];
```

```cuda
// ❌ 32 路 Bank Conflict：所有线程访问同一 Bank
// T0 → s_data[0]  (Bank 0)
// T1 → s_data[32] (Bank 0) ← 冲突！
// T2 → s_data[64] (Bank 0) ← 冲突！
// ...
// T31 → s_data[992] (Bank 0) ← 冲突！
// 32 路冲突 → 32 个周期完成
float val = s_data[threadIdx.x * 32];
```

```cuda
// 广播特例：所有线程访问同一地址
// T0 → s_data[5]  (Bank 5)
// T1 → s_data[5]  (Bank 5) ← 硬件广播，无冲突
// T2 → s_data[5]  (Bank 5) ← 硬件广播，无冲突
// ...
// 一次访问满足所有线程
float val = s_data[5];  // 所有线程读同一个地址 → 无冲突（广播）
```

### 避免 Bank Conflict 的技巧

**技巧 1：填充（Padding）**

通过添加额外的列来破坏步长规律：

```cuda
// 无填充：列数为 32 的倍数 → 32 路 Bank Conflict
__shared__ float s_mat[32][32];
// 访问 s_mat[tx][ty]：
// 同一行在不同列 → (tx, 0): Bank=tx, (tx, 1): Bank=tx → 冲突

// 填充：列数设为 33 → Bank 分布被打散
__shared__ float s_mat[32][33];  // 注意第二维是 33
// 访问 s_mat[tx][ty]：
// (tx, 0): Bank = tx % 32
// (tx, 1): Bank = (33+tx) % 32 = (tx+1) % 32 → 不冲突!
```

**技巧 2：数据重排**

修改数据存储布局以减少 Bank Conflict：

```cuda
// Bank-friendly 布局：交错存储
// 将 s_data[i] 重排为 s_data[i ^ (i >> 5)] 等
// 高级技巧，通常不需要手动处理
```

**技巧 3：利用 Warp 级原语**

使用 `__shfl_*` 避免共享内存访问：

```cuda
// 使用 shfl 替代共享内存访问
float val = __shfl_xor_sync(0xFFFFFFFF, local_val, 1);
// 无需共享内存 → 无 Bank Conflict
```

---

## 3. 合并访问与 Bank Conflict 的关系

| 对比 | 合并访问 | Bank Conflict |
|------|---------|--------------|
| 作用域 | 全局内存访问 | 共享内存访问 |
| 粒度 | warp（32 线程） | warp（32 线程） |
| 优化目标 | 减少内存事务数 | 减少 Bank 争用 |
| 核心思想 | 连续对齐访存 | 分散 Bank 映射 |
| 硬件机制 | L1/L2 缓存合并 | 32 个 Bank 并行 |

两者独立但都关系到内存性能：全局内存优化关注合并访问，共享内存优化关注 Bank Conflict。

---

## 参考文献

- Kirk, D. B. & Hwu, W. W., *Programming Massively Parallel Processors: A Hands-on Approach*, 3rd ed., Chapter 5: Memory Architecture and Data Locality, Chapter 6: Performance Considerations, Morgan Kaufmann, 2016.
- NVIDIA, *CUDA C++ Best Practices Guide*, Section 6: Memory Optimizations, Section 6.1: Coalesced Access to Global Memory, Section 6.2: Shared Memory Bank Conflicts.
- NVIDIA, *CUDA C++ Programming Guide*, Section 5.3: Shared Memory, Section 5.3.2: Shared Memory Bank Conflicts.
- Harris, M., "How to Access Global Memory Efficiently", *NVIDIA Developer Blog*, 2012.
- Harris, M., "Using Shared Memory in CUDA", *NVIDIA GPU Gems*, 2007.
- Jia, Z. et al., "Dissecting the NVIDIA Volta GPU Architecture via Microbenchmarking", *arXiv:1804.06826*, 2018. Section: Global Memory and Coalescing.
- NVIDIA, *PTX ISA (Parallel Thread Execution ISA)*, Section: Memory Consistency Model.
