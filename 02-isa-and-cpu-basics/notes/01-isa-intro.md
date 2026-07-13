# Module 02: ISA and CPU Basics
## 01 -- Introduction to Instruction Set Architecture (ISA)

### What is an ISA?

An **Instruction Set Architecture (ISA)** is the abstract interface between a computer's software and its hardware. It defines:

- The **instructions** the processor can execute
- The **registers** visible to software
- The **memory model** (address space, alignment, endianness)
- The **addressing modes** available
- The **data types** supported

The ISA is the contract: any program compiled to a given ISA will run on any processor implementing that ISA, regardless of the microarchitecture. This separation of ISA from microarchitecture is one of the most important concepts in computer architecture.

> **Key Insight:** The ISA is what the programmer/compiler sees. The microarchitecture is how the hardware implements it. The same ISA (e.g., x86) can have vastly different microarchitectures (Intel Core vs. Atom vs. Pentium).

### The Hardware-Software Interface

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

The ISA acts as the boundary: above it, software is portable; below it, hardware can be optimized freely.

### RISC vs. CISC Philosophy

The two dominant ISA design philosophies emerged in the 1980s. Their tradeoffs remain central to architecture today.

| Feature              | RISC (Reduced Instruction Set Computer) | CISC (Complex Instruction Set Computer) |
|----------------------|----------------------------------------|----------------------------------------|
| Instruction length   | Fixed (typically 32-bit)               | Variable (1--15 bytes)                 |
| Instruction count    | Small (~50--100)                       | Large (~300--1000+)                    |
| Addressing modes     | Few (typically 1--3)                   | Many (10+)                             |
| Memory operands      | Load/store only                        | Many instructions can access memory    |
| Registers            | Many general-purpose registers         | Fewer, some special-purpose            |
| Control unit         | Simple, often hardwired                | Complex, often microprogrammed         |
| Pipelining           | Easier due to uniformity               | Harder due to variable length          |

#### x86 / x86-64 (CISC)

Intel's 8086 (1978) established the x86 ISA, which evolved through 32-bit (IA-32) and 64-bit (x86-64 / AMD64) extensions. Despite its CISC origins, modern x86 processors decode instructions into micro-ops (RISC-like internal operations).

- **Dominant in** desktops, laptops, servers
- **Vendors:** Intel, AMD
- **Key trait:** Backward compatibility stretching back decades
- **Reference:** Intel 64 and IA-32 Architectures Software Developer's Manual

#### ARM (RISC)

The ARM ISA began as Acorn RISC Machine (1985). It has evolved from ARMv1 through ARMv9, adding Thumb (16-bit instructions), NEON (SIMD), and 64-bit (AArch64).

- **Dominant in** mobile phones, embedded systems, IoT, and increasingly laptops/servers
- **Vendors:** Arm Ltd. (licenses to Apple, Qualcomm, Samsung, NVIDIA, Amazon, etc.)
- **Key trait:** Energy-efficient design
- **Reference:** ARM Architecture Reference Manual

#### RISC-V (RISC)

RISC-V is a free, open ISA developed at UC Berkeley (2010). It is modular: a small mandatory base integer ISA (RV32I/RV64I) plus optional standard extensions.

- **Dominant in** research, education, growing commercial adoption
- **Key trait:** Open standard, no licensing fees, clean design
- **Reference:** RISC-V ISA Manual, Volume I

### Instruction Formats

Instructions are encoded as binary words. The format determines how the bits are partitioned into fields (opcode, operands, etc.).

| Field     | Purpose                                    |
|-----------|--------------------------------------------|
| opcode    | Identifies the instruction type            |
| rd        | Destination register                       |
| rs1, rs2  | Source registers                           |
| funct3/funct7 | Further specify the operation          |
| immediate | Constant value (encoded in the instruction) |

Different ISA families use different formats. RISC-V uses six uniform formats (covered in detail in section 03).

### Addressing Modes

Addressing modes specify how to compute the memory address of an operand.

| Mode                  | Effective Address      | Example (RISC-V)  |
|-----------------------|------------------------|--------------------|
| Register              | `R[rs1]`               | `add x1, x2, x3`  |
| Immediate             | value encoded          | `addi x1, x2, 5`  |
| Base+Offset           | `R[rs1] + imm`         | `lw x1, 8(x2)`    |
| PC-relative           | `PC + imm`             | `beq x1, x2, off` |
| Register indirect     | `M[R[rs1]]`            | `jalr x1, 0(x2)`  |

RISC-V deliberately keeps addressing modes simple, using only register, immediate, and base+offset for memory operations.

### Key Concepts Summary

- **ISA** = contract between software and hardware
- **RISC** = simple, fixed-length instructions, load/store architecture
- **CISC** = complex, variable-length instructions, memory operands
- x86 dominates servers/PCs; ARM dominates mobile; RISC-V is the open rising star
- Instruction format = how bits encode operations and operands
- Addressing mode = how to compute a memory address

### Real-World Impact

Choosing an ISA affects the entire ecosystem: compiler toolchains, operating system support, runtime libraries, and hardware design costs. The RISC-V revolution is significant because it decouples ISA innovation from corporate ownership, much like Linux did for operating systems.

---

### References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapters 1--2.
2. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann. Appendix A.
3. Patterson, D. A. "Reduced Instruction Set Computers." *Communications of the ACM*, Vol. 28 No. 1, 1985.
4. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213.
5. Intel Corporation. *Intel 64 and IA-32 Architectures Software Developer's Manual*. Volume 1.
6. Arm Limited. *Arm Architecture Reference Manual for A-profile architecture*.
