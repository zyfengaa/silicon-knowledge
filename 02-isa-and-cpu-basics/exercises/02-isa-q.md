# Module 02: ISA and CPU Basics -- Exercises

## 02-isa-q.md: Questions and Problems

---

## Section 1: RISC vs CISC Comparison

### Question 1.1

Compare RISC and CISC ISAs across five dimensions. For each dimension, give a concrete example of how the design philosophy differs.

### Question 1.2

Explain why x86 processors internally decode instructions into micro-ops (micro-operations). What does this say about the boundary between ISA and microarchitecture?

### Question 1.3

For each of the following processors, state whether it uses a RISC or CISC ISA, and name one dominant market where it competes:

a) Intel Core i7
b) Apple M3
c) ESP32-C5 (RISC-V core)
d) AMD Ryzen
e) Qualcomm Snapdragon 8 Gen 3

### Question 1.4

Why does a CISC ISA typically have more addressing modes than a RISC ISA? How does this affect compiler design?

### Question 1.5

List three advantages and three disadvantages of fixed-length instruction encoding (like RISC-V's 32-bit instructions).

---

## Section 2: RISC-V Instruction Encoding

### Question 2.1

For each of the following RISC-V instructions, identify the format (R, I, S, B, U, J), and encode it as a 32-bit hexadecimal value. Show your work.

a) `add x10, x5, x6`
b) `sub x15, x10, x11`
c) `addi x7, x2, 42`
d) `lw x8, 16(x3)`
e) `sw x9, -8(x4)`
f) `beq x1, x2, 24` (branch target is 24 bytes from current PC)
g) `lui x1, 0xABCDE`
h) `jal x0, -32` (jump back 32 bytes)

### Question 2.2

Decode the following RISC-V instruction hex values. For each, give the mnemonic, register operands, and any immediate value:

a) `0x00A282B3`
b) `0x40B502B3`
c) `0xFFF28293`
d) `0x0082A023`
e) `0x00428463`
f) `0x00008067`

### Question 2.3

The B-type branch encoding splits the immediate across bit fields. Explain why the immediate is encoded in this split manner rather than as a contiguous field.

### Question 2.4

What is the range of branch offsets in RV32I? (Consider that the immediate is 12 bits for I-type, but B-type has what effective range?)

### Question 2.5

Why is register x0 hardwired to zero in RISC-V? Give three programming examples where this simplifies the ISA.

---

## Section 3: Datapath Tracing

### Question 3.1

Trace the execution of `lw x5, 8(x6)` through the single-cycle datapath. For each of the five stages (IF, ID, EX, MEM, WB), answer:

a) What are the values of the key control signals (RegWrite, ALUSrc, MemWrite, MemRead, MemtoReg)?
b) What is the ALU doing in the EX stage?
c) Which component produces the value written to x5?
d) What is the ALU input B? Where does it come from?

### Question 3.2

Trace the execution of `beq x10, x11, 16` through the single-cycle datapath. Answer:

a) What does the ALU compute in the EX stage?
b) What is the zero flag value if x10 == x11? If x10 != x11?
c) How does the PCSrc signal get generated?
d) What is the next PC value in each case (branch taken vs. not taken)?

### Question 3.3

In a single-cycle CPU, can the register file be written and read in the same cycle? Explain the timing of register writes and reads, and what happens if an instruction reads a register that the previous instruction wrote.

### Question 3.4

Draw a simplified datapath for the R-type instruction `and x20, x5, x6`. Show the flow of data through the register file, ALU, and write-back. Identify which control signals are active.

### Question 3.5

Identify the critical path for a SW instruction. Explain why it might be shorter or longer than the critical path for an LW instruction.

---

## Section 4: Control Signal Table

### Question 4.1

Complete the following control signal truth table for the given RV32I instructions:

| Instruction | RegWrite | ALUSrc | MemWrite | MemRead | MemtoReg | Branch | Jump | ALUOp |
|-------------|----------|--------|----------|---------|----------|--------|------|-------|
| ADD x1,x2,x3|          |        |          |         |          |        |      |       |
| SUB x4,x5,x6|          |        |          |         |          |        |      |       |
| ADDI x1,x2,5|          |        |          |         |          |        |      |       |
| LW x5,0(x6) |          |        |          |         |          |        |      |       |
| SW x5,8(x6) |          |        |          |         |          |        |      |       |
| BEQ x1,x2, L|          |        |          |         |          |        |      |       |
| JAL x1, func|          |        |          |         |          |        |      |       |
| LUI x1,0x123|          |        |          |         |          |        |      |       |

### Question 4.2

The ALUOp signal is 2 bits wide, encoding three modes (00, 01, 10). Explain how the ALU decoder uses ALUOp together with funct3 and funct7 to produce the exact ALU control.

### Question 4.3

Design the logic equations (in Verilog or Boolean algebra) for the RegWrite and ALUSrc control signals. Assume you have decoded signals for each instruction class (e.g., `r_type`, `i_type`, `load`, `store`, `branch`, `jal`, `jalr`, `lui`, `auipc`).

### Question 4.4

What would happen to the execution of `add x1, x2, x3` if the ALUSrc signal were incorrectly set to 1? What value would the ALU compute?

### Question 4.5

Explain the difference between hardwired control and microprogrammed control. For a RISC-V CPU, which approach is more appropriate and why?

---

## Section 5: Multi-Cycle CPU

### Question 5.1

List the number of cycles required for each instruction type in a multi-cycle CPU: LW, SW, R-type, branch, and JAL.

### Question 5.2

Why does a multi-cycle CPU allow a faster clock than a single-cycle CPU? What is the main performance tradeoff?

### Question 5.3

Given the following instruction mix for a program:
- 22% LW, 12% SW, 42% R-type, 20% branch, 4% JAL

Calculate the average CPI for:
a) A single-cycle CPU (CPI = 1)
b) A multi-cycle CPU (using the cycle counts from Question 5.1)

If the single-cycle CPU runs at 1 GHz and the multi-cycle CPU runs at 3 GHz, which is faster?

### Question 5.4

In a multi-cycle CPU, the control unit is a finite state machine. Draw the state transition diagram for the LW instruction, showing all states and the control signals asserted in each state.

### Question 5.5

The multi-cycle CPU uses internal registers (IR, A, B, ALUOut, Data) to hold intermediate values between cycles. Explain why these registers are needed. What would happen without them?

---

## Section 6: Applied Problems

### Question 6.1

Write a RISC-V assembly function that computes the sum of the first n natural numbers (1 + 2 + ... + n) where n is passed in a0. Return the result in a0.

### Question 6.2

Translate the following C code to RISC-V assembly:

```c
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
```

### Question 6.3

A RISC-V processor has the following timing for its datapath components:
- Instruction memory: 250 ps
- Register file (read): 100 ps
- Register file (write): 80 ps
- ALU: 200 ps
- Data memory: 250 ps
- Control unit: 50 ps
- Immediate generator: 50 ps
- Multiplexers: 20 ps each
- PC register (clk-to-q): 30 ps
- Setup time: 30 ps

a) What is the minimum cycle time for a single-cycle CPU?
b) Which instruction determines this critical path?
c) If we pipelined the CPU (5 stages), what would be the approximate cycle time?
d) What speedup would pipelining provide over single-cycle for a program with no hazards?

### Question 6.4

Explain the difference between the Harvard architecture (used in the single-cycle CPU model) and the von Neumann architecture. Why does the single-cycle model assume separate instruction and data memories?

### Question 6.5

Research question: Look up the RISC-V calling convention specification. Explain:
a) Which registers are caller-saved vs. callee-saved?
b) How are function arguments passed (which registers, and what if there are more than 8)?
c) How is the return value from a function stored?

---

## Answer Guidelines

- For encoding questions (Section 2), show the binary fields before converting to hex
- For datapath questions (Section 3), identify which control signals are 0 or 1 and trace the flow
- For applied problems (Section 6), label each assembly instruction with a comment

---

## References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapters 2, 4.
2. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213.
3. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapters 6, 7.
