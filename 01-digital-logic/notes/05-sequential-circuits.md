# Sequential Circuits

Unlike combinational circuits, sequential circuits have **state** -- their output depends on both current inputs and the history of past inputs. This state is stored in memory elements called flip-flops and latches. Sequential circuits are the foundation of registers, counters, and all synchronous digital systems [1,2].

---

## The SR Latch

The SR (Set-Reset) latch is the simplest sequential element. It stores one bit.

### NOR-Based SR Latch

```
Truth Table:
S  R | Q  Q'  | State
-----|--------|--------------
0  0 | Q  Q'  | Hold (latched)
0  1 | 0   1  | Reset
1  0 | 1   0  | Set
1  1 | 0   0  | Forbidden (invalid)
```

**Operation**:
- S=1, R=0: Q goes to 1 (Set). Feedback keeps Q=1 after S returns to 0.
- S=0, R=1: Q goes to 0 (Reset). Feedback keeps Q=0 after R returns to 0.
- S=0, R=0: Latch holds its previous value (memory state).
- S=1, R=1: Both outputs go to 0, violating Q != Q'. Forbidden.

### NAND-Based SR Latch

Active-low inputs (S' and R'). S'=0,R'=1 sets; S'=1,R'=0 resets; S'=R'=1 holds; S'=R'=0 is forbidden.

---

## D Latch (Level-Triggered)

The D latch eliminates the SR latch's forbidden state with a data input (D) and an enable (EN).

```
EN  D | Q    Q'
------|---------
0   x | Q    Q'   (hold, latch is opaque)
1   0 | 0    1    (transparent, Q follows D)
1   1 | 1    0    (transparent)
```

When EN=1, the latch is **transparent**: Q follows D. When EN=0, opaque: Q holds its last value.

---

## D Flip-Flop (Edge-Triggered)

A D flip-flop samples the D input only at the **edge** of the clock signal (rising or falling), holding the value for the rest of the clock cycle.

```
Truth Table (rising edge triggered):
CLK  D | Q    Q'
--------|---------
  /   0 | 0    1
  /   1 | 1    0
 not / | Q    Q'   (hold)
```

### Edge-Triggered vs. Level-Triggered

| Feature | Level-Triggered (Latch) | Edge-Triggered (Flip-Flop) |
|---------|------------------------|----------------------------|
| Sampling | Active while clock high | Only at clock edge |
| Transparency | Transparent when enabled | Never transparent |
| Hazard sensitivity | Higher | Lower |

### Master-Slave Construction

Two back-to-back D latches: master is transparent when CLK=0, slave when CLK=1. When CLK rises, master freezes and slave copies the frozen value to Q, producing edge-triggered behavior.

---

## Registers

A register is an array of D flip-flops sharing a common clock, storing an N-bit value.

### Register with Write Enable

Each bit feeds its current Q and new D into a 2-to-1 MUX controlled by WE. When WE=1, new data is loaded on the clock edge. When WE=0, the current value is re-latched.

---

## Counters

### Ripple Counter (Asynchronous)

Each flip-flop toggles its next stage. Simple but slow: MSB toggles after N x t_FF delay.

### Synchronous Counter

All flip-flops share the same clock. Each toggle enable is the AND of all lower bits:

```
EN0 = 1, EN1 = Q0, EN2 = Q0.Q1, EN3 = Q0.Q1.Q2
```

### Up/Down Counter

A control input selects direction: UP=1 counts up (count+1), UP=0 counts down (count-1).

---

## Clock Signal and Timing Parameters

```
CLK:  __    __    __    __    __
      | |  | |  | |  | |  | |
     _| |__| |__| |__| |__| |__
     |<->| period = T
```

| Parameter | Definition |
|-----------|-----------|
| T (period) | Time between rising edges |
| f (frequency) | 1/T |
| Duty cycle | Percentage of period clock is high |

### Setup and Hold Timing [3]

```
          Clock edge
                |
           _____|_____
CLK  _____|           |_________

D    ==========X===============
          |<->|  |<->
          tsu  thold
```

- **Setup time (t_su)**: Data must be stable **before** the clock edge. Violation may cause metastability.
- **Hold time (t_hold)**: Data must remain stable **after** the clock edge.

### Maximum Clock Frequency

```
T_min > t_clk-to-Q + t_comb_max + t_su + t_skew_margin
```

### Metastability

If D changes too close to the clock edge, the flip-flop may enter a metastable state (neither 0 nor 1, but intermediate). Resolution time is unbounded. Synchronizers (cascaded flip-flops) reduce metastability probability [3].

---

## References

1. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 5: Synchronous Sequential Logic.

2. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 3: Sequential Logic Design.

4. Weste, N. H. E., & Harris, D. (2010). *CMOS VLSI Design: A Circuits and Systems Perspective* (4th ed.). Addison-Wesley. Chapter 10: Timing Analysis.

5. Rabaey, J. M., Chandrakasan, A., & Nikolic, B. (2003). *Digital Integrated Circuits: A Design Perspective* (2nd ed.). Prentice Hall. Chapter 7: Sequential Logic Circuits.
