# Logic Gates

Logic gates are the basic building blocks of digital circuits. Each gate implements a Boolean function, taking one or more binary inputs and producing a single binary output. This note covers the seven fundamental gates, their truth tables, and introduces CMOS implementation concepts [1,2].

---

## Basic Gates: AND, OR, NOT

### AND Gate

Output is 1 only when **all** inputs are 1.

```
Truth Table:
A  B | Y = A AND B
-----|-------------
0  0 |      0
0  1 |      0
1  0 |      0
1  1 |      1
```

### OR Gate

Output is 1 when **any** input is 1.

```
Truth Table:
A  B | Y = A OR B
-----|------------
0  0 |     0
0  1 |     1
1  0 |     1
1  1 |     1
```

### NOT Gate (Inverter)

Output is the complement of the input.

```
Truth Table:
A | Y = NOT A
--|----------
0 |    1
1 |    0
```

---

## Universal Gates: NAND and NOR

### NAND Gate

NAND = NOT + AND. Output is 0 only when **all** inputs are 1.

```
Truth Table:
A  B | Y = A NAND B = (A.B)'
-----|-----------------
0  0 |      1
0  1 |      1
1  0 |      1
1  1 |      0
```

### NOR Gate

NOR = NOT + OR. Output is 0 when **any** input is 1.

```
Truth Table:
A  B | Y = A NOR B = (A+B)'
-----|-----------------
0  0 |      1
0  1 |      0
1  0 |      0
1  1 |      0
```

### Why NAND and NOR Are Universal

Any Boolean function can be implemented using only NAND gates (or only NOR gates). This is economically significant: a manufacturer can produce just one gate type and build any circuit.

**Constructing basic gates from NAND**:

```
NOT:    (A NAND A) = A'
AND:    (A NAND B)' = A . B         (NAND then NOT)
OR:     A' NAND B' = A + B          (Invert inputs, then NAND)
```

Proof for NOT: A NAND A = (A.A)' = A' (by idempotent law).
Proof for AND: (A NAND B) NAND (A NAND B) = ((A.B)')' = A.B.
Proof for OR: A' NAND B' = (A' . B')' = A'' + B'' = A + B (by De Morgan's).

### XOR (Exclusive OR)

Output is 1 when inputs **differ**.

```
Truth Table:
A  B | Y = A XOR B = A'B + AB'
-----|-----------------
0  0 |      0
0  1 |      1
1  0 |      1
1  1 |      0
```

### XNOR (Exclusive NOR)

Output is 1 when inputs **match**. XNOR = NOT XOR.

```
Truth Table:
A  B | Y = A XNOR B
-----|--------------
0  0 |      1
0  1 |      0
1  0 |      0
1  1 |      1
```

---

## CMOS Implementation (Brief Introduction)

CMOS (Complementary Metal-Oxide-Semiconductor) is the dominant fabrication technology for digital logic. Each CMOS gate consists of two networks [3]:

- **Pull-up network (PUN)**: PMOS transistors connecting output to Vdd (logic 1).
- **Pull-down network (PDN)**: NMOS transistors connecting output to GND (logic 0).

The two networks are **complementary**: when one is conducting, the other is off. This means CMOS gates consume negligible static power (current flows only during switching).

### CMOS Inverter

- A = 0: PMOS ON, NMOS OFF -> output connected to Vdd -> Y = 1
- A = 1: PMOS OFF, NMOS ON -> output connected to GND -> Y = 0

### CMOS NAND Gate

NMOS transistors in series, PMOS in parallel. A=0 or B=0 yields Y=1; A=1 and B=1 yields Y=0.

### CMOS NOR Gate

NMOS transistors in parallel, PMOS in series. A=1 or B=1 yields Y=0; A=0 and B=0 yields Y=1.

| Gate     | PUN pattern    | PDN pattern    |
|----------|----------------|----------------|
| Inverter | 1 PMOS         | 1 NMOS         |
| NAND     | Parallel PMOS  | Series NMOS    |
| NOR      | Series PMOS    | Parallel NMOS  |

---

## Summary Table

| Gate  | Boolean Expression | Output = 1 when... | Universal? |
|-------|--------------------|--------------------|------------|
| AND   | Y = A . B          | All inputs = 1     | No         |
| OR    | Y = A + B          | Any input = 1      | No         |
| NOT   | Y = A'             | Input = 0          | No         |
| NAND  | Y = (A.B)'         | Any input = 0      | **Yes**    |
| NOR   | Y = (A+B)'         | All inputs = 0     | **Yes**    |
| XOR   | Y = A'B + AB'      | Inputs differ      | No         |
| XNOR  | Y = AB + A'B'      | Inputs match       | No         |

---

## References

1. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 1: Digital Systems and Binary Numbers; Chapter 2: Boolean Algebra and Logic Gates.

2. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Weste, N. H. E., & Harris, D. (2010). *CMOS VLSI Design: A Circuits and Systems Perspective* (4th ed.). Addison-Wesley. Chapter 1: Introduction; Chapter 5: The CMOS Inverter.

4. Rabaey, J. M., Chandrakasan, A., & Nikolic, B. (2003). *Digital Integrated Circuits: A Design Perspective* (2nd ed.). Prentice Hall. Chapter 5: The CMOS Inverter and Its Static Characteristics.

5. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 2: Combinational Logic Design.
