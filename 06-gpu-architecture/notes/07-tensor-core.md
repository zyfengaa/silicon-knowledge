# 07 — Tensor Core

> Tensor Core 是 NVIDIA GPU 中专为矩阵乘法加速设计的专用硬件单元，是深度学习训练和推理性能提升的核心驱动力。

---

## 1. 为什么需要 Tensor Core

### 矩阵乘法在深度学习中的作用

深度学习的大部分计算量来自矩阵乘法：

- **全连接层**：`Y = X · W + b`
- **卷积层**：通过 im2col 或 Winograd 转化为矩阵乘法
- **注意力机制**：`Attention(Q,K,V) = softmax(QK^T/√d) · V`（Transformer 的核心）
- **Batch Normalization**、**Layer Normalization** 等也包含矩阵运算

### 通用 GPU 的问题

通用 CUDA Core 执行矩阵乘法时存在效率瓶颈：

```
C[M][N] = A[M][K] × B[K][N]

CUDA Core 实现：
- 需要大量指令（ld, mul, add, st）
- 寄存器压力大
- 需要共享内存做 tiling
- 控制逻辑开销大
```

**Tensor Core 解决方案**：使用专用硬件直接执行 `D = A × B + C` 运算，一条指令完成一次 4×4 矩阵乘加。

---

## 2. Tensor Core 架构

### 基本运算

Tensor Core 执行**矩阵乘加**（matrix multiply-accumulate）运算：

```
D = A × B + C

其中：
A: m×k 矩阵
B: k×n 矩阵  
C: m×n 矩阵（累加矩阵）
D: m×n 矩阵（输出矩阵）
```

在 Volta 架构中，Tensor Core 被设计为在 warp 级工作：warp 中 32 个线程协作完成一次矩阵乘法。

### 运算的编组（Warp-Level Matrix Multiply-Accumulate, WMMA）

Tensor Core 不是每个线程独立操作的单元，而是**整个 warp 协同工作**：

```
Warp（32 个线程）协作：
┌────────────────────────────────────────────────┐
│  每个线程持有 A 的一部分 + B 的一部分            │
│  Tensor Core 将 A×B+C 的结果写入到所有线程的寄存器 │
│  所有线程一起构成完整的 C 矩阵                    │
└────────────────────────────────────────────────┘
```

CUDA WMMA API（`nvcuda::wmma`）提供了使用 Tensor Core 的接口：

```cuda
#include <cuda_fp16.h>
#include <mma.h>

using namespace nvcuda;

__global__ void tensor_core_mm(half *a, half *b, float *c, int M, int N, int K) {
    // 声明 warp 级矩阵片段
    wmma::fragment<wmma::matrix_a, 16, 16, 16, half, wmma::row_major> a_frag;
    wmma::fragment<wmma::matrix_b, 16, 16, 16, half, wmma::col_major> b_frag;
    wmma::fragment<wmma::accumulator, 16, 16, 16, float> c_frag;
    
    // 初始化累加器
    wmma::fill_fragment(c_frag, 0.0f);
    
    // 加载数据到片段
    wmma::load_matrix_sync(a_frag, a + offset, K);
    wmma::load_matrix_sync(b_frag, b + offset, K);
    
    // 执行矩阵乘加：c_frag = a_frag × b_frag + c_frag
    wmma::mma_sync(c_frag, a_frag, b_frag, c_frag);
    
    // 存储结果
    wmma::store_matrix_sync(c + offset, c_frag, N, wmma::mem_row_major);
}
```

### 混合精度

Tensor Core 的核心能力是**混合精度计算**：

| 精度模式 | 输入精度 | 累加精度 | 相对性能（基础单位） |
|---------|---------|---------|------------------|
| FP16 | FP16 | FP16/FP32 | 1× |
| BF16 | BF16 | FP32 | ~1× |
| TF32 | TF32 (19-bit) | FP32 | ~0.5× |
| INT8 | INT8 | INT32 | ~2× |
| INT4 | INT4 | INT32 | ~4× |
| FP8 (E4M3/E5M2) | FP8 | FP32 | ~2× |

**TF32（Tensor Float 32）**—— Ampere 引入：
- 10-bit 指数（同 FP32），8-bit 尾数（同 FP16）
- 输入精度从 23-bit 减少到 10-bit，输出保持 FP32 精度
- 不修改代码即可获得 ~8× 加速（配合自动混合精度）

---

## 3. Tensor Core 代际演进

### Volta (2017) — 第 1 代

- 第一代 Tensor Core
- 支持 4×4×4 矩阵乘法：FP16 输入，FP32 累加
- 每个 SM 有 8 个 Tensor Core
- FP16 TFLOPS: V100 约 125 TFLOPS（对比 FP32 15.7 TFLOPS）

### Turing (2018) — 第 2 代

- 增加 INT8、INT4 支持
- 增加 INT1（二进制神经网络支持）
- 独立的 Tensor Core + CUDA Core 管线
- 支持稀疏化推理

### Ampere (2020) — 第 3 代

- 增加 BF16、TF32、FP64 支持
- 支持**结构化稀疏**（2:4 sparse）：利用特有空值模式，^TFLOPS翻倍
- TF32 模式下无需修改代码获 8× 加速
- 单 SM 性能大幅提升

### Hopper (2022) — 第 4 代

- 增加 FP8 (E4M3/E5M2) 支持
- **Transformer Engine**：自动检测精度需求，切换 FP8/FP16
- 支持 async copy（从全局内存到共享内存的 DMA，独立于计算）
- DPX 指令加速动态规划算法
- Tensor Core 使用率进一步提升

### Blackwell (2024) — 第 5 代

- 第 5 代 Tensor Core 支持 FP4、FP6
- NF4（Normal Float 4）—— 适配权重的非均匀 4-bit 格式
- 单 SM 的 Tensor Core 密度进一步增加
- 支持第二代 Transformer Engine

### 性能演进

| GPU | 架构 | 核心规格 | FP16 TFLOPS | INT8 TFLOPS | FP8 TFLOPS |
|-----|------|---------|------------|------------|-----------|
| V100 | Volta | 1st Gen | 125 | — | — |
| T4 | Turing | 2nd Gen | 65 | 130 | — |
| A100 | Ampere | 3rd Gen | 312 | 624 | — |
| H100 | Hopper | 4th Gen | 989 | 1,979 | 1,979 |
| B200 | Blackwell | 5th Gen | 2,250 | 4,500 | 4,500 |

---

## 4. Tensor Core 编程模型

### 使用 CUDA WMMA API

```cuda
#include <mma.h>
using namespace nvcuda::wmma;

// 定义片段类型
// fragment<matrix_a, 16, 16, 16, half, row_major>
// 参数: M=16, N=16, K=16, 类型=half, 布局=行主序

// 支持的矩阵尺寸:
// mma_sync 的 M×N×K 可选值:
// - 16×16×16 (Volta+)
// - 8×32×16   (Volta+, M=8, N=32)
// - 32×8×16   (Volta+, M=32, N=8)
// - 8×8×4     (Turing+)
```

### 使用 cuBLAS 的 Tensor Core 后端

cuBLAS 自动检测并使用 Tensor Core（需要设置 `CUBLAS_TF32_TENSOR_OP_MATH=1` 或使用 `cublasSetMathMode`）：

```c
cublasHandle_t handle;
cublasCreate(&handle);

// 启用 Tensor Core
cublasSetMathMode(handle, CUBLAS_TF32_TENSOR_OP_MATH);

// cublasGemmEx 自动使用 Tensor Core
cublasGemmEx(handle, ...);
```

### 使用 cuDNN 的 Tensor Core 后端

cuDNN 在卷积实现中自动使用 Tensor Core：

```c
cudnnSetConvolutionMathType(convDesc, CUDNN_TENSOR_OP_MATH);
cudnnConvolutionForward(handle, ...);
```

### 使用 PyTorch

PyTorch 的自动混合精度（AMP）自动利用 Tensor Core：

```python
# 自动混合精度训练
with torch.cuda.amp.autocast():
    output = model(input)
    loss = criterion(output, target)

# 或显式设置 TF32
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

---

## 5. Tensor Core 性能优化

### 性能峰值条件

要获得 Tensor Core 的理论峰值需要：

1. **分块尺寸匹配**：M, N, K 是 16 的倍数
2. **数据布局对齐**：矩阵行对齐（row-major 或 col-major 对齐到 128 字节）
3. **持续运算**：尽量减少 Tensor Core 启动/停止的开销
4. **隐藏内存延迟**：使用共享内存缓冲 + async copy
5. **无流水线停顿**：减少 warp divergence，保持高占用率

### 与 CUDA Core 的对比

| 对比维度 | CUDA Core | Tensor Core |
|---------|-----------|-------------|
| 运算类型 | 标量运算 | 矩阵乘加（D=A×B+C） |
| 输入大小 | 单元素 | 4×4 矩阵 |
| 每周期操作数 | 1 次 FMA | 64+ 次 FMA |
| 精度支持 | FP32/FP64 | FP16/BF16/TF32/FP8/INT8 |
| 适用场景 | 通用计算 | 矩阵乘法/卷积 |
| 编程接口 | 标准 CUDA | WMMA/cuBLAS/cuDNN |

Tensor Core 在最关键的计算上提供了 **8-16 倍**的吞吐量提升，是 GPU 发展路线中最重要的架构创新之一。

---

## 参考文献

- NVIDIA, *Volta V100 GPU Architecture Whitepaper*, 2017. Section: Tensor Core.
- NVIDIA, *Turing T102 GPU Architecture Whitepaper*, 2018. Section: Tensor Core Gen 2.
- NVIDIA, *Ampere A100 GPU Architecture Whitepaper*, 2020. Section: Tensor Core Gen 3.
- NVIDIA, *Hopper H100 GPU Architecture Whitepaper*, 2022. Section: Tensor Core Gen 4, Transformer Engine.
- NVIDIA, *Blackwell B200 GPU Architecture Whitepaper*, 2024.
- Markidis, S. et al., "NVIDIA Tensor Core Programmability, Performance & Precision", *IEEE International Parallel and Distributed Processing Symposium Workshops (IPDPSW)*, 2018. doi:10.1109/IPDPSW.2018.00091
- NVIDIA, *CUDA C++ Programming Guide*, Section 9: WMMA (Warp Matrix Multiply-Accumulate).
- Sze, V. et al., "Efficient Processing of Deep Neural Networks: A Tutorial and Survey", *Proceedings of the IEEE*, 105(12), 2017, pp. 2295-2329. Section 4.2: Tensor Core.
- Micikevicius, P. et al., "Mixed Precision Training", *arXiv:1710.03740*, 2017.
- Micikevicius, P. et al., "FP8 Formats for Deep Learning", *arXiv:2209.05433*, 2022.
