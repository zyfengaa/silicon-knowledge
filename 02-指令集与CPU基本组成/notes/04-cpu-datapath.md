# 模块 02：指令集与 CPU 基本组成
## 04 — 单周期 CPU 数据通路

### 概述

**数据通路（datapath）**是执行数据处理操作的功能单元（functional unit）的集合。它与负责指挥数据通路的**控制单元（control unit）**一起构成 CPU 的核心。

在**单周期实现（single-cycle implementation）**中，每条指令恰好在一个时钟周期（clock cycle）内执行。时钟周期必须长到足以容纳最慢的指令。

### 基本数据通路组件

| 组件        | 功能                                                      |
|------------------|--------------------------------------------------------------|
| 程序计数器（Program Counter） | 保存当前指令的地址                         |
| 指令存储器（Instruction Memory） | 存储程序；在 PC 地址处读取                        |
| 寄存器堆（Register File） | 32 个 32 位寄存器（x0--x31）；2 个读端口、1 个写端口 |
| 算术逻辑单元（ALU） | 执行算术/逻辑运算                       |
| 数据存储器（Data Memory） | 存储数据；加载/存储指令使用 ALU 结果作为地址        |
| 加法器（Adders） | PC+4 自增；分支目标（branch target）计算                    |
| 多路选择器（Multiplexers） | 在数据源之间选择，由控制信号（control signals）控制  |

### 指令执行的五个阶段

每条指令最多经历五个阶段：

1. **取指（IF，Instruction Fetch）**：在 PC 处从存储器取指令
2. **译码（ID，Instruction Decode）**：对指令译码，读取寄存器
3. **执行（EX，Execute）**：执行 ALU 运算或地址计算
4. **访存（MEM，Memory Access）**：读/写数据存储器（仅限加载/存储指令）
5. **写回（WB，Write Back）**：将结果写入寄存器堆

对于单周期 CPU，全部五个阶段在一个时钟周期内完成。

### 逐步分析：`add x1, x2, x3` 如何流经数据通路

让我们追踪 `add x1, x2, x3`（编码：`0x003100B3`）的执行过程。

#### 阶段 1：取指（IF）

```
+----------+
|   PC     |---> Address to Instruction Memory
| (0x100)  |
+----------+

+---------------------+
| Instruction Memory  |
| Address 0x100:      |
| 0x003100B3 (add)    |
+---------------------+

Result: 32-bit instruction word = 0x003100B3 is read from memory
PC is also sent to the adder for PC+4 calculation
```

**硬件**：PC 寄存器驱动指令存储器的地址输入。指令字（instruction word）出现在输出数据线上。同时，一个加法器计算 PC + 4（下一条指令的地址）。

#### 阶段 2：译码（ID）

```
Instruction bits are extracted:
- opcode [6:0] = 0110011  (R-type)
- rd [11:7]    = 00001    (x1)
- funct3 [14:12] = 000
- rs1 [19:15]  = 00010    (x2)
- rs2 [24:20]  = 00011    (x3)
- funct7 [31:25] = 0000000

Register File:
- Read address 1 (rs1 = x2) --> Read data 1 = value of x2
- Read address 2 (rs2 = x3) --> Read data 2 = value of x3
```

**硬件**：指令字的 rs1 和 rs2 字段驱动寄存器堆的读地址端口。寄存器堆输出 x2 和 x3 的内容。

#### 阶段 3：执行（EX）

```
ALU inputs:
- Input A = Read data 1 (value of x2)
- Input B = Read data 2 (value of x3)

ALU control determines operation based on:
- funct3 = 000
- funct7 = 0000000
- opcode = 0110011
--> ALU performs ADD

ALU result = x2 + x3
```

**硬件**：两个寄存器值送入 ALU。ALU 控制逻辑（ALU control logic）对 funct3、funct7 和 opcode 进行译码以选择 ADD。ALU 计算和值。

#### 阶段 4：访存（MEM）

```
For add instruction: no memory access needed.
ALU result passes through unmodified.

(LW/SW would access data memory here.)
```

**硬件**：对于 R 型（R-type）指令，MEM 阶段是直通（pass-through）。ALU 结果被直接转发。

#### 阶段 5：写回（WB）

```
Register File write:
- Write address = rd = x1
- Write data = ALU result = x2 + x3
- RegWrite signal = 1 (enabled for R-type)

Result: x1 is updated with the sum of x2 and x3
```

**硬件**：ALU 结果被路由到寄存器堆的写数据输入端。rd 字段驱动写地址。RegWrite 控制信号被置为有效，使寄存器堆存储结果。

### ASCII 数据通路图

```
                  +-----------------------+
                  |   Instruction Memory  |
                  |   (address -> data)   |
                  +-----------------------+
                    ^              |
                    |              | instruction
                    |              v
+--------+          |    +------------------+
|   PC   |----------+    |                  |
|(32-bit)|               |  Control Unit    |
+--------+               |  (see notes/05)  |
    |                    |                  |
    | PC+4               +------------------+
    v                           |
+-------+                      | control signals
| Addr  |                      |
| PC+4  |                      v
+-------+              +------------------+
    |                  |  Register File   |
    | MUX              |  32 x 32-bit     |
    |                  |                  |
    +----> PC (next)   +---------+--------+
                                  |
                  +---------------+---------------+
                  |               |               |
                  v               v               v
              +--------+    +---------+     +----------+
              |  ALU   |<---|   MUX   |     |  Data    |
              |        |    +---------+     |  Memory  |
              +--------+         ^          +----------+
                  |              |               |
                  v              |               v
             +--------+          |          +--------+
             |  MUX   |----------+          |  MUX   |
             +--------+                     +--------+
                  |                              |
                  v                              v
            Register WB                     (branch target)
```

### 数据通路设计决策

**寄存器堆端口**：两个读端口（rs1、rs2）和一个写端口（rd）允许在 ID 阶段同时读取寄存器，并在 WB 阶段写入寄存器。

**指令存储器与数据存储器**：哈佛架构（Harvard architecture，分离的存储器）允许指令取指和数据访问在同一周期内发生而不产生争用。在流水线设计（pipelined design）中，这种同样的冲突被称为结构冒险（structural hazard）。现代 CPU 通常提供由缓存（cache）支撑的统一地址空间（unified address space），即改进型哈佛架构（modified Harvard）。

**PC 更新**：始终计算 PC+4。分支/跳转多路选择器在 PC+4（顺序执行）与分支目标（跳转成立的分支，taken branch）或 ALU 结果（JALR）之间进行选择。

### 为什么要学习单周期数据通路？

单周期数据通路是基础：
- 每个概念（寄存器堆、ALU、多路选择器、控制信号）都会沿用到流水线设计中
- 它使指令流程变得具体——你可以追踪每一个比特
- 关键路径（critical path）分析正是引入多周期和流水线设计的直接动因

---

### 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Sections 4.1--4.4.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Sections 7.1--7.3.
3. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix C.
