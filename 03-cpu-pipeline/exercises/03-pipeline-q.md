# 模块 03：CPU 流水线（CPU Pipeline）-- 练习题

## 03-pipeline-q.md：问题与练习

---

## 第 1 节：冒险识别（Hazard Identification）

### 问题 1.1

识别以下指令序列中的冒险类型：

```assembly
lw  x1, 0(x2)
add x3, x1, x4
sub x5, x1, x6
```

考虑 RAW 数据冒险（data hazard）。对于每一对依赖关系，判断转发（forwarding）能否解决它，或者是否需要插入气泡（stall）。解释原因。

### 问题 1.2

对于以下每对指令，识别所有 RAW 冒险。对于每个冒险，指出：
- 哪条指令产生值，哪条指令消费值
- 值在哪个流水线阶段变得可用（对于生产者）
- 值在哪个流水线阶段被需要（对于消费者）
- 转发能否解决它，或者是否需要插入气泡

a) `add x1, x2, x3` 后跟 `sub x4, x1, x5`
b) `lw x1, 0(x2)` 后跟 `add x4, x1, x5`
c) `lw x1, 0(x2)` 后跟 `sw x1, 0(x3)`
d) `add x1, x2, x3` 后跟 `addi x1, x1, 1`

### 问题 1.3

以下哪些指令序列包含 WAW（Write After Write）或 WAR（Write After Read）冒险？解释这些冒险在 5 级顺序 RISC 流水线中为什么会发生或不会发生。

a) `add x1, x2, x3` / `sub x1, x4, x5`
b) `lw x1, 0(x2)` / `add x3, x1, x4` / `sw x5, 0(x1)`
c) `sw x1, 0(x2)` / `add x1, x3, x4`

---

## 第 2 节：流水线执行图（Pipeline Execution Diagram）

### 问题 2.1

为以下指令序列画出**开启转发**时的流水线执行图（文本/ASCII 格式）：

```assembly
add x1, x2, x3
lw  x4, 0(x1)
add x5, x4, x6
```

展示每条指令在周期 1-9 中各阶段（IF/ID/EX/MEM/WB）的执行情况。标记哪些周期通过转发解决了数据依赖。

### 问题 2.2

现在为相同的指令序列画出**不开启转发**时的流水线执行图。需要多少个额外的气泡周期？展示周期 1-11 的执行图。

---

## 第 3 节：CPI 计算（CPI Calculation）

### 问题 3.1

给定以下冒险频率，计算 5 级流水线的 CPI：
- 20% 的指令是 load，其中 30% 导致 RAW 气泡
- 15% 的指令是分支（branch），其中 60% 被跳转，采用预测-不跳转（predict-not-taken）策略，惩罚为 2 个周期
- 5% 的结构冒险（structural hazard）导致 1 个周期的气泡

假设基础 CPI = 1.0。展示每种冒险类型的分解计算。

### 问题 3.2

现在假设我们将分支预测器改进为达到 90% 的准确率（而不是使用静态的 predict-not-taken 策略）。预测错误的惩罚仍然是 2 个周期，分支指令仍占 15%。重新计算 CPI。更好的分支预测带来了多少改进？

### 问题 3.3

根据实际基准测试运行得到的以下 CPI 分量值，确定哪个分量对性能影响最大。提出一种硬件优化方案来减少该分量：

| 分量（Component） | CPI 贡献 |
|-------------------|-----------------|
| 基础 CPI（Base CPI） | 1.00 |
| Load-使用气泡（Load-use stalls） | 0.08 |
| 分支预测错误（Branch mispredict） | 0.15 |
| 结构冒险气泡（Structural stalls） | 0.03 |
| 缓存缺失（Cache misses） | 0.40 |
| **总 CPI（Total CPI）** | **1.66** |

---

## 第 4 节：Load-Use 冒险（Load-Use Hazards）

### 问题 4.1

解释为什么即使有完整的转发机制，load-use 冒险仍然需要一个气泡。最少需要多少个气泡？为什么转发硬件无法解决这个问题？

### 问题 4.2

编译器如何减少 load-use 气泡？给出一个具体的代码示例，展示变换前后的效果。

### 问题 4.3

给定以下存在 load-use 冒险的指令序列：

```assembly
lw  x1, 0(x2)
add x3, x1, x4
or  x5, x6, x7
sub x8, x9, x10
```

a) 开启完整转发时需要多少个气泡周期？
b) 编译器能否重新排列这些指令以消除气泡？展示重排后的序列。
c) 如果 `or` 指令也依赖于 x1，重新排序还有帮助吗？

---

## 第 5 节：分支预测比较（Branch Prediction Comparison）

### 问题 5.1

比较 predict-not-taken 和 predict-taken 策略的分支惩罚。给定：
- 15% 的分支指令
- 65% 被跳转（taken）
- 预测错误的惩罚为 3 个周期

计算每种策略的平均 CPI 影响。展示计算过程。

### 问题 5.2

对于问题 5.1 中的参数，哪种策略更好，为什么？在什么跳转比例下两种策略的效果相同？

### 问题 5.3

一个更准确的分支预测器在相同条件下（15% 分支频率，3 周期预测错误惩罚）达到了 92% 的预测准确率。计算平均 CPI 影响。与问题 5.1 中的静态策略相比如何？

### 问题 5.4

解释分支目标缓冲区（Branch Target Buffer, BTB）的工作原理。对于哪种预测策略（predict-taken 或 predict-not-taken），BTB 更为重要？为什么？

---

## 第 6 节：流水线加速比分析（Pipeline Speedup Analysis）

### 问题 6.1

计算 5 级流水线相对于单周期处理器的加速比。假设：
- 单周期时钟 = 10 ns（所有指令需要 1 个周期）
- 流水线时钟 = 2.5 ns（5 级）

考虑流水线中由冒险导致的 0.2 CPI 惩罚。展示理想情况（无冒险）和实际加速比。

### 问题 6.2

N 级流水线相对于单周期处理器的最大理论加速比是多少？为什么这个最大值在实践中永远无法达到？列出至少三个原因。

### 问题 6.3

一个 10 级流水线的参数如下：
- 单周期时钟 = 12 ns
- 流水线时钟 = 1.5 ns
- 实际 CPI = 1.4（包含所有冒险影响）

计算：
a) 理想加速比（无冒险，10 级）
b) 实际加速比
c) 实际流水线达到了理想性能的百分之多少？

### 问题 6.4

给定同一 ISA 的两种流水线设计：
- **设计 A：** 5 级，2.5 ns 时钟，CPI = 1.1
- **设计 B：** 10 级，1.5 ns 时钟，CPI = 1.4

哪种设计的吞吐量更高（每秒指令数）？展示计算过程。

---

## 答题指南（Answer Guidelines）

- 对于冒险识别问题（第 1 节），明确说明冒险类型并解释涉及的流水线阶段
- 对于流水线图问题（第 2 节），使用表格格式，以周期为列、阶段为行。将气泡标记为"BUBBLE"，将转发标记为"FWD: EX->EX"或"FWD: MEM->EX"
- 对于 CPI 计算（第 3 节），在求和之前展示分解的每一项
- 对于加速比问题（第 6 节），展示公式：Speedup = (Execution Time_single) / (Execution Time_pipeline) = (CPI_single * T_single) / (CPI_pipeline * T_pipeline)

---

## 参考文献（References）

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. 第 4 章。
2. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 第 6 版. Morgan Kaufmann, 2019. 第 3 章。
3. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. 第 6、7 章。
4. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 135--148.
