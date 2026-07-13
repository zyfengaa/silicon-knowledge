# Module 02: ISA and CPU Basics
## 06 -- Complete Single-Cycle CPU Design

### Overview

A **single-cycle CPU** executes every instruction in exactly one clock cycle. The clock period is determined by the critical path -- the longest delay through the datapath.

### Combined Datapath + Control Diagram

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
      | |                 | WriteData (ALU or Mem)    |
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
      | |      |  Input A = RD1                    |  |
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

### Component-by-Component Description

#### 1. Program Counter (PC)
- 32-bit register holding the current instruction address
- Updated at the rising clock edge
- Next PC = PC+4 (sequential) or branch/jump target

#### 2. Instruction Memory
- Read-only (in this model; real systems use separate I-cache)
- Address = PC (word-aligned)
- Output = 32-bit instruction

#### 3. Register File
- 32 registers, x0 hardwired to 0
- Two asynchronous read ports (RD1, RD2)
- One synchronous write port (written on clock edge if RegWrite=1)
- Write occurs during the WB stage of the same cycle

#### 4. Immediate Generator
- Decodes the instruction's immediate field based on format:
  - R-type: no immediate needed
  - I-type: sign-extend bits [31:20]
  - S-type: sign-extend bits [31:25] and [11:7]
  - B-type: sign-extend bits [31], [7], [30:25], [11:8]
  - U-type: shift left 12 bits of [31:12]
  - J-type: sign-extend bits [31], [19:12], [20], [30:21]

#### 5. ALU
- Performs ADD, SUB, AND, OR, XOR, SLT, SLL, SRL, SRA
- Generates Zero flag (output = 0) for branch comparison
- ALU control is derived from ALUOp (from main control), funct3, and funct7

#### 6. Data Memory
- Used only by LW (read) and SW (write)
- Address = ALU result
- Read data goes to register file via MemtoReg mux
- Write data = RD2 (from register file)

#### 7. Control Unit
- Generates all control signals from opcode (plus funct3/funct7 for ALU)
- Signals: RegWrite, ALUSrc, MemWrite, MemRead, MemtoReg, Branch, Jump, ALUOp

### Critical Path Analysis

The **critical path** is the longest combinational delay in the system. It determines the minimum clock period.

For a single-cycle RISC-V CPU, the critical path is typically:

```
PC -> Instruction Memory -> Register File (read) -> ALU -> Data Memory -> MUX -> Register File (setup)
```

This includes:

| Component              | Typical delay (arbitrary units) |
|------------------------|--------------------------------|
| PC register output     | 0 (clock-to-Q)                 |
| Instruction memory     | 200 ps                         |
| Register file read     | 100 ps                         |
| ALU                    | 200 ps                         |
| Data memory (LW)       | 250 ps                         |
| MUX (MemtoReg)         | 50 ps                          |
| Register file setup    | 50 ps                          |
| **Total**              | **850 ps** (~1.18 GHz max)    |

For a SW instruction, data memory latency is included (write), but the write-back MUX and register setup are shorter. For R-type, data memory is not in the path.

**The critical path for the cycle time is the LW instruction**, because it uses all five stages including data memory read and write-back to the register file.

### Performance Calculation

```
Cycle time = max(critical path among all instructions)

For LW:    850 ps  (longest)
For SW:    700 ps
For R-type: 600 ps
For branch: 550 ps

Cycle time = 850 ps
Frequency  = 1 / 850 ps = ~1.18 GHz
```

**Problem**: Even though most instructions are faster, every instruction takes 850 ps. This is the key motivation for multi-cycle and pipelined designs.

### Datapath Widths and Control Signal Routing

| Signal/Component       | Width | Notes                                    |
|------------------------|-------|------------------------------------------|
| PC                     | 32    | Word-aligned (lower 2 bits = 0)          |
| Instruction            | 32    | Aligned to 4-byte boundaries             |
| Register file data     | 32    | 32-bit GPRs                              |
| ALU result              | 32    |                                          |
| Data memory address     | 32    | Physical address space                   |
| Control signals        | ~10   | 1-bit each except ALUOp (2 bits)         |

### Assumptions and Simplifications

The single-cycle model makes these simplifications:
1. **Separate instruction and data memories** (Harvard architecture) -- avoids read-after-write conflicts
2. **Register file writes happen at the end of the cycle** -- allows same-cycle read-after-write
3. **All memories have zero setup time** -- in reality, SRAM/DRAM have timing constraints
4. **No forwarding or hazard detection** -- each instruction is independent
5. **PC is updated on every clock edge** -- no stalls or flushes

### Single-Cycle Timing Diagram

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

### References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Sections 4.1--4.5.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Section 7.5.
3. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix C, Sections C.1--C.3.
