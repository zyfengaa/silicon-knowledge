# 03 — 数据冒险

> 数据冒险是流水线中最常见、影响最直接的冒险类型。核心是解决"一条指令需要另一个指令的结果，而结果还没写好"的问题。

---

## 1. 数据依赖类型

### 1.1 三种数据依赖

前面提到数据冒险有三种类型，但实际在按序 5 级流水线中只有 RAW 是真正的冒险：

| 依赖 | 含义 | 在 5 级流水线中 |
|------|------|----------------|
| **RAW** | 读后写：指令 j 读一个由指令 i 写入的寄存器 | **需要处理** |
| **WAR** | 写后读：指令 j 写一个指令 i 将要读的寄存器 | 不会出现（？？？说明见下方） |
| **WAW** | 写后写：指令 j 和指令 i 写同一个寄存器 | 不会出现（？） |

**为什么 WAR 和 WAW 在按序流水线中不影响？**

- **WAR**: 寄存器读发生在 ID 阶段（较早），写发生在 WB 阶段（较晚）。因此指令 i 读寄存器一定在指令 j（后续指令）写寄存器之前完成。即使有数据依赖，读在写之前，不会出错。
- **WAW**: 在按序流水线中，两条指令按程序顺序写回。后续指令的写必然晚于前一条指令的写，结果总是正确的。

> 在乱序执行（out-of-order）处理器中，WAR 和 WAW 成为真正的问题，需要**寄存器重命名**（register renaming）来解决。乱序执行超出了本模块范围。

### 1.2 RAW 冒险的检测条件

给定指令 A（前一条）和指令 B（后一条），满足以下任一条件即存在 RAW 冒险：

1. **EX 冒险**: A 的目标寄存器 = B 的源寄存器 1 **且** A 要写寄存器（RegWrite=1）
2. **EX 冒险**: A 的目标寄存器 = B 的源寄存器 2 **且** A 要写寄存器
3. **MEM 冒险**: A 的目标寄存器 = B 的源寄存器 1 **且** A 要写寄存器（情况同 1，但 A 在 MEM 阶段）
4. **MEM 冒险**: A 的目标寄存器 = B 的源寄存器 2 **且** A 要写寄存器

---

## 2. 转发（Forwarding / Bypassing）

### 2.1 基本思想

RAW 冒险的根源在于：EX 阶段需要的源操作数在寄存器堆中还没有更新（前一条指令还在流水线中尚未写回），但该数据实际上已经在流水线的某个位置**可用**了——可能是 EX 阶段的 ALU 输出端，或是 MEM 阶段从存储器读出的数据。

转发的思路是：不等待写回寄存器堆，而是直接从流水线的中间结果中**偷**数据，送到需要它的 ALU 输入端。

### 2.2 转发通路

```
           ┌──────────────────────────────────┐
           │            Forwarding            │
           │             Unit                 │
           └────┬──────────┬──────────┬───────┘
                │          │          │
                │    ┌─────▼──────┐   │
                │    │  ID/EX     │   │
                │    │  寄存器    │   │
                │    └─────┬──────┘   │
                │          │          │
           ┌────▼──┐  ┌───▼────┐  ┌──▼────┐
           │ EX/MEM│  │  ALU   │  │MEM/WB │
           │ 寄存器 │  │        │  │ 寄存器│
           └───┬───┘  └───┬────┘  └───┬───┘
               │          │            │
               └──────────┼────────────┘
                          │
                  ┌───────▼───────┐
                  │  MUX (选择器)   │
                  └───────┬───────┘
                          │
                    ┌─────▼────┐
                    │ ALU 输入  │
                    └──────────┘
```

通常需要以下转发通路：

| 来源阶段 | 转发目的地 | 说明 |
|---------|-----------|------|
| EX/MEM → ALU 输入 | ID/EX 的 ALU 输入 | 前一条指令的 ALU 结果直接输入当前 ALU |
| MEM/WB → ALU 输入 | ID/EX 的 ALU 输入 | 前两条指令的结果（可能从 DMEM 读出）输入当前 ALU |
| MEM/WB → DMEM 输入 | EX/MEM 的 DMEM 输入 | 存储数据的前向传递（sw 指令的写入数据） |

### 2.3 转发示例

```
add x1, x2, x3    # R[1] ← R[2] + R[3]
sub x4, x1, x5    # R[4] ← R[1] - R[5]
```

**无转发时的执行流程：**

```
周期:   1      2      3      4      5      6      7
add:   IF    ID    EX    MEM    WB
sub:         IF    ID    ---   EX    MEM    WB
                      ↑ stall: sub 等待 add WB 后读 x1
```

**有转发时的执行流程：**

```
周期:   1      2      3      4      5
add:   IF    ID    EX    MEM    WB
sub:         IF    ID    EX    MEM    WB
                      ↑ 转发: sub 在 EX 阶段直接使用
                        add 在 EX 阶段计算的 ALU 结果
```

转发避免了 1 个停顿周期。

### 2.4 转发控制逻辑

转发单元通过比较流水线寄存器中的寄存器号来决定是否启用转发：

```python
# EX 阶段冒险检测（转发来自 EX/MEM）
if (EX/MEM.RegWrite == 1 
    and EX/MEM.rd != 0
    and EX/MEM.rd == ID/EX.rs1):
    forwardA = FROM_EX_MEM  # 源操作数 1 转发来自 EX/MEM

if (EX/MEM.RegWrite == 1 
    and EX/MEM.rd != 0
    and EX/MEM.rd == ID/EX.rs2):
    forwardB = FROM_EX_MEM  # 源操作数 2 转发来自 EX/MEM

# MEM 阶段冒险检测（转发来自 MEM/WB）
if (MEM/WB.RegWrite == 1 
    and MEM/WB.rd != 0
    and MEM/WB.rd == ID/EX.rs1
    and not (前面 EX/MEM 的转发已覆盖)):
    forwardA = FROM_MEM_WB

if (MEM/WB.RegWrite == 1 
    and MEM/WB.rd != 0
    and MEM/WB.rd == ID/EX.rs2
    and not (前面 EX/MEM 的转发已覆盖)):
    forwardB = FROM_MEM_WB
```

> 比较时排除 x0 寄存器（RISC-V 中 x0 恒为 0，永远不会被写入）。

---

## 3. Load-Use 冒险

### 3.1 为什么转发不够？

加载指令（lw）从数据存储器读取数据，结果要到 MEM 阶段结束时才可用。如果下一条指令在 EX 阶段就需要这个结果，即使转发也来不及——因为 MEM 在 EX 之后。

```
lw  x1, 0(x2)     # x1 ← Mem[x2]
add x4, x1, x5    # x4 ← x1 + x5

周期:   1      2      3      4      5      6
lw:    IF    ID    EX    MEM    WB
add:         IF    ID    ---   EX    MEM    WB
                      ↑ stall: lw 这时才得到数据（MEM 末）
                        add 无法在 EX 开始时拿到数据
```

这种情况下，即使转发，也需要插入**一个停顿周期**（一个气泡）。

### 3.2 Load-Use 冒险的检测

```python
# 在 ID 阶段检测
if (ID/EX.MemRead == 1                  # 前一条指令是 lw
    and ID/EX.rd == IF/ID.rs1           # 需要读 lw 的目标寄存器
    or ID/EX.rd == IF/ID.rs2):          # 需要读 lw 的目标寄存器
    stall_pipeline()                    # 插入一个气泡
```

检测到 load-use 冒险后，流水线控制单元会：

1. **冻结 PC**: 保持 PC 不变，IF 阶段重复取当前指令
2. **冻结 IF/ID**: IF/ID 寄存器保持不变
3. **冲刷 ID/EX**: 将 ID/EX 寄存器的控制信号全部置 0（插入气泡）

经过一个停顿周期后，lw 的结果在 MEM 阶段可用，转发单元可以将其转发给 add（在 EX 阶段的新时刻）。

### 3.3 Load-Use 冒险的完整流程

```
# 原始代码
lw   x1, 0(x2)
add  x4, x1, x5
or   x6, x7, x8

# 流水线执行（带 load-use 停顿+转发）

周期 1: IF = lw         ID = —        EX = —        MEM = —       WB = —
周期 2: IF = add        ID = lw       EX = —        MEM = —       WB = —
周期 3: IF = or         ID = add      EX = lw       MEM = —       WB = —
周期 4: IF = or(重取)   ID = bubble   EX = add      MEM = lw      WB = —
                                      ↑ stall bubble
周期 5: IF = next       ID = or       EX = bubble   MEM = add     WB = lw
周期 6: IF = ...        ID = next     EX = or       MEM = bubble  WB = add
                        （add 现在得到来自 MEM/WB 的转发值）
```

### 3.4 编译器调度优化

有经验的编译器可以通过**指令调度**（instruction scheduling）来减少 load-use 停顿：

```assembly
# 原始代码（有 load-use 停顿）
lw   x1, 0(x2)       # 加载
add  x4, x1, x5      # 立即使用 → 停顿 1 周期
lw   x3, 8(x2)       # 另一个加载
add  x6, x3, x7      # 又停顿 1 周期

# 调度后（无 load-use 停顿）
lw   x1, 0(x2)       # 加载
lw   x3, 8(x2)       # 在 lw 和 add 之间插入无关指令
add  x4, x1, x5      # 转发解决了（lw 的结果在 MEM 末已可用？）
                     # 不对，这里还是有 load-use，因为中间插的 lw x3 不影响 x1
                     # 重新调度：

lw   x1, 0(x2)       # 加载
or   x9, x10, x11    # 无关指令 → 填充 load-use 间隙
add  x4, x1, x5      # 不再需要停顿
```

编译器调度可以将无关的指令插入到 load 之后的位置，从而隐藏加载延迟。这是编译器优化流水线性能的重要手段。

---

## 4. 数据冒险的 CPI 影响

### 4.1 无转发时的 CPI

如果没有转发，每条 RAW 依赖的指令都需要等待前一条指令写回寄存器堆：

```
add x1, x2, x3
sub x4, x1, x5    # 需要等待 add 的 WB 阶段
                   # add 在周期 3 的 EX 计算出结果
                   # 周期 5 的 WB 写入寄存器
                   # sub 在周期 6 才能用 → 2 个气泡
```

每对相邻的 RAW 指令可能引入 2 个停顿周期。这导致 CPI 急剧恶化。

### 4.2 有转发时的 CPI

有转发时，只有 load-use 冒险需要停顿：

```
add x1, x2, x3
sub x4, x1, x5    # 转发解决，0 停顿

lw  x1, 0(x2)
add x4, x1, x5    # load-use，1 停顿

sw  x1, 0(x2)     # 不是 load-use（sw 写存储器，不是读寄存器）
                   # 但如果是：
lw  x1, 0(x2)
sw  x1, 0(x3)     # 实际上 sw 在 ID 阶段读 x1，EX 阶段计算地址
                   # lw 结果在 MEM 末可用，sw 的 ID 需要 x1
                   # 需要停顿！（lw→sw 也是 load-use）
```

> lw 之后的 sw 同样需要停顿，因为 sw 在 ID 阶段需要读取 lw 的目标寄存器值用于写入存储器，而 lw 的结果直到 MEM 末才可用。

### 4.3 典型 CPI 估算

假设程序中：

- 14% 的指令是 lw（其中约 20% 的后续指令使用 lw 的结果 → load-use 需要停顿）
- 12% 的指令是 sw（其中约 15% 跟踪的 lw 直接相关，需要停顿）
- ~50% 的算数指令有 RAW 依赖（转发解决，0 CPI 损失）

Data hazard CPI loss ≈ 0.14 × 0.20 × 1 + 0.12 × 0.15 × 1 ≈ 0.046

实际程序中数据冒险的 CPI 损失大约在 0.05-0.15 之间，远小于无转发时的损失（可能超过 0.5）。

---

## 5. 特殊情况

### 5.1 转发到自身（Duplicate Instructions）

```
add x1, x2, x3
add x1, x1, x4    # RAW，x1 既是源又是目标
```

转发单元会检测到 ID/EX.rd == ID/EX.rs1，将 EX/MEM 的结果转发给 ALU 输入。这可以正常工作。

### 5.2 多级转发

```
add x1, x2, x3
nop
sub x4, x1, x5    # add 的结果在 MEM/WB，转发到 sub 的 EX 阶段
```

需要 MEM/WB → ALU 的转发通路。

### 5.3 连续转发优先级

当 EX/MEM 和 MEM/WB 同时持有转发数据时：

```
add x1, x2, x3
add x1, x1, x4    # 写入 x1
sub x5, x1, x6    # 需要 x1
```

- EX/MEM 持有第二条 add 的结果（最新→正确值）
- MEM/WB 持有第一条 add 的结果（过时→错误值）
- 转发单元必须优先选择 EX/MEM 的转发数据

规则：**最近的源优先**。在检测时需要按 EX/MEM → MEM/WB 的顺序判断。

---

## 总结

- RAW 是按序流水线中唯一需要处理的数据冒险类型
- **转发**将中间结果直接送到 ALU 输入端，避免多数数据冒险的停顿
- 转发单元比较寄存器号决定转发来源（EX/MEM 或 MEM/WB）
- **Load-use 冒险**仍需一个停顿周期（lw 结果在 MEM 末才可用）
- 编译器调度可以减少 load-use 停顿
- 转发优先级：EX/MEM 高于 MEM/WB（保持数据最新）

## 参考文献

- Patterson & Hennessy, *Computer Organization and Design RISC-V Edition*, 第 4 章 Section 4.5.3 "Data Hazards", Section 4.7 "Data Hazards and Forwarding"
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach* 6th Edition, Section 3.4 "Data Hazards"
- John Paul Shen, Mikko H. Lipasti, *Modern Processor Design: Fundamentals of Superscalar Processors*, 第 3 章 "Dataflow and Dependencies"
- David A. Patterson, "Reduced Instruction Set Computers", Communications of the ACM 28(1), 1985 — 讨论精简指令集中的流水线设计
- D. W. Anderson, F. J. Sparacio, R. M. Tomasulo, "The IBM System/360 Model 91: Machine Philosophy", IBM Journal of Research and Development, 1967 — 最早的数据转发方案（Tomasulo 算法前身）
