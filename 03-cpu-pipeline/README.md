# 03 — CPU 流水线

> 现代 CPU 性能的基石。理解如何通过"分阶段并行"让 CPU 每个时钟周期完成一条以上指令。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **流水线基础** | 5 段流水线（IF/ID/EX/MEM/WB），各阶段做什么 |
| 02 | **冒险概览** | 三类冒险（结构/数据/控制）的产生原因 |
| 03 | **数据冒险** | RAW/WAR/WAW 依赖、forwarding 技术、流水线停顿 |
| 04 | **控制冒险** | 分支预测失败的影响、静态预测策略、分支延迟槽 |
| 05 | **流水线性能** | CPI 计算、流水线深度对时钟频率和性能的影响 |

## 前置知识

- [02 ISA 与 CPU 基本组成](/02-isa-and-cpu-basics/)（单周期 CPU 数据通路、RISC-V 常用指令）

## 建议学习方式

1. 先复习单周期 CPU 的数据通路图（模块 02 的产出）
2. 在单周期基础上添加流水线寄存器 → 理解 5 段拆分
3. 跟踪 3-5 条连续指令在流水线中的执行过程
4. 运行 `code/python/pipeline_sim.py`，观察冒险和转发效果
5. 完成 `exercises/` 中的 CPI 计算题

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/pipeline_sim.py` | 5 段流水线行为模拟器，支持冒险检测和 forwarding |
| `python/pipeline_perf.py` | 不同冒险场景下的 CPI 计算与分析 |

## 关键产出

- [ ] 能画出带流水线寄存器的 5 段流水线结构图
- [ ] 能识别任意指令序列中的数据冒险并判断是否需要 forwarding
- [ ] 能手工计算给定指令序列在流水线中的 CPI
- [ ] 理解为什么流水线越深，频率越高但冒险代价也越大
- [ ] 理解 forwarding 为什么不能消除 load-use 停顿

## 参考文献

- Patterson & Hennessy, *Computer Organization and Design RISC-V Edition*, 第 4 章
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 3 章
