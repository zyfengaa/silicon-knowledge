# 06 — cuBLAS 与 cuDNN

> 在写自己的 CUDA Kernel 之前，先想想：NVIDIA 的工程师已经帮你优化好了吗？cuBLAS 和 cuDNN 就是那个"官方优化版"。

## 为什么要用厂商优化库

NVIDIA 为每一代 GPU 架构（Volta、Turing、Ampere、Hopper）重新优化 cuBLAS 和 cuDNN：

1. **每个 GPU 的代际调优**：不同架构有不同数量的 SM、寄存器、共享内存，最优的 Tile Size 和 Launch Configuration 也不同
2. **手写汇编**：核心 Kernel 由 NVIDIA 工程师手写 PTX/汇编（如 CUTLASS 生成的代码）
3. **自动选择算法**：cuDNN 会在启动时 benchmark 多种算法，选择最快的一个
4. **跨架构兼容**：同样的 API 在不同 GPU 上都能获得接近峰值的性能

**规则：只要 cuBLAS/cuDNN 提供了你要的功能，就先用它们。只有在你需要非常特定的算子组合时，才考虑自己写 Kernel。**

## cuBLAS

### 基本概念

cuBLAS 是 BLAS (Basic Linear Algebra Subprograms) 在 GPU 上的实现。

- **Level 1**: 向量-向量操作 (如 dot product, axpy)
- **Level 2**: 矩阵-向量操作 (如 gemv, ger)
- **Level 3**: 矩阵-矩阵操作 (如 gemm, symm)

### 使用流程

```cuda
#include <cublas_v2.h>

// 1. 创建 handle
cublasHandle_t handle;
cublasCreate(&handle);

// 2. 准备数据（Device 端）
float *d_A, *d_B, *d_C;
cudaMalloc(&d_A, M * K * sizeof(float));
cudaMalloc(&d_B, K * N * sizeof(float));
cudaMalloc(&d_C, M * N * sizeof(float));
// ... cudaMemcpy Host → Device ...

// 3. 调用 cuBLAS 函数
float alpha = 1.0f, beta = 0.0f;
cublasSgemm(handle,
    CUBLAS_OP_N, CUBLAS_OP_N,       // A, B 不转置
    M, N, K,                         // M, N, K
    &alpha,                          // alpha
    d_A, M,                          // A, lda
    d_B, K,                          // B, ldb
    &beta,                           // beta
    d_C, M                           // C, ldc
);

// 4. 同步（cuBLAS 操作默认在默认 Stream 中执行）
cudaDeviceSynchronize();

// 5. 释放
cublasDestroy(handle);
cudaFree(d_A); cudaFree(d_B); cudaFree(d_C);
```

### 数据类型

cuBLAS 支持多种数据类型，通过函数名区分：

| 函数 | 类型 | 精度 | 适用场景 |
|------|------|------|----------|
| `cublasSgemm` | float | 单精度 (FP32) | 通用计算 |
| `cublasDgemm` | double | 双精度 (FP64) | 科学计算 |
| `cublasHgemm` | half | 半精度 (FP16) | 深度学习推理/训练 |
| `cublasGemmEx` | 多种 | 可指定类型 | 混合精度 (TF32/FP16/BF16/INT8) |
| `cublasGemmStridedBatchedEx` | 多种 | 批量 + 混合精度 | 批量矩阵乘 |

### cublasSgemm 参数详解

```cuda
cublasStatus_t cublasSgemm(
    cublasHandle_t handle,
    cublasOperation_t transA,  // CUBLAS_OP_N / CUBLAS_OP_T / CUBLAS_OP_C
    cublasOperation_t transB,
    int m,                     // C 的行数
    int n,                     // C 的列数
    int k,                     // A 的列数 / B 的行数（内积维度）
    const float *alpha,        // 标量 alpha
    const float *A,            // 矩阵 A (m × k)
    int lda,                   // A 的 leading dimension
    const float *B,            // 矩阵 B (k × n)
    int ldb,                   // B 的 leading dimension
    const float *beta,         // 标量 beta
    float *C,                  // 矩阵 C (m × n)
    int ldc                    // C 的 leading dimension
);
```

计算：`C = alpha * op(A) * op(B) + beta * C`

**Note:** cuBLAS 默认使用**列主序**（Column-Major）。如果使用行主序数据，可以：
- 用 `CUBLAS_OP_T` 交换矩阵维度
- 或者交换 A 和 B 的角色

### cuBLAS 与 Stream

cuBLAS 操作可以绑定到指定 Stream，与其他操作重叠：

```cuda
cudaStream_t stream;
cudaStreamCreate(&stream);

cublasSetStream(handle, stream);

// 在指定 Stream 上执行，与 CPU 和其他 Stream 异步
cublasSgemm(handle, CUBLAS_OP_N, CUBLAS_OP_N, 
            M, N, K, &alpha, d_A, M, d_B, K, &beta, d_C, M);

// 不需要显式同步，除非需要确保完成
```

### cuBLAS 性能建议

1. **矩阵尺寸越大越好**：小矩阵（M, N, K < 1024）时 cuBLAS 也受限，建议批量处理
2. **对齐到 16/32 bytes**：矩阵的 leading dimension 最好对齐到 16/32 的倍数
3. **使用 cuBLASLt**：对特定尺寸有更多的算法选择 `cublasLtMatmul`
4. **重用 Handle**：不要再每个 CUDA 操作都创建/销毁 handle

## cuDNN

### 基本概念

cuDNN 提供深度学习常用算子的 GPU 实现：

| 算子类别 | 主要 API |
|----------|----------|
| 卷积 (Convolution) | `cudnnConvolutionForward`, `cudnnConvolutionBackwardData` |
| 池化 (Pooling) | `cudnnPoolingForward`, `cudnnPoolingBackward` |
| 激活函数 (Activation) | `cudnnActivationForward` (ReLU, sigmoid, tanh) |
| 批归一化 (Batch Norm) | `cudnnBatchNormalizationForwardTraining` |
| 循环层 (RNN/LSTM/GRU) | `cudnnRNNForwardTraining` |
| 张量变换 (Tensor Ops) | `cudnnOpTensor` (element-wise add/mul) |
| 归约 (Reduction) | `cudnnReduceTensor` (sum, mean, min, max) |

### 卷积示例

```cuda
#include <cudnn.h>

// 1. 创建 handle
cudnnHandle_t cudnn;
cudnnCreate(&cudnn);

// 2. 创建张量描述符
cudnnTensorDescriptor_t input_desc, output_desc;
cudnnCreateTensorDescriptor(&input_desc);
cudnnCreateTensorDescriptor(&output_desc);

// 输入: NCHW 格式 (batch=32, channels=3, height=224, width=224)
cudnnSetTensor4dDescriptor(input_desc, CUDNN_TENSOR_NCHW, 
                           CUDNN_DATA_FLOAT, 32, 3, 224, 224);

// 3. 创建卷积描述符
cudnnFilterDescriptor_t filter_desc;
cudnnCreateFilterDescriptor(&filter_desc);
// 32 个 3x3 filter, 输入通道=3
cudnnSetFilter4dDescriptor(filter_desc, CUDNN_DATA_FLOAT, 
                           CUDNN_TENSOR_NCHW, 32, 3, 3, 3);

cudnnConvolutionDescriptor_t conv_desc;
cudnnCreateConvolutionDescriptor(&conv_desc);
cudnnSetConvolution2dDescriptor(conv_desc,
    1, 1,          // padding (height, width)
    1, 1,          // stride (height, width)
    1, 1,          // dilation
    CUDNN_CROSS_CORRELATION,  // mode
    CUDNN_DATA_FLOAT          // compute type
);

// 4. 获取输出维度
int out_n, out_c, out_h, out_w;
cudnnGetConvolution2dForwardOutputDim(
    conv_desc, input_desc, filter_desc,
    &out_n, &out_c, &out_h, &out_w
);
// out_n=32, out_c=32, out_h=224, out_w=224 (padding=1, stride=1)
cudnnSetTensor4dDescriptor(output_desc, CUDNN_TENSOR_NCHW,
                           CUDNN_DATA_FLOAT, out_n, out_c, out_h, out_w);

// 5. 选择最快的卷积算法
cudnnConvolutionFwdAlgoPerf_t perf_results;
int returned_algo_count;
cudnnGetConvolutionForwardAlgorithm_v7(
    cudnn, input_desc, filter_desc,
    conv_desc, output_desc,
    1,                    // max requested algos
    &returned_algo_count,
    &perf_results
);
cudnnConvolutionFwdAlgo_t algo = perf_results.algo;
// 或使用以下 API 自动寻找最佳算法:
// cudnnFindConvolutionForwardAlgorithm(...)

// 6. 分配工作空间
size_t workspace_size;
cudnnGetConvolutionForwardWorkspaceSize(
    cudnn, input_desc, filter_desc, 
    conv_desc, output_desc, algo,
    &workspace_size
);
void *workspace;
cudaMalloc(&workspace, workspace_size);

// 7. 执行卷积
float alpha = 1.0f, beta = 0.0f;
cudnnConvolutionForward(
    cudnn,
    &alpha,
    input_desc, d_input,
    filter_desc, d_filter,
    conv_desc, algo,
    workspace, workspace_size,
    &beta,
    output_desc, d_output
);

// 8. 同步并释放
cudaDeviceSynchronize();
cudaFree(workspace);
cudnnDestroyTensorDescriptor(input_desc);
cudnnDestroyTensorDescriptor(output_desc);
cudnnDestroyFilterDescriptor(filter_desc);
cudnnDestroyConvolutionDescriptor(conv_desc);
cudnnDestroy(cudnn);
```

### cuDNN 算法选择

cuDNN 卷积支持多种实现算法，性能差异很大（可到数倍）。

| 算法 | 特点 | 适用场景 |
|------|------|----------|
| `CUDNN_CONVOLUTION_FWD_ALGO_GEMM` | 转化为矩阵乘（cublasGemm） | 大 batch，大 kernel |
| `CUDNN_CONVOLUTION_FWD_ALGO_FFT` | 用 FFT 实现 | 大 kernel (≥ 7x7) |
| `CUDNN_CONVOLUTION_FWD_ALGO_WINOGRAD` | Winograd 变换 | 小 kernel (3x3, 5x5) |
| `CUDNN_CONVOLUTION_FWD_ALGO_IMPLICIT_GEMM` | 隐式矩阵乘 | 通用情况 |

**最佳实践：** 使用 `cudnnFindConvolutionForwardAlgorithm`（或 TensorRT 的自动调优）来为你的特定尺寸和硬件选择最快算法。

### Batch Norm 示例

```cuda
// 设置 BN 描述符
cudnnBatchNormMode_t bn_mode = CUDNN_BATCHNORM_SPATIAL;  // 每个通道

// 前向（训练时）
cudnnBatchNormalizationForwardTraining(
    cudnn,
    bn_mode,
    &alpha, &beta,                 // 输入 alpha, beta
    input_desc, d_input,           // 输入
    input_desc, d_output,          // 输出（归一化后的）
    bn_param_desc,                 // 参数描述符
    d_gamma, d_beta,               // 学习的 scale 和 shift
    .05,                           // 指数移动平均衰减率
    d_running_mean, d_running_var, // 运行统计
    epsilon,                       // 防止除零
    d_save_mean, d_save_inv_var   // 保存用于 backward
);
```

## 混合精度与 Tensor Cores

cuBLAS 和 cuDNN 都支持 NVIDIA Tensor Cores：

```cuda
// cuBLAS: 使用 Tensor Cores 的 FP16 矩阵乘
cublasGemmEx(handle,
    CUBLAS_OP_N, CUBLAS_OP_N,
    M, N, K,
    &alpha,
    d_A, CUDA_R_16F, M,
    d_B, CUDA_R_16F, K,
    &beta,
    d_C, CUDA_R_32F, M,
    CUDA_R_32F,          // 计算类型（累加用 FP32）
    CUBLAS_GEMM_DEFAULT_TENSOR_OP
);

// cuDNN: 启用 Tensor Core
cudnnSetConvolutionMathType(conv_desc, CUDNN_TENSOR_OP_MATH);
```

Tensor Cores 在 Volta 及之后架构可用，Hopper 架构达到最佳效率。

## 何时使用 cuBLAS/cuDNN vs 自己写 Kernel

| 情况 | 推荐 |
|------|------|
| 标准矩阵乘 (SGEMM/GEMM) | cuBLAS |
| 标准卷积 (3x3, 5x5) | cuDNN（自动选择算法） |
| 自定义激活函数 | cuBLAS 或自己写 |
| 矩阵乘 + 后续自定义算子 | 先 cuBLAS 做 GEMM，自己写后面的 Element-wise |
| 非常规数据布局 | 先尝试 cuBLAS/cuDNN，不行再自定义 |
| 批量矩阵乘（相同大小） | cuBLAS batched GEMM |
| 很稀疏的矩阵运算 | cuSPARSE |

## 总结

| 概念 | 要点 |
|------|------|
| cuBLAS | BLAS on GPU — 矩阵乘、向量操作 |
| cuDNN | Deep Learning 算子 — 卷积、BN、RNN |
| Handle | 创建 cuBLAS/cuDNN 的上下文 |
| 算法选择 | cuDNN 自动 benchmark 选择最快算法 |
| Tensor Cores | 在支持的 GPU 上自动利用（需要设置 math type） |
| 混合精度 | FP16/BF16 计算 + FP32 累加 |
| 规则 | 先用库，只有必要时才自己写 Kernel |

## 参考文献

- NVIDIA. *cuBLAS Developer Guide*. https://docs.nvidia.com/cuda/cublas/
- NVIDIA. *cuDNN Developer Guide*. https://docs.nvidia.com/deeplearning/cudnn/developer-guide/
- NVIDIA. *cuBLAS API Reference*. https://docs.nvidia.com/cuda/cublas/index.html
- NVIDIA. *cuDNN API Reference*. https://docs.nvidia.com/deeplearning/cudnn/api/
- NVIDIA. "Mixed Precision Training." *NVIDIA Deep Learning Performance Documentation*. https://docs.nvidia.com/deeplearning/performance/mixed-precision-training/
- NVIDIA. "Tensor Core Performance." *NVIDIA Deep Learning Performance Guide*. https://docs.nvidia.com/deeplearning/performance/dl-performance-gpu-background/index.html#tensor-cores
