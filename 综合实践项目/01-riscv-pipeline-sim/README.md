# 项目 01 — RISC-V 5 段流水线模拟器

> 实现一个周期级、可观测的 RV32I 5 段流水线模拟器，用 CPI 和逐周期 trace 解释"程序为什么没有跑满一个周期一条指令"。

## 目标

- 从单周期数据通路自然过渡到 IF / ID / EX / MEM / WB 五级流水线。
- 显式建模流水线寄存器、数据冒险、load-use 停顿、控制冒险与分支冲刷。
- 让每一条指令、每一个停顿、每一次转发都可追踪、可统计、可复现。
- 最终能用自己模拟器输出的数字解释 IPC 损失来自哪里。

## 前置知识

- [模块 02：指令集与 CPU 基本组成](../../02-指令集与CPU基本组成/README.md)
- [RISC-V 指令格式与常用指令](../../02-指令集与CPU基本组成/notes/03-riscv-instructions.md)
- [CPU 数据通路](../../02-指令集与CPU基本组成/notes/04-cpu-datapath.md) 与 [单周期 CPU](../../02-指令集与CPU基本组成/notes/06-single-cycle-cpu.md)
- [模块 03：CPU 流水线](../../03-CPU流水线/README.md)
- [流水线基础](../../03-CPU流水线/notes/01-pipeline-basics.md)、[数据冒险](../../03-CPU流水线/notes/03-data-hazards.md)、[控制冒险](../../03-CPU流水线/notes/04-control-hazards.md)、[流水线性能](../../03-CPU流水线/notes/05-pipeline-performance.md)
- 可先运行 [pipeline_sim.py](../../03-CPU流水线/code/python/pipeline_sim.py) 观察行为模型；本项目要求独立实现**周期级**版本。

## 任务要求

**必做**

1. 用 C++17 或 Python 3.10+ 实现 RV32I 全部 40 条指令（`FENCE` 可作 NOP，`ECALL` / `EBREAK` 作停机），支持小端字节、半字、字访存与符号扩展。
2. 实现 5 段流水线与段间寄存器（IF/ID、ID/EX、EX/MEM、MEM/WB），正确处理 stall 与 flush。
3. 实现 EX/MEM、MEM/WB 到 EX 的完整转发，包括 ALU 结果与 **store data** 转发；load-use 冒险停顿 1 拍后经 MEM/WB 转发。
4. 分支在 EX 段解析；默认预测不跳转；实现 256 项、2-bit 饱和计数器 BHT（索引 `PC[9:2]`，初值 weakly not-taken），预测失败冲刷 2 条年轻指令。
5. 输入为十六进制机器码文件（每行一条 32-bit 指令），输出逐周期 CSV 与汇总 JSON：总周期、退休指令数、CPI、各类停顿周期、分支次数 / 失败率、转发的操作数次数。
6. 另写一个**不建模时序的功能模拟器**作为 golden model，比较最终寄存器堆与内存。

**可选扩展**

- 对比 gshare、局部历史预测器与 tournament 预测器。
- 增加 RV32IM 乘除法多周期单元与相应停顿。
- 加入返回地址栈（RAS）、指令缓存模型或双发射。
- 生成可读的流水线时空图（文本或 matplotlib）。

## 里程碑

- **M1 骨架**：机器码加载、译码、功能模拟器跑通；5 个手写测试程序结果正确。
- **M2 核心**：5 段寄存器、转发、load-use 停顿、分支与冲刷；能输出逐周期 trace。
- **M3 验证**：与 golden model 做差分测试；手算 3 段指令序列的周期数并与模拟器逐拍对齐。
- **M4 报告**：扫描分支预测器 / 转发开关，绘图并解释 CPI 分解。

## 交付物

- `src/`：模拟器与 golden model；`tests/`：汇编源、机器码、期望状态。
- `traces/`：至少 3 个程序的逐周期 CSV；`results/`：CPI 与冒险统计。
- `plots/`：CPI 分解图、预测器对比图；`report.md`：方法、实验、结论、局限。
- 根目录 `README.md`：构建 / 运行 / 测试命令与 trace 字段说明。

## 验收标准

- 20 个功能测试程序（含递归、函数调用、字节 / 半字访存、负数和 `x0` 写入）最终架构状态与 golden model **逐寄存器、逐字节一致**。
- 10,000 条随机合法指令的差分测试 100% 通过；非法指令必须在正确 PC 报错。
- 3 段指定序列的总周期数与手算完全一致（误差 0 周期）；CPI 分解各项之和等于总周期。
- 构造的 load-use 序列恰好停顿 1 拍，且停顿后数值正确；store 转发测试通过。
- 分支预测器在给定循环 trace 上的失败率与手工计数一致；flush 周期计入总周期。
- trace 每周期恰好一行，字段完整；汇总 JSON 可由脚本重新计算并与模拟器输出一致。

## 参考

- [模块 03 练习题](../../03-CPU流水线/exercises/03-pipeline-q.md) 与 [流水线性能论文笔记](../../03-CPU流水线/papers/01-pipeline-performance.md)
- Patterson & Hennessy, *Computer Organization and Design: RISC-V Edition*, 第 4 章。
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 3 章。
- [RISC-V Instruction Set Manual, Volume I](https://riscv.org/technical/specifications/)
- Smith, J. E. "A Study of Branch Prediction Strategies." *ISCA'81*.

## 常见陷阱与口径

- **分支在 EX 解析**意味着同拍有 2 条更年轻的指令被冲刷；若改在 ID 解析，必须重算周期并说明口径。
- forwarding 不能消除 load-use 停顿；停顿拍里 PC 与 IF/ID 保持不变，ID/EX 注入 bubble。
- CPI 统一用 `总周期 / 退休指令数`；被冲刷的指令不计入退休数，但周期必须计入。
- `x0` 永远为 0；`jalr` 的 LSB 清零；`auipc` 使用当前指令 PC；分支目标按字节地址计算。
- store 的数据可能来自前一条 ALU 指令，不能只转发地址；这是最常见的数值错误来源。
- 内存模型要固定字节序、非对齐访问策略（支持或精确报错）和访存延迟口径，报告中写清楚。
