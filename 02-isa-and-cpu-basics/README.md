# 02 — 指令集与 CPU 基本组成

> 软件与硬件的边界。理解 CPU 到底"认识"什么样的指令，以及一条指令从取指到写回经历了什么。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **ISA 导论** | 什么是指令集架构？RISC 与 CISC 的设计哲学差异 |
| 02 | **为什么选 RISC-V** | RISC-V 作为教学 ISA 的优势：简洁、开源、模块化 |
| 03 | **RISC-V 指令集** | RV32I 指令格式（R/I/S/B/U/J）、常用指令用法 |
| 04 | **CPU 数据通路** | 取指→译码→执行→访存→写回：数据在 CPU 中的完整路径 |
| 05 | **控制单元** | 硬连线控制 vs 微程序控制 |
| 06 | **单周期 CPU** | 每条指令一个时钟周期的 CPU 设计与时序 |
| 07 | **多周期 CPU** | 用状态机实现分步执行的多周期 CPU |

## 前置知识

- [01 数字逻辑基础](/01-digital-logic/)（加法器、寄存器、时钟概念）

## 建议学习方式

1. **先装工具**：安装 RISC-V 工具链或使用 Venus 在线模拟器
2. **读 + 写汇编**：读懂笔记后，手写简单的 RISC-V 汇编并运行
3. **画数据通路**：在地上/纸上画出单周期 CPU 各部件连接关系
4. **逐步推理**：选几条指令（`add`、`lw`、`beq`），跟踪它们在数据通路中的每一步

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/riscv_sim.py` | 简单 RISC-V 指令模拟器 |
| `asm/fib.S` | 递归求 Fibonacci 数列的 RISC-V 汇编 |
| `asm/function_call.S` | 函数调用栈帧的汇编示例 |
| `asm/mem_access.S` | 内存读写指令的汇编示例 |

## 关键产出

- [ ] 能读 RISC-V 汇编代码，能手写简单循环/条件/函数调用
- [ ] 能画出单周期 CPU 的数据通路图
- [ ] 能解释 R-C 型（RISC） 与 C-C 型（CISC）指令的本质区别
- [ ] 知道控制单元的两种实现方式及其取舍
- [ ] 能用工具将 C 代码编译为 RISC-V 汇编并查看结果

## 参考文献

- Patterson & Hennessy, *Computer Organization and Design RISC-V Edition*, 第 1-4 章
- [RISC-V 官方指令集规范](https://riscv.org/technical/specifications/)
- Waterman, A. & Asanović, K., *The RISC-V Instruction Set Manual Volume I*
