# 11 — 系统分析与性能工程

> 把前面 10 个模块的知识串起来。面对一个真实系统，能够分析瓶颈、定位问题、提出优化方案。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **Roofline 模型** | 如何判断程序是 compute-bound 还是 memory-bound |
| 02 | **Amdahl vs Gustafson** | 并行加速的理论上限分析 |
| 03 | **功耗与散熱** | TDP、DVFS、暗硅（Dark Silicon）、异构设计 |
| 04 | **异构计算系统** | CPU + GPU + NPU 协同工作的系统设计 |
| 05 | **Linux perf** | CPU 性能计数器采样、火焰图生成 |
| 06 | **GPU Profiling** | Nsight Compute / Nsight Systems / rocprof 实操指南 |
| 07 | **TPU Profiling** | TPU 性能分析工具链 |
| 08 | **端到端案例** | 大模型训练系统的硬件端到端分析与优化 |

## 前置知识

- 模块 01~10 全部知识（需要综合运用）

## 建议学习方式

1. 先学 Roofline 模型——它是贯穿整个模块的分析框架
2. 学习 perf / nsys 等工具的操作
3. 找一个你熟悉的程序或模型，做一个完整的 Roofline 分析
4. 完成端到端案例分析（笔记 08）

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/roofline_plot.py` | 给定参数生成 Roofline 模型可视化图表 |
| `python/perf_model.py` | 简单的性能建模脚本：输入程序特征，输出理论性能上限 |

## 关键产出

- [ ] 能画出一个程序的 Roofline 模型图，标出 bottleneck 类型
- [ ] 能用 `perf stat` 测量 CPU 程序的 IPC、cache miss、branch miss
- [ ] 能用 Nsight 定位 GPU kernel 的瓶颈
- [ ] 能对大模型训练系统做端到端分析（计算时间、通信时间、访存时间）
- [ ] 能做出"优化还是不优化"的工程决策——算 ROI

## 参考文献

- Williams, S. et al. "Roofline: An Insightful Visual Performance Model..." *CACM* 2009.
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 1 章（性能方法论）
- Gregg, B. *Systems Performance: Enterprise and the Cloud*, 第 2 版
- [Linux perf Wiki](https://perf.wiki.kernel.org/)
- NVIDIA, *Nsight Compute 用户指南*
