# Digital Logic -- Exercises

## Questions

### Question 1: Binary Conversion

Convert the following numbers:

a) `101101_2` to decimal
b) `42` to binary
c) `0x3F` to binary and decimal
d) `101011_2` to hexadecimal

### Question 2: Two's Complement

Given 8-bit two's complement representation:

a) What is the range of representable numbers?
b) Represent -23 in 8-bit two's complement.
c) Compute (-23) + 15 in 8-bit two's complement. Show the binary addition. Is there overflow?

### Question 3: IEEE 754

A 32-bit IEEE 754 floating-point value has the bit pattern `0x40A00000`.

a) What are the sign bit, exponent bits, and mantissa bits?
b) What is the numerical value (show work)?
c) How would -5.75 be represented as a 32-bit IEEE 754 value?

### Question 4: Boolean Simplification

Simplify using Boolean algebra laws. Show each step.

a) F = A.B + A.B' + A'.B
b) F = (A + B').(A' + B)
c) F = A'.B'.C' + A'.B'.C + A.B'.C' + A.B'.C

### Question 5: Karnaugh Map

Use a K-map to simplify F(A,B,C,D) = sum m(0,1,2,4,5,8,9,10).

a) Show the K-map with all entries.
b) Identify the prime implicants.
c) Give the minimal sum-of-products expression.

### Question 6: Adder Design

a) Write the full adder truth table.
b) Derive Boolean expressions for sum and carry-out.
c) Explain how carry-lookahead improves speed over ripple-carry.
d) Derive the expression for C2 (carry out of bit 2) in a CLA.

### Question 7: Sequential Circuits

a) Draw the circuit diagram of a NOR-based SR latch. Explain the forbidden state.
b) What is the difference between a level-sensitive D latch and an edge-triggered D flip-flop?
c) Explain setup time and hold time. What happens when violated?
d) A flip-flop has t_clk-to-Q=2ns, t_su=1ns, combinational delay=5ns. What is max clock frequency?

### Question 8: Arithmetic Circuits

a) Using Booth's radix-2 algorithm, multiply 6 (0110) by 5 (0101) step by step.
b) Explain the advantage of a Wallace tree multiplier over an array multiplier.
c) What is the key difference between restoring and non-restoring division?

---

## Answers

### Answer 1: Binary Conversion

**a)** 101101_2 = 1x32 + 0x16 + 1x8 + 1x4 + 0x2 + 1x1 = 32+8+4+1 = **45**

**b)** 42 to binary:
```
42/2=21r0, 21/2=10r1, 10/2=5r0, 5/2=2r1, 2/2=1r0, 1/2=0r1
Reading remainders bottom-up: 101010_2
```

**c)** 0x3F: binary 00111111_2, decimal 3x16+15 = **63**

**d)** 101011_2 -> 0010 1011 -> **0x2B**

### Answer 2: Two's Complement

**a)** Range: -128 to +127

**b)** -23: +23 = 00010111. Invert: 11101000. Add 1: **11101001**

**c)** (-23) + 15: 11101001 + 00001111 = 11111000. Invert: 00000111. Add 1: 00001000 = -8.
Carry in = 1, carry out = 1 -> no overflow. **Answer: -8**

### Answer 3: IEEE 754

**a)** 0x40A00000 = 0100_0000_1010_0000_...
Sign: 0, Exponent: 10000001=129, Mantissa: 010000...

**b)** S=0, E=129 (unbiased=2), Mantissa=1.01_2 -> 1.01 x 2^2 = 101 = **5.0**

**c)** -5.75: 5.75=101.11_2, normalized=1.0111x2^2. S=1, E=129=10000001, M=011100...
Bit pattern: 1 10000001 01110000000000000000000 = **0xC0B80000**

### Answer 4: Boolean Simplification

**a)** F = A.B + A.B' + A'.B = A.(B+B') + A'.B = A + A'.B = A + B

**b)** F = (A+B').(A'+B) = 0 + A.B + A'.B' + 0 = A.B + A'.B' = A XNOR B

**c)** F = A'.B'.(C'+C) + A.B'.(C'+C) = A'.B' + A.B' = B'.(A'+A) = **B'**

### Answer 5: Karnaugh Map

**a) K-map:**
```
           CD
           00  01  11  10
AB 00  | 1 | 1 | 0 | 1 |
   01  | 1 | 1 | 0 | 0 |
   11  | 0 | 0 | 0 | 0 |
   10  | 1 | 1 | 0 | 1 |
```

**b)** Prime implicants: A'C' (m0,m1,m4,m5), B'D' (m0,m2,m8,m10), AB'C' (m8,m9)

**c)** Minimal SOP: **F = A'C' + B'D' + AB'C'**

### Answer 6: Adder Design

**a)** Full adder truth table:
```
A B Cin | Sum Cout
0 0 0 | 0 0
0 0 1 | 1 0
0 1 0 | 1 0
0 1 1 | 0 1
1 0 0 | 1 0
1 0 1 | 0 1
1 1 0 | 0 1
1 1 1 | 1 1
```

**b)** Sum = A XOR B XOR Cin. Cout = (A.B) + (B.Cin) + (A.Cin)

**c)** CLA computes carries in parallel using G_i = A_i.B_i and P_i = A_i XOR B_i. C_{i+1} = G_i + P_i.C_i. All carries available in constant time (2-level AND-OR), independent of N.

**d)** C2 = G1 + P1.G0 + P1.P0.C0

### Answer 7: Sequential Circuits

**a)** Two cross-coupled NOR gates. Forbidden: S=1,R=1 -> Q=Q'=0, violates Q != Q'.

**b)** D latch: level-sensitive, transparent when enabled. D flip-flop: edge-triggered, samples only at clock edge.

**c)** Setup: data stable before edge. Hold: data stable after edge. Violation -> metastability.

**d)** T_min = 2+5+1 = 8ns. F_max = **125 MHz**

### Answer 8: Arithmetic Circuits

**a)** Booth: M=0110, Multiplier=0101. +M(0110), -M(1010)<<1, +M(0110)<<2. Sum = 0110 + 10100 + 011000 = 0011110 = **30**

**b)** Wallace tree: O(log N) delay vs O(N) for array. More wires but faster for large multipliers.

**c)** Restoring: restores after failed subtraction (2N ops). Non-restoring: avoids restore by choosing add/subtract based on sign (N ops, final correction if needed).

---

## References

1. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design* (5th ed.). Morgan Kaufmann.
2. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design* (6th ed.). Pearson.
3. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann.
4. IEEE Standard for Floating-Point Arithmetic. (2019). *IEEE Std 754-2019*.
5. Koren, I. (2002). *Computer Arithmetic Algorithms* (2nd ed.). A K Peters/CRC Press.
