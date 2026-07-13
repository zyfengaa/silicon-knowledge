# Combinational Circuits

A combinational circuit is one whose output depends only on the current inputs -- there is no memory or state. This note covers the fundamental combinational building blocks used in digital systems: adders, multiplexers, decoders, encoders, and comparators [1,2].

---

## Adders

### Half Adder

The half adder adds two single-bit numbers, producing a sum and a carry.

```
Truth Table:
A  B | Sum  Carry
-----|-----------
0  0 |  0    0
0  1 |  1    0
1  0 |  1    0
1  1 |  0    1
```

**Boolean expressions**:
- Sum = A XOR B
- Carry = A AND B

### Full Adder

The full adder adds three single-bit numbers: A, B, and Carry-in (Cin), producing Sum and Carry-out (Cout).

```
Truth Table:
A  B Cin | Sum  Cout
---------|----------
0  0  0  |  0    0
0  0  1  |  1    0
0  1  0  |  1    0
0  1  1  |  0    1
1  0  0  |  1    0
1  0  1  |  0    1
1  1  0  |  0    1
1  1  1  |  1    1
```

**Boolean expressions**:
- Sum = A XOR B XOR Cin
- Cout = (A AND B) OR (A AND Cin) OR (B AND Cin)
  Equivalently: Cout = (A AND B) OR (Cin AND (A XOR B))

### Ripple-Carry Adder (RCA)

A ripple-carry adder chains N full adders to add two N-bit numbers. The carry out of each stage feeds the carry in of the next stage.

```
4-bit Ripple-Carry Adder:

       A3  B3       A2  B2       A1  B1       A0  B0
       |   |        |   |        |   |        |   |
    +--------+   +--------+   +--------+   +--------+
    |  FA    |   |  FA    |   |  FA    |   |  FA    |
C4--| Cout   |---| Cin    |---| Cin    |---| Cin 0 |
    +--------+   +--------+   +--------+   +--------+
       |            |            |            |
      S3           S2           S1           S0
```

**Timing**: The carry must propagate through all N stages. The worst-case delay is proportional to N.

**4-bit RCA example**: Add 7 (0111) + 5 (0101) = 12 (1100)

```
Bit 0: 1 + 1 = 0, carry 1
Bit 1: 1 + 0 + cin=1 = 0, carry 1
Bit 2: 1 + 1 + cin=1 = 1, carry 1
Bit 3: 0 + 0 + cin=1 = 1, carry 0
Result: 1100 (12)
```

### Carry-Lookahead Adder (CLA)

The CLA computes all carries in parallel, using generate (G) and propagate (P) signals [3]:

```
G_i = A_i AND B_i         -- generates a carry regardless of Cin
P_i = A_i XOR B_i         -- propagates Cin to Cout
C_{i+1} = G_i + P_i.C_i
```

**Expanded carries** (all computed from C0 in one gate delay):

```
C1 = G0 + P0.C0
C2 = G1 + P1.G0 + P1.P0.C0
C3 = G2 + P2.G1 + P2.P1.G0 + P2.P1.P0.C0
```

Each carry requires only a 2-level AND-OR circuit. The CLA computes N-bit addition in O(log N) delay vs. O(N) for RCA, at the cost of more gates.

---

## Multiplexers (MUX)

A multiplexer selects one of several inputs based on select lines.

### 2-to-1 MUX

```
Truth Table:
S | Y
--|---
0 | D0
1 | D1

Logic: Y = (S'.D0) + (S.D1)
```

### 4-to-1 MUX

```
Truth Table:
S1 S0 |  Y
------|----
 0  0 | D0
 0  1 | D1
 1  0 | D2
 1  1 | D3

Logic: Y = (S1'.S0'.D0) + (S1'.S0.D1) + (S1.S0'.D2) + (S1.S0.D3)
```

### MUX Applications

- **Data selection**: choosing between multiple data sources.
- **Function generation**: any N+1-variable Boolean function with a 2^N-to-1 MUX.
- **Barrel shifters**: arrays of MUXes implement bit rotation/shifting.

---

## Decoders

A decoder converts an N-bit binary code to 2^N output lines, where exactly one output is active.

### 2-to-4 Decoder

```
Truth Table:
A1 A0 | Y3 Y2 Y1 Y0
------|--------------
 0  0 |  0  0  0  1
 0  1 |  0  0  1  0
 1  0 |  0  1  0  0
 1  1 |  1  0  0  0

Logic:
  Y0 = A1'.A0', Y1 = A1'.A0, Y2 = A1.A0', Y3 = A1.A0
```

**Applications**: Memory address decoding, instruction decoding, BCD-to-7-segment display drivers.

---

## Encoders

An encoder performs the inverse of a decoder: it converts 2^N input lines to an N-bit binary code.

### 4-to-2 Encoder

```
Truth Table (assumes exactly one input active):
I3 I2 I1 I0 | A1 A0
------------|------
 0  0  0  1 |  0  0
 0  0  1  0 |  0  1
 0  1  0  0 |  1  0
 1  0  0  0 |  1  1

Logic: A0 = I3 + I1, A1 = I3 + I2
```

### Priority Encoder

Handles multiple simultaneous active inputs by prioritizing the highest-numbered input.

**4-to-2 Priority Encoder** (highest index wins):

```
Truth Table:
I3 I2 I1 I0 | A1 A0 | V (valid)
------------|-------|---------
 0  0  0  0 |  x  x |   0
 0  0  0  1 |  0  0 |   1
 0  0  1  x |  0  1 |   1
 0  1  x  x |  1  0 |   1
 1  x  x  x |  1  1 |   1

Logic: V = I3+I2+I1+I0, A1 = I3+I2, A0 = I3+I2'.I1
```

---

## Comparators

A comparator determines whether two binary numbers are equal, and/or which is larger.

### Equality Comparator

For N-bit numbers A and B:
```
Equal = (A0 XNOR B0) AND (A1 XNOR B1) AND ... AND (A{N-1} XNOR B{N-1})
```

### 1-bit Magnitude Comparator

```
Truth Table:
A B | A>B  A=B  A<B
----|---------------
0 0 |  0    1    0
0 1 |  0    0    1
1 0 |  1    0    0
1 1 |  0    1    0

Logic: A>B = A.B', A=B = A XNOR B, A<B = A'.B
```

N-bit magnitude comparator compares from MSB to LSB; the first differing bit determines the result.

---

## Combinational Circuit Timing

The **critical path** is the longest path from any input to any output. The circuit's operating frequency is limited by this delay:

```
F_max <= 1 / t_critical
```

Where t_critical is the sum of all gate delays along the critical path [2].

---

## References

1. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 4: Combinational Logic.

2. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 5: Digital Building Blocks.

4. Weinberger, A., & Smith, J. L. (1958). A Logic for High-Speed Addition. *National Bureau of Standards Circular*, 591, 3-12.

5. Koren, I. (2002). *Computer Arithmetic Algorithms* (2nd ed.). A K Peters/CRC Press. Chapter 2: Addition.
