# 04 — CPU 微架构进阶

> 现代高性能 CPU 的内部引擎。从"完成一条指令"到"同时完成多条指令"，理解超标量、乱序执行、分支预测和 SIMD。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **超标量** | 多发射架构：每周期发射多条指令的限制因素 |
| 02 | **乱序执行** | 重排序缓冲（ROB）、保留站（Reservation Station）、寄存器重命名 |
| 03 | **推测执行** | 分支预测后如何"推测性"执行指令，以及误预测回滚机制 |
| 04 | **分支预测** | 从 2-bit 饱和计数器到 TAGE：现代预测器为什么能 >97% 准确 |
| 05 | **SIMD** | SSE/AVX/NEON/SVE 的原理、向量化编程、与标量的性能对比 |
| 06 | **多核与缓存一致性** | MESI 协议、False Sharing 问题、NUMA 架构 |
| 07 | **现代 CPU 实例** | Apple M 系列、Intel Golden Cove、AMD Zen 4/5 架构解读 |

## 前置知识

- [03 CPU 流水线](/03-cpu-pipeline/)（流水线冒险、转发、CPI 计算）

## 建议学习方式

1. 理解为什么简单的 5 段流水线不够用→引出超标量和乱序
2. 逐个概念深入：先理解每个部件"干什么"，再理解"为什么需要它"
3. 运行分支预测模拟器观察不同预测策略的差异
4. 编写 SIMD 代码并反汇编查看编译器生成的向量指令
5. 运行 false sharing 示例程序观察性能退化

## 本模块代码

| 文件 | 内容 | 运行环境 |
|------|------|---------|
| `c/simd_add.c` | SIMD 向量加法示例 | x86 CPU with AVX |
| `c/simd_vs_scalar.c` | SIMD vs 标量性能对比 + 时间测量 | x86 CPU |
| `c/false_sharing.c` | False Sharing 现象复现与优化对比 | 多核 CPU |
| `python/branch_pred_sim.py` | 不同分支预测策略（2-bit / 两级）的模拟对比 | Python |

## 关键产出

- [ ] 能用中文通俗解释"乱序执行"并画出 ROB + 保留站的结构
- [ ] 知道分支预测的发展历程（2-bit → 两级 → TAGE → 神经网络预测）
- [ ] 能用 SIMD intrinsics 编写向量化代码并对比性能
- [ ] 能解释 false sharing 的发生条件和解决方案
- [ ] 能列出现代 CPU（Apple M / Intel / AMD）各自的微架构特色

## 参考文献

- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 3 章
- Intel 64 and IA-32 Architectures Optimization Reference Manual
- ARM Cortex-X Series Technical Reference Manual
- Seznec, A. "TAGE-SC-L Branch Predictors." *JILP* 2014.
