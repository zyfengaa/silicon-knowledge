# 项目 03 — 高性能 Softmax CUDA Kernel

> 手写行级 Softmax kernel，从"能算对"优化到"接近显存带宽上限"，并用 Nsight Compute 证明瓶颈在哪里。

## 目标

- 掌握数值稳定的 Softmax：先减最大值，再求指数和，避免溢出。
- 实践 shared memory 归约、warp shuffle、向量化访存与在线（online）单趟算法。
- 用统一基准与 PyTorch / cuDNN 对比，解释差距来自带宽、占用率还是同步。
- 用 profiler 指标而不是直觉定位瓶颈。

## 前置知识

- [模块 06：GPU 架构](../../06-GPU架构/README.md)
- [SIMT 模型](../../06-GPU架构/notes/02-simt-model.md)、[Warp 执行](../../06-GPU架构/notes/04-warp-execution.md)
- [GPU 内存层次](../../06-GPU架构/notes/05-gpu-memory-hierarchy.md)、[内存优化](../../06-GPU架构/notes/06-memory-optimization.md)、[Tensor Core](../../06-GPU架构/notes/07-tensor-core.md)
- [模块 07：CUDA 编程与优化](../../07-CUDA编程与优化/README.md)
- [执行模型](../../07-CUDA编程与优化/notes/01-execution-model.md)、[内存模型](../../07-CUDA编程与优化/notes/02-memory-model.md)、[Occupancy](../../07-CUDA编程与优化/notes/03-occupancy.md)、[性能分析](../../07-CUDA编程与优化/notes/05-profiling.md)
- [模块 11：Roofline 模型](../../11-系统分析与性能工程/notes/01-roofline-model.md)

## 任务要求

**必做**

1. 实现 float32 行级 Softmax：输入 `X[B, N]`，输出 `Y[B, N]`，`N ∈ {1024, 4096, 16384}`，总元素数约 4M（三个规模分别取合适 batch）。
2. 至少实现 4 个版本并保留各自的 benchmark：
   - V0：朴素多 kernel（求 max、求 exp 和、归一化），作为正确性与性能基线；
   - V1：block-per-row + shared memory 两趟归约（max，然后 exp 与 sum）；
   - V2：`N ≤ 1024` 时 warp-per-row + `__shfl_xor_sync`，`N` 更大时 block-per-row；
   - V3：在线 Softmax 单趟流式版本（维护 running max 与 rescaled sum），或 float4 向量化 + `__expf` 版本，二选一必做。
3. 处理非 2 的幂行宽与尾元素；支持 mask（被 mask 位置不参与 max / sum）作为可选扩展。
4. 用 float64 CPU 参考实现校验；输入包含大幅值（如 ±1000）、全相等、单元素突出等边界用例。
5. 与 PyTorch `torch.softmax` 对比（同一 dtype / layout / 输入），记录 GPU 型号、CUDA、驱动、PyTorch 版本与时钟状态。
6. 用 Nsight Compute 采集 SpeedOfLight、MemoryWorkloadAnalysis、Occupancy、SchedulerStats，报告 DRAM 吞吐、achieved occupancy、寄存器数、shared memory 用量与前 3 个 warp stall 原因。

**可选扩展**

- Fused masked Softmax + attention 的 `softmax(QKᵀ/√d)`（不要求完整 FlashAttention）。
- 半精度 / BF16 版本与数值误差对比。
- 多行 per block、persistent kernel、`cp.async` 或 TMA 流水线。

## 里程碑

- **M1 骨架**：V0 + 基准框架 + float64 参考；所有边界用例通过。
- **M2 核心**：V1 / V2，shared memory 与 warp 归约正确；性能超过 V0。
- **M3 优化**：V3、向量化、launch config 调优；Nsight 对比优化前后。
- **M4 报告**：三规模性能表、Roofline 定位、瓶颈解释与可复现命令。

## 交付物

- `src/softmax.cu`、`src/softmax_ref.cpp`、`bench/bench.py`（或 C++ benchmark）。
- `tests/`：边界输入与容差检查；`results/`：每个版本的原始计时 CSV（含 median / p10 / p90）。
- `profiles/`：Nsight Compute 导出的报告或关键指标截图；`plots/`：带宽与耗时对比图。
- `report.md`：优化步骤、每步收益、瓶颈证据、与 PyTorch 的差距分析。

## 验收标准

- 所有行与 float64 参考的 `max_abs_err ≤ 1e-5` 且 `max_rel_err ≤ 1e-4`（排除参考值接近 0 的位置，需说明）；无 NaN / Inf 泄漏。
- 大幅值输入（±1000）不溢出；若实现 mask 扩展，被 mask 位置的输出严格为 0。
- 在 `N=4096` 与 `N=16384` 上，最佳版本吞吐 **≥ PyTorch 的 80%**（扩展目标 ≥ 95%）。
- 最佳版本达到实测 copy 带宽的 **≥ 65%**；copy 带宽由同一张卡上的 `cudaMemcpy` 或 triad kernel 测得。
- 每个优化步骤至少 5 次运行取中位数，报告离散度；计时只包含 kernel，不包含分配与 H2D/D2H。
- Nsight 报告包含上述 5 类指标；能指出限制因素（如 DRAM 吞吐、occupancy、同步或尾块），并用数据支持。
- 不出现 shared memory bank conflict（或明确量化并解释为何可接受）。

## 参考

- [模块 07 练习题](../../07-CUDA编程与优化/exercises/07-cuda-q.md) 与 [custom_kernel_opt.cu](../../07-CUDA编程与优化/code/cuda/custom_kernel_opt.cu)
- [reduction.cu](../../06-GPU架构/code/cuda/reduction.cu)（shared memory + warp 归约示例）
- Milakov, M., & Gimelshein, N. "Online Normalizer Calculation for Softmax." 2018.
- Dao, T. et al. "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness." *NeurIPS'22*.
- NVIDIA, *CUDA C++ Programming Guide* 与 *Nsight Compute User Guide*.

## 常见陷阱与口径

- **在线 Softmax 不是两趟 reduction**：它单趟维护 `m_new = max(m, x)` 与 `l = l·exp(m−m_new) + exp(x−m_new)`，最后除以 `l`；不要与"先 max 再 sum"的两趟版本混写。
- block 归约的每一步之间要有 `__syncthreads()`；在归约完成前 `return` 会导致死锁或错误。
- warp shuffle 要用正确的 mask；`__shfl_down_sync` 的宽度与尾部 lane 处理要单独测试。
- 先减最大值再 `exp`；直接 `exp(x)` 在 x≈1000 时溢出。`__expf` 更快但精度较低，需用容差验证。
- 分母可能为 0（全 mask / 全 `-inf`）；定义输出策略（全 0 或 NaN）并写入测试。
- 与 PyTorch 比较时关闭不必要的分配，使用相同连续布局；PyTorch 可能已做向量化，必须同规模同 dtype。
- 计时用 CUDA event 并 warmup；避免把首次 kernel launch 的初始化成本算入稳态。
