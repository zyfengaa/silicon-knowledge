# Module 02: ISA and CPU Basics
## 02 -- Introduction to RISC-V

### Why RISC-V for Learning?

RISC-V is an ideal ISA for learning computer architecture for several reasons:

1. **Open and Free**: Unlike ARM (proprietary) and x86 (proprietary), RISC-V is an open standard with no licensing fees. Anyone can design, implement, and sell RISC-V processors without paying royalties.

2. **Modular Design**: RISC-V is designed as a small base integer ISA plus optional extensions. This allows minimal implementations (e.g., for embedded systems) and rich implementations (e.g., for application processors) to share the same ISA.

3. **Clean and Minimal**: RISC-V strips away decades of legacy baggage found in x86 and ARM. The base integer ISA (RV32I) contains only about 50 instructions that fit in six simple formats.

4. **Academic Foundation**: Created at UC Berkeley by Krste Asanovic, Andrew Waterman, and David Patterson (co-author of the definitive computer architecture textbooks), RISC-V was designed for education from the start.

5. **Industry Adoption**: RISC-V is no longer just academic. Companies like SiFive, Esperanto, and Microchip produce RISC-V silicon. Google, NVIDIA, and Qualcomm are investing heavily.

### RISC-V Design Principles

RISC-V follows a clean RISC philosophy:

| Principle                  | How RISC-V Implements It                                       |
|----------------------------|----------------------------------------------------------------|
| Fixed instruction length   | 32-bit instructions (RV32I/RV64I); 16-bit compressed extension (RVC) |
| Load/store architecture    | Only `lw`/`sw` (and variants) access memory                   |
| Few addressing modes       | Register, immediate, base+offset                               |
| Large register file        | 32 x registers (x0--x31), with x0 hardwired to zero           |
| Simple instruction formats | Six uniform formats (R, I, S, B, U, J)                        |
| No condition codes         | Branches compare registers directly (like MIPS, unlike ARM32) |

### The RISC-V Base Integer ISA: RV32I

RV32I is the mandatory base for 32-bit RISC-V. Every RISC-V implementation must include RV32I (or RV64I for 64-bit).

Key characteristics:

- **32-bit address space** (2^32 bytes = 4 GiB)
- **32 registers** (x0--x31), each 32 bits wide
- **x0** is hardwired to the constant 0
- **PC** (program counter) is a separate register, not part of the register file
- **Little-endian** byte ordering
- **Instructions are 32 bits** (4 bytes), aligned to 4-byte boundaries

#### Register Set

| Register | ABI Name | Description                     | Saver     |
|----------|----------|---------------------------------|-----------|
| x0       | zero     | Hardwired zero                  | --        |
| x1       | ra       | Return address                  | Caller    |
| x2       | sp       | Stack pointer                   | Callee    |
| x3       | gp       | Global pointer                  | --        |
| x4       | tp       | Thread pointer                  | --        |
| x5       | t0       | Temporary / alternate link      | Caller    |
| x6--x7   | t1--t2   | Temporaries                     | Caller    |
| x8       | s0/fp    | Saved / frame pointer           | Callee    |
| x9       | s1       | Saved register                  | Callee    |
| x10--x11 | a0--a1   | Function args / return values   | Caller    |
| x12--x17 | a2--a7   | Function arguments              | Caller    |
| x18--x27 | s2--s11  | Saved registers                 | Callee    |
| x28--x31 | t3--t6   | Temporaries                     | Caller    |

The ABI (Application Binary Interface) names are conventions; hardware sees only x0--x31.

### RISC-V Extensions

The modular design allows implementations to choose which extensions to include:

| Extension | Name                        | Description                                      |
|-----------|-----------------------------|--------------------------------------------------|
| M         | Integer Multiply/Divide     | Hardware multiply and divide                     |
| A         | Atomic                      | Atomic memory operations (LR/SC, AMO)            |
| F         | Single-Precision Float      | 32-bit floating-point (IEEE 754)                 |
| D         | Double-Precision Float      | 64-bit floating-point                            |
| C         | Compressed                  | 16-bit instructions for code density             |
| Zicsr     | CSR Instructions            | Control and status register access               |
| Zifencei  | Fence.I                     | Instruction stream synchronization               |
| V         | Vector                      | 128+ bit vector/SIMD operations                  |

The combination **RV32IMAFDZicsr_Zifencei** is called **RV32G** (General-purpose). Most application processors implement RV64G.

### Comparison: RV32I vs ARM vs x86

| Aspect            | RV32I (RISC-V)    | ARMv8-A (AArch32) | x86-64 (IA-32e)    |
|-------------------|-------------------|-------------------|--------------------|
| Instruction count | ~50               | ~200+             | ~1000+             |
| Fixed length      | Yes (32-bit)      | Yes (32-bit)      | No (1--15 bytes)   |
| Registers         | 31 + x0=0         | 15 + PC           | 16 (8 GPR + stack) |
| Condition codes   | No                | Yes (NZCV)        | Yes (RFLAGS)       |
| Addressing modes  | 3                 | ~9                | ~10+               |
| License fee       | None (open)       | Yes               | Yes (cross-license)|

### Getting Started with RISC-V Toolchains

To experiment with RISC-V assembly:

```bash
# Install the GNU RISC-V toolchain (Ubuntu/Debian)
sudo apt install gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu

# Compile a C program
riscv64-linux-gnu-gcc -march=rv32im -mabi=ilp32 -o prog prog.c

# Disassemble to see instructions
riscv64-linux-gnu-objdump -d prog

# Or use the spike simulator
sudo apt install spike pk
```

Alternatively, the online [RISC-V Interpreter](https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/) is excellent for learning.

---

### References

1. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213. Available at: https://riscv.org/technical/specifications/
2. Waterman, A. "Design of the RISC-V Instruction Set Architecture." PhD Dissertation, UC Berkeley, 2016.
3. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 2.
4. Asanovic, K., & Patterson, D. A. "Instruction Sets Should Be Free: The Case for RISC-V." *IEEE Micro*, 2014.
5. SiFive Inc. *RISC-V Core IP Documentation*. https://www.sifive.com/risc-v-core-ip
