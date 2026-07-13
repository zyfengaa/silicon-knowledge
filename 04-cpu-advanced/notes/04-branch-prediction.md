# 04 — 分支预测（Branch Prediction）

## 概述

分支指令在典型的通用程序中每 5 ~ 10 条指令出现一次。没有分支预测，每遇到一条分支就需要停顿等待分支结果。

**目标**：在分支条件被计算出之前，预测分支方向和目标地址，使处理器能持续取指。

## 分支预测的准确率要求

```
性能损失 = 分支密度 × 误预测率 × 误预测代价
```

假设：20 级流水线、4-wide、分支密度 15%：
- 误预测率 5% → 性能损失约 60%
- 误预测率 2% → 性能损失约 24%
- 误预测率 1% → 性能损失约 12%

现代高性能 CPU 的分支预测准确率已达 **97% ~ 99.5%+**。

## 分支预测类型

### 静态预测（Static Prediction）

编译时决定，不需要硬件状态：

- **Always Taken（总是跳转）**：预测所有条件分支都被跳转。准确率约 60% ~ 70%。
- **Always Not-Taken（总是不跳转）**：预测所有条件分支都不跳转。准确率约 30% ~ 40%。
- **Backward Taken, Forward Not-Taken（BTFN）**：向后分支预测跳转（循环），向前分支预测不跳转。准确率约 70% ~ 80%。

### 动态预测（Dynamic Prediction）

硬件利用分支的历史行为进行预测，预测结果随程序行为动态变化。

## 1. 1-bit 预测器 / 2-bit 饱和计数器

### 1-bit 预测器

记录上一次分支结果，下一次预测相同。

问题：**嵌套循环**的末尾总是预测错误两次（退出时一次，重新进入时一次）。

示例：
```
for (i = 0; i < 10; i++)    // 内层循环 10 次
    for (j = 0; j < 10; j++);  // 每次进入需要重新学习
```

最内层的分支模式：`TTTTTTTTTT N TTTTTTTTTT N ...`
- 每次退出（N）预测错误一次
- 每次重新进入（T）再错误一次

### 2-bit 饱和计数器

**状态机**：四个状态组成有限状态自动机（FSM）。

```
        (Not-Taken)          (Taken)
          ┌─────┐             ┌─────┐
          │  00  │ ←──────── │  01  │
          │Strong│ (Not-Taken)│ Weak │
          │ N-T  │ ─────────→│ N-T  │
          └──┬──┘             └──┬──┘
     Taken │               │ Taken
           ▼                 ▼
          ┌─────┐             ┌─────┐
          │  10  │ ←──────── │  11  │
          │ Weak │ (Not-Taken)│Strong│
          │ Taken│ ─────────→│Taken │
          └─────┘             └─────┘
```

- **状态**：00（强不跳）、01（弱不跳）、10（弱跳）、11（强跳）
- **预测**：11/10 → 预测跳转；01/00 → 预测不跳转
- **更新**：遇到跳转 +1（饱和 11），遇到不跳转 -1（饱和 00）
- **优点**：对单次异常分支不敏感。比如 `TTTTTNTTTT` → 只在 N 时从 11 变为 10，下一次仍预测 T。

**何时会误预测？**
- 分支模式变化频繁（如交替 `TNTNTN`）
- 分支模式周期 > 2（无法捕获更长的规律）

**准确率**：约 80% ~ 90%（取决于程序分支行为）。

## 2. 两级自适应预测器（Two-Level Adaptive Predictor）

### 基本思想

利用分支的**历史模式**来进行预测。例如，一个分支的模式是 `TTTNT TTNT`，那么看到 `TTN` 后很可能是 `T`。

### 结构

由两部分组成：

1. **分支历史寄存器（BHR, Branch History Register）**：移位寄存器，记录最近 k 条分支的结果（T/N）
2. **模式历史表（PHT, Pattern History Table）**：以 BHR 的值作为索引，每个表项是一个 2-bit 饱和计数器

```
BHR (4-bit): T T N T (1101)
                    ↓ (index into PHT)
PHT[1101] → 2-bit counter → 预测
```

### YAGS / GShare / GSelect 变体

| 名称 | 索引方式 | 特点 |
|------|---------|------|
| GShare | BHR ⊕ PC | XOR 组合历史与地址，减少别名冲突 |
| GSelect | (BHR, PC) 拼接 | 简单拼接，需要更大的表 |
| YAGS | 使用两个表减少冲突 | 对别名冲突更有弹性的设计 |
| Bi-mode | 跳转/不跳转分开预测 | 减少干扰 |

**准确率**：约 92% ~ 96%。

## 3. TAGE 预测器（Tagged Geometric History LengTH）

### 背景

两级预测器使用固定长度的历史，但不同分支需要不同长度的历史：
- 循环分支：短历史足够（如 4-bit）
- 嵌套控制流：需要更长历史

### TAGE 的核心设计

TAGE 由 Seznec 等人提出，是现代分支预测器的事实标准。

**结构**：
- 一个基础预测器（**T0**）：无历史，仅使用 PC 索引的 2-bit 计数器
- 多个标记预测表（**T1 ~ Tn**）：使用不同长度（几何级数）的历史

| 组件 | 历史长度 | 索引公式 |
|------|---------|---------|
| T0 | 0 | PC |
| T1 | 4 | PC ⊕ H4 |
| T2 | 8 | PC ⊕ H8 |
| T3 | 16 | PC ⊕ H16 |
| T4 | 32 | PC ⊕ H32 |
| ... | 几何增长 | ... |

**预测决策**：
1. 在所有表中找到最长历史且**标记（tag）匹配**的表项
2. 使用该表项的 3-bit 或 4-bit 计数器进行预测
3. 如果多个表都命中标记，选历史最长的
4. 如果没有表命中，使用基础预测器 T0

**更新策略**：
- 预测正确：更新命中最长表的计数器
- 预测错误：更新命中最长表的计数器 + 尝试在更高阶表中分配新条目

### TAGE 的变体

| 变体 | 改进 |
|------|------|
| TAGE-SC | 加入**统计修正（Statistical Corrector）** 处理 TAGE 预测较弱的边界情况 |
| TAGE-SC-L | 加入**循环预测器（Loop predictor）** 专门处理长循环 |
| 6-TAGE | Google 的改进，用于 TPU 等芯片 |

**准确率**：97% ~ 99.5%+（TAGE-SC-L 在 CBP 竞赛中表现最佳）。

## 4. BTB（Branch Target Buffer）

预测分支方向只是第一步，处理器还需要知道**跳转的目标地址**。

**BTB 结构**：一个小型缓存，以分支指令地址为索引，保存目标地址和预测信息。

```
BTB 条目 = { PC_tag, target_address, prediction_bits, branch_type }
```

| 概念 | 说明 |
|------|------|
| BTB Hit | 当前取指地址在 BTB 中找到 → 预测方向+目标 |
| BTB Miss | BTB 中没有该分支的信息 → 使用静态预测或简单的方向预测 |
| BTB 容量 | 通常为 512 ~ 4096 条目 |

### 间接分支预测

间接跳转（如 `JMP *%rax`）的目标可能是任何地址。现代 CPU 使用**ITBTB（Indirect Target BTB）** 或 **IDT（Indirect Diff Target）** 来预测。

## 5. 返回地址栈（Return Address Stack, RAS）

函数调用 `CALL` 和返回 `RET` 是一类特殊的分支。

- `CALL` → 跳转并保存返回地址
- `RET` → 从栈中弹出返回地址

**问题**：BTB 对 `RET` 预测效果不好，因为不同调用点的 `RET` 指令地址相同。

**RAS 解决方案**：一个类似栈的硬件结构，模仿调用栈的行为。

```
CALL func1 → RAS.push(PC+4)    // 保存返回地址
CALL func2 → RAS.push(PC+4)    // 嵌套调用
RET         → addr = RAS.pop()  // 精准返回 func1 之后
RET         → addr = RAS.pop()  // 精准返回主程序
```

- RAS 深度通常为 16 ~ 32
- RAS 的准确率 ≈ 99.9%+（仅当调用/返回栈不匹配时出错，如 `longjmp`）

## 预测器准确率对比

| 预测器类型 | 典型准确率 | 硬件开销 | 说明 |
|-----------|-----------|---------|------|
| Always Not-Taken | ~40% | 无 | 最基础的"预测" |
| Always Taken | ~65% | 无 | 对向后分支效果好 |
| 1-bit 动态 | ~80% | ~1 位/分支 | 历史敏感但适应性差 |
| 2-bit 饱和 | ~88% | ~2 位/分支 | 对噪声不敏感 |
| 两级（GShare） | ~94% | ~4KB ~ 16KB | 捕获模式 |
| 混合预测器（ Tournament） | ~96% | ~32KB | 组合多种预测器 |
| TAGE | ~97.5% | ~8KB ~ 64KB | 多表、不同历史长度 |
| TAGE-SC-L | ~98.5%+ | ~64KB ~ 256KB | 带统计修正和循环预测 |
| 神经网络预测器 | ~99%+ | 很大（>1MB） | 实际部署极少 |

## 现代 CPU 的分支预测配置

| CPU | 预测器类型 | BTB 条目 | RAS 深度 | 误预测代价 |
|-----|-----------|---------|---------|-----------|
| Intel Core i7-6700 (Skylake) | 两级+TAGE 混合 | 4096 | 16 | ~17 周期 |
| Intel Golden Cove (12th gen) | 改进型 TAGE + ITTAGE | ~5000+ | 24 | ~20 周期 |
| AMD Zen 3/4 | TAGE-like + 神经网络辅助 | 8192 | 32 | ~14 周期 |
| Apple M1 Firestorm | 专有 TAGE + 回环预测 | ~5000+ | 32+ | ~12~15 周期 |
| ARM Cortex-X2 | TAGE-like (分支预测宽) | ~4000+ | 24 | ~15 周期 |

## 关键概念总结

- **2-bit 饱和计数器**：最基本的状态机预测器
- **两级自适应预测器**：利用分支历史模式
- **TAGE**：多表几何历史长度，现代黄金标准
- **BTB**：预测分支目标地址
- **RAS**：精准预测函数返回

## 思考题

1. 为什么 TAGE 的表中使用不同历史长度（几何增长）而不是等长？
2. 对于交替模式 `TNTNTNTN`，2-bit 饱和计数器和两级预测器哪个表现更好？为什么？
3. 间接分支（如虚函数调用、switch-case）为什么比直接条件分支更难预测？
4. 为什么现代预测器要达到 >97% 准确率才足够？如果有 5% 的误预测率会怎样？

## 参考文献

- Seznec, A. "TAGE-SC-L Branch Predictors." *Journal of Instruction-Level Parallelism (JILP)*, Vol. 16, 2014.
- Seznec, A. & Michaud, P. "A Case for (Partially) Tagged Geometric History Length Branch Prediction." *JILP*, 2006.
- Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*, 6th Edition, Chapter 3: Instruction-Level Parallelism and Its Exploitation.
- Yeh, T. Y. & Patt, Y. N. "Alternative Implementations of Two-Level Adaptive Branch Prediction." *ISCA*, 1992.
- McFarling, S. "Combining Branch Predictors." *WRL Technical Note TN-36*, 1993.
- Jimenez, D. A. & Lin, C. "Dynamic Branch Prediction with Perceptrons." *HPCA*, 2001.
