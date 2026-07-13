# Module 02: ISA and CPU Basics
## 03 -- RV32I Instruction Formats and Common Instructions

### Overview of RV32I Formats

All RV32I instructions are exactly 32 bits long and aligned to 4-byte boundaries. The opcode occupies bits [6:0] and determines the instruction format. There are six core formats:

```
R-type:   | funct7[31:25] | rs2[24:20] | rs1[19:15] | funct3[14:12] | rd[11:7] | opcode[6:0] |
I-type:   | imm[31:20]              | rs1[19:15] | funct3[14:12] | rd[11:7] | opcode[6:0] |
S-type:   | imm[11:5][31:25]| rs2[24:20]| rs1[19:15]| funct3[14:12]| imm[4:0][11:7]| opcode|
B-type:   | [12|10:5][31:25]| rs2[24:20]| rs1[19:15]| funct3[14:12]| [4:1|11][11:7]| opcode|
U-type:   | imm[31:12]                                        | rd[11:7] | opcode[6:0] |
J-type:   | imm[20|10:1|11|19:12]                            | rd[11:7] | opcode[6:0] |
```

### Detailed Field Descriptions

| Field      | Bits        | Purpose                                                    |
|------------|-------------|------------------------------------------------------------|
| opcode     | [6:0]       | Primary operation code; identifies instruction class       |
| rd         | [11:7]      | Destination register (written by operation)                |
| funct3     | [14:12]     | 3-bit opcode modifier                                      |
| rs1        | [19:15]     | First source register operand                              |
| rs2        | [24:20]     | Second source register operand                             |
| funct7     | [31:25]     | 7-bit opcode modifier (R-type)                             |
| imm        | varies      | Immediate value, sign-extended to 32 bits                  |

### Format-by-Format Breakdown

#### R-type (Register)

Used for arithmetic/logical operations on two register operands.

```
31          25|24   20|19   15|14      12|11     7|6       0
+------------+--------+--------+----------+--------+---------+
|  funct7    |  rs2   |  rs1   |  funct3  |   rd   | opcode  |
|  7 bits    | 5 bits | 5 bits |  3 bits  | 5 bits | 7 bits  |
+------------+--------+--------+----------+--------+---------+
```

**Example `add x1, x2, x3`**: `x1 = x2 + x3`
- opcode = 0110011 (0x33)
- rd = x1 = 00001
- funct3 = 000
- rs1 = x2 = 00010
- rs2 = x3 = 00011
- funct7 = 0000000

Encoded binary: `0000000 00011 00010 000 00001 0110011`

Hex: `0x002100B3`

#### I-type (Immediate)

Used for immediate arithmetic, loads, and JALR. The immediate field is sign-extended.

```
31                              20|19   15|14      12|11     7|6       0
+--------------------------------+--------+----------+--------+---------+
|              imm               |  rs1   |  funct3  |   rd   | opcode  |
|            12 bits             | 5 bits |  3 bits  | 5 bits | 7 bits  |
+--------------------------------+--------+----------+--------+---------+
```

**Example `addi x1, x2, -5`**: `x1 = x2 + (-5)`
- opcode = 0010011 (0x13)
- rd = x1 = 00001
- funct3 = 000
- rs1 = x2 = 00010
- imm = -5 = 111111111011 (12-bit two's complement)

Encoded binary: `111111111011 00010 000 00001 0010011`

Hex: `0xFFF10113`

#### S-type (Store)

Used for store instructions. The immediate is split across two bit positions for opcode uniformity.

```
31           25|24   20|19   15|14      12|11        7|6       0
+-------------+--------+--------+----------+-----------+---------+
|  imm[11:5]  |  rs2   |  rs1   |  funct3  | imm[4:0]  | opcode  |
|   7 bits    | 5 bits | 5 bits |  3 bits  |  5 bits   | 7 bits  |
+-------------+--------+--------+----------+-----------+---------+
```

**Example `sw x1, 8(x2)`**: `Mem[x2 + 8] = x1`
- opcode = 0100011 (0x23)
- funct3 = 010
- rs1 = x2 = 00010
- rs2 = x1 = 00001
- imm[11:5] = 0000000 (bits 11:5 of 8)
- imm[4:0] = 01000 (bits 4:0 of 8)

Binary: `0000000 00001 00010 010 01000 0100011`

Hex: `0x00112423`

#### B-type (Branch)

Used for conditional branches. The immediate encodes a signed PC-relative offset. Bit 0 of the offset is always 0 (instruction alignment), so bit [0] is not stored.

```
31          30|29       25|24   20|19   15|14      12|11    10|9      8|7       0
+------------+-----------+--------+--------+----------+-------+--------+---------+
|  [12|10:5] |   rs2     |  rs1   | funct3  |[4:1|11] | opcode |
|  imm[12]   | imm[10:5] | 5 bits | 5 bits | 3 bits  |imm[9:4]|imm[4:1]|imm[11] |
+------------+-----------+--------+--------+----------+--------+--------+---------+
```

Simplified view:
```
31       25|24   20|19   15|14      12|11       7|6      0
+-----------+--------+--------+----------+----------+--------+
| imm[12|10:5] |  rs2 |  rs1  |  funct3  | imm[4:1|11]|opcode |
|  7 bits      |5 bits|5 bits |  3 bits  |  5 bits   |7 bits  |
+-----------+--------+--------+----------+----------+--------+
```

**Example `beq x1, x2, label`** (where label is +16 bytes = +4 instructions):
- opcode = 1100011 (0x63)
- funct3 = 000
- rs1 = x1 = 00001
- rs2 = x2 = 00010
- imm = 16 = 000000010000

B-type immediate encoding: bit[12|10:5|4:1|11]
Bit positions of 16 (binary 000000010000):
- bit 12 = 0, bits 10:5 = 000001, bits 4:1 = 0000, bit 11 = 0
- So imm[12|10:5] = 0|000001 = 0000001
- imm[4:1|11] = 0000|0 = 00000

Binary: `0000001 00010 00001 000 00000 1100011`

Hex: `0x00208463`

#### U-type (Upper immediate)

Used for LUI (load upper immediate) and AUIPC (add upper immediate to PC). The immediate forms the upper 20 bits; lower 12 bits are zero.

```
31                       12|11     7|6       0
+---------------------------+--------+---------+
|          imm              |   rd   | opcode  |
|        20 bits            | 5 bits | 7 bits  |
+---------------------------+--------+---------+
```

**Example `lui x1, 0x12345`**: `x1 = 0x12345000`
- opcode = 0110111 (0x37)
- rd = x1 = 00001
- imm = 0x12345 = 00010010001101000101

Hex: `0x123450B7`

#### J-type (Jump)

Used for JAL (jump and link). The immediate encodes a signed PC-relative offset with the same alignment constraint as B-type.

```
31            30|29     21|20   19         12|11     7|6       0
+--------------+----------+-------+-------------+--------+---------+
|  imm[20]     | imm[10:1]| imm[11]| imm[19:12] |   rd   | opcode  |
|  1 bit       | 10 bits  | 1 bit  |  8 bits    | 5 bits | 7 bits  |
+--------------+----------+-------+-------------+--------+---------+
```

### Common RV32I Instructions

#### Arithmetic Instructions (R-type)

| Mnemonic | Operation              | funct7    | funct3 | opcode |
|----------|------------------------|-----------|--------|--------|
| ADD      | rd = rs1 + rs2        | 0000000   | 000    | 0110011|
| SUB      | rd = rs1 - rs2        | 0100000   | 000    | 0110011|
| SLL      | rd = rs1 << rs2[4:0]  | 0000000   | 001    | 0110011|
| SLT      | rd = (rs1 < rs2) signed| 0000000  | 010    | 0110011|
| SLTU     | rd = (rs1 < rs2) unsigned| 0000000| 011    | 0110011|
| XOR      | rd = rs1 ^ rs2        | 0000000   | 100    | 0110011|
| SRL      | rd = rs1 >> rs2[4:0]  | 0000000   | 101    | 0110011|
| SRA      | rd = rs1 >> rs2[4:0] (arith)| 0100000| 101  | 0110011|
| OR       | rd = rs1 | rs2        | 0000000   | 110    | 0110011|
| AND      | rd = rs1 & rs2        | 0000000   | 111    | 0110011|

#### Immediate Arithmetic (I-type)

| Mnemonic | Operation                 | funct3 | opcode |
|----------|---------------------------|--------|--------|
| ADDI     | rd = rs1 + sext(imm)      | 000    | 0010011|
| SLTI     | rd = (rs1 < sext(imm)) signed| 010 | 0010011|
| SLTIU    | rd = (rs1 < sext(imm)) unsigned| 011| 0010011|
| XORI     | rd = rs1 ^ sext(imm)      | 100    | 0010011|
| ORI      | rd = rs1 | sext(imm)      | 110    | 0010011|
| ANDI     | rd = rs1 & sext(imm)      | 111    | 0010011|
| SLLI     | rd = rs1 << imm[4:0]      | 001    | 0010011|
| SRLI     | rd = rs1 >> imm[4:0]      | 101    | 0010011|
| SRAI     | rd = rs1 >> imm[4:0] (arith)| 101  | 0010011|

Note: For shifts, funct7 distinguishes SRLI (0000000) from SRAI (0100000).

#### Load and Store Instructions

| Mnemonic | Operation                    | funct3 | opcode |
|----------|------------------------------|--------|--------|
| LB       | rd = sext(M[rs1+imm], 8 bits)| 000    | 0000011|
| LH       | rd = sext(M[rs1+imm],16 bits)| 001    | 0000011|
| LW       | rd = M[rs1+imm]              | 010    | 0000011|
| LBU      | rd = zext(M[rs1+imm], 8 bits)| 100    | 0000011|
| LHU      | rd = zext(M[rs1+imm],16 bits)| 101    | 0000011|
| SB       | M[rs1+imm] = rs1[7:0]        | 000    | 0100011|
| SH       | M[rs1+imm] = rs1[15:0]       | 001    | 0100011|
| SW       | M[rs1+imm] = rs1             | 010    | 0100011|

LW example encoding: `lw x1, 8(x2)` (already shown above in I-type).

#### Branch Instructions (B-type)

| Mnemonic | Condition                           | funct3 | opcode |
|----------|-------------------------------------|--------|--------|
| BEQ      | if (rs1 == rs2) PC += imm           | 000    | 1100011|
| BNE      | if (rs1 != rs2) PC += imm           | 001    | 1100011|
| BLT      | if (rs1 < rs2, signed) PC += imm    | 100    | 1100011|
| BGE      | if (rs1 >= rs2, signed) PC += imm   | 101    | 1100011|
| BLTU     | if (rs1 < rs2, unsigned) PC += imm  | 110    | 1100011|
| BGEU     | if (rs1 >= rs2, unsigned) PC += imm | 111    | 1100011|

#### Jump Instructions (J-type and I-type)

| Mnemonic | Operation                    | opcode |
|----------|------------------------------|--------|
| JAL      | rd = PC+4; PC += imm         | 1101111|
| JALR     | rd = PC+4; PC = rs1 + imm   | 1100111|

`jal x1, func` saves return address in x1 and jumps.
`jalr x0, x1, 0` returns (x0 discards result, x1 holds return address).

#### Upper Immediate Instructions (U-type)

| Mnemonic | Operation                      | opcode |
|----------|--------------------------------|--------|
| LUI      | rd = imm << 12                 | 0110111|
| AUIPC    | rd = PC + (imm << 12)          | 0010111|

### Encoding Exercises

**Exercise 1**: Encode `addi x5, x6, 100`
- opcode = 0010011
- rd = x5 = 00101
- funct3 = 000
- rs1 = x6 = 00110
- imm = 100 = 000001100100 (12-bit)
- Binary: `000001100100 00110 000 00101 0010011`
- Hex: `0x06430293`

**Exercise 2**: Encode `sub x10, x11, x12`
- opcode = 0110011
- rd = x10 = 01010
- funct3 = 000
- rs1 = x11 = 01011
- rs2 = x12 = 01100
- funct7 = 0100000 (distinguishes SUB from ADD)
- Binary: `0100000 01100 01011 000 01010 0110011`
- Hex: `0x40C582B3`

---

### References

1. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213. Chapter 2. Available at: https://riscv.org/technical/specifications/
2. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 2, Appendix A.
3. Waterman, A. "Design of the RISC-V Instruction Set Architecture." PhD Dissertation, UC Berkeley, 2016. Chapter 2.
4. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 6.
