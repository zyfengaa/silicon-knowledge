# 模块 02：ISA 与 CPU 基础 -- 练习题

## 02-isa-q.md：问题与练习

---

## 第 1 节：RISC 与 CISC 对比（RISC vs CISC Comparison）

### 问题 1.1

从五个维度比较 RISC 和 CISC 的 ISA。对于每个维度，给出一个具体例子说明设计理念有何不同。

### 问题 1.2

解释为什么 x86 处理器会在内部将指令解码为微操作（micro-ops / micro-operations）。这对 ISA 与微架构（microarchitecture）之间的界限有何启示？

### 问题 1.3

对于以下每个处理器，说明它使用的是 RISC 还是 CISC ISA，并指出它竞争的一个主要市场：

a) Intel Core i7
b) Apple M3
c) ESP32-C5（RISC-V 核心）
d) AMD Ryzen
e) Qualcomm Snapdragon 8 Gen 3

### 问题 1.4

为什么 CISC ISA 通常比 RISC ISA 拥有更多寻址模式（addressing modes）？这对编译器设计有何影响？

### 问题 1.5

列出定长指令编码（如 RISC-V 的 32 位指令）的三个优点和三个缺点。

---

## 第 2 节：RISC-V 指令编码（RISC-V Instruction Encoding）

### 问题 2.1

对于以下每条 RISC-V 指令，确定其格式（R, I, S, B, U, J），并将其编码为 32 位十六进制值。展示你的计算过程。

a) `add x10, x5, x6`
b) `sub x15, x10, x11`
c) `addi x7, x2, 42`
d) `lw x8, 16(x3)`
e) `sw x9, -8(x4)`
f) `beq x1, x2, 24`（分支目标距离当前 PC 24 字节）
g) `lui x1, 0xABCDE`
h) `jal x0, -32`（向后跳转 32 字节）

### 问题 2.2

解码以下 RISC-V 指令的十六进制值。对于每条指令，给出助记符（mnemonic）、寄存器操作数和立即数（immediate value）：

a) `0x00A282B3`
b) `0x40B502B3`
c) `0xFFF28293`
d) `0x0082A023`
e) `0x00428463`
f) `0x00008067`

### 问题 2.3

B 型分支编码将立即数分散到多个位段中。解释为什么立即数要以这种分散方式编码，而不是作为连续字段。

### 问题 2.4

RV32I 中分支偏移量（branch offset）的范围是多少？（考虑 I 型的立即数为 12 位，但 B 型的有效范围是多少？）

### 问题 2.5

为什么 RISC-V 中将寄存器 x0 硬连线为零？给出三个编程示例，说明这如何简化 ISA。

---

## 第 3 节：数据通路追踪（Datapath Tracing）

### 问题 3.1

追踪 `lw x5, 8(x6)` 在单周期数据通路（single-cycle datapath）中的执行过程。对于五个阶段中的每一个（IF, ID, EX, MEM, WB），回答：

a) 关键控制信号（RegWrite, ALUSrc, MemWrite, MemRead, MemtoReg）的值是什么？
b) ALU 在 EX 阶段做什么？
c) 哪个部件产生写入 x5 的值？
d) ALU 的输入 B 是什么？它来自哪里？

### 问题 3.2

追踪 `beq x10, x11, 16` 在单周期数据通路中的执行过程。回答：

a) ALU 在 EX 阶段计算什么？
b) 如果 x10 == x11，零标志（zero flag）的值是什么？如果 x10 != x11 呢？
c) PCSrc 信号是如何产生的？
d) 在两种情况下（分支跳转 vs. 不跳转），下一 PC 值分别是什么？

### 问题 3.3

在单周期 CPU 中，寄存器文件（register file）能否在同一周期内同时写入和读取？解释寄存器写入和读取的时序，以及当一条指令读取前一条指令刚刚写入的寄存器时会发生什么。

### 问题 3.4

画出 R 型指令 `and x20, x5, x6` 的简化数据通路。展示数据通过寄存器文件、ALU 和写回（write-back）的流程。指出哪些控制信号是有效的。

### 问题 3.5

识别 SW 指令的 critical path（关键路径）。解释为什么它可能比 LW 指令的关键路径更短或更长。

---

## 第 4 节：控制信号表（Control Signal Table）

### 问题 4.1

为以下 RV32I 指令填写控制信号真值表：

| 指令 | RegWrite | ALUSrc | MemWrite | MemRead | MemtoReg | Branch | Jump | ALUOp |
|-------------|----------|--------|----------|---------|----------|--------|------|-------|
| ADD x1,x2,x3|          |        |          |         |          |        |      |       |
| SUB x4,x5,x6|          |        |          |         |          |        |      |       |
| ADDI x1,x2,5|          |        |          |         |          |        |      |       |
| LW x5,0(x6) |          |        |          |         |          |        |      |       |
| SW x5,8(x6) |          |        |          |         |          |        |      |       |
| BEQ x1,x2, L|          |        |          |         |          |        |      |       |
| JAL x1, func|          |        |          |         |          |        |      |       |
| LUI x1,0x123|          |        |          |         |          |        |      |       |

### 问题 4.2

ALUOp 信号宽度为 2 位，编码三种模式（00, 01, 10）。解释 ALU 解码器（ALU decoder）如何结合 ALUOp、funct3 和 funct7 来产生精确的 ALU 控制信号。

### 问题 4.3

设计 RegWrite 和 ALUSrc 控制信号的逻辑方程（用 Verilog 或布尔代数表示）。假设你已经有了每条指令类别的解码信号（例如 r_type, i_type, load, store, branch, jal, jalr, lui, auipc）。

### 问题 4.4

如果 ALUSrc 信号被错误地设置为 1，`add x1, x2, x3` 的执行会发生什么？ALU 会计算出什么值？

### 问题 4.5

解释硬连线控制（hardwired control）和微程序控制（microprogrammed control）的区别。对于 RISC-V CPU，哪种方法更合适，为什么？

---

## 第 5 节：多周期 CPU（Multi-Cycle CPU）

### 问题 5.1

列出多周期 CPU 中每条指令类型所需的周期数：LW, SW, R-type, branch, JAL。

### 问题 5.2

为什么多周期 CPU 允许比单周期 CPU 更快的时钟？主要的性能权衡（tradeoff）是什么？

### 问题 5.3

给定以下程序的指令混合比例：
- 22% LW, 12% SW, 42% R-type, 20% branch, 4% JAL

计算以下情况的平均 CPI：
a) 单周期 CPU（CPI = 1）
b) 多周期 CPU（使用问题 5.1 中的周期数）

如果单周期 CPU 运行在 1 GHz，多周期 CPU 运行在 3 GHz，哪个更快？

### 问题 5.4

在多周期 CPU 中，控制单元是一个有限状态机（finite state machine）。画出 LW 指令的状态转换图，展示所有状态以及每个状态中断言的控制信号。

### 问题 5.5

多周期 CPU 使用内部寄存器（IR, A, B, ALUOut, Data）来保存各周期之间的中间值。解释为什么需要这些寄存器。如果没有它们会发生什么？

---

## 第 6 节：应用题（Applied Problems）

### 问题 6.1

编写一个 RISC-V 汇编函数，计算前 n 个自然数的和（1 + 2 + ... + n），其中 n 通过 a0 传递。将结果返回到 a0 中。

### 问题 6.2

将以下 C 代码翻译为 RISC-V 汇编：

```c
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
```

### 问题 6.3

一个 RISC-V 处理器的数据通路部件时序如下：
- 指令存储器（Instruction memory）：250 ps
- 寄存器文件读取（Register file read）：100 ps
- 寄存器文件写入（Register file write）：80 ps
- ALU：200 ps
- 数据存储器（Data memory）：250 ps
- 控制单元（Control unit）：50 ps
- 立即数生成器（Immediate generator）：50 ps
- 多路选择器（Multiplexers）：每个 20 ps
- PC 寄存器（clk-to-q）：30 ps
- 建立时间（Setup time）：30 ps

a) 单周期 CPU 的最小周期时间是多少？
b) 哪条指令决定了这个关键路径？
c) 如果我们将 CPU 流水线化（5 级），大约的周期时间是多少？
d) 对于无冒险（hazard）的程序，流水线相比单周期能提供多大的加速比（speedup）？

### 问题 6.4

解释哈佛架构（Harvard architecture，单周期 CPU 模型中使用的）与冯诺依曼架构（von Neumann architecture）的区别。为什么单周期模型假设指令存储器与数据存储器是分开的？

### 问题 6.5

调研问题：查阅 RISC-V 调用约定规范（calling convention specification）。解释：
a) 哪些寄存器由调用者保存（caller-saved）vs. 被调用者保存（callee-saved）？
b) 函数参数是如何传递的（使用哪些寄存器，如果参数超过 8 个怎么办）？
c) 函数的返回值是如何存储的？

---

## 答题指南（Answer Guidelines）

- 对于编码问题（第 2 节），在转换为十六进制之前展示二进制字段
- 对于数据通路问题（第 3 节），确定哪些控制信号为 0 或 1，并追踪数据流
- 对于应用题（第 6 节），为每条汇编指令添加注释

---

## 参考文献（References）

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. 第 2、4 章。
2. Waterman, A., & Asanovic, K. (编). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. 文档版本 20191213.
3. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. 第 6、7 章。
