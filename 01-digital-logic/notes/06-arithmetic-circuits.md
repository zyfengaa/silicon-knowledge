# Arithmetic Circuits

Beyond basic addition, digital systems require hardware for multiplication, division, and other arithmetic operations. This note covers key circuit architectures and their area/latency/throughput trade-offs [1,2].

---

## Multipliers

Multiplication of two N-bit numbers produces a 2N-bit result. The basic concept: generate partial products and sum them.

**Example**: 4-bit multiplication (3 x 6 = 18)

```
        0011  (3)
      x 0110  (6)
      -------
        0000   (partial product 0)
       0011    (partial product 1, shifted left 1)
      0011     (partial product 2, shifted left 2)
     0000      (partial product 3, shifted left 3)
     --------
     0010010   (18)
```

### Array Multiplier

Uses AND gates to generate partial product bits and adders to sum them. Area grows as O(N^2). Delay is O(N).

### Booth Encoding

Reduces the number of partial products, especially effective when the multiplier has long runs of 1s [3].

**Radix-2 Booth**: Examine two bits of the multiplier (with an extra bit to the right, initially 0):

| b_{i+1} | b_i | Prev | Operation |
|---------|-----|------|-----------|
| 0 | 0 | 0 | Add 0 |
| 0 | 0 | 1 | Add M |
| 0 | 1 | 0 | Add M |
| 0 | 1 | 1 | Add 2M |
| 1 | 0 | 0 | Add -2M |
| 1 | 0 | 1 | Add -M |
| 1 | 1 | 0 | Add -M |
| 1 | 1 | 1 | Add 0 |

**Booth Example**: 3 x 5 (M=0011, multiplier=0101)

```
Step 0: (0,1), prev=0 -> +M   = 0011 at position 0
Step 1: (1,0), prev=0 -> -M   = 1101 at position 1
Step 2: (0,1), prev=1 -> +M   = 0011 at position 2
Step 3: (0,0), prev=1 -> 0    = 0000 at position 3

Sum:  0011 + 11010 + 001100 = 00001111 = 15. Correct.
```

**Radix-4 Booth** (modified Booth): examines 3-bit overlapping groups, reducing partial products from N to N/2.

### Wallace Tree Multiplier

Sums partial products in parallel using carry-save adders (CSAs), reducing depth from O(N) to O(log N) [4].

Each CSA takes 3 numbers and produces (Sum, Carry) in one full-adder delay. The tree reduces N rows to 2, then a final carry-propagate adder produces the result.

**Timing comparison** (8x8 multiplier):

| Architecture | Delay (adder stages) | Gate count |
|-------------|---------------------|------------|
| Array | ~14 | ~500 |
| Wallace tree | ~8 | ~800 |
| Booth + Wallace | ~6 | ~900 |

---

## Dividers

Division is harder than multiplication. Implementations range from iterative (slow, area-efficient) to lookup-table-based (fast, area-intensive).

### Restoring Division

Resembles long division. One decision per quotient bit [5].

```
Remainder = Dividend (2N bits)
Divisor = Divisor shifted left by N-1
For i = 0 to N-1:
    Remainder = Remainder - Divisor
    If Remainder >= 0: Qbit = 1
    Else: Qbit = 0, Remainder = Remainder + Divisor (restore)
    Shift Divisor right by 1 bit
```

**Example**: 7 / 3 (4-bit)

```
Initial: R=0111, D=0011_0000
Step 1: R-D=negative, Q=0, restore, D>>1
Step 2: R-D=negative, Q=0, restore, D>>1
Step 3: R-D=negative, Q=0, restore, D>>1
Step 4: R-D=0001 (positive), Q=1
Result: Quotient=0010 (2), Remainder=0001 (1). 7/3=2 rem 1.
```

### Non-Restoring Division

Avoids the restore step by using the quotient bit to determine the next operation:
- If R >= 0: R = 2R - D, Qbit = 1
- If R < 0: R = 2R + D, Qbit = 0

Final correction: if R < 0, R = R + D. Eliminates one addition per iteration.

### SRT Division

Uses redundant digit set (quotient digits from {-1, 0, +1}) and a lookup table to retire multiple bits per iteration. Used in most modern CPUs. The Intel Pentium FDIV bug (1994) was caused by five missing entries in the SRT lookup table [1].

---

## Multiply-Accumulate (MAC)

```
MAC: Accumulator = Accumulator + (A x B)
```

Foundation for DSP and matrix computations. Fused multiply-add (FMA) performs multiplication and addition with one rounding step, improving accuracy (required by IEEE 754-2008).

---

## References

1. Koren, I. (2002). *Computer Arithmetic Algorithms* (2nd ed.). A K Peters/CRC Press. Chapter 3: Multiplication; Chapter 4: Division.

2. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Booth, A. D. (1951). A Signed Binary Multiplication Technique. *The Quarterly Journal of Mechanics and Applied Mathematics*, 4(2), 236-240. doi:10.1093/qjmam/4.2.236.

4. Wallace, C. S. (1964). A Suggestion for a Fast Multiplier. *IEEE Transactions on Electronic Computers*, EC-13(1), 14-17. doi:10.1109/PGEC.1964.263830.

5. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 5: Digital Building Blocks.

6. Robertson, J. E. (1958). A New Class of Digital Division Methods. *IRE Transactions on Electronic Computers*, EC-7(3), 218-222. doi:10.1109/TEC.1958.5222579.
