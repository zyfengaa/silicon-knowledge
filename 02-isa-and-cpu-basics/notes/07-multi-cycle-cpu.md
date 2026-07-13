# Module 02: ISA and CPU Basics
## 07 -- Multi-Cycle CPU Design

### Motivation

A single-cycle CPU's clock period must accommodate the slowest instruction (LW). Most instructions do not use all five stages to their full extent. A multi-cycle CPU breaks each instruction into multiple shorter steps, each taking one clock cycle. This allows:

1. **Faster clock** -- each cycle is just long enough for one step
2. **Resource sharing** -- one ALU, one memory can be reused across steps
3. **Variable instruction latency** -- simple instructions finish faster

### Basic Concept

Instead of all five stages happening in one long cycle, the CPU uses a finite state machine to sequence the steps:

```
Single-cycle:       [ IF | ID | EX | MEM | WB ]    <-- 1 long cycle

Multi-cycle:       [ IF ] [ ID ] [ EX ] [ MEM ] [ WB ]  <-- 1-5 short cycles
                    cyc1   cyc2   cyc3   cyc4   cyc5
```

For at least one instruction type the number of cycles matches the single-cycle stages. But each individual cycle is shorter.

### Instruction Breakdown by Cycles

#### LW (Load Word) -- 5 cycles

| Cycle | State | Operation |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = sign-extend(imm) |
| 3     | EX    | ALUOut = A + Imm (compute address) |
| 4     | MEM   | Data = Mem[ALUOut] (read from memory) |
| 5     | WB    | Reg[rd] = Data (write to register) |

#### SW (Store Word) -- 4 cycles

| Cycle | State | Operation |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = sign-extend(imm) |
| 3     | EX    | ALUOut = A + Imm (compute address) |
| 4     | MEM   | Mem[ALUOut] = B (write to memory) |

#### R-type (e.g., ADD) -- 4 cycles

| Cycle | State | Operation |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = sign-extend(imm) |
| 3     | EX    | ALUOut = A op B (compute result) |
| 4     | WB    | Reg[rd] = ALUOut (write result) |

#### Branch (BEQ) -- 3 cycles

| Cycle | State | Operation |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; B = Reg[rs2]; Imm = sign-extend(imm) |
| 3     | EX    | ALUOut = PC + Imm (branch target); if A == B, PC = ALUOut |

#### JAL -- 3 cycles

| Cycle | State | Operation |
|-------|-------|-----------|
| 1     | IF    | IR = Mem[PC]; PC = PC + 4 |
| 2     | ID    | A = Reg[rs1]; Imm = sign-extend(imm) |
| 3     | EX    | ALUOut = PC + Imm; Reg[ra] = PC; PC = ALUOut |

### State Machine for Multi-Cycle Control

Instead of a hardwired decoder that produces static control signals, a multi-cycle CPU uses a state machine:

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

Each state asserts the appropriate control signals for that step.

### Multi-Cycle Datapath

The multi-cycle datapath adds registers between stages to hold intermediate results:

| Register | Holds                       |
|----------|------------------------------|
| IR       | Instruction Register (from IF) |
| A, B     | Register file read outputs (from ID) |
| Imm      | Sign-extended immediate (from ID) |
| ALUOut   | ALU result (from EX)          |
| Data     | Data memory output (from MEM)  |
| PC       | Program counter                |

These registers allow resource sharing: the ALU can be used for PC+4 in one cycle and for address calculation in the next.

### Control Signals for Multi-Cycle CPU

Each state asserts a specific set of control signals:

| State | Control Signals                                                         |
|-------|-------------------------------------------------------------------------|
| IF    | IorD = 0 (PC to memory); IRWrite = 1; PCWrite = 1; ALUSrcA = 0 (PC), ALUSrcB = 01 (4); ALUOp = 00 (ADD) |
| ID    | ALUSrcA = 0 (PC); ALUSrcB = 11 (imm); ALUOp = 00 (ADD) -- computes branch target |
| EX_R  | ALUSrcA = 1 (A); ALUSrcB = 00 (B); ALUOp = 10 (decode from funct) |
| EX_LW | ALUSrcA = 1 (A); ALUSrcB = 10 (imm); ALUOp = 00 (ADD) |
| EX_SW | ALUSrcA = 1 (A); ALUSrcB = 10 (imm); ALUOp = 00 (ADD) |
| MEM_LW| IorD = 1 (ALUOut to memory); MemRead = 1                    |
| MEM_SW| IorD = 1 (ALUOut to memory); MemWrite = 1                   |
| WB_R  | RegWrite = 1; MemtoReg = 0 (ALUOut)                          |
| WB_LW | RegWrite = 1; MemtoReg = 1 (Data)                            |

### State Machine Pseudocode

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

### Multi-Cycle vs. Single-Cycle Comparison

| Aspect                  | Single-Cycle            | Multi-Cycle                  |
|-------------------------|-------------------------|------------------------------|
| Cycles per instruction  | 1                       | 3--5                         |
| Cycle time              | Long (850 ps)           | Short (~300 ps)              |
| Clock frequency         | ~1.18 GHz               | ~3.33 GHz                    |
| CPI (average)           | 1.0                     | ~4.0 (for typical mix)       |
| Time per instruction    | 850 ps                  | 1200 ps (4 x 300 ps)         |
| Control complexity      | Simple combinational    | Finite state machine         |
| Resource sharing        | None (dedicated units)  | Shared (1 ALU, 1 memory)     |
| Hardware cost             | More ALUs, more muxes   | Fewer ALUs, more registers   |
| Implementation          | Easy to understand      | FSM-based, more complex      |

**Performance comparison** for a program with instruction mix: 20% LW, 10% SW, 40% R-type, 25% branch, 5% JAL:

```
Single-cycle: Total time = N * 1 * 850 ps = N * 850 ps
Multi-cycle:  Total time = N * CPI_avg * 300 ps
              CPI_avg = 0.20*5 + 0.10*4 + 0.40*4 + 0.25*3 + 0.05*3
                      = 1.0 + 0.4 + 1.6 + 0.75 + 0.15
                      = 3.90
              Total time = N * 3.90 * 300 ps = N * 1170 ps

Multi-cycle is ~38% slower in this example!
```

Wait -- multi-cycle is slower? Multi-cycle was primarily motivated by hardware cost, not performance. The real performance leap comes with **pipelining** (Module 03), which overlaps the execution of multiple instructions.

### Why Study Multi-Cycle?

1. **Conceptual bridge** between single-cycle and pipelined designs
2. **Resource sharing** is a key idea in all real processors
3. **Finite state machine control** appears in many hardware systems
4. **Understanding the tradeoff** reinforces why pipelining is needed

### Summary

- Multi-cycle CPUs break instructions into 3--5 shorter cycles
- Each cycle uses only the resources needed for that step
- The control unit is a finite state machine, not combinational logic
- Cycle time is shorter but CPI is higher
- The main benefit historically was lower hardware cost
- Performance improvements require pipelining

---

### References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Section 4.6.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Section 7.6.
3. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix C, Sections C.4--C.5.
4. Patterson, D. A. "Reduced Instruction Set Computers." *Communications of the ACM*, Vol. 28 No. 1, 1985 -- original RISC-I paper that motivated the multi-cycle approach for cost reduction.
