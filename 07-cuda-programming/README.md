# 07 — CUDA 编程与优化

> 把 GPU 硬件知识变成代码。从写对到写快——掌握 CUDA 编程模型、性能分析和优化方法论。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **执行模型** | Grid / Block / Thread 的硬件映射逻辑 |
| 02 | **内存模型** | CUDA 内存模型的层级和可见性规则 |
| 03 | **Occupancy 与配置** | 如何通过 Launch Configuration 最大化硬件利用率 |
| 04 | **Streams 与异步** | Stream 并发、Async 操作、Host-Device 数据传输重叠 |
| 05 | **性能分析** | Nsight Compute / Nsight Systems 的实用指南 |
| 06 | **cuBLAS / cuDNN** | 厂商优化库的原理与正确调用方式 |

## 前置知识

- [06 GPU 架构](/06-gpu-architecture/)（SM、Warp、内存层次）

## 建议学习方式

1. 先掌握 CUDA 基本编程模式（已经通过模块 06 的代码有所接触）
2. 深入理解 occupancy 的计算方式，用 `ncu` 查看 kernel 的实际 occupancy
3. 优化一个 kernel（比如矩阵乘），记录每一步优化的性能变化
4. 学习分析工具：先用 `nsys` 看整体，再用 `ncu` 看 kernel 细节

## 本模块代码

| 文件 | 内容 |
|------|------|
| `cuda/async_copy.cu` | 异步内存传输 + kernel 执行重叠 |
| `cuda/multi_stream.cu` | 多 Stream 并发执行 |
| `cuda/custom_kernel_opt.cu` | 综合 kernel 优化案例 |

## 关键产出

- [ ] 能计算给定 kernel 的理论 occupancy
- [ ] 能用 Nsight Compute 定位 kernel 瓶颈
- [ ] 能用 Stream 实现数据传输与计算的重叠
- [ ] 理解 cuBLAS 的 API 设计并能在项目中正确调用

## 参考文献

- NVIDIA, *CUDA C++ Programming Guide*
- NVIDIA, *CUDA Best Practices Guide*
- Cheng & Grossman, *Professional CUDA C Programming*
- [Nsight Compute 官方文档](https://docs.nvidia.com/nsight-compute/)
