# 06 — GPU 架构

> GPU 如何从"图形渲染器"变成"通用并行计算引擎"？理解 SIMT 模型、warp 调度、GPU 内存层次和 Tensor Core。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **CPU vs GPU** | 两者设计哲学的根本差异：延迟优化 vs 吞吐优化 |
| 02 | **SIMT 模型** | Single Instruction Multiple Threads 如何工作 |
| 03 | **GPU 硬件组成** | SM（流式多处理器）、CUDA Core、Warp、Warp Scheduler |
| 04 | **Warp 执行** | Warp divergence / convergence、掩蔽执行 |
| 05 | **GPU 内存层次** | Global / Shared / Local / Register / Constant / Texture 各层级特性 |
| 06 | **内存优化** | 合并访问（Coalescing）、Bank Conflict |
| 07 | **Tensor Core** | 4×4 矩阵乘加速单元、混合精度（FP16/BF16/INT8） |
| 08 | **GPU 互联** | NVLink、NVSwitch、PCIe 拓扑 |
| 09 | **架构演进** | NVIDIA Fermi → Kepler → Maxwell → Pascal → Volta → Turing → Ampere → Hopper → Blackwell |
| 10 | **AMD / Intel GPU** | AMD CDNA 3、Intel Xe HPC 架构简介 |

## 前置知识

- [03 CPU 流水线](/03-cpu-pipeline/)（需要理解并行执行的基本概念）
- [05 存储层次](/05-memory-hierarchy/)（缓存概念用于类比 GPU 内存）

## 建议学习方式

1. 先从 CPU vs GPU 的宏观对比入手，建立直觉
2. 理解 SIMT 与 SIMD 的本质区别（模块 04 的知识用到这了）
3. 用 `deviceQuery` 工具查看你本地 GPU 的硬件参数
4. 运行 CUDA 入门示例（vec_add）感受 GPU 编程的基本模式
5. 深入 memory optimization：理解合并访问为什么影响带宽

## 本模块代码

| 文件 | 内容 |
|------|------|
| `cuda/vec_add.cu` | GPU 入门：向量加法，对比 CPU 和 GPU 执行时间 |
| `cuda/matrix_mul.cu` | 矩阵乘优化：naive → tiled shared memory → Tensor Core |
| `cuda/reduction.cu` | 规约操作优化：shared memory + warp-level reduction |
| `cuda/coalescing.cu` | 合并访问 vs 非合并访问的带宽对比 |
| `cuda/bank_conflict.cu` | Bank Conflict 的条件和影响演示 |

注意：此模块代码需要 **NVIDIA GPU + CUDA Toolkit** 才能运行。

## 关键产出

- [ ] 能用一句话说清 CPU 和 GPU 的根本设计差异
- [ ] 能解释 SIMT 与 SIMD 的区别，以及为什么 warp divergence 影响性能
- [ ] 能画出 GPU 的内存层次并说出每层的用途和延迟量级
- [ ] 理解合并访问的条件，能识别什么样的访问模式会导致带宽浪费
- [ ] 能说清 Tensor Core 解决了什么问题（矩阵乘加速 + 降低精度）

## 参考文献

- Kirk & Hwu, *Programming Massively Parallel Processors*, 第 1-5 章
- NVIDIA, *CUDA C++ Programming Guide*
- NVIDIA, *Turing T102 GPU Architecture Whitepaper*
- NVIDIA, *Hopper H100 GPU Architecture Whitepaper*
- [AMD CDNA 3 Whitepaper](https://www.amd.com/en/products/accelerators/cdna-3.html)
