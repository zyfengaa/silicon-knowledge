# 模块 06：GPU 架构（GPU Architecture）-- 练习题

## 06-gpu-q.md：问题与练习

---

## 第 1 节：SIMT 与 SIMD 对比（SIMT vs SIMD）

### 问题 1.1

解释 SIMT 与 SIMD 的关键区别。给出一个具体的代码示例，该代码在 SIMT 中高效运行，但在 SIMD 中难以或无法实现。

### 问题 1.2

考虑以下 CUDA kernel：

```cuda
__global__ void kernel(float *data, int *keys, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        float val = data[idx];
        // 基于运行时数据的间接索引访问
        float result = data[keys[idx]] + val;
        data[idx] = result;
    }
}
```

解释为什么该 kernel 在 SIMT（CUDA）中非常简单，但在 SIMD（例如 AVX）中却极其困难或低效。GPU 中有哪些具体的硬件特性使这成为可能？

### 问题 1.3

在 SIMD 中，程序员必须确保数据是连续且对齐的。在 SIMT 中，合并访问（coalescing）是一种性能优化，但不是正确性的必要条件。解释这一差异背后的架构原因。

---

## 第 2 节：Warp 分歧（Warp Divergence）

### 问题 2.1

展示一个会导致 warp 分歧的 if/else 条件。给定以下代码：

```cuda
if (threadIdx.x < 16) {
    // 路径 A：10 条指令
    result = a * b + c * d;
} else {
    // 路径 B：15 条指令
    result = expf(a) + logf(b);
}
```

假设 50% 的线程走路径 A，50% 走路径 B。计算：
a) 执行这个分歧分支需要多少个周期？
b) 在执行每条路径期间，利用率（活跃线程数/总线程数）是多少？
c) 两条路径的整体利用率是多少？
d) 如果两条路径各有 12 条指令并使用谓词执行（predication，所有线程执行所有指令），需要多少个周期？哪种方法更好？

### 问题 2.2

以下哪些条件会导致 warp 分歧？解释原因：

```cuda
// (a)
if (threadIdx.x % 2 == 0) { ... } else { ... }

// (b)
if (blockIdx.x > 0) { ... } else { ... }

// (c)
if (data[threadIdx.x] > 0.0f) { ... } else { ... }

// (d)
switch (threadIdx.x / 8) {
    case 0: ... break;
    case 1: ... break;
    case 2: ... break;
    case 3: ... break;
}
```

### 问题 2.3

描述三种避免或缓解 warp 分歧的编程策略。为每种策略提供代码示例。

---

## 第 3 节：合并访问分析（Coalescing Analysis）

### 问题 3.1

给定一个包含 128 个线程的线程块（thread block），每个线程读取一个 float（4 字节），分析以下三种访问模式。识别哪些是合并的（coalesced），哪些不是，并解释原因。

```cuda
// 模式 (a)
float val = array[threadIdx.x];

// 模式 (b)
float val = array[threadIdx.x * 2];

// 模式 (c)
float val = array[blockIdx.x * blockDim.x + threadIdx.x];
```

对于每种模式，计算：
- 单个 warp（32 个线程）访问的地址范围
- 产生多少次 128 字节缓存行传输（cache line transactions）
- 带宽利用率（有用字节数 / 总传输字节数）

### 问题 3.2

假设一个 GPU 具有 128 字节缓存行。一个包含 32 个线程的 warp 以步长 S 读取 4 字节的 float。填写下表：

| 步长 S | 每个 warp 的地址范围（字节） | 获取的缓存行数 | 带宽利用率 |
|----------|-------------------------------|--------------------|----------------|
| 1 | | | |
| 2 | | | |
| 4 | | | |
| 8 | | | |

### 问题 3.3

解释共享内存分块（shared memory tiling，如分块矩阵乘法中使用的）如何改善全局内存的合并访问。为什么矩阵乘法中朴素的全局内存 kernel 对两个输入矩阵之一的合并访问较差？

---

## 第 4 节：Bank 冲突检测（Bank Conflict Detection）

### 问题 4.1

给定具有 32 个 bank（每个 4 字节宽）的共享内存，分析以下哪些访问模式会导致 bank 冲突。展示每个模式的 bank 映射（bank = (address / 4) % 32）。

```cuda
__shared__ float shmem[1024];

// 模式 (a) — 无冲突场景
float a = shmem[threadIdx.x];

// 模式 (b) — 步长为 2
float b = shmem[threadIdx.x * 2];

// 模式 (c) — 质数步长
float c = shmem[threadIdx.x * 33];
```

对于每种模式，确定：
- 第一个 warp（32 个线程）访问了多少个不同的 bank
- 存在多少种 bank 冲突
- 有效带宽倍数（理想 = 32，最差 = 1）

### 问题 4.2

考虑一个声明为 `__shared__ float s_data[32][32]` 的二维共享内存数组。一个包含 32 个线程的 warp（threadIdx.x 范围 0-31，threadIdx.y 固定）按以下方式访问该数组：

```cuda
// 模式 1：行主序（row-major）
float v1 = s_data[threadIdx.x][threadIdx.y];

// 模式 2：列主序（column-major）
float v2 = s_data[threadIdx.x][threadIdx.y];
```

等等——两者看起来一样。让我们更精确一些。线程 (tx, ty) 执行：

```cuda
// 模式 1：无冲突
float val = s_data[tx][ty];  // tx = threadIdx.x, ty = threadIdx.y

// 模式 2：bank 冲突
float val = s_data[ty][tx];  // 交换：tx = threadIdx.x, ty = threadIdx.y
```

假设一个二维块 `dim3 block(32, 32)`：
- 对于模式 1，当 `ty` 在 warp 内变化时分析访问模式（warp = 具有相同 tx、不同 ty 的线程）。提示：连续的 ty 值是否在同一个 bank 中？
- 对于模式 2，当 `tx` 在 warp 内变化时分析访问模式（warp = 具有相同 tx、不同 ty 的线程）。展示 bank 映射。
- 如何使用填充（padding）修复模式 2？

### 问题 4.3

解释在共享内存 bank 冲突上下文中的"广播（broadcast）"。当一个 warp 中的多个线程读取完全相同的地址时，硬件如何处理？这与多个线程读取映射到同一 bank 的不同地址有何不同？

---

## 第 5 节：Tensor Core 编程（Tensor Core Programming）

### 问题 5.1

描述三种受益于 Tensor Core 的矩阵运算类型。对于每种运算，指定：
- 操作维度（M, N, K）
- 精度要求
- 典型应用领域

### 问题 5.2

Tensor Core 操作的精度要求是什么？列出在不同 Tensor Core 世代（Volta 到 Hopper）中支持的至少三种精度模式。对于每种模式，说明：
- 输入精度
- 累加精度
- 相对于 FP32 的计算吞吐量（近似值）

### 问题 5.3

在什么情况下，尽管 Tensor Core 的峰值吞吐量更高，你仍不想使用它们？描述至少三个场景，并解释为什么 Tensor Core 在每种情况下不是最优选择。

### 问题 5.4

WMMA（Warp Matrix Multiply-Accumulate）API 要求特定的分块大小（例如 16x16x16）。解释：
- 为什么分块大小被限制在特定值（什么硬件限制导致了这一点？）
- 如何使用 Tensor Core 计算任意维度（例如 N=1000）的矩阵
- 为什么线程块必须至少包含一个 warp（32 个线程）

### 问题 5.5

比较 Tensor Core 与脉动阵列（systolic array，如 Google TPU 中使用的）。对于每种架构，描述：
- 数据流模型
- 精度灵活性
- 可编程性
- 何时更偏好其中一种

---

## 答题指南（Answer Guidelines）

- 对于分歧计算（第 2 节），清晰展示每条路径的活跃线程数
- 对于合并访问分析（第 3 节），显式计算地址范围
- 对于 bank 冲突分析（第 4 节），至少展示一个线程索引的 bank 计算过程
- 对于 Tensor Core 问题（第 5 节），参考具体的 NVIDIA 架构白皮书

---

## 参考文献（References）

1. NVIDIA. *CUDA C++ Programming Guide*. 2024. — 第 4 章：硬件实现（SIMT 模型），第 9 章：WMMA API。
2. Kirk, D. B., & Hwu, W. W. *Programming Massively Parallel Processors: A Hands-on Approach*. 第 4 版. Morgan Kaufmann, 2022. — 第 4-6 章。
3. NVIDIA. *NVIDIA A100 Tensor Core GPU Architecture Whitepaper*. 2020.
4. NVIDIA. *NVIDIA H100 Tensor Core GPU Architecture Whitepaper*. 2022.
5. Harris, M. "How to Access Global Memory Efficiently." *NVIDIA Developer Blog*, 2013.
6. NVIDIA. "CUDA Pro Tip: Use Shared Memory to Reduce Global Memory Accesses." *NVIDIA Developer Blog*, 2014.
7. NVIDIA. *CUDA C++ Best Practices Guide*. 2024. — 第 9 章：内存优化。
