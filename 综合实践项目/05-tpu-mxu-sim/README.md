# 项目 05 — TPU MXU 矩阵乘单元模拟

> 用 C++ 实现 BF16 输入、FP32 累加的 128×128 脉动 MXU，并配上 HBM 模型与指令队列，量化"算得快"与"喂得饱"之间的差距。

## 目标

- 理解 TPU 风格 MXU 的组织：PE 阵列、BF16 乘法、FP32 累加、分块 GEMM。
- 把计算单元放进存储层次里：HBM → 片上 buffer → MXU → HBM。
- 用指令队列描述 `LD` / `MXU` / `ST` 的依赖与执行顺序。
- 用 MAC 利用率、DMA 时间占比、有效 TOPS 和算术强度评价设计。

## 前置知识

- [模块 08：NPU 神经网络处理器](../../08-NPU神经网络处理器/README.md)
- [脉动阵列](../../08-NPU神经网络处理器/notes/02-systolic-array.md)、[映射 GEMM](../../08-NPU神经网络处理器/notes/03-mapping-gemm.md)
- [量化与数值格式](../../08-NPU神经网络处理器/notes/04-quantization.md)、[片上存储](../../08-NPU神经网络处理器/notes/06-on-chip-memory.md)
- [模块 09：Google TPU](../../09-Google-TPU/README.md)
- [TPU v1](../../09-Google-TPU/notes/02-tpu-v1.md)、[TPU v2](../../09-Google-TPU/notes/03-tpu-v2.md)、[TPU 核心架构](../../09-Google-TPU/notes/07-tpu-arch-core.md)
- [TPU v1 论文笔记](../../09-Google-TPU/papers/01-tpu-v1.md)、[TPU v2/v3 论文笔记](../../09-Google-TPU/papers/02-tpu-v2-v3.md)

## 任务要求

**必做**

1. C++17 + CMake，不依赖第三方库；实现 `bf16` 类型（`uint16_t` 存储）与 **round-to-nearest-even** 的 float32→bf16 转换。
2. 实现可配置的 R×C 脉动 MXU（至少 32×32、64×64、128×128），每个 PE 每拍完成一次 BF16 乘 + FP32 累加；支持 M/N/K 非整块时的补零。
3. 实现 HBM 模型：容量至少 1 GiB（可用稀疏 `unordered_map` 或文件映射），可配置带宽、延迟与 64 B 传输粒度；统计读 / 写字数与字节数。
4. 实现片上统一 buffer（UB）与 DMA：`LD` 把 A/B tile 从 HBM 搬到 UB，`MXU` 从 UB 读并写回 UB，`ST` 把 C tile 写回 HBM；检查容量与越界。
5. 实现顺序指令队列：每条指令带操作码、源 / 目的地址、M/N/K、stride；用简单 scoreboard 跟踪 RAW / WAW 依赖，按序发射，统计每类指令的等待周期。
6. 从文件加载矩阵（文本或二进制格式自定义并写入文档）；输出结果、逐指令周期、总周期、HBM 字节、有效 MAC 数、MAC 利用率、按 1 GHz 示例时钟计算的有效 TFLOPS。
7. 与"BF16 量化后的 float32 参考矩阵乘"对比，验证数值正确性。

**可选扩展**

- 双缓冲，让下一 tile 的 `LD` 与当前 `MXU` 重叠；报告重叠前后的周期差。
- 2:4 结构化稀疏（或 4:1），跳过零块并验证加速比不超过理论上限。
- 加入 `ACT`（激活）或 `VEC` 指令，形成最小推理流水线。
- 统计不同 tile 形状下的 HBM 流量与算术强度，寻找带宽拐点。

## 里程碑

- **M1 骨架**：bf16 转换、矩阵文件加载、CPU 参考 GEMM；转换单测通过。
- **M2 核心**：MXU 分块计算、UB 与 DMA、HBM 模型；单条 `MXU` 指令正确。
- **M3 验证**：指令队列、依赖、统计；与参考实现对比，周期与流量账目闭合。
- **M4 报告**：阵列尺寸 / 时钟 / 带宽扫描，利用率与有效 TOPS，瓶颈分析。

## 交付物

- `src/`：`bf16`、MXU、HBM、UB、DMA、指令队列；`tests/`：转换、GEMM、依赖测试。
- `bench/`：矩阵生成与批量运行脚本；`results/`：不同尺寸与配置的 CSV。
- `plots/`：周期分解、MAC 利用率、HBM 流量 vs 算术强度。
- `report.md`：架构图、指令格式、周期模型、数值误差、示例 TOPS 的口径与局限。

## 验收标准

- 10,000 个随机有限 float32 值（含次正规数）的 bf16 转换与参考 RNE 实现 **逐位一致**；±Inf 保持符号，NaN 保持 NaN，quiet / signaling 与 payload 策略需写明，不要求 payload 逐位一致。
- 128/256/1024 三组 M/N/K 的结果与 BF16 量化输入的 FP32 参考相比，`max_rel_err ≤ 1e-3`（报告需说明误差来源）。
- 32×32、64×64、128×128 三种阵列在相同问题上输出一致；周期数随阵列尺寸变化的趋势可解释。
- 至少 3 条有依赖的指令序列按序执行；RAW 依赖必须等待，WAW 不得覆盖未读结果。
- 单次 GEMM 的 HBM 读 / 写字节与手算一致（含 tile 重复读取时需说明）；总周期 = DMA 周期 + MXU 周期 + 等待周期（无重叠模式下误差 0）。
- 有效 TOPS 计算正确：`2·M·N·K / 总时间`，并同时报告峰值 `2·R·C·f` 与利用率；示例时钟必须标注为假设。
- 报告中不得把模拟的有效 TOPS 与真实 TPU 峰值混为一谈。

## 参考

- Jouppi, N. et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *ISCA'17*.
- Jouppi, N. et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *CACM*, 2020.
- [TPU 核心架构笔记](../../09-Google-TPU/notes/07-tpu-arch-core.md)、[TPU vs GPU](../../09-Google-TPU/notes/10-tpu-vs-gpu.md)
- [模块 09 练习题](../../09-Google-TPU/exercises/09-tpu-q.md)
- [BF16 与精度硬件](../../06-GPU架构/notes/12-precision-hardware.md)

## 常见陷阱与口径

- **BF16 不是 FP16**：BF16 有 8 位指数、7 位尾数，动态范围接近 FP32 但精度低；不要用 FP16 类型冒充。
- BF16 输入、FP32 累加是两件事；不要把累加器也截断成 BF16，否则误差量级完全不同。
- 峰值 MAC 数 = `R×C×频率`；峰值 FLOPS = `2×R×C×频率`。利用率的分母要包含填充与 DMA 等待。
- 128×128 指 PE 数，不是矩阵维度；tile 大小、K 分块和补零都会改变周期与流量。
- HBM 字节按传输粒度向上取整；tile 重复加载会增加流量，不能只按理想一次读写计算。
- 1 GHz 是为了把周期换算成 TOPS 的**示例假设**，不是 TPU 的实际频率；报告中必须单独标注。
- 指令队列的"顺序发射"不等于"顺序完成"；若允许重叠，必须说明 scoreboard 的完成与唤醒规则。
