# Number Systems

## Why Computers Use Binary

Digital computers use the binary (base-2) number system for a fundamental reason: physical reliability. A binary system represents information using only two states -- typically 0 V (low voltage) and Vdd (high voltage). These two discrete voltage levels are far easier to distinguish reliably than ten levels (as decimal would require). Noise margins, process variation, and component aging all degrade signal integrity; with only two states, the system can tolerate significant degradation before a 0 is mistaken for a 1 or vice versa.

Key advantages of binary:
- **Noise immunity**: voltage thresholds can be set with wide margins (e.g., TTL logic: 0-0.8 V for logic 0, 2.0-5.0 V for logic 1).
- **Simple switching devices**: transistors operate naturally as switches (cut-off vs. saturation), mapping directly to 0/1.
- **Boolean algebra**: binary maps cleanly onto Boolean logic, enabling formal design and optimization of circuits.
- **Error detection**: binary codes (parity, CRC, Hamming codes) provide straightforward error detection and correction.

As Patterson and Hennessy state: "The two-valued nature of binary digits matches the on/off nature of the signals in a digital circuit" [1].

---

## Binary Representation

A binary number is a sequence of bits (binary digits), each being 0 or 1. The place value of each bit is a power of 2.

**Example**: The binary number `1011_2` (underscores group nibbles for readability):

```
1    0    1    1
2^3  2^2  2^1  2^0
8    4    2    1
```

Value = 1x8 + 0x4 + 1x2 + 1x1 = 11 in decimal.

### Conversion: Binary to Decimal

Sum each bit multiplied by its place value.

**Example**: Convert `11010_2` to decimal.

| Bit | Place value | Contribution |
|-----|-------------|-------------|
| 1   | 2^4 = 16    | 16          |
| 1   | 2^3 = 8     | 8           |
| 0   | 2^2 = 4     | 0           |
| 1   | 2^1 = 2     | 2           |
| 0   | 2^0 = 1     | 0           |

**Result**: 16 + 8 + 2 = **26**.

### Conversion: Decimal to Binary

Use repeated division by 2. The remainder at each step is the next least significant bit (LSB).

**Example**: Convert 42 to binary.

```
42 / 2 = 21 remainder 0 (LSB)
21 / 2 = 10 remainder 1
10 / 2 =  5 remainder 0
 5 / 2 =  2 remainder 1
 2 / 2 =  1 remainder 0
 1 / 2 =  0 remainder 1 (MSB)
```

Reading remainders from top to bottom gives: **101010_2**.

---

## Hexadecimal Representation

Hexadecimal (base-16) uses digits 0-9 and letters A-F. It is a compact notation for binary: one hex digit represents exactly four bits.

| Hex | Binary | Decimal |
|-----|--------|---------|
| 0   | 0000   | 0       |
| 1   | 0001   | 1       |
| 2   | 0010   | 2       |
| 3   | 0011   | 3       |
| 4   | 0100   | 4       |
| 5   | 0101   | 5       |
| 6   | 0110   | 6       |
| 7   | 0111   | 7       |
| 8   | 1000   | 8       |
| 9   | 1001   | 9       |
| A   | 1010   | 10      |
| B   | 1011   | 11      |
| C   | 1100   | 12      |
| D   | 1101   | 13      |
| E   | 1110   | 14      |
| F   | 1111   | 15      |

### Conversion: Binary to Hex

Group bits into sets of four from the right, then convert each group.

**Example**: `101110101001_2` -> `1011 1010 1001` -> `B A 9` -> **0xB A9**.

### Conversion: Hex to Binary

Replace each hex digit with its 4-bit equivalent.

**Example**: `0x3F 7` -> `3` = `0011`, `F` = `1111`, `7` = `0111` -> **001111110111_2**.

---

## Two's Complement (Signed Numbers)

Two's complement is the dominant method for representing signed integers in computers because it unifies addition and subtraction: the same hardware handles both unsigned and signed operations for addition.

### Representation

For an n-bit number:
- The most significant bit (MSB) has place value **-2^(n-1)** (negative weight).
- All other bits have their usual positive weight.

**Range**: -2^(n-1) to 2^(n-1) - 1. For 8 bits: -128 to 127.

### Computing the Negative

To compute -X for an n-bit number:
1. Write X in binary (n bits).
2. Invert all bits (bitwise NOT).
3. Add 1.

**Example**: Represent -5 in 8-bit two's complement.

1. +5 = `00000101`
2. Invert: `11111010`
3. Add 1: `11111011`

So -5 in 8-bit two's complement is `11111011`.

### Sign Extension

To widen a two's complement number, extend the sign bit (MSB) into the new high-order bits.

**Example**: Extend 4-bit `1011` (-5) to 8 bits: `11111011`.

### Addition and Subtraction

Add two's complement numbers with standard binary addition, discarding any final carry out of the MSB. Overflow occurs when the carry into the sign bit differs from the carry out of the sign bit.

**Example**: 5 + (-3) = 2.

```
  00000101  (+5)
+ 11111101  (-3)
----------
1 00000010  (carry out discarded -> +2, correct)
```

### Why Two's Complement Works

The negation procedure (invert + add 1) is equivalent to computing 2^n - X. Adding -X = 2^n - X to X gives 2^n, which is 0 modulo 2^n. This means addition circuits can be purely combinational -- no special subtractor hardware is needed [1].

---

## IEEE 754 Floating Point

The IEEE 754 standard [2] defines formats for representing real numbers in binary. The single-precision (32-bit) format is the most commonly taught and used.

### Single-Precision Format (32 bits)

```
Bit 31      Bits 30-23        Bits 22-0
[ Sign ]   [ Exponent ]      [ Mantissa/Significand ]
   1 bit      8 bits              23 bits
```

| Field     | Width | Purpose                                              |
|-----------|-------|------------------------------------------------------|
| Sign (S)  | 1 bit | 0 = positive, 1 = negative                           |
| Exponent (E) | 8 bits | Biased representation (actual exponent = E - 127) |
| Mantissa (M) | 23 bits | Fractional part (the leading 1 is implicit)       |

### Value Formula

For **normalized** numbers (E not all 0s or all 1s):

**Value = (-1)^S x (1.M) x 2^(E - 127)**

The leading 1 (the "hidden bit") is implied and not stored, giving 24 bits of precision.

### Biased Exponent

The stored exponent E is the actual exponent plus 127 (the bias). This allows exponents from -126 to +127 (E = 1 to 254). E = 0 and E = 255 are reserved for special values.

### Example: Convert 5.75 to IEEE 754 Single-Precision

**Step 1**: Convert to binary.
- Integer part: 5 = `101_2`
- Fractional part: 0.75 = `0.11_2` (because 0.75 x 2 = 1.50 -> 1; 0.50 x 2 = 1.00 -> 1)
- Combined: `101.11_2`

**Step 2**: Normalize.
- `101.11_2` = `1.0111_2 x 2^2`
- Sign: 0 (positive)
- Exponent: 2 + 127 = 129 = `10000001_2`
- Mantissa: `01110000000000000000000` (the leading 1 is dropped)

**Step 3**: Pack.

```
0 10000001 01110000000000000000000
```

In hex: `0x40B80000`.

### Example: Convert 0.1 to IEEE 754 Single-Precision

0.1 in binary is a **repeating fraction**: 0.00011001100110011001100...

```
0.1 = 0.000110011001100110011001100..._2
    = 1.10011001100110011001100..._2 x 2^(-4)
```

- Sign: 0
- Exponent: -4 + 127 = 123 = `01111011_2`
- Mantissa: `10011001100110011001101` (rounded to 23 bits)

```
0 01111011 10011001100110011001101
```

In hex: `0x3DCCCCCD`.

This demonstrates a key issue: many decimal fractions cannot be represented exactly in binary -- the value stored is a close approximation, not 0.1 exactly [3].

### Special Values

| Exponent | Mantissa | Meaning                             |
|----------|----------|-------------------------------------|
| 0        | 0        | Zero (signed: +0 and -0 exist)      |
| 0        | non-zero | Denormalized (subnormal) numbers    |
| 255      | 0        | Infinity (signed: +inf, -inf)       |
| 255      | non-zero | NaN (Not a Number)                  |

### Denormalized Numbers

When E = 0 and M != 0, the number is denormalized: the implicit leading bit is 0, and the exponent is -126 (not -127). This allows gradual underflow -- representing numbers closer to zero than the smallest normalized number.

**Value = (-1)^S x (0.M) x 2^(-126)**

### Double Precision (64 bits)

| Field    | Width | Bias   |
|----------|-------|--------|
| Sign     | 1     | --     |
| Exponent | 11    | 1023   |
| Mantissa | 52    | --     |

---

## References

1. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Chapter 1: Computer Abstractions and Technology.

2. IEEE Standard for Floating-Point Arithmetic. (2019). *IEEE Std 754-2019 (Revision of IEEE 754-2008)*, pp.1-84. doi:10.1109/IEEESTD.2019.8766229.

3. Goldberg, D. (1991). What Every Computer Scientist Should Know About Floating-Point Arithmetic. *ACM Computing Surveys*, 23(1), 5-48. doi:10.1145/103162.103163.

4. Koren, I. (2002). *Computer Arithmetic Algorithms* (2nd ed.). A K Peters/CRC Press. Chapter 1: Conventional Number Systems.

5. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 1: From Zero to One.
