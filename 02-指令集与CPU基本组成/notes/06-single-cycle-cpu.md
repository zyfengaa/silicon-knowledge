# 模块 02：指令集与 CPU 基本组成
## 06 — 完整的单周期 CPU 设计

### 概述

**单周期 CPU（single-cycle CPU）** 在每个时钟周期内恰好执行一条指令。时钟周期（clock cycle）由关键路径（critical path）决定——即穿过数据通路（datapath）的最长延迟。

### 组合数据通路与控制图

```
                              +-----------------------+
                +------------>|   Instruction Memory   |
                |             |   (32-bit address in,  |
                |             |    32-bit data out)    |
                |             +----------+------------+
                |                        |
                |                        | instruction[31:0]
                |                        v
+-----------+   |             +-----------------------+
|    PC     |---+             |   Control Unit         |
|  32-bit   |                 |   (Main Decoder)       |
+-----------+                 +----------+------------+
      |                                  |
      | PC+4                             | control signals
      v                                  v
+-----------+              +---------------------------+
|  Adder1   |              |      Register File        |
| (PC+4)    |              |   32 x 32-bit Registers   |
+-----------+              |                           |
      |                    | ReadAddr1 (rs1) -> RD1    |
      |                    | ReadAddr2 (rs2) -> RD2    |
      | +---> PC MUX       | WriteAddr (rd)            |
      | |                 | WriteData (ALU/Mem/PC+4)|
      | |                 | RegWrite (control)        |
      | |                 +----------------+----------+
      | |                                  |
      | |                    +-------------+----------+
      | |                    | RD1         | RD2      |
      | |                    v             v          |
      | |      +-----------+------+  +---------+      |
      | |      | Immediate |Sign  |  |  MUX     |     |
      | |      | Generator |Extend|  | ALUSrc   |     |
      | |      +-----------+------+  +----+----+     |
      | |           |         |            |          |
      | |           v         v            v          |
      | |      +-----------------------------------+  |
      | |      |               ALU                 |  |
      | |      |  Input A = MUX(RD1, PC, 0)        |  |
      | |      |  Input B = MUX(RD2, Imm)          |  |
      | |      |  ALU control from funct3/funct7   |  |
      | |      |  and ALUOp from control unit      |  |
      | |      +------------------+----------------+  |
      | |                           |                  |
      | |              +------------+-----+            |
      | |              |                |              |
      | |              v                v              |
      | |     +-----------------+  +-----------+       |
      | |     |  Data Memory    |  |    |            |
      | |     |  MemRead        |  |    |            |
      | |     |  MemWrite       |  |    |            |
      | |     |  Address = ALU  |  |    |            |
      | |     |  ReadData ->    |  |    |            |
      | |     +--------+--------+  |    |            |
      | |              |           |    |            |
      | |              v           v    |            |
      | |          +--------+        |  |            |
      | |          | WB MUX |<-------+  |            |
      | |          | MemtoReg       |  |            |
      | |          +---+----+       |  |            |
      | |              |            |  |            |
      | +<-------------+------------+  |            |
      |                |               |            |
      +---- PCSrc MUX -+- Branch MUX --+            |
                       |               |            |
                       v               v            v
                   (next PC)      (branch addr) (zero flag)
```

### 逐组件说明

#### 1. 程序计数器（Program Counter，PC）
- 保存当前指令地址的 32 位寄存器
- 在时钟上升沿更新
- 下一 PC = PC+4（顺序执行）或分支/跳转目标

#### 2. 指令存储器（Instruction Memory）
- 只读（在本模型中如此；真实系统使用独立的指令缓存（I-cache））
- 地址 = PC（字对齐）
- 输出 = 32 位指令

#### 3. 寄存器堆（Register File）
- 32 个寄存器，x0 硬连线为 0
- 两个异步读端口（RD1、RD2）
- 一个同步写端口（当 RegWrite=1 时在时钟沿写入）
- 写操作在同一个周期的 WB 阶段进行

#### 4. 立即数生成器（Immediate Generator）
- 根据指令格式解码指令中的立即数字段：
  - R-type：无需立即数
  - I-type：对位 [31:20] 进行符号扩展
  - S-type：对位 [31:25] 和 [11:7] 进行符号扩展
  - B-type：对位 [31]、[7]、[30:25]、[11:8] 进行符号扩展
  - U-type：将 [31:12] 左移 12 位
  - J-type：对位 [31]、[19:12]、[20]、[30:21] 进行符号扩展

#### 5. 算术逻辑单元（ALU）
- 执行 ADD、SUB、AND、OR、XOR、SLT、SLTU、SLL、SRL、SRA
- 产生 `Zero`、`Less`（有符号）和 `LessU`（无符号）标志，用于分支比较
- ALU 控制信号由 ALUOp（来自主控制器）、funct3 和 funct7 推导得到

#### 6. 数据存储器（Data Memory）
- 仅由 LW（读）和 SW（写）使用
- 地址 = ALU 结果
- 读出的数据通过 MemtoReg 多路选择器（MUX）送入寄存器堆
- 写数据 = RD2（来自寄存器堆）

#### 7. 控制单元（Control Unit）
- 根据操作码（opcode）生成所有控制信号（ALU 相关部分还需 funct3/funct7）
- 信号：RegWrite、ALUSrcA、ALUSrc、MemWrite、MemRead、MemtoReg、PCtoReg、Branch、Jump、ALUOp

### 关键路径分析

**关键路径（critical path）** 是系统中最长的组合逻辑延迟。它决定了最小时钟周期。

对于单周期 RISC-V CPU，关键路径通常为：

```
PC -> Instruction Memory -> Register File (read) -> ALU -> Data Memory -> MUX -> Register File (setup)
```

这包括：

| 组件                   | 典型延迟（任意单位）           |
|------------------------|--------------------------------|
| PC 寄存器输出          | 0（clock-to-Q）                |
| 指令存储器             | 200 ps                         |
| 寄存器堆读             | 100 ps                         |
| ALU                    | 200 ps                         |
| 数据存储器（LW）       | 250 ps                         |
| 多路选择器（MemtoReg） | 50 ps                          |
| 寄存器堆建立时间       | 50 ps                          |
| **总计**               | **850 ps**（最大约 1.18 GHz）  |

对于 SW 指令，路径中包含数据存储器延迟（写），但写回多路选择器和寄存器建立时间（setup time）较短。对于 R-type，数据存储器不在路径中。

**决定周期时间的关键路径是 LW 指令**，因为它使用了全部五个阶段，包括数据存储器读取和写回寄存器堆。

### 性能计算

```
Cycle time = max(critical path among all instructions)

For LW:    850 ps  (longest)
For SW:    750 ps
For R-type: 600 ps
For branch: 550 ps

Cycle time = 850 ps
Frequency  = 1 / 850 ps = ~1.18 GHz
```

**问题**：尽管大多数指令更快，但每条指令都要耗费 850 ps。这是多周期（multi-cycle）设计和流水线（pipelined）设计的关键动机。

### 数据通路位宽与控制信号布线

| 信号/组件              | 位宽  | 备注                                     |
|------------------------|-------|------------------------------------------|
| PC                     | 32    | 字对齐（低 2 位 = 0）                    |
| 指令                   | 32    | 对齐到 4 字节边界                        |
| 寄存器堆数据           | 32    | 32 位通用寄存器（GPR）                   |
| ALU 结果               | 32    |                                          |
| 数据存储器地址         | 32    | 物理地址空间                             |
| 控制信号               | ~13   | 除 ALUOp 和 ALUSrcA 外均为 1 位          |

### 假设与简化

单周期模型做出了以下简化：
1. **独立的指令存储器和数据存储器**（哈佛架构（Harvard architecture））——允许在同一周期内完成取指令和数据访问
2. **寄存器堆写入发生在周期末尾**——允许同一周期内的写后读
3. **所有存储器的建立时间（setup time）均为零**——现实中，SRAM/DRAM 存在时序约束
4. **没有转发（forwarding）或冒险检测（hazard detection）**——每条指令相互独立
5. **PC 在每个时钟沿更新**——没有停顿（stall）或冲刷（flush）

### 单周期时序图

```
         +---+   +---+   +---+   +---+   +---+
Clock    |   |   |   |   |   |   |   |   |   |
         |   |   |   |   |   |   |   |   |   |
      ---+   +---+   +---+   +---+   +---+   +---

         |<------- 1 clock cycle (850 ps) ------>|
         | IF | ID | EX | MEM | WB |            |
         |                                       |
         |<--- all 5 stages in ONE cycle ------->|

         Next clock edge: results committed,
         PC updated to PC+4
```

---

### 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Sections 4.1--4.5.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Section 7.3.
3. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix C, Sections C.1--C.3.
