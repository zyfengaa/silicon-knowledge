# 05 — 流水线性能

> 流水线的性能受多个因素共同影响：理想 CPI、数据停顿、控制停顿以及流水线深度带来的物理限制。

---

## 1. 流水线 CPI 公式

### 1.1 分层 CPI 模型

流水线 CPU 的平均 CPI 可以分解为三个组成部分：

```
CPI = CPI_ideal + CPI_data_stall + CPI_control_stall
```

其中：

- **CPI_ideal**: 理想流水线的 CPI = 1.0（每周期完成一条指令）
- **CPI_data_stall**: 数据冒险导致的额外 CPI
- **CPI_control_stall**: 控制冒险（主要是分支预测错误）导致的额外 CPI

如果流水线中还有其他停顿（如结构冒险、cache miss），也可以继续加：

```
CPI = CPI_ideal + CPI_struct + CPI_data + CPI_control + CPI_mem
```

### 1.2 各部分详细计算

#### 数据停顿（Data Stall CPI）

数据停顿来自 load-use 冒险（转发无法解决的 RAW 依赖）：

```
CPI_data_stall = P(load) × P(load_use) × stall_cycles_per_load_use

P(load)       = lw 指令在全部指令中的比例（约 15-25%）
P(load_use)   = lw 指令的下一条使用其结果的概率（约 20-30%）
stall_cycles  = 每次 load-use 停顿周期数（5 级流水线中 = 1）
```

**示例**：
```
CPI_data_stall = 0.20 × 0.25 × 1 = 0.05
```

#### 控制停顿（Control Stall CPI）

控制停顿来自分支预测错误：

```
CPI_control_stall = P(branch) × P(mispredict) × penalty_per_mispredict

P(branch)          = 分支指令在全部指令中的比例（约 15-20%）
P(mispredict)      = 分支预测错误率（1 - 预测准确率）
penalty_per_mispredict = 每次预测错误需要停顿的时钟周期数
```

**示例（静态预测，准确率 70%，分支比例 17%）**：
```
CPI_control_stall = 0.17 × 0.30 × 2 = 0.102
```

#### 结构停顿（Structural Stall CPI）

在分离 I-cache 和 D-cache 的设计中，结构冒险很少出现。但如果存储器资源受限：
```
CPI_struct_stall = P(struct_conflict) × stall_cycles
```

通常情况下 CPI_struct_stall ≈ 0。

### 1.3 综合示例

假设：
- 20% lw、17% 分支、5% sw，其余 ALU 指令
- 25% 的 lw 导致 load-use 停顿（1 周期）
- 2 位动态分支预测，准确率 91%，错误代价 2 周期
- 无结构冒险

```
CPI_ideal          = 1.00
CPI_data_stall     = 0.20 × 0.25 × 1 = 0.05
CPI_control_stall  = 0.17 × 0.09 × 2 = 0.0306
─────────────────────────────────────────
CPI_total          = 1.0806
```

这意味着流水线 CPU 的实际性能比理想情况慢约 8%。

---

## 2. 流水线深度与性能权衡

### 2.1 更深流水线的动机

将 5 级流水线增加到更深（如 10 级、15 级、甚至 30 级）的主要动机：

1. **更高的时钟频率**: 每个逻辑段的延迟更短，允许更快的时钟
2. **更高的吞吐量潜力**: 更多指令同时处于执行状态

Intel 的 Pentium 4（NetBurst 架构）的流水线深度达到 20-31 级，时钟频率突破 3 GHz。

### 2.2 深度增加的代价

流水线并非越深越好，有多个抵消因素：

#### 2.2.1 寄存器开销

每增加一级流水线就需要增加一组寄存器。寄存器有固定的建立时间（setup time）和传播延迟（propagation delay）。

设：
- t_logic: 每个流水线段的逻辑延迟
- t_reg: 寄存器延迟（建立时间 + 传播延迟）
- N: 流水线级数

时钟周期 = max(t_logic_i) + t_reg （假设各段平衡）

随着 N 增大，t_logic 减小，但 t_reg 不变。当 t_logic 接近 t_reg 时，进一步的流水线深度收益递减。

```
示例（假设总逻辑延迟 2000ps，寄存器延迟 50ps）：
N=5:  时钟 = 2000/5 + 50 = 450ps  → 频率 = 2.22 GHz
N=10: 时钟 = 2000/10 + 50 = 250ps  → 频率 = 4.00 GHz  (加速 1.8x)
N=20: 时钟 = 2000/20 + 50 = 150ps  → 频率 = 6.67 GHz  (加速 1.67x)
N=40: 时钟 = 2000/40 + 50 = 100ps  → 频率 = 10.0 GHz  (加速 1.5x)
```

可以看到，随着深度增加，时钟频率的提升幅度在减少。

#### 2.2.2 冒险代价增加

更深流水线意味着：
- 分支代价更大（需要冲刷更多阶段）
- 转发逻辑更复杂（需要更多级转发通路）
- Load-use 冒险的停顿周期更多（load 结果可用更晚）

具体来说，分支错误代价 = N/2 - 1 左右（取决于分支条件判断的位置），而不是固定的 2。

```
不同深度下，分支预测错误的 CPI 影响（假设分支 17%，错误率 10%）：
N=5:  CPI_control = 0.17 × 0.10 × 2  = 0.034
N=10: CPI_control = 0.17 × 0.10 × 5  = 0.085
N=20: CPI_control = 0.17 × 0.10 × 10 = 0.170
```

随着深度增加，分支错误的 CPI 损失线性增长。

#### 2.2.3 功耗增加

每增加一级流水线：
- 增加一组流水线寄存器 → 面积增加
- 更多的冒险检测逻辑和转发通路 → 功耗增加
- 更高的时钟频率 → 动态功耗增加（P ∝ fV²）

```
P_total = P_base + P_registers(N) + P_hazard_logic(N) + P_clock(N)
```

### 2.3 最优流水线深度

性能可以用以下模型近似：

```
性能 ∝ N / (T_logic + N * T_reg) × 1 / (1 + CPI_stall(N))
```

其中 CPI_stall(N) 随 N 增加而增加。

通过计算可发现：最优深度通常在 N=10~15 左右（对于通用处理器），但在实际设计中还受到功耗、面积、工艺等因素的影响。

```
              性能（归一化）
              ▲
   2.0        │    •最优深度~10-15
              │      •
   1.5        │    •   •
              │   •     •
   1.0        │  •       •
              │ •         •
   0.5        │•           •
              │              •
              └──────────────────────► N
              5  10  15  20  25  30
```

> 数据来源：Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, Section 3.7

---

## 3. 性能方程回顾

处理器的性能最终由**执行时间**衡量：

```
CPU_time = Instruction_Count × CPI × Clock_Cycle_Time
```

流水线对这三大因素的影响：

| 因素 | 流水线的影响 |
|------|-------------|
| **IC** | 不变（流水线不改变指令条数） |
| **CPI** | 理想为 1，实际 >1（冒险导致） |
| **T_cycle** | 减少（深度越深，周期越短） |

流水线深度对执行时间的影响：

```
CPU_time(N) = IC × CPI(N) × T_cycle(N)
```

如果流水线太浅（N 小）：T_cycle 大，频率低。
如果流水线太深（N 大）：CPI 大（冒险代价大），T_cycle 改善有限（寄存器开销占比增加）。

---

## 4. 实际性能分析案例

### 4.1 基准程序：SPEC CPU 2006 整数程序

| 场景 | CPI | 说明 |
|------|-----|------|
| 理想流水线 | 1.00 | 无冒险 |
| + 数据冒险（有转发） | 1.05-1.10 | 负载相关停顿 |
| + 控制冒险（2 位预测） | 1.08-1.15 | 分支预测错误 |
| + cache 缺失 | 2.0-5.0 | 这是现代 CPU 的 CPI 主要影响因素！ |

> 注意：现代 CPU 的 CPI 通常在 1.0-2.0 之间（理想情况下接近 1），但 cache 缺失会使 CPI 剧增到数十甚至上百。这就是为什么模块 04 的内存层次结构如此重要。

### 4.2 比较：不同分支预测器的 CPI

```
基础条件：10 万条指令，17% 分支，20% load（25% load-use）
5 级流水线，load-use 停顿 1 周期，分支错误代价 2 周期

预测器           准确率    CPI_control    CPI_total
─────────────────────────────────────────────────────
理想                100%       0.000         1.050
完美 2 位动态       93%        0.024         1.074
一般 2 位动态       90%        0.034         1.084
1 位动态            85%        0.051         1.101
静态-不跳转         70%        0.102         1.152
无预测（总是停顿）   0%        0.340         1.390

CPI_ideal = 1.00
CPI_data = 0.20 × 0.25 × 1.0 = 0.050 (各场景相同)
```

---

## 5. Amdahl 定律与流水线

Amdahl 定律指出：系统加速比受限于无法加速的部分。

在流水线中，可以将关键路径分段实现加速，但流水线寄存器开销和冒险是"无法加速"的部分。

```
Speedup_max = 1 / (f_unpipelined + (1-f_unpipelined)/N)

f_unpipelined: 流水线中不可加速部分的比例（寄存器开销）
```

当 N → ∞，Speedup_max → 1 / f_unpipelined。

这解释了为什么流水线深度不能无限增加——物理开销限制了最终收益。

---

## 6. 实践：理解真实处理器的流水线

| 处理器 | 年份 | 流水线深度 | 最高频率 | 特点 |
|--------|------|-----------|---------|------|
| RISC V 5 级 | 教学 | 5 | — | 经典教学模型 |
| MIPS R4000 | 1991 | 8 | 100 MHz | 第一个深度 RISC 流水线 |
| Intel Pentium Pro | 1995 | 10-12 | 200 MHz | 乱序执行 |
| Intel Pentium 4 | 2000 | 20 | 2.0 GHz | 极深流水线（Williamette） |
| Intel Pentium 4 (Prescott) | 2004 | 31 | 3.8 GHz | 最深流水线之一 |
| Intel Core (Nehalem) | 2008 | 14-16 | 3.3 GHz | 回归较浅流水线 |
| Apple M1 (Firestorm) | 2020 | 10+ (推测) | 3.2 GHz | 宽发射、低延迟 |
| AMD Zen 4 | 2022 | 19 | 5.7 GHz | 平衡深度与频率 |

从历史中可以观察到：Pentium 4 的极端深度流水线并未带来预期的性能提升（因分支错误代价和发热太大），随后 Intel Core 架构回调到 14-16 级。这验证了前面的分析——存在一个最优深度范围。

---

## 总结

- 流水线 CPI = CPI_ideal + CPI_data + CPI_control + CPI_struct（分层模型）
- CPI_data 主要来自 load-use 冒险（约 0.05-0.10）
- CPI_control 取决于分支预测准确率和错误代价（约 0.03-0.15）
- 更深流水线 → 更高时钟频率，但冒险代价增大、寄存器开销导致收益递减
- 最优深度通常在 10-15 级左右（设计权衡的结果）
- Amdahl 定律限制了流水线深度的最大收益

## 参考文献

- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach* 6th Edition, 第 3 章 "Pipelining: Basic and Intermediate Concepts", Section 3.7 "How Much Pipeline is Enough?"
- Patterson & Hennessy, *Computer Organization and Design RISC-V Edition*, 第 4 章 Section 4.5-4.10
- John Paul Shen, Mikko H. Lipasti, *Modern Processor Design: Fundamentals of Superscalar Processors*, 第 3-4 章
- David A. Patterson, "Latency Lags Bandwidth", Communications of the ACM 47(10), 2004 — 讨论延迟与带宽的权衡
- Intel Corporation, "Pentium 4 Processor Optimization Reference Manual", 2001 — NetBurst 微架构的官方文档
- M. Horowitz, R. Ho, K. Mai, "The Future of Wires and Scaling", Proceedings of the IEEE, 2001 — 讨论互连线延迟对流水线深度的影响
- SPEC CPU 2006 Benchmark Results, Standard Performance Evaluation Corporation (www.spec.org)
