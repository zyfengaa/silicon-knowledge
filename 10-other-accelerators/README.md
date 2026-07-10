# 10 — 其他加速器

> CPU / GPU / NPU / TPU 之外的世界。了解 FPGA、Cerebras、Groq、Graphcore、SambaNova 等不同流派的设计理念，以及近存计算、光计算等前沿方向。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **FPGA 基础** | LUT、CLB、可编程互联、与 CPU/GPU 的本质区别 |
| 02 | **FPGA vs CPU/GPU** | 什么场景下 FPGA 是更好的选择 |
| 03 | **Cerebras WSE** | 整晶圆互联：Wafer-Scale Engine 的胆大方案 |
| 04 | **Groq LPU** | 确定性执行架构：为什么不需要乱序执行 |
| 05 | **Graphcore IPU** | MIMD 架构：Poplar 编译器与计算图调度 |
| 06 | **SambaNova RDU** | 可重构数据流：编译器驱动的硬件配置 |
| 07 | **近存计算** | 存算一体 / PIM（Processing-In-Memory）的动机和挑战 |
| 08 | **前沿方向** | 光计算、模拟计算、量子计算的发展现状 |

## 前置知识

- [08 NPU](/08-npu/)（作为对照基准，理解"专有加速"的设计权衡）

## 建议学习方式

1. 本模块以拓宽视野为主，每个方向 1-2 篇笔记即可
2. 选 1-2 个你最感兴趣的方向深入（比如 Groq 或 Cerebras）
3. 对比每种加速器的设计哲学和适用场景

## 关键产出

- [ ] 能说出 FPGA 与 CPU/GPU 的本质区别（可重构 vs 固定指令）
- [ ] 能解释 Cerebras 为什么选择"整晶圆"方案
- [ ] 理解 Groq LPU 的确定性架构为什么省掉了 OOO 和分支预测
- [ ] 了解近存计算为什么越来越重要

## 参考文献

- Cerebras, *Wafer-Scale Engine: The Largest Chip Ever Built* (白皮书)
- Groq, *Groq Architecture Whitepaper*
- Graphcore, *Graphcore IPU Architecture Whitepaper*
- SambaNova, *Reconfigurable Dataflow Unit*
- Mutlu, O. "Processing-in-Memory: A Workload-Driven Perspective." *IBM Research*, 2021.
