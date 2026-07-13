# Module 02: ISA and CPU Basics
## 04 -- CPU Datapath for a Single-Cycle Implementation

### Overview

The **datapath** is the collection of functional units that perform data processing operations. Together with the **control unit** (which directs the datapath), it forms the core of a CPU.

In a **single-cycle implementation**, every instruction executes in exactly one clock cycle. The clock period must be long enough to accommodate the slowest instruction.

### Basic Datapath Components

| Component        | Function                                                      |
|------------------|--------------------------------------------------------------|
| Program Counter  | Holds address of current instruction                         |
| Instruction Memory | Stores program; reads at PC address                        |
| Register File    | 32 x 32-bit registers (x0--x31); 2 read ports, 1 write port |
| ALU              | Performs arithmetic/logical operations                       |
| Data Memory      | Stores data; addressed by ALU result for loads/stores        |
| Adders           | PC+4 increment; branch target computation                    |
| Multiplexers     | Select between data sources (controlled by control signals)  |

### The Five Stages of Instruction Execution

Every instruction goes through up to five stages:

1. **IF (Instruction Fetch)**: Fetch instruction from memory at PC
2. **ID (Instruction Decode)**: Decode instruction, read registers
3. **EX (Execute)**: Perform ALU operation or address calculation
4. **MEM (Memory Access)**: Read/write data memory (load/store only)
5. **WB (Write Back)**: Write result to register file

For a single-cycle CPU, all five stages complete within one clock cycle.

### Step-by-Step: How `add x1, x2, x3` Flows Through the Datapath

Let us trace the execution of `add x1, x2, x3` (encoding: `0x002100B3`).

#### Stage 1: Instruction Fetch (IF)

```
+----------+
|   PC     |---> Address to Instruction Memory
| (0x100)  |
+----------+

+---------------------+
| Instruction Memory  |
| Address 0x100:      |
| 0x002100B3 (add)    |
+---------------------+

Result: 32-bit instruction word = 0x002100B3 is read from memory
PC is also sent to the adder for PC+4 calculation
```

**Hardware**: The PC register drives the address input of instruction memory. The instruction word appears on the output data lines. Concurrently, an adder computes PC + 4 (the next instruction address).

#### Stage 2: Instruction Decode (ID)

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

**Hardware**: The instruction word's rs1 and rs2 fields drive the register file's read address ports. The register file outputs the contents of x2 and x3.

#### Stage 3: Execute (EX)

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

**Hardware**: The two register values feed into the ALU. The ALU control logic decodes funct3, funct7, and opcode to select ADD. The ALU computes the sum.

#### Stage 4: Memory Access (MEM)

```
For add instruction: no memory access needed.
ALU result passes through unmodified.

(LW/SW would access data memory here.)
```

**Hardware**: For R-type instructions, the MEM stage is a pass-through. The ALU result is simply forwarded.

#### Stage 5: Write Back (WB)

```
Register File write:
- Write address = rd = x1
- Write data = ALU result = x2 + x3
- RegWrite signal = 1 (enabled for R-type)

Result: x1 is updated with the sum of x2 and x3
```

**Hardware**: The ALU result is routed to the register file's write data input. The rd field drives the write address. RegWrite control signal is asserted, causing the register file to store the result.

### ASCII Datapath Diagram

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

### Datapath Design Decisions

**Register File Ports**: Two read ports (rs1, rs2) and one write port (rd) allow simultaneous register reads in the ID stage and writes in the WB stage.

**Instruction vs. Data Memory**: Harvard architecture (separate memories) avoids a structural hazard in single-cycle design. Modern CPUs unify them with caches (modified Harvard).

**PC Update**: PC+4 is always computed. The branch/jump multiplexer selects between PC+4 (sequential) and the branch target (taken branch) or ALU result (JALR).

### Why Study the Single-Cycle Datapath?

The single-cycle datapath is the foundation:
- Every concept (register file, ALU, muxes, control signals) carries forward to pipelined designs
- It makes the instruction flow concrete -- you can trace every bit
- The critical path analysis directly motivates multi-cycle and pipelined designs

---

### References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Sections 4.1--4.4.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Sections 7.1--7.3.
3. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix C.
