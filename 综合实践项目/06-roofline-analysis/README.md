# 项目 06 — 真实程序的 Roofline 分析

> 选 2–3 个真实程序，实测峰值带宽与算力，画出 Roofline，找出瓶颈并用实验验证优化是否真的把点"抬上去"。

## 目标

- 用实测而非规格书数字建立 Roofline 的两个屋顶：峰值带宽与峰值算力。
- 从源代码 / 算法计算 FLOPs，从性能计数器或流量模型估计实际字节数。
- 区分理想算术强度、实测算术强度、cache-resident 与 DRAM-resident 的不同口径。
- 用 `perf` 证据支持"compute-bound / memory-bound"判断，并量化优化收益。

## 前置知识

- [模块 11：系统分析与性能工程](../../11-系统分析与性能工程/README.md)
- [Roofline 模型](../../11-系统分析与性能工程/notes/01-roofline-model.md)
- [Linux perf](../../11-系统分析与性能工程/notes/05-perf-tools.md)、[GPU Profiling](../../11-系统分析与性能工程/notes/06-gpu-profiling.md)
- [Amdahl vs Gustafson](../../11-系统分析与性能工程/notes/02-amdahl-gustafson.md)、[端到端案例](../../11-系统分析与性能工程/notes/08-end-to-end-case.md)
- [缓存基础](../../05-存储层次/notes/02-cache-basics.md)、[分块优化示例](../../05-存储层次/code/c/matrix_mult_tiling.c)
- 工具脚本：[roofline_plot.py](../../11-系统分析与性能工程/code/python/roofline_plot.py)、[perf_model.py](../../11-系统分析与性能工程/code/python/perf_model.py)

## 任务要求

**必做**

1. 默认在 Linux 或 WSL2 上完成（需要 `perf`）；在**同一台机器、同一编译选项**下准备至少 2 个 workload、4 个数据点：
   - 朴素 `ijk` 矩阵乘 vs 分块 / OpenBLAS / MKL 矩阵乘（`N=512/1024/2048` 中至少两个尺寸）；
   - 标量循环向量加法 vs 自动向量化 / 手写 SIMD 版本，或 STREAM triad vs 普通循环。
2. 用 STREAM 风格 copy / triad 微基准实测可持续内存带宽；用重复 FMA 或最优 GEMM 微基准实测 FP32 峰值算力。**禁止直接填 CPU / GPU 规格书数字**。
3. 用 `perf stat` 采集 `cycles`、`instructions`、`cache-references`、`cache-misses`、`LLC-loads`、`LLC-load-misses`、`branch-misses`；若平台支持，采集 `fp_arith_inst_retired.*` 事件。记录完整命令行与内核版本。
4. FLOPs 由算法计算（GEMM 为 `2·M·N·K`，一次 FMA 计 2 FLOP），并说明编译器是否融合、是否引入额外操作。
5. 分别报告：理想 DRAM 字节（只读一次、写一次）与实测 DRAM 字节（由计数器或 cache 模拟估计）；算术强度 = FLOPs / 字节，注明采用哪一种。
6. 画 log-log Roofline：屋顶取 `min(峰值算力, 峰值带宽 × 算术强度)`，标注每个程序点、误差条与瓶颈类型；可选叠加 L1/L2/L3 的 cache roof。
7. 至少做一次优化（分块、向量化、循环交换、OpenBLAS），验证输出正确（`rtol ≤ 1e-4`）并记录加速比。
8. 报告中给出"下一个最值得做的优化"及其预期上限（可用 Amdahl 估算），并说明依据。

**可选扩展**

- 同一程序在 CPU 与 GPU 上各画一条 Roofline（注意两者屋顶与精度不同，不能共用一个屋顶）。
- 用 Nsight Compute 为 GPU kernel 采集 `dram__throughput`、`sm__throughput` 与算术强度。
- 用缓存模拟器（项目 02）估计真实 DRAM 流量，与计数器交叉验证。

## 里程碑

- **M1 骨架**：workload 编译、计时框架、正确性参考、`perf` 可用性验证。
- **M2 核心**：实测带宽 / 算力，收集 4 个数据点的 FLOPs、时间与计数器。
- **M3 验证**：Roofline 绘制、瓶颈分类、优化实现与加速比复测。
- **M4 报告**：误差分析、口径说明、优化建议与原始数据归档。

## 交付物

- `src/`：各 workload 与微基准；`scripts/`：运行、采集、绘图脚本。
- `results/raw/`：`perf stat` 原始文本与计时 CSV；`results/summary.csv`：每个点的 FLOPs、字节、时间、GFLOP/s、AI。
- `plots/roofline.png`：带标注的 Roofline；`report.md`：硬件 / 编译器 / 命令、方法、结果、局限。
- 根目录 `README.md`：一条命令复现实验的说明。

## 验收标准

- 至少 2 个 workload、4 个数据点；每个点有 5 次运行的中位数与离散度，重复测量差异 ≤ 10%。
- 实测带宽与实测 FP32 峰值均来自本机微基准，报告中给出微基准代码与结果；与规格书的差异需解释。
- Roofline 坐标轴、单位、屋顶公式、数据点标签完整；所有点都能归入 compute-bound 或 memory-bound，并有计数器证据。
- 至少一个优化取得 **≥ 2×** 加速且数值正确；优化后的点相对原点的移动方向与预期一致。
- 实测算术强度与理想值的差异有解释（缓存复用、分块、写分配、计数器口径等）。
- 若有数据点高于屋顶，必须给出原因（测量误差、cache-resident、屋顶取错、频率变化等），不得忽略。
- 原始命令、版本、CPU 亲和性与计时方法齐全，另一位读者可按 README 复现。

## 参考

- Williams, S., Waterman, A., & Patterson, D. "Roofline: An Insightful Visual Performance Model for Multicore Architectures." *CACM*, 2009.
- [Roofline 论文笔记](../../11-系统分析与性能工程/papers/01-roofline.md)
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 1 章。
- Gregg, B. *Systems Performance: Enterprise and the Cloud*, 第 2 版。
- [Linux perf Wiki](https://perf.wiki.kernel.org/)、[roofline_plot.py](../../11-系统分析与性能工程/code/python/roofline_plot.py)

## 常见陷阱与口径

- 规格书带宽是理论峰值；Roofline 的屋顶应使用**实测可持续带宽**，否则所有点都会"看起来没到顶"。
- 一次 FMA 是 2 FLOP；GEMM 的 FLOPs 是 `2MNK`，不是 `MNK`。
- 理想字节数假设每个元素只从 DRAM 读一次；分块程序可能因重复加载产生更多流量，必须用实测或模型校正。
- 数据完全驻留 cache 时，用 DRAM 屋顶会严重低估上限；此时应使用对应层级的 cache roof。
- 标量基线可能被编译器自动向量化；用 `-O2 -fno-tree-vectorize` 固定基线，并检查汇编。
- Turbo、超线程、频率漂移与 NUMA 会影响结果；固定 CPU 亲和性，记录频率策略，至少重复 5 次。
- `perf` 可能因权限不可用；若改用其他计数器工具，必须在报告中说明替代方案与限制。
