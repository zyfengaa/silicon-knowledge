# Roofline 模型论文阅读笔记

## 一句话贡献

提出了一种直观的性能分析可视化模型——Roofline Model，将程序性能与计算强度和硬件峰值算力/带宽关联起来，帮助快速判断程序是计算受限还是访存受限。

## 基本信息

- **标题**：Roofline: An Insightful Visual Performance Model for Floating-Point Programs and Multicore Architectures
- **作者**：Samuel Williams, Andrew Waterman, David Patterson
- **会议**：Communications of the ACM, 2009 (CACM)
- **原文**：基于 2008 年 UC Berkeley 的技术报告

## 背景

多核时代的到来使得程序员需要面对越来越复杂的存储层次。传统的性能分析方法（仅看 FLOPS 或仅看缓存命中率）无法完整描述程序在系统中的行为。需要一个统一的框架来同时考虑计算能力和访存带宽。

## 核心思想

Roolline 模型建立在两个关键观察上：

1. **计算强度（Arithmetic Intensity, AI）** = FLOPs / Bytes（从 DRAM 读取的总字节数）
2. 程序的实际性能受限于两个「天花板」中较低的那个：**计算天花板**（峰值 FLOPS）和**访存天花板**（峰值带宽 × 计算强度）

**公式表达：**
```
Attainable GFLOPS = min(Peak GFLOPS, Peak BW × AI)
```

**图中呈现**：
- x 轴 = 计算强度（FLOP/Byte，对数坐标）
- y 轴 = 性能（GFLOPS，对数坐标）
- 水平线 = 计算峰值
- 斜线 = 内存带宽（斜率 = 峰值带宽）
- 交点 = Ridge Point（分界点）
- Ridge 左侧 = 访存受限（Memory-bound）
- Ridge 右侧 = 计算受限（Compute-bound）

## 关键贡献

1. **统一的性能分析框架**：将计算和访存两个维度合并到一个图中
2. **直观的瓶颈识别**：一眼看出程序瓶颈在哪个方向，以及距离「天花板」还有多少优化空间
3. **硬件天花板的叠加**：不仅考虑 DRAM 带宽，还可以叠加 L1/L2 缓存带宽、指令级并行等额外天花板
4. **优化指导**：左半边的程序应优化数据局部性（减少访存），右半边的应优化计算（向量化、并行化）

## 局限

1. 只考虑计算和访存，忽略通信、同步、I/O 等开销
2. 计算强度依赖于输入数据大小（大 batch 的 AI 更高）
3. 对复杂的非规则访问模式（稀疏、图计算）建模不够精确
4. 缓存层次的详细行为（cache thrashing、TLB miss）无法体现

## 我的思考

Roofline 模型最有价值的地方在于提供了一个**通用语言**——无论是 CPU、GPU 还是 NPU，都可以用同一张图的语言来讨论性能瓶颈。在实践中：

- 对 AI 推理引擎分析非常有用：GEMM 通常在 Ridge 右侧（计算受限），而 LayerNorm 在左侧（访存受限）
- 结合 `perf stat` 和 `nsys` 可以快速定位瓶颈
- 在 GPU 上使用 Nsight Compute 可以自动生成 Roofline 视图

## 参考文献

1. Williams, S., Waterman, A., & Patterson, D. "Roofline: An Insightful Visual Performance Model for Floating-Point Programs and Multicore Architectures." *Communications of the ACM*, 2009.
2. Williams, S. et al. "Optimization of Dense Matrix Operations on Multicore Architectures." *UC Berkeley Technical Report*, 2008.
3. [NVIDIA Nsight Compute Roofline Analysis](https://docs.nvidia.com/nsight-compute/)
