# 04 — 控制冒险

> 分支指令改变了程序原本的顺序执行流，而流水线在 ID/EX 阶段才能确定分支是否跳转——这就造成了"取错了指令"的问题。

---

## 1. 问题描述

### 1.1 分支指令的执行流程

以 RISC-V 的 `beq` 指令为例：

```
beq x1, x2, offset    # 若 x1 == x2，则 PC ← PC + offset
```

在流水线各阶段的行为：

| 阶段 | beq 的操作 |
|------|-----------|
| IF | 取 beq 指令 |
| ID | 译码，确定是分支指令，读取 x1、x2 |
| EX | 比较 x1 和 x2，计算目标地址（PC+offset） |
| MEM | （分支不需要访存，传递结果） |
| WB | （分支不写寄存器） |

流水线在 **EX 阶段** 才能确定是否要跳转。但在 IF 阶段已经取入了下一条指令（`beq` 之后的指令）。如果 `beq` 决定跳转，这条已经被取入的指令就不应该被执行——它是在错误路径上取的指令。

### 1.2 控制冒险的代价

```
# 程序示例
0x00: beq x1, x2, target
0x04: add x3, x4, x5      ← 在 IF 阶段已经被取入
0x08: sub x6, x7, x8
...
0x40: target: or x9,x10,x11

# 流水线执行
周期:  1       2       3       4       5       6
beq:   IF      ID      EX      MEM     WB
add:           IF      ID      —(flush)—
or:                    IF(?)...
                     ↑ EX 阶段判断跳转
                       IF 和 ID 已经取入了错误的指令
```

需要**冲刷**（flush）IF 和 ID 阶段中错误路径的指令，插入气泡。

### 1.3 分支代价

**分支代价（Branch Penalty）** = 从取分支指令到能够确定分支方向的阶段数 - 1

在我们的 5 级流水线中，分支方向在 EX 阶段确定：

```
分支代价 = 2 - 1 = 1 个气泡
（IF 阶段取入错误指令，ID 阶段也进入错误指令）
```

实际上，如果 ID 阶段提前比较分支条件（如寄存器值已准备好），分支代价可以减少：

- **EX 阶段判断**: 代价 = 2 个周期（冲掉 IF 和 ID 中的指令）
- **ID 阶段判断**: 代价 = 1 个周期（只冲掉 IF 中的指令）

许多处理器在 ID 阶段就做简单的分支条件判断（增加比较器），以降低分支代价。

---

## 2. 静态分支预测

### 2.1 预测-不跳转（Predict Not Taken）

最简单的策略：**默认不跳转**，继续取 `PC+4` 处的指令。如果分支真的不跳转，执行正确。如果分支跳转，冲刷已经取入的错误指令，将 PC 指向目标地址。

```
# 如果预测不跳转但实际跳转（beq 取跳转）：
周期:  1       2       3       4       5
beq:   IF      ID      EX      MEM     WB
inst4:         IF      ID      —flush—
                  ↑ 发现需要跳转，冲刷 ID 阶段指令

# 实际上需要从目标地址重新取指令
周期:  3       4       5       6       7
beq:   EX      MEM     WB
目标:  IF      ID      EX      MEM     WB
      （目标指令在周期 3 开始 IF，周期 6 完成）
```

**预测不跳转的总代价**：
- 预测正确（不跳转）：0 个气泡
- 预测错误（实际跳转）：2 个气泡（需要冲刷 2 个阶段）

### 2.2 预测-跳转（Predict Taken）

默认认为分支会跳转，取指令时从目标地址取。

但有一个问题：在 IF 阶段不知道目标地址（目标地址在 EX 或 ID 阶段才能计算）。因此需要**分支目标缓冲器**（Branch Target Buffer, BTB）来缓存分支指令的 PC 和对应的目标地址。

```
# 如果预测跳转且实际跳转：
周期:  1       2       3       4       5
beq:   IF      ID      EX      MEM     WB
目标:          IF      ID      EX      MEM     WB
              ✓ 在 ID 阶段从 BTB 读取目标地址
```

**预测跳转的总代价**：
- 预测正确（跳转）：0 个气泡（假设 BTB 命中）
- 预测错误（实际不跳转）：至少 1-2 个气泡（需要从 PC+4 重新取指）

### 2.3 哪种静态策略更好？

取决于分支行为：

- **条件分支大约 60-70% 是跳转的**（循环末尾的分支通常跳回循环开始，for 循环通常跳转）
- 对于向后分支（backward branch，目标地址小于当前 PC），**预测跳转**更好（如循环）
- 对于向前分支（forward branch，目标地址大于当前 PC），行为取决于程序逻辑

RISC-V 的 `bne`、`beq` 没有编码分支方向提示。一些架构（如 MIPS）有"likely"分支，提示编译器推荐的方向。

### 2.4 分支延迟槽（Branch Delay Slot）

有些处理器设计利用**分支延迟槽**来减少分支代价：

```
# 带延迟槽的分支执行
beq x1, x2, target
delay_slot_inst    ← 无论分支是否跳转，都一定要执行！
target: ...
```

在分支延迟槽中放置的指令是"免费的"——它在分支指令判定结果的同时执行，不需要被冲刷。

编译器会尝试将合适的指令移入延迟槽：

```
# 原始代码
add x1, x2, x3      # 循环结尾
beq x1, x0, loop
sub x4, x5, x6      # 分支后的指令

# 调度后（将 sub 移入延迟槽）
beq x1, x0, loop
sub x4, x5, x6      ← 延迟槽：无论分支是否跳转都执行
add x1, x2, x3      ← 原始循环结尾移到这里
```

RISC-V 的 ISA 手册明确指出 RISC-V **不要求硬件实现分支延迟槽**，也不推荐使用它。延迟槽是 MIPS、SPARC 等早期 RISC 架构的做法，在现代处理器中已经被动态分支预测取代。

---

## 3. 简单动态分支预测

### 3.1 1 位饱和计数器

最简单的动态预测：记录分支指令**上一次**的行为。

```
状态图：

        Taken
   ┌─────────────┐
   ▼             │
  N(ot Taken) ──► T(aken)
   │             ▲
   └─────────────┘
        Not Taken
```

使用一个 1 位寄存器（Branch History Table 的一个条目），初始化为"Taken"或"Not Taken"。每次分支执行后更新：

```python
if branch_is_taken:
    state = TAKEN
else:
    state = NOT_TAKEN
```

下次遇到同一条分支指令时，按当前状态预测。

**问题**：对于嵌套循环，内层循环最后的分支会"失败"两次（内层循环退出时），导致错误预测。

### 3.2 2 位饱和计数器

更稳健的方案：使用 2 位状态机，需要连续两次预测错误才会改变预测方向。

```
状态图：

                   Taken
         ┌───────────────────────┐
         ▼                       │
   ┌─────────┐     Taken    ┌─────────┐
   │ Strong  │─────────────►│ Strong  │
   │  Not    │              │  Taken  │
   │  Taken  │◄─────────────│         │
   └─────────┘   Not Taken  └─────────┘
         │                       ▲
         │    Not Taken          │
         ▼                       │
   ┌─────────┐     Taken    ┌─────────┐
   │  Weak   │─────────────►│  Weak   │
   │  Not    │              │  Taken  │
   │  Taken  │◄─────────────│         │
   └─────────┘   Not Taken  └─────────┘
         ▲                       │
         └───────────────────────┘
                    Not Taken
```

状态编码：

| 值 | 含义 | 预测方向 |
|----|------|---------|
| 00 | Strongly Not Taken | 不跳转 |
| 01 | Weakly Not Taken | 不跳转 |
| 10 | Weakly Taken | 跳转 |
| 11 | Strongly Taken | 跳转 |

更新规则：如果实际跳转，状态值 +1（最大 11）；如果实际不跳转，状态值 -1（最小 00）。

2 位计数器的优势：即使分支偶尔反转（如循环的最后一次迭代退出），仍然可以维持正确的预测方向。

### 3.3 分支历史表（Branch History Table, BHT）

硬件实现：一个小的直接映射表（如 1024 项），以分支指令 PC 的低位索引：

```
分支 PC: 0x1000 → 索引 = 0x000
分支 PC: 0x2000 → 索引 = 0x000  (冲突！)
```

冲突导致不同的分支指令共享同一个历史记录，可能降低预测准确率。可以使用更大的表或增加关联度来减少冲突。

### 3.4 动态预测的性能

| 预测器 | 预测准确率 | 说明 |
|--------|-----------|------|
| 静态（预测不跳转） | ~60-70% | 取决于程序 |
| 静态（预测跳转） | ~65-80% | 向后分支更准确 |
| 1 位预测器 | ~80-85% | 嵌套循环中表现差 |
| 2 位预测器 | ~85-93% | 工业标准方案 |
| 相关预测器（2 级） | ~93-97% | 结合全局/局部分支历史 |
| Tournament 预测器 | ~95-98% | Alpha 21264 等高性能 CPU 采用 |

> 数据来源：Hennessy & Patterson, *Computer Architecture: A Quantitative Approach* 6th Ed., Table 3.5

### 3.5 分支目标缓冲器（BTB）

动态预测不仅需要预测**是否跳转**，还需要知道**跳转到哪里**。BTB 缓存了每条分支指令的目标地址：

```
BTB 表项：
  ┌────────────┬────────────────┐
  │ 分支 PC    │ 目标 PC        │
  ├────────────┼────────────────┤
  │ 0x1000     │ 0x2000         │
  │ 0x1040     │ 0x2000         │
  │ 0x01F8     │ 0x0010         │
  └────────────┴────────────────┘
```

当 IF 阶段取到一条指令时，同时用当前的 PC 查询 BTB。如果命中且预测跳转，下一个指令取 BTB 中的目标地址。

---

## 4. 其他控制冒险

### 4.1 无条件跳转

`jal`（Jump and Link）和 `jalr`（Jump and Link Register）指令**总是跳转**，不需要预测。

```
jal ra, function    # ra ← PC+4, PC ← function
```

但仍然有代价：目标地址在 EX 阶段计算（或 ID 阶段），在此之前已经取了错误的指令。

```
周期:  1       2       3
jal:   IF      ID      EX
错误:          IF      ID(flush)
目标:                  IF
```

无条件跳转的代价通常与分支预测错误相同（1-2 个气泡），但无法通过预测来避免——除非使用 BTB 缓存目标地址。

### 4.2 间接跳转

`jalr rd, rs1, imm` 的目标地址来自寄存器，在 EX 阶段才可用（需要先读寄存器，然后加偏移）。这类跳转的目标地址更难预测，现代处理器使用**跳转目标地址预测器**（Indirect Branch Predictor）来处理。

---

## 5. 分支预测的准确率对 CPI 的影响

假设：

- 程序约 15-20% 的指令是分支
- 分支预测准确率 = P
- 预测错误代价 = 2 个周期（冲掉错误路径的 2 条指令）

```
CPI_control = 分支比例 × 错误率 × 错误代价
            = 0.20 × (1-P) × 2

P = 0.70 (静态预测):  CPI_control = 0.20 × 0.30 × 2 = 0.12
P = 0.85 (1 位动态):  CPI_control = 0.20 × 0.15 × 2 = 0.06
P = 0.90 (2 位动态):  CPI_control = 0.20 × 0.10 × 2 = 0.04
P = 0.95 (相关预测):  CPI_control = 0.20 × 0.05 × 2 = 0.02
```

提高分支预测准确率对 CPI 的改善非常显著。

---

## 总结

- 分支/跳转指令在 ID 或 EX 阶段才能确定目标地址，但 IF 阶段已取下一条指令——造成控制冒险
- **分支代价**: 预测错误的周期数（5 级流水线中通常 1-2 周期）
- **静态预测**: predict-not-taken（简单）或 predict-taken（需要 BTB）
- **分支延迟槽**: 在槽中的指令无论分支跳转与否都执行（RISC-V 不支持）
- **动态预测**: 使用分支历史表（BHT）记录分支行为，2 位饱和计数器是经典方案
- 控制冒险对 CPI 的影响取决于分支比例 × 预测错误率 × 错误代价

## 参考文献

- Patterson & Hennessy, *Computer Organization and Design RISC-V Edition*, 第 4 章 Section 4.8 "Control Hazards"
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach* 6th Edition, Section 3.5-3.6 "Reducing Branch Costs" and "Static and Dynamic Branch Prediction"
- James E. Smith, "A Study of Branch Prediction Strategies", ISCA 1981 — 最早系统研究分支预测的论文
- Tse-Yu Yeh, Yale N. Patt, "Alternative Implementations of Two-Level Adaptive Branch Prediction", ISCA 1992 — 2 级自适应预测器
- S. McFarling, "Combining Branch Predictors", WRL Technical Note TN-36, 1993 — Tournament 预测器的提出
- RISC-V Instruction Set Manual, Volume I: Unprivileged ISA, Section 2.5 "Control Transfer Instructions" — RISC-V 分支指令规范
