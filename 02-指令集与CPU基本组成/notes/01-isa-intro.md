# 模块 02：指令集与 CPU 基本组成
## 01 — 指令集架构（ISA）导论

### 什么是 ISA？

一个**指令集架构（Instruction Set Architecture, ISA）**是计算机软件与其硬件之间的抽象接口。它定义了：

- 处理器可以执行的**指令（instructions）**
- 软件可见的**寄存器（registers）**
- **内存模型（memory model）**（地址空间、对齐方式、字节序）
- 可用的**寻址模式（addressing modes）**
- 支持的**数据类型（data types）**

ISA 是一份契约：任何编译到给定 ISA 的程序，都能在任何实现该 ISA 的处理器上运行，而与微架构无关。将 ISA 与微架构（microarchitecture）分离，是计算机体系结构中最重要的概念之一。

> **关键洞察：** ISA 是程序员/编译器所看到的内容。微架构是硬件实现它的方式。同一个 ISA（例如 x86）可以拥有截然不同的微架构（Intel Core、Atom、Pentium）。

### 硬件-软件接口

```
+--------------------------------------------------+
|                   Applications                    |
+--------------------------------------------------+
|          Operating System / Runtime               |
+--------------------------------------------------+
|    Compiler    |    ISA (the interface layer)     |
+--------------------------------------------------+
|              Microarchitecture                    |
+--------------------------------------------------+
|              Circuit Logic                        |
+--------------------------------------------------+
|               Transistors                         |
+--------------------------------------------------+
```

ISA 充当分界线：在其之上，软件是可移植的；在其之下，硬件可以被自由优化。

### RISC 与 CISC 的设计哲学

两种主流的 ISA 设计哲学诞生于 20 世纪 80 年代。它们之间的权衡至今仍是体系结构领域的核心。

| 特性 | RISC（精简指令集计算机，Reduced Instruction Set Computer） | CISC（复杂指令集计算机，Complex Instruction Set Computer） |
|----------------------|----------------------------------------|----------------------------------------|
| 指令长度 | 固定（通常为 32 位） | 可变（1--15 字节） |
| 指令数量 | 少（约 50--100） | 多（约 300--1000+） |
| 寻址模式 | 少（通常为 1--3 种） | 多（10 种以上） |
| 内存操作数（memory operands） | 仅限 load/store | 许多指令都能访问内存 |
| 寄存器 | 大量通用寄存器 | 较少，且部分为专用寄存器 |
| 控制单元（control unit） | 简单，通常采用硬布线（hardwired） | 复杂，通常采用微程序控制（microprogrammed） |
| 流水线（pipelining） | 因规整性而更易实现 | 因指令长度可变而更难实现 |

#### x86 / x86-64（CISC）

Intel 的 8086（1978 年）确立了 x86 ISA，随后通过 32 位（IA-32）与 64 位（x86-64 / AMD64）扩展不断演进。尽管 x86 源自 CISC，现代 x86 处理器会将指令解码为微操作（micro-ops，即类似 RISC 的内部操作）。

- **主导领域：** 台式机、笔记本电脑、服务器
- **厂商：** Intel、AMD
- **关键特征：** 向后兼容性可追溯至数十年前
- **参考：** Intel 64 and IA-32 Architectures Software Developer's Manual

#### ARM（RISC）

ARM ISA 最初名为 Acorn RISC Machine（1985 年）。它从 ARMv1 演进到 ARMv9，陆续加入了 Thumb（16 位指令）、NEON（SIMD）以及 64 位（AArch64）。

- **主导领域：** 手机、嵌入式系统、物联网，并越来越多地进入笔记本电脑/服务器
- **厂商：** Arm Ltd.（授权给 Apple、Qualcomm、Samsung、NVIDIA、Amazon 等）
- **关键特征：** 高能效设计
- **参考：** ARM Architecture Reference Manual

#### RISC-V（RISC）

RISC-V 是一个自由、开放的 ISA，由加州大学伯克利分校于 2010 年开发。它采用模块化设计：一个精简的强制基础整数 ISA（RV32I/RV64I），加上可选的标准扩展。

- **主导领域：** 研究、教育以及日益增长的商业应用
- **关键特征：** 开放标准、无授权费用、设计简洁
- **参考：** RISC-V ISA Manual, Volume I

### 指令格式（Instruction Formats）

指令被编码为二进制字。格式决定了如何将比特划分为操作码（opcode）、操作数等字段。

| 字段 | 用途 |
|-----------|--------------------------------------------|
| opcode | 标识指令类型 |
| rd | 目标寄存器 |
| rs1, rs2 | 源寄存器 |
| funct3/funct7 | 进一步指定具体操作 |
| immediate | 常量值（编码在指令中） |

不同的 ISA 家族使用不同的格式。RISC-V 使用六种统一的格式（将在第 03 节中详细介绍）。

### 寻址模式

寻址模式规定了如何计算操作数的内存地址。

| 模式 | 有效地址（effective address） | 示例（RISC-V） |
|-----------------------|------------------------|--------------------|
| 寄存器操作数 | 无内存访问；操作数为 `R[rs]` | `add x1, x2, x3` |
| 立即数（immediate） | 无内存访问；操作数为编码的常量 | `addi x1, x2, 5` |
| 基址+偏移（base+offset） | `R[rs1] + imm` | `lw x1, 8(x2)` |
| PC 相对（PC-relative） | `PC + imm`（分支/跳转目标） | `beq x1, x2, off` |
| 寄存器间接（register indirect） | `R[rs1] + 0`（imm = 0 的基址+偏移） | `lw x1, 0(x2)` |

RISC-V 刻意让寻址模式保持简单：内存操作只使用基址+偏移（寄存器间接只是 imm = 0 时的特例），而分支和跳转使用 PC 相对或 `rs1 + imm` 目标。

### 关键概念总结

- **ISA** = 软件与硬件之间的契约
- **RISC** = 指令简单且长度固定，采用 load/store 架构
- **CISC** = 指令复杂且长度可变，支持内存操作数
- x86 主导服务器/PC；ARM 主导移动端；RISC-V 是正在崛起的开放之星
- 指令格式 = 比特如何编码操作与操作数
- 寻址模式 = 如何计算内存地址

### 现实世界的影响

选择一个 ISA 会影响整个生态系统：编译器工具链、操作系统支持、运行时库以及硬件设计成本。RISC-V 革命之所以意义重大，是因为它让 ISA 创新与公司所有权解耦，正如 Linux 为操作系统所做的那样。

---

### 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapters 1--2.
2. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix A.
3. Patterson, D. A. "Reduced Instruction Set Computers." *Communications of the ACM*, Vol. 28 No. 1, 1985.
4. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213.
5. Intel Corporation. *Intel 64 and IA-32 Architectures Software Developer's Manual*. Volume 1.
6. Arm Limited. *Arm Architecture Reference Manual for A-profile architecture*.
