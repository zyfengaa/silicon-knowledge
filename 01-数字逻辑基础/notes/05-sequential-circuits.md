# 时序逻辑电路

与组合逻辑电路（combinational circuits）不同，时序逻辑电路（sequential circuits）具有**状态（state）**——其输出既取决于当前输入，也取决于过去输入的历史。该状态存储在称为触发器（flip-flop）和锁存器（latch）的存储元件中。时序逻辑电路是寄存器（register）、计数器（counter）以及所有同步数字系统（synchronous digital systems）的基础 [1,2]。

---

## SR 锁存器

SR（置位-复位，Set-Reset）锁存器是最简单的时序元件。它存储一个比特。

### 基于或非门（NOR）的 SR 锁存器

```
Truth Table:
S  R | Q  Q'  | State
-----|--------|--------------
0  0 | Q  Q'  | Hold (latched)
0  1 | 0   1  | Reset
1  0 | 1   0  | Set
1  1 | 0   0  | Forbidden (invalid)
```

**工作原理**：
- S=1, R=0：Q 变为 1（置位，Set）。在 S 回到 0 后，反馈使 Q 保持为 1。
- S=0, R=1：Q 变为 0（复位，Reset）。在 R 回到 0 后，反馈使 Q 保持为 0。
- S=0, R=0：锁存器保持其先前值（记忆状态）。
- S=1, R=1：两个输出都变为 0，违反 Q != Q'。这是禁止状态（forbidden state）。

### 基于与非门（NAND）的 SR 锁存器

低电平有效（active-low）输入（S' 和 R'）。S'=0、R'=1 时置位；S'=1、R'=0 时复位；S'=R'=1 时保持；S'=R'=0 时为禁止状态。

---

## D 锁存器（电平触发，Level-Triggered）

D 锁存器通过数据输入（data input，D）和使能端（enable，EN）消除了 SR 锁存器的禁止状态。

```
EN  D | Q    Q'
------|---------
0   x | Q    Q'   (hold, latch is opaque)
1   0 | 0    1    (transparent, Q follows D)
1   1 | 1    0    (transparent)
```

当 EN=1 时，锁存器**透明（transparent）**：Q 跟随 D。当 EN=0 时，锁存器不透明（opaque）：Q 保持其最后一个值。

---

## D 触发器（边沿触发，Edge-Triggered）

D 触发器仅在时钟信号（clock signal）的**边沿（edge）**（上升沿或下降沿）对 D 输入进行采样，并在时钟周期（clock cycle）的其余时间内保持该值。

```
Truth Table (rising-edge triggered):
CLK edge        D | Q(next)
----------------|---|------
rising edge     0 | 0
rising edge     1 | 1
no rising edge  X | Q (hold)
```

### 边沿触发（edge-triggered）与电平触发（level-triggered）

| 特性 | 电平触发（锁存器） | 边沿触发（触发器） |
|---------|------------------------|----------------------------|
| 采样方式 | 时钟为高电平时有效 | 仅在时钟边沿采样 |
| 透明性 | 使能时透明 | 从不透明 |
| 冒险敏感度 | 较高 | 较低 |

### 主从结构（Master-Slave）的构造

两个背靠背连接的 D 锁存器：当 CLK=0 时主锁存器透明，当 CLK=1 时从锁存器透明。当 CLK 上升时，主锁存器冻结，从锁存器将冻结的值复制到 Q，从而产生边沿触发行为。

---

## 寄存器

寄存器（register）是由共享公共时钟的 D 触发器组成的阵列，用于存储 N 位值。

### 带写使能（Write Enable）的寄存器

每个位将其当前 Q 和新 D 送入一个由 WE 控制的二选一多路复用器（2-to-1 multiplexer，MUX）。当 WE=1 时，新数据在时钟边沿被加载。当 WE=0 时，当前值被重新锁存。

---

## 计数器

### 行波计数器（异步，Ripple Counter）

每个触发器翻转其下一级。结构简单但速度慢：最高有效位（MSB）在 N x t_FF 延迟之后才翻转。

### 同步计数器（Synchronous Counter）

所有触发器共享同一时钟。每个翻转使能（toggle enable）信号都是所有低位进行与（AND）运算的结果：

```
EN0 = 1, EN1 = Q0, EN2 = Q0.Q1, EN3 = Q0.Q1.Q2
```

### 加/减计数器（Up/Down Counter）

一个控制输入选择计数方向：UP=1 时向上计数（count+1），UP=0 时向下计数（count-1）。

---

## 时钟信号与时序参数（Timing Parameters）

```
CLK:  __    __    __    __    __
      | |  | |  | |  | |  | |
     _| |__| |__| |__| |__| |__
     |<->| period = T
```

| 参数 | 定义 |
|-----------|-----------|
| T（周期，period） | 相邻上升沿之间的时间 |
| f（频率，frequency） | 1/T |
| 占空比（duty cycle） | 时钟在一个周期内为高电平的时间百分比 |

### 建立时间与保持时间（Setup and Hold Timing）[3]

```
              clock edge
                   |
CLK  ______________|______________
                   |
D    ==============|==============
              |<-->|<-->|
               tsu  thold
```

- **建立时间（setup time，t_su）**：数据必须在时钟边沿**之前**保持稳定。违反该要求可能导致亚稳态（metastability）。
- **保持时间（hold time，t_hold）**：数据必须在时钟边沿**之后**保持稳定。

### 最高时钟频率

```
T_min > t_clk-to-Q + t_comb_max + t_su + t_skew_margin
```

还必须满足保持时间约束（它与时钟周期无关）：

```
t_hold <= t_clk-to-Q + t_comb_min
```

### 亚稳态

如果 D 在过于接近时钟边沿时发生变化，触发器可能进入亚稳态（metastable state，既不是 0 也不是 1，而是介于两者之间的中间状态）。分辨时间（resolution time）是无界的。同步器（synchronizer，级联的触发器）可降低亚稳态发生的概率 [3]。

---

## 参考文献

1. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 5: Synchronous Sequential Logic.

2. Patterson, D. A., & Hennessy, J. L. (2013). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 3: Sequential Logic Design.

4. Weste, N. H. E., & Harris, D. (2010). *CMOS VLSI Design: A Circuits and Systems Perspective* (4th ed.). Addison-Wesley. Chapter 10: Sequential Circuit Design; timing analysis is covered in Chapter 4 and Section 10.2.

5. Rabaey, J. M., Chandrakasan, A., & Nikolic, B. (2003). *Digital Integrated Circuits: A Design Perspective* (2nd ed.). Prentice Hall. Chapter 7: Sequential Logic Circuits.

