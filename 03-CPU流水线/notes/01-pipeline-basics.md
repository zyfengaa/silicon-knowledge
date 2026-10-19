# 01 — 流水线基础

> 将一条指令的执行过程拆分为多个阶段，每个阶段由独立的硬件单元并行处理不同指令，从而在每个时钟周期完成一条（以上）指令的吞吐量。

---

## 1. 从单周期到流水线

单周期 CPU 在一个时钟周期内完成一条指令的全部操作。数据通路上的关键路径（critical path）决定了时钟周期的最短长度：

```
T_single = max(PC → IMEM → RegFile → ALU → DMEM → RegFile)
```

一条指令需要等待上一条指令完全结束后才能开始，**吞吐量 = 1 条指令 / T_single 秒**。

流水线的思路是将这个长路径切分为 N 个较短的阶段，每个阶段在一个较短的时钟周期内完成：

```
T_pipeline = T_single / N  (理想情况下)
```

每周期可以开始一条新指令，**吞吐量接近 N 条指令 / T_single 秒**。

---

## 2. RISC-V 5 级流水线

RISC-V 的整数指令可以自然地分为 5 个阶段：

| 阶段 | 名称 | 功能 |
|------|------|------|
| **IF** | Instruction Fetch | 从指令存储器取出指令，PC ← PC + 4 |
| **ID** | Instruction Decode | 译码，读取寄存器堆，生成控制信号 |
| **EX** | Execute | ALU 运算或地址计算 |
| **MEM** | Memory Access | 访存（仅 lw/sw 需要） |
| **WB** | Write Back | 将结果写回寄存器堆 |

### 流水线结构图

```
              ┌─────────────┐
              │    PC       │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
    IF ──────►│ Instruction │
              │   Memory    │
              └──────┬──────┘
                     │ 指令
              ┌──────▼──────┐
              │ IF/ID       │◄──── 流水线寄存器
              │ 寄存器      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
    ID ──────►│  Register   │
              │   File      │
              └──────┬──────┘
                     │ rs1, rs2, imm, 控制信号
              ┌──────▼──────┐
              │ ID/EX       │
              │ 寄存器      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
    EX ──────►│    ALU      │
              └──────┬──────┘
                     │ ALU 结果
              ┌──────▼──────┐
              │ EX/MEM      │
              │ 寄存器      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
    MEM ─────►│   Data      │
              │   Memory    │
              └──────┬──────┘
                     │ 读取数据 / 待写数据
              ┌──────▼──────┐
              │ MEM/WB      │
              │ 寄存器      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
    WB ──────►│  Register   │
              │   File      │
              └─────────────┘
```

每对相邻阶段之间都有**流水线寄存器**（pipeline registers），保存上一阶段的执行结果，供下一阶段在下一个时钟周期使用：

- **IF/ID**: 保存取到的指令和 PC+4
- **ID/EX**: 保存读取的寄存器值、立即数、控制信号
- **EX/MEM**: 保存 ALU 结果、分支目标地址
- **MEM/WB**: 保存访存结果或 ALU 结果、目标寄存器号

---

## 3. 流水线指令执行示例

考虑三条连续指令：

```
1: add x1, x2, x3     # x1 ← x2 + x3
2: sub x4, x5, x6     # x4 ← x5 - x6
3: lw  x7, 0(x8)      # x7 ← Mem[x8 + 0]
```

### 5 周期内的流水线状态

```
周期  │  IF    │  ID    │  EX    │  MEM   │  WB
──────┼────────┼────────┼────────┼────────┼──────
  1   │ inst1  │  —     │  —     │  —     │  —
  2   │ inst2  │ inst1  │  —     │  —     │  —
  3   │ inst3  │ inst2  │ inst1  │  —     │  —
  4   │ inst4  │ inst3  │ inst2  │ inst1  │  —
  5   │ inst5  │ inst4  │ inst3  │ inst2  │ inst1
```

- **延迟（Latency）**: 一条指令从 IF 到 WB 需要 5 个周期
- **吞吐量（Throughput）**: 从第 5 周期开始，每周期完成一条指令

---

## 4. 性能分析

### 4.1 符号定义

| 符号 | 含义 |
|------|------|
| N | 流水线级数（本模块中 N=5） |
| T_single | 单周期 CPU 的时钟周期时间 |
| T_pipe | 流水线 CPU 的时钟周期时间 |
| CPI | Cycles Per Instruction（每条指令平均周期数） |
| S | 流水线带来的加速比 |

### 4.2 理想加速比

理想情况下（无冒险），流水线 CPU：

- T_pipe ≈ T_single / N（每段的关键路径约为单周期的 1/N）
- CPI_pipe ≈ 1（每周期完成一条指令）

加速比公式：

```
Speedup = (T_single × CPI_single) / (T_pipe × CPI_pipe)
        = (T_single × 1) / ((T_single / N) × 1)
        = N
```

**理想的 5 级流水线比单周期快 5 倍。**

### 4.3 考虑停顿的实际加速比

流水线停顿（stall）会降低有效吞吐量，增加 CPI：

```
Speedup = N × (1 + Stall_cycles)^(-1)
```

其中 Stall_cycles 是每条指令平均的停顿周期数。

当 Stall_cycles = 0.5（平均每 2 条指令停顿 1 周期）时：

```
Speedup = 5 × (1 + 0.5)^(-1) = 5 × 0.667 ≈ 3.33
```

### 4.4 单周期 vs 流水线对比

| 指标 | 单周期 | 流水线（理想） | 流水线（实际） |
|------|--------|---------------|---------------|
| 时钟周期 | 长（关键路径） | 短（≈单周期/N） | 短（≈单周期/N） |
| 指令延迟 | 1 周期 | N 周期 | N + stall 周期 |
| 吞吐量 | 1 CPI | 1 CPI | >1 CPI |
| 硬件利用率 | ~20%（每周期只有一部分在工作） | ~100%（每周期所有级都在工作） | 较高 |
| 控制逻辑 | 简单 | 中等（需处理旁路/停顿） | 复杂（冒险检测+转发） |

### 4.5 关键洞察

流水线**不减少单条指令的延迟**（实际上延迟从 1 周期增加到 N 周期），而是通过**提高吞吐量**来提升整体性能。这正是"使程序运行更快"的两种途径之一：

- **降低延迟**（latency）：让一条指令更快完成
- **提高吞吐量**（throughput）：让更多指令在单位时间内完成

流水线走的是第二条路。

---

## 5. 流水线设计的其他考量

### 5.1 阶段平衡

流水线的速度受最慢阶段限制：

```
T_pipe = max(T_IF, T_ID, T_EX, T_MEM, T_WB)
```

如果 MEM 阶段需要 300ps，而其他阶段只需 200ps，时钟周期至少为 300ps，其他阶段就会有 100ps 的空闲。这就是为什么实际处理器的流水线级数往往更多（更深），以便将 MEM 这样的慢阶段进一步拆分为更小的子阶段。

### 5.2 流水线寄存器开销

每增加一个流水线阶段就需要增加一组流水线寄存器，这会带来：

- **面积开销**: 额外的触发器
- **延迟开销**: 寄存器本身的建立时间（setup time）和传播延迟（propagation delay）

因此流水线级数不能无限增加——当每个逻辑阶段的延迟小到与寄存器延迟相当时，再增加级数反而会降低性能。

### 5.3 控制信号

流水线上需要传递控制信号。在单周期 CPU 中，控制信号在 ID 阶段产生并立即生效。在流水线中，这些控制信号需要与指令一起通过流水线寄存器传递到后续阶段：

```
ID 阶段产生的控制信号：
  RegWrite ──► ID/EX ──► EX/MEM ──► MEM/WB ──► WB 阶段使用
  MemRead  ──► ID/EX ──► EX/MEM ──► MEM 阶段使用
  MemWrite ──► ID/EX ──► EX/MEM ──► MEM 阶段使用
  ALUSrc   ──► ID/EX ──► EX 阶段使用
  Branch   ──► ID/EX ──► EX/MEM ──► 决定是否跳转
```

这种设计称为**控制信号流水线化**（pipelined control），保证了每个阶段的控制信号在正确的时钟周期到达正确的硬件单元。

---

## 6. 从单周期到 5 级流水线的改造步骤

将单周期 CPU 改为流水线只需要几个步骤：

1. **识别关键路径**: 找到单周期数据通路的 5 个自然分界点
2. **插入流水线寄存器**: 在每个分界点之间插入 IF/ID、ID/EX、EX/MEM、MEM/WB
3. **分割控制信号**: 将控制信号分配到对应的流水线阶段，信号随指令一同传递
4. **处理冒险**: 添加旁路（forwarding）通路和冒险检测单元（后续笔记展开）
5. **调整 PC 更新**: PC 在 IF 阶段更新，而非等到 WB 完成

---

## 总结

- 流水线将指令执行拆分为多个阶段，每个阶段由独立的硬件并行处理
- RISC-V 5 级流水线：IF → ID → EX → MEM → WB
- 流水线寄存器保存相邻阶段之间的中间结果
- 理想加速比 = 流水线级数 N；实际加速比受停顿影响
- 流水线不减少单条指令延迟，但提高吞吐量
- 阶段平衡决定实际时钟频率；寄存器开销限制流水线最大深度

## 参考文献

- Patterson & Hennessy, *Computer Organization and Design RISC-V Edition*, 第 4 章 "The Processor", Section 4.5 "An Overview of Pipelining"
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 3 章 "Pipelining: Basic and Intermediate Concepts", Section 3.1-3.3
- John L. Hennessy, David A. Patterson, *Computer Architecture: A Quantitative Approach* 6th Edition, Section 3.2 "The Basics of Pipelining"
- David A. Patterson, *Computer Organization and Design: The Hardware/Software Interface* RISC-V Edition, Section 4.5 "A Simple Implementation of RISC-V"
- Smith & Pleszkun, "Implementation of Precise Interrupts in Pipelined Processors", ISCA 1985 (经典论文，讨论流水线寄存器与精确中断的关系)
