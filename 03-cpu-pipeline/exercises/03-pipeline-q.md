# Module 03: CPU Pipeline -- Exercises

## 03-pipeline-q.md: Questions and Problems

---

## Section 1: Hazard Identification

### Question 1.1

Identify the hazard type in this instruction sequence:

```assembly
lw  x1, 0(x2)
add x3, x1, x4
sub x5, x1, x6
```

Consider RAW data hazards. For each dependent pair, identify whether forwarding can resolve it, or if a stall is needed. Explain why.

### Question 1.2

For each of the following instruction pairs, identify all RAW hazards. For each hazard, state:
- Which instruction produces the value and which consumes it
- Which pipeline stage the value becomes available (for the producer)
- Which pipeline stage the value is needed (for the consumer)
- Whether forwarding can resolve it, or whether a stall is needed

a) `add x1, x2, x3` followed by `sub x4, x1, x5`
b) `lw x1, 0(x2)` followed by `add x4, x1, x5`
c) `lw x1, 0(x2)` followed by `sw x1, 0(x3)`
d) `add x1, x2, x3` followed by `addi x1, x1, 1`

### Question 1.3

Which of the following instruction sequences contain WAW (Write After Write) or WAR (Write After Read) hazards? Explain why these hazards do or do not occur in the 5-stage in-order RISC pipeline.

a) `add x1, x2, x3` / `sub x1, x4, x5`
b) `lw x1, 0(x2)` / `add x3, x1, x4` / `sw x5, 0(x1)`
c) `sw x1, 0(x2)` / `add x1, x3, x4`

---

## Section 2: Pipeline Execution Diagram

### Question 2.1

Draw a pipeline execution diagram (in text/ASCII form) for this instruction sequence WITH forwarding enabled:

```assembly
add x1, x2, x3
lw  x4, 0(x1)
add x5, x4, x6
```

Show each instruction's IF/ID/EX/MEM/WB stages cycle-by-cycle for cycles 1--9. Mark which cycles forwarding resolves the data dependencies.

### Question 2.2

Now draw the pipeline execution diagram for the same instruction sequence WITHOUT forwarding. How many additional stall cycles are needed? Show the diagram for cycles 1--11.

---

## Section 3: CPI Calculation

### Question 3.1

Calculate the CPI for a 5-stage pipeline given these hazard frequencies:
- 20% loads, of which 30% cause RAW stalls
- 15% branches, of which 60% are taken, with a 2-cycle penalty (predict-not-taken strategy)
- 5% structural hazards causing 1-cycle stalls

Assume base CPI = 1.0. Show the breakdown for each hazard type.

### Question 3.2

Now suppose we improve the branch predictor to achieve 90% accuracy (instead of using a static predict-not-taken strategy). The misprediction penalty is still 2 cycles, and branches are still 15% of instructions. Recalculate the CPI. How much improvement does better branch prediction provide?

### Question 3.3

Given these CPI component values from an actual benchmark run, identify which component has the largest impact on performance. Propose a hardware optimization to reduce that component:

| Component         | CPI Contribution |
|-------------------|-----------------|
| Base CPI          | 1.00            |
| Load-use stalls   | 0.08            |
| Branch mispredict | 0.15            |
| Structural stalls | 0.03            |
| Cache misses      | 0.40            |
| **Total CPI**     | **1.66**        |

---

## Section 4: Load-Use Hazards

### Question 4.1

Explain why load-use hazards require a stall even with full forwarding. What is the minimum stall? Why can't forwarding hardware resolve this?

### Question 4.2

How does a compiler reduce load-use stalls? Give a concrete code example showing the transformation.

### Question 4.3

Given the following instruction sequence with a load-use hazard:

```assembly
lw  x1, 0(x2)
add x3, x1, x4
or  x5, x6, x7
sub x8, x9, x10
```

a) How many stall cycles are needed with full forwarding?
b) Can the compiler reorder these instructions to eliminate the stall? Show the reordered sequence.
c) What if the `or` instruction also depended on x1? Would reordering still help?

---

## Section 5: Branch Prediction Comparison

### Question 5.1

Compare branch penalty for predict-not-taken vs. predict-taken strategies. Given:
- 15% branches
- 65% taken
- 3-cycle penalty for misprediction

Calculate the average CPI impact for each strategy. Show your work.

### Question 5.2

Which strategy is better for the parameters in Question 5.1, and why? At what taken fraction would the two strategies be equal?

### Question 5.3

A more accurate branch predictor achieves 92% prediction accuracy with the same 15% branch frequency and 3-cycle misprediction penalty. Calculate the average CPI impact. How does this compare to the static strategies from Question 5.1?

### Question 5.4

Explain how a Branch Target Buffer (BTB) works. For which prediction strategy (predict-taken or predict-not-taken) is a BTB more important? Why?

---

## Section 6: Pipeline Speedup Analysis

### Question 6.1

Calculate the speedup of a 5-stage pipeline over a single-cycle processor. Assume:
- Single-cycle clock = 10 ns (all instructions take 1 cycle)
- Pipeline clock = 2.5 ns (5 stages)

Include the effect of 0.2 CPI penalty from hazards in the pipeline. Show both ideal (no hazards) and real speedup.

### Question 6.2

What is the maximum theoretical speedup of an N-stage pipeline over a single-cycle processor? Why is this maximum never achieved in practice? List at least three reasons.

### Question 6.3

A 10-stage pipeline has these parameters:
- Single-cycle clock = 12 ns
- Pipeline clock = 1.5 ns
- Real CPI = 1.4 (includes all hazard effects)

Calculate:
a) Ideal speedup (no hazards, 10-stage)
b) Real speedup
c) What fraction of ideal performance does the real pipeline achieve?

### Question 6.4

Given two pipeline designs for the same ISA:
- **Design A:** 5-stage, 2.5 ns clock, CPI = 1.1
- **Design B:** 10-stage, 1.5 ns clock, CPI = 1.4

Which design has higher throughput (instructions per second)? Show your calculation.

---

## Answer Guidelines

- For hazard identification questions (Section 1), state the hazard type clearly and explain the pipeline stages involved
- For pipeline diagram questions (Section 2), use a table format with cycles as columns and stages as rows. Mark bubbles as "BUBBLE" and forwarding as "FWD: EX->EX" or "FWD: MEM->EX"
- For CPI calculations (Section 3), show each term of the breakdown before summing
- For speedup questions (Section 6), show the formula: Speedup = (Execution Time_single) / (Execution Time_pipeline) = (CPI_single * T_single) / (CPI_pipeline * T_pipeline)

---

## References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 4.
2. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 3.
3. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapters 6, 7.
4. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 135--148.
