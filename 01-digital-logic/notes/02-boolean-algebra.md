# Boolean Algebra

Boolean algebra, developed by George Boole in the mid-19th century, is the mathematical foundation of digital logic design. Claude Shannon first applied it to relay circuits in his 1937 master's thesis, establishing the field of digital circuit design [1].

---

## Basic Axioms and Operations

Boolean algebra operates on binary values: 0 (false) and 1 (true). Three fundamental operations are defined:

| Operation | Notation | Description |
|-----------|----------|-------------|
| AND       | A . B or A B | True only if both A AND B are true |
| OR        | A + B        | True if A OR B (or both) is true |
| NOT       | A' or A or ~A | Inverts the value |

### Truth Tables for Basic Operations

```
AND                OR                 NOT
A  B | A.B         A  B | A+B         A | A'
-----|-----        -----|-----        ---|----
0  0 |  0          0  0 |  0          0 |  1
0  1 |  0          0  1 |  1          1 |  0
1  0 |  0          1  0 |  1
1  1 |  1          1  1 |  1
```

---

## Boolean Laws

All Boolean laws can be proved by perfect induction (checking all combinations of inputs).

### Fundamental Laws

| Law            | AND Form               | OR Form                |
|----------------|------------------------|------------------------|
| Identity       | A . 1 = A              | A + 0 = A              |
| Null element   | A . 0 = 0              | A + 1 = 1              |
| Idempotent     | A . A = A              | A + A = A              |
| Complement     | A . A' = 0             | A + A' = 1             |
| Involution     | (A')' = A              | (A')' = A              |

### Commutative Law

**A . B = B . A** and **A + B = B + A**

The order of operands does not affect the result.

### Associative Law

**(A . B) . C = A . (B . C)** and **(A + B) + C = A + (B + C)**

Grouping of operations does not affect the result.

### Distributive Law

**A . (B + C) = A . B + A . C** (AND distributes over OR)

**A + (B . C) = (A + B) . (A + C)** (OR distributes over AND)

Note: Unlike regular algebra, both forms of distributivity hold in Boolean algebra.

### De Morgan's Laws

**(A . B)' = A' + B'** and **(A + B)' = A' . B'**

De Morgan's laws are critical for circuit simplification and for converting between AND/OR and NAND/NOR implementations.

Proof by truth table for **(A . B)' = A' + B'**:

```
A  B | A.B | (A.B)' | A' | B' | A' + B'
-----|-----|--------|----|----|---------
0  0 |  0  |   1    | 1  | 1  |   1
0  1 |  0  |   1    | 1  | 0  |   1
1  0 |  0  |   1    | 0  | 1  |   1
1  1 |  1  |   0    | 0  | 0  |   0
```

The columns for (A.B)' and A' + B' match in every row, proving the law.

### Absorption Laws

**A + (A . B) = A**

**A . (A + B) = A**

These are useful for eliminating redundant terms.

### Consensus Theorem

**A . B + A' . C + B . C = A . B + A' . C**

The term B . C is redundant (the "consensus").

---

## Boolean Function Representations

### Sum of Products (SOP)

A Boolean function expressed as OR of AND terms (minterms).

**Example**: F(A, B, C) = A'.B.C + A.B'.C + A.B.C

### Product of Sums (POS)

A Boolean function expressed as AND of OR terms (maxterms).

**Example**: F(A, B, C) = (A+B+C) . (A+B+C') . (A+B'+C)

### Minimization Using Boolean Laws

**Example**: Simplify F = A.B + A.B' + A'.B

```
F = A.B + A.B' + A'.B
  = A.(B + B') + A'.B         (Distributive)
  = A.1 + A'.B                (Complement: B + B' = 1)
  = A + A'.B                  (Identity: A.1 = A)
  = (A + A') . (A + B)         (Distributive: A + A'.B = (A+A').(A+B))
  = 1 . (A + B)                (Complement: A + A' = 1)
  = A + B                      (Identity)
```

---

## Karnaugh Maps (K-Maps)

K-maps are a graphical method for simplifying Boolean expressions. They arrange truth table cells so that adjacent cells differ by exactly one variable (Gray code ordering), making simplifications visually apparent [1,2].

### 2-Variable K-Map

```
        B
        0   1
     +---+---+
A  0 | m0| m1|
     +---+---+
   1 | m2| m3|
     +---+---+
```

Adjacent cells differ by one variable: e.g., m0 (A'B') and m1 (A'B) differ only in B, so they combine to A'.

**Example**: F(A,B) = A'B + AB' + AB

```
        B
        0   1
     +---+---+
A  0 | 0 | 1 |  <- m1 = A'B
     +---+---+
   1 | 1 | 1 |  <- m2+m3 = A
     +---+---+
```

Grouping: The two 1s in row A=1 form group A. The isolated 1 at m1 stays as A'B.
Simplified: **F = A + A'B = A + B**

### 3-Variable K-Map

```
         BC
         00  01  11  10
      +----+----+----+----+
A  0  | m0 | m1 | m3 | m2 |
      +----+----+----+----+
   1  | m4 | m5 | m7 | m6 |
      +----+----+----+----+
```

Note: Columns use Gray code (00 -> 01 -> 11 -> 10), so adjacent columns differ by one bit.

**Example**: F(A,B,C) = sum(2, 3, 6, 7)

```
         BC
         00  01  11  10
      +----+----+----+----+
A  0  | 0  | 0  | 1  | 1  |
      +----+----+----+----+
   1  | 0  | 0  | 1  | 1  |
      +----+----+----+----+
```

Grouping: The four 1s form a 2x2 square covering all cases where B=1 (C and A vary).
Simplified: **F = B**

**Example**: F(A,B,C) = sum(0, 2, 4, 6)

```
         BC
         00  01  11  10
      +----+----+----+----+
A  0  | 1  | 0  | 0  | 1  |
      +----+----+----+----+
   1  | 1  | 0  | 0  | 1  |
      +----+----+----+----+
```

Grouping: Four corners -- m0 (000), m2 (010), m4 (100), m6 (110). The corners where C=0.
Simplified: **F = C'**

### 4-Variable K-Map

```
           CD
           00   01   11   10
       +----+----+----+----+
AB 00  | m0 | m1 | m3 | m2 |
       +----+----+----+----+
   01  | m4 | m5 | m7 | m6 |
       +----+----+----+----+
   11  | m12| m13| m15| m14|
       +----+----+----+----+
   10  | m8 | m9 | m11| m10|
       +----+----+----+----+
```

**Example**: F(A,B,C,D) = sum(0, 2, 5, 7, 8, 10, 13, 15)

```
           CD
           00  01  11  10
       +---+---+---+---+
AB 00  | 1 | 0 | 0 | 1 |  <- A'B' (m0, m2)
       +---+---+---+---+
   01  | 0 | 1 | 1 | 0 |  <- A'B (m5, m7)
       +---+---+---+---+
   11  | 0 | 0 | 0 | 0 |
       +---+---+---+---+
   10  | 1 | 0 | 0 | 1 |  <- AB' (m8, m10)
       +---+---+---+---+
```

Groupings:
- m0 + m2: A'B'C'D' + A'B'CD' = A'B'D'
- m5 + m7: A'BC'D + A'BCD = A'BD
- m8 + m10: AB'C'D' + AB'CD' = AB'D'
- m13 + m15: ABCD + ABC'D = ABD (wait, m15 is 1111, m13 is 1101, so that's ACD? Let me re-check)

Wait, let me verify the groupings:
- m0 (0000) + m2 (0010) = A'B'C'D' + A'B'CD' = A'B'D'
- m8 (1000) + m10 (1010) = AB'C'D' + AB'CD' = AB'D'

Actually, wait -- the problem says m5(0101) and m7(0111) and m13(1101) and m15(1111). Let me re-examine.

The truth table I wrote has 1s at 0, 2, 5, 7, 8, 10, 13, 15. Let me look at the CD=01 and CD=11 columns carefully.

Actually, looking at my map: AB=01, CD=01 -> m5=1; AB=01, CD=11 -> m7=1; AB=11, CD=01 -> m13=1; AB=11, CD=11 -> m15=1.

These four (m5, m7, m13, m15) form a group: variable B=1, variable D=1 -> BD.

For m0+m2+m8+m10: A varies (0 and 1), B=0, C varies, D=0. Group: B'D'.

Simplified: **F = B'D' + BD = (B XOR D)' = XNOR(B, D)**

### Don't Care Conditions

In many circuits, certain input combinations never occur. These can be treated as "don't cares" (X) and assigned either 0 or 1 to produce a simpler expression.

**Example**: BCD to 7-segment display decoder. Inputs 1010-1111 never occur for BCD (0000-1001).

```
F(A,B,C,D) = sum(0,1,2,3,4,5,6,7,8,9) + d(10,11,12,13,14,15)
```

The don't care terms can be used to create larger groupings (and thus simpler terms) in the K-map.

---

## Canonical Forms

### Minterms

A minterm is a product term that includes each variable exactly once (either true or complemented). For n variables, there are 2^n minterms. A function in **sum of minterms** form is written as a sum of product terms where each variable appears in every term.

**Example**: F(A,B) = A'B + AB' + AB = sum(1, 2, 3)

### Maxterms

A maxterm is a sum term that includes each variable exactly once. A function in **product of maxterms** form is the dual.

**Example**: F(A,B) = (A+B) . (A+B') . (A'+B) = product(0, 1, 2)

Any function can be expressed as either sum of minterms or product of maxterms -- these are the canonical forms.

---

## Practical Simplification Example

**Problem**: Design a circuit for F(A,B,C,D) = AB + A'C + BC

Using the consensus theorem: AB + A'C + BC = AB + A'C (the BC term is redundant).

**Verification**:
- When A=1: F = B + 0 + BC = B
- When A=0: F = 0 + C + BC = C
- The consensus term BC is already covered by the other terms.

---

## References

1. Shannon, C. E. (1938). A Symbolic Analysis of Relay and Switching Circuits. *Transactions of the American Institute of Electrical Engineers*, 57(12), 713-723. doi:10.1109/T-AIEE.1938.5057767.

2. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 2: Boolean Algebra and Logic Gates.

3. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

4. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 2: Combinational Logic Design.

5. Karnaugh, M. (1953). The Map Method for Synthesis of Combinational Logic Circuits. *Transactions of the American Institute of Electrical Engineers, Part I: Communication and Electronics*, 72(5), 593-599. doi:10.1109/TCE.1953.6371448.
