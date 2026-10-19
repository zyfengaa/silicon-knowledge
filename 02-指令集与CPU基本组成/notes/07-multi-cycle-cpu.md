# 模块 02：指令集与 CPU 基本组成
## 07 — 多周期 CPU 设计

### 动机

单周期（single-cycle）CPU 的时钟周期必须满足最慢指令（LW）的需求。大多数指令并不会完整使用全部五个阶段。多周期（multi-cycle）CPU 将每条指令拆分为多个更短的步骤，每个步骤占用一个时钟周期。这样做可以带来：

1. **更快的时钟** —— 每个周期只需足够完成一个步骤
2. **资源复用** —— 一个 ALU、一个存储器可以跨步骤重复使用
3. **可变的指令延迟** —— 简单指令能更快完成

### 基本概念

不是让全部五个阶段在一个长周期内完成，CPU 使用有限状态机（finite state machine, FSM）来编排这些步骤：

```
Single-cycle:       [ IF | ID | EX | MEM | WB ]    <-- 1 long cycle

Multi-cycle:       [ IF ] [ ID ] [ EX ] [ MEM ] [ WB ]  <-- 1-5 short cycles
                    cyc1   cyc2   cyc3   cyc4   cyc5
```

对于至少一种指令类型，周期数与单周期中的阶段数相同。但每个单独的周期都更短。

**重要细节**：IF 状态已经执行了 `PC = PC + 4`。因此，当后续状态计算 PC 相对目标地址时，原始指令地址已不在 PC 中。数据通路（datapath）在 IF 期间将自增前的值保存到临时寄存器（`PC_old`）中，后续状态计算 `PC_old + Imm`。一种等价的实现是给 ALU 的 A 输入多路选择器增加一个 `PC - 4` 选择项。

### 按周期拆解指令

#### LW（加载字，Load Word）—— 5 个周期

| 周期 | 状态 | 操作 |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = 符号扩展（sign-extend）(imm) |
| 3     | EX    | ALUOut = A + Imm（计算地址） |
| 4     | MEM   | Data = Mem[ALUOut]（从存储器读取） |
| 5     | WB    | Reg[rd] = Data（写入寄存器） |

#### SW（存储字，Store Word）—— 4 个周期

| 周期 | 状态 | 操作 |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = 符号扩展(imm) |
| 3     | EX    | ALUOut = A + Imm（计算地址） |
| 4     | MEM   | Mem[ALUOut] = B（写入存储器） |

#### R 型指令（例如 ADD）—— 4 个周期

| 周期 | 状态 | 操作 |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = 符号扩展(imm) |
| 3     | EX    | ALUOut = A op B（计算结果） |
| 4     | WB    | Reg[rd] = ALUOut（写入结果） |

#### 分支指令（BEQ）—— 3 个周期

| 周期 | 状态 | 操作 |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = 符号扩展(imm) |
| 3     | EX    | ALUOut = PC_old + Imm（分支目标地址）；若 A == B，则 PC = ALUOut |

#### JAL —— 3 个周期

| 周期 | 状态 | 操作 |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; Imm = 符号扩展(imm) |
| 3     | EX    | ALUOut = PC_old + Imm；Reg[ra] = PC（已经更新过的 PC+4）；PC = ALUOut |

### 多周期控制的状态机

多周期 CPU 不使用产生静态控制信号的硬连线译码器（hardwired decoder），而是使用状态机：

```
                           +------+
                           |  IF  |<----------+
                           +------+           |
                              |               |
                              v               |
                           +------+           |
                     +---->|  ID  |--+        |
                     |     +------+  |        |
                     |        |      |        |
                     |        v      |        |
                     |     +------+  |        |
                     |     |  EX  |  |        |
                     |     +------+  |        |
                     |        |      |        |
                     |    +---+---+  |        |
                     |    |       |  |        |
                     v    v       v  |        |
                  +------+  +------+ |        |
                  | MEM  |  |  WB  | |        |
                  +------+  +------+ |        |
                     |          |    |        |
                     +-----+----+    |        |
                           |         |        |
                           v         v        |
                        +------+  +------+    |
                        | LW 5 |  |next  |----+
                        | done |  |inst  |
                        +------+  +------+
```

每个状态都置位该步骤相应的控制信号。

### 多周期数据通路

多周期数据通路在各阶段之间增加寄存器，用于保存中间结果：

| 寄存器 | 保存的内容                       |
|----------|------------------------------|
| IR       | 指令寄存器（来自 IF） |
| A, B     | 寄存器堆读出的结果（来自 ID） |
| Imm      | 符号扩展后的立即数（来自 ID） |
| ALUOut   | ALU 运算结果（来自 EX）          |
| Data     | 数据存储器输出（来自 MEM）  |
| PC       | 程序计数器                |
| PC_old   | IF 期间保存的自增前 PC（用于 PC 相对目标地址） |

这些寄存器实现了资源复用：ALU 可以在一个周期中用于 PC+4，在下一个周期中用于地址计算。

### 多周期 CPU 的控制信号

每个状态置位一组特定的控制信号：

| 状态 | 控制信号                                                         |
|-------|-------------------------------------------------------------------------|
| IF    | IorD = 0（PC 送往存储器）；IRWrite = 1；PCWrite = 1；PC_old = PC（自增前保存）；ALUSrcA = 0（PC），ALUSrcB = 01（4）；ALUOp = 00（ADD） |
| ID    | A = Reg[rs1]；B = Reg[rs2]；Imm = 符号扩展(imm) —— 为下一状态锁存操作数 |
| EX_BR | ALUSrcA = 0（PC_old）；ALUSrcB = 10（imm）；ALUOp = 00（ADD）—— 目标地址 = PC_old + Imm；比较器检查 A 与 B |
| EX_JAL| ALUSrcA = 0（PC_old）；ALUSrcB = 10（imm）；ALUOp = 00（ADD）—— 目标地址 = PC_old + Imm；Reg[ra] = PC（已是 PC_old + 4） |
| EX_R  | ALUSrcA = 1（A）；ALUSrcB = 00（B）；ALUOp = 10（根据 funct 译码） |
| EX_LW | ALUSrcA = 1（A）；ALUSrcB = 10（imm）；ALUOp = 00（ADD） |
| EX_SW | ALUSrcA = 1（A）；ALUSrcB = 10（imm）；ALUOp = 00（ADD） |
| MEM_LW| IorD = 1（ALUOut 送往存储器）；MemRead = 1                    |
| MEM_SW| IorD = 1（ALUOut 送往存储器）；MemWrite = 1                   |
| WB_R  | RegWrite = 1；MemtoReg = 0（ALUOut）                          |
| WB_LW | RegWrite = 1；MemtoReg = 1（Data）                            |

### 状态机伪代码

```
// State transition logic
case (current_state)
    IF: next_state = ID
    
    ID: next_state = EX (all instructions)
    
    EX:
        case (opcode)
            LW:  next_state = MEM_LW
            SW:  next_state = MEM_SW
            R-type: next_state = WB_R
            BEQ/BNE: next_state = IF (branch taken) or IF (not taken)
            JAL: next_state = IF
        endcase
    
    MEM_LW: next_state = WB_LW
    MEM_SW: next_state = IF
    WB_R:   next_state = IF
    WB_LW:  next_state = IF
endcase
```

### 多周期与单周期对比

| 方面                  | 单周期            | 多周期                  |
|-------------------------|-------------------------|------------------------------|
| 每条指令的周期数  | 1                       | 3--5                         |
| 周期时间              | 长（850 ps）           | 短（约 300 ps）              |
| 时钟频率         | 约 1.18 GHz               | 约 3.33 GHz                    |
| 平均每条指令周期数（CPI）           | 1.0                     | 约 4.0（典型指令混合）       |
| 每条指令耗时    | 850 ps                  | 1200 ps（4 x 300 ps）         |
| 控制复杂度      | 简单组合逻辑    | 有限状态机         |
| 资源共享    | 无（专用单元）  | 共享（1 个 ALU、1 个存储器）     |
| 硬件成本             | 更多 ALU、更多多路选择器   | 更少 ALU、更多寄存器   |
| 实现          | 易于理解      | 基于 FSM，更复杂      |

**性能对比**：对于指令混合比例为 20% LW、10% SW、40% R 型、25% 分支、5% JAL 的程序：

```
Single-cycle: Total time = N * 1 * 850 ps = N * 850 ps
Multi-cycle:  Total time = N * CPI_avg * 300 ps
              CPI_avg = 0.20*5 + 0.10*4 + 0.40*4 + 0.25*3 + 0.05*3
                      = 1.0 + 0.4 + 1.6 + 0.75 + 0.15
                      = 3.90
              Total time = N * 3.90 * 300 ps = N * 1170 ps

Multi-cycle is ~38% slower in this example!
```

等等——多周期反而更慢？多周期的主要动机是硬件成本，而不是性能。真正的性能飞跃来自**流水线（pipelining）**（模块 03），它让多条指令的执行相互重叠。

### 为什么要学习多周期？

1. **概念桥梁**：连接单周期设计与流水线设计
2. **资源共享**是所有真实处理器中的关键思想
3. **有限状态机控制**出现在许多硬件系统中
4. **理解这种权衡**能加深对流水线必要性的认识

### 小结

- 多周期 CPU 将指令拆分为 3--5 个更短的周期
- 每个周期只使用该步骤所需的资源
- 控制单元是有限状态机，而不是组合逻辑
- 周期时间更短，但 CPI 更高
- 历史上主要收益是更低的硬件成本
- 性能提升需要流水线

---

### 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Section 4.6.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Section 7.4.
3. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix C, Sections C.4--C.5.
4. Patterson, D. A., & Séquin, C. H. "RISC I: A Reduced Instruction Set VLSI Computer." *Proceedings of the 8th Annual Symposium on Computer Architecture (ISCA)*, 1981. (Patterson's 1985 *Communications of the ACM* article "Reduced Instruction Set Computers" is a later survey, not the original RISC-I paper.)
