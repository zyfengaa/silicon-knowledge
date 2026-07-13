# Paper Note: CPU Pipeline Performance

## Paper Information

- **Textbook:** Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 4: The Processor.
- **Section Focus:** Sections 4.5--4.9 (Pipeline Hazards, Forwarding, Branch Prediction, Performance Analysis)

## Also Referenced

- **Textbook:** Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 3: Pipelining.
- **Paper:** Kuck, D. J. "A Survey of Computer Architecture." *IEEE Transactions on Computers*, Vol. C-26 No. 12, 1977, pp. 1199--1210. (Early pipeline taxonomy)
- **Paper:** Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 135--148.

## Contribution (One Sentence)

Patterson and Hennessy's systematic treatment of pipelining in *Computer Organization and Design* established the 5-stage RISC pipeline as the canonical pedagogical model, demonstrating how forwarding, hazard detection, and branch prediction together enable near-ideal CPI while quantifying the performance gap between ideal and real pipelines.

## Background: Why Pipeline Matters

Before pipelining, CPUs used either single-cycle or multi-cycle implementations:

| Implementation | Cycles per Instruction | Clock Period | Limitation |
|----------------|----------------------|--------------|------------|
| Single-cycle   | 1                    | Longest path (slowest instruction) | All instructions wait for the slowest |
| Multi-cycle    | Variable (3--5)      | Balanced, shorter | Low throughput: only one stage active at a time |
| **Pipelined**  | ~1 (ideal)           | Balanced (stage-limited) | Hazards reduce throughput |

Pipelining works by splitting instruction execution into independent stages. While one instruction is in the ALU stage, another is fetching, another is accessing memory, etc. This **overlap** is the fundamental source of performance gain.

The key insight: pipelining does not reduce the **latency** of a single instruction (it actually increases it slightly due to pipeline registers), but it dramatically improves **throughput** (instructions per cycle).

## Key Concepts

### The 5-Stage RISC Pipeline

The canonical 5-stage pipeline divides execution into:

| Stage | Name | What Happens |
|-------|------|-------------|
| IF    | Instruction Fetch | Read instruction from instruction memory; update PC |
| ID    | Instruction Decode | Read register file; decode instruction; generate control signals |
| EX    | Execute | ALU operation; effective address calculation; branch condition check |
| MEM   | Memory Access | Load/store data memory access |
| WB    | Write Back | Write result to register file |

Between each stage is a **pipeline register** (IF/ID, ID/EX, EX/MEM, MEM/WB) that holds the intermediate state. The pipeline registers are clocked registers -- they capture data at the end of one cycle and present it to the next stage at the beginning of the next cycle.

The pipeline register format grows as instructions progress:

```
IF/ID:   PC + 4, instruction word
ID/EX:   PC + 4, read data 1, read data 2, immediate, rs1, rs2, rd, control signals
EX/MEM:  PC + 4, ALU result, write data, rd, control signals (narrowing)
MEM/WB:  ALU result (or memory read data), rd, control signals (narrowing)
```

### Structural Hazards

A structural hazard occurs when two instructions need the same hardware resource at the same time. In the classic 5-stage pipeline with separate instruction and data memories (Harvard architecture), structural hazards are avoided for memory accesses. However, a unified cache (von Neumann architecture with a single memory port) would create a structural hazard when a load/store in MEM needs the same memory as an instruction fetch in IF.

**Resolution:** Stall the pipeline for one cycle, or duplicate the resource (separate I-cache and D-cache).

### Data Hazards

Data hazards occur when an instruction depends on the result of a previous instruction that has not yet completed. The classic three types:

| Hazard | Meaning | Example |
|--------|---------|---------|
| RAW (Read After Write) | Instruction reads a register before the previous one writes it | `add x1,x2,x3` / `sub x4,x1,x5` |
| WAR (Write After Read) | Instruction writes a register before the previous one reads it | Impossible in in-order pipeline |
| WAW (Write After Write) | Instruction writes a register before the previous one writes it | `add x1,...` / `sub x1,...` -- rare in 5-stage RISC |

**RAW hazards** dominate in RISC pipelines. The key insight is that the result of an ALU instruction is available at the end of EX (not WB), and a dependent instruction needs it at the start of EX. Forwarding (bypassing) routes the value directly.

### Forwarding (Bypassing)

Forwarding is a hardware technique that routes the result from a pipeline stage back to the ALU input before the result is actually written to the register file.

Forwarding paths:

| Source Stage | Destination Stage | Latency | Used For |
|-------------|-------------------|---------|----------|
| EX/MEM (ALU result) | EX input | 0 cycles (same cycle) | EX-to-EX forwarding |
| MEM/WB (ALU or load result) | EX input | 1 cycle | MEM-to-EX forwarding |

**Forwarding unit logic:** The forwarding unit compares the destination register of instructions in EX/MEM and MEM/WB with the source registers of the instruction in EX. If a match is found and the instruction writes a register, the forwarded value replaces the register file read value.

```
// Simplified forwarding logic
if (EX/MEM.RegWrite and EX/MEM.rd != 0 and EX/MEM.rd == ID/EX.rs1)
    ForwardA = 2'b10  // forward from EX/MEM
if (MEM/WB.RegWrite and MEM/WB.rd != 0 and MEM/WB.rd == ID/EX.rs1 and
    not (EX/MEM.RegWrite and EX/MEM.rd != 0 and EX/MEM.rd == ID/EX.rs1))
    ForwardA = 2'b01  // forward from MEM/WB
```

### The Load-Use Hazard Problem

Forwarding cannot fully resolve **load-use hazards** because a load instruction's data is only available at the end of MEM, but the dependent instruction needs it at the beginning of EX. The result arrives one cycle too late.

```
Cycle:      1       2       3       4       5
lw x1,0(x2): IF      ID      EX      MEM     WB
                            (data ready here)
add x3,x1,x4:         IF      ID      EX     ...
                              (needs x1 here)
                                  ^-- 1 cycle gap
```

The minimum stall for a load-use hazard is **1 cycle** (a "bubble" in the pipeline). The hardware inserts a stall by:
1. Freezing the PC (preventing IF from fetching the next instruction)
2. Inserting a bubble in the ID/EX pipeline register (setting control signals to 0)
3. Allowing the load to complete MEM while keeping the dependent instruction in ID

### Control Hazards and Branch Prediction

Control hazards arise from branches and jumps. The pipeline doesn't know the next PC until the branch outcome is computed (typically in EX for simple pipelines).

Branch penalty depends on the prediction strategy:

| Strategy | Description | Penalty (taken) | Penalty (not taken) |
|----------|-------------|-----------------|---------------------|
| Predict not taken | Assume branch not taken, fetch sequentially | 2 cycles (flush IF, ID) | 0 cycles |
| Predict taken | Assume branch taken, fetch from target | 0 cycles | 2 cycles (flush IF, ID) |

Using a **branch target buffer (BTB)** can reduce the taken penalty by predicting the target address early (in IF or ID).

### Pipeline Diagram Convention

A standard pipeline diagram shows stages progressing left-to-right across clock cycles:

```
         C1    C2    C3    C4    C5    C6    C7
lw:      IF    ID    EX    MEM   WB
add:          IF    ID    EX    MEM   WB
sub:                IF    ID    EX    MEM   WB
```

Stalls (bubbles) are shown as empty stages or explicitly marked:

```
         C1    C2    C3    C4    C5    C6    C7
lw:      IF    ID    EX    MEM   WB
add:          IF    ID    BUBBLE EX   MEM   WB
sub:                IF    IF    ID   ...   ...
                  (stall)
```

## Performance Model: CPI Analysis

### Ideal Pipeline CPI

In an ideal pipeline with no hazards, one instruction completes every cycle:

```
CPI_ideal = 1.0
Speedup_ideal = (1 cycle/inst) * (T_single / T_pipeline)
             = 1 * (T_single / (T_single / N))   -- N stages
             = N
```

An N-stage pipeline ideally provides Nx speedup over single-cycle.

### Real Pipeline CPI

Real CPI accounts for pipeline stalls:

```
CPI_real = 1.0 + CPI_structural + CPI_data + CPI_control
```

Each term is calculated as:

**Structural hazard contribution:**
```
CPI_structural = Frequency(structural_hazards) * Stall_cycles
```

**Data hazard contribution (load-use stalls in 5-stage):**
```
CPI_data = Frequency(loads) * Fraction(load_use) * Stall_cycles
```

**Control hazard contribution (branch mispredictions):**
```
CPI_branch = Frequency(branches) * Fraction(mispredicted) * Penalty_cycles
```

### Worked Example

Given:
- 22% loads, 30% of loads cause RAW (load-use), 1-cycle stall
- 15% branches, 60% taken, 2-cycle penalty (predict-not-taken)
- 5% structural hazards, 1-cycle stall each
- Base CPI = 1.0

Calculation:

```
CPI_data      = 0.22 * 0.30 * 1     = 0.066
CPI_branch    = 0.15 * 0.60 * 2     = 0.180
CPI_structural = 0.05 * 1           = 0.050
CPI_real      = 1.0 + 0.066 + 0.180 + 0.050 = 1.296
```

Performance relative to ideal pipeline: 1 / 1.296 = 77.2% of ideal throughput.

### Why Branches Dominate

In the example above, branches contribute the largest penalty (0.180 CPI, or 60.8% of total CPI penalty), despite being only 15% of instructions. This is why branch prediction is one of the most active research areas in computer architecture -- even small improvements in prediction accuracy have outsized effects on performance.

## My Reflections

### 1. Pipelining Is an Exercise in Latency Hiding

Pipelining does not make individual instructions faster. It hides the latency of one instruction behind the execution of others. This is a recurring theme in computer architecture: out-of-order execution, prefetching, multithreading, and even memory hierarchies all use latency hiding. The 5-stage pipeline is the simplest, cleanest example of this principle.

### 2. The Forwarding vs. Stalling Tradeoff

Forwarding is elegant but has physical limits. The load-use hazard shows that even with full forwarding, the fundamental pipeline depth creates a minimum latency between producing and consuming data. This is why compiler scheduling (reordering independent instructions to fill load-use gaps) is as important as the hardware forwarding logic itself. The best performance comes from hardware-software cooperation.

### 3. The Diminishing Returns of Deeper Pipelines

The 5-stage pipeline is pedagogically convenient, but commercial processors have moved to much deeper pipelines (14--20 stages in high-performance x86). Deeper pipelines allow faster clock frequencies but increase branch penalties (more stages to flush on misprediction) and create more forwarding paths. There is an optimal pipeline depth for a given technology and workload, and finding it is a central engineering challenge.

### 4. Branch Prediction Is the Hard Problem

Control hazards are the most damaging in real pipelines because (a) branches are frequent (15--25% of instructions), (b) prediction is inherently imperfect, and (c) deeper pipelines amplify the penalty. Modern processors spend significant die area on sophisticated branch predictors (two-level adaptive predictors, neural predictors, tournament predictors) -- a testament to how critical this problem is.

### 5. The Quantitative Approach in Action

The CPI model is the signature contribution of Patterson and Hennessy's quantitative approach. It decomposes performance into measurable components, each tied to specific pipeline features. This lets architects make design decisions (add more forwarding? better branch prediction? deeper pipeline?) based on data, not intuition. The "iron law" (Time/Program = Instructions * CPI * Clock) remains the fundamental performance equation.

---

## References

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 4.
2. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 3.
3. Kuck, D. J. "A Survey of Computer Architecture." *IEEE Transactions on Computers*, Vol. C-26 No. 12, 1977, pp. 1199--1210.
4. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 135--148.
5. Patterson, D. A. "RISC-I: A Reduced Instruction Set VLSI Computer." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 443--457.
6. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapters 6, 7.
7. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213.
