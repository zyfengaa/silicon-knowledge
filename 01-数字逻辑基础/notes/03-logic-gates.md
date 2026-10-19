# 逻辑门

逻辑门（logic gates）是数字电路的基本构建模块。每个门实现一个布尔函数（Boolean function），接收一个或多个二进制输入，并产生单个二进制输出。本笔记涵盖七种基本门及其真值表，并介绍 CMOS 实现的概念 [1,2]。

---

## 基本门：与门（AND）、或门（OR）、非门（NOT）

### 与门（AND Gate）

仅当**所有**输入均为 1 时，输出才为 1。

```
Truth Table:
A  B | Y = A AND B
-----|-------------
0  0 |      0
0  1 |      0
1  0 |      0
1  1 |      1
```

### 或门（OR Gate）

当**任意**一个输入为 1 时，输出为 1。

```
Truth Table:
A  B | Y = A OR B
-----|------------
0  0 |     0
0  1 |     1
1  0 |     1
1  1 |     1
```

### 非门（NOT Gate）/ 反相器（Inverter）

输出是输入的反码。

```
Truth Table:
A | Y = NOT A
--|----------
0 |    1
1 |    0
```

---

## 通用门（universal gates）：与非门（NAND）与或非门（NOR）

### 与非门（NAND Gate）

NAND = NOT + AND。仅当**所有**输入均为 1 时，输出才为 0。

```
Truth Table:
A  B | Y = A NAND B = (A.B)'
-----|-----------------
0  0 |      1
0  1 |      1
1  0 |      1
1  1 |      0
```

### 或非门（NOR Gate）

NOR = NOT + OR。当**任意**一个输入为 1 时，输出为 0。

```
Truth Table:
A  B | Y = A NOR B = (A+B)'
-----|-----------------
0  0 |      1
0  1 |      0
1  0 |      0
1  1 |      0
```

### 为什么 NAND 和 NOR 是通用门

任何布尔函数都可以仅使用 NAND 门（或仅使用 NOR 门）来实现。这在理论上很重要：一种门类型就足以构建任何电路。在实践中，标准单元库（standard-cell libraries）会提供多种门类型，因为仅使用 NAND 的实现可能更慢且面积更大。

**用 NAND 构造基本门**：

```
NOT:    (A NAND A) = A'
AND:    (A NAND B)' = A . B         (NAND then NOT)
OR:     A' NAND B' = A + B          (Invert inputs, then NAND)
```

NOT 的证明：A NAND A = (A.A)' = A'（根据幂等律（idempotent law））。
AND 的证明：(A NAND B) NAND (A NAND B) = ((A.B)')' = A.B。
OR 的证明：A' NAND B' = (A' . B')' = A'' + B'' = A + B（根据德摩根定律（De Morgan's laws））。

### 异或（XOR，Exclusive OR）

当输入**不同**时，输出为 1。

```
Truth Table:
A  B | Y = A XOR B = A'B + AB'
-----|-----------------
0  0 |      0
0  1 |      1
1  0 |      1
1  1 |      0
```

### 同或（XNOR，Exclusive NOR）

当输入**相同**时，输出为 1。XNOR = NOT XOR。

```
Truth Table:
A  B | Y = A XNOR B
-----|--------------
0  0 |      1
0  1 |      0
1  0 |      0
1  1 |      1
```

---

## CMOS 实现（简要介绍）

CMOS（Complementary Metal-Oxide-Semiconductor，互补金属氧化物半导体）是数字逻辑的主导制造技术。每个 CMOS 门由两个网络组成 [3]：

- **上拉网络（PUN，Pull-up Network）**：将输出连接到 Vdd（逻辑 1）的 PMOS 晶体管。
- **下拉网络（PDN，Pull-down Network）**：将输出连接到 GND（逻辑 0）的 NMOS 晶体管。

这两个网络是**互补的**：当一个网络导通时，另一个网络关断。理想情况下，静态 CMOS 在不发生翻转时不消耗静态功耗；在实际的先进工艺中，亚阈值漏电（subthreshold leakage）和栅极漏电（gate leakage）会使静态功耗变得显著，因此“可忽略的静态功耗”只是一个一阶模型。

### CMOS 反相器

- A = 0：PMOS 导通，NMOS 关断 -> 输出连接到 Vdd -> Y = 1
- A = 1：PMOS 关断，NMOS 导通 -> 输出连接到 GND -> Y = 0

### CMOS 与非门

NMOS 晶体管串联，PMOS 晶体管并联。A=0 或 B=0 时，Y=1；A=1 且 B=1 时，Y=0。

### CMOS 或非门

NMOS 晶体管并联，PMOS 晶体管串联。A=1 或 B=1 时，Y=0；A=0 且 B=0 时，Y=1。

| 门 | PUN 模式 | PDN 模式 |
|----------|----------------|----------------|
| 反相器 | 1 个 PMOS | 1 个 NMOS |
| 与非门（NAND） | PMOS 并联 | NMOS 串联 |
| 或非门（NOR） | PMOS 串联 | NMOS 并联 |

---

## 汇总表

| 门 | 布尔表达式 | 输出 = 1 的条件…… | 是否通用门？ |
|-------|--------------------|--------------------|------------|
| 与门（AND） | Y = A . B          | 所有输入 = 1     | 否         |
| 或门（OR） | Y = A + B          | 任意输入 = 1      | 否         |
| 非门（NOT） | Y = A'             | 输入 = 0          | 否         |
| 与非门（NAND） | Y = (A.B)'         | 任意输入 = 0      | **是**    |
| 或非门（NOR） | Y = (A+B)'         | 所有输入 = 0     | **是**    |
| 异或门（XOR） | Y = A'B + AB'      | 输入不同      | 否         |
| 同或门（XNOR） | Y = AB + A'B'      | 输入相同       | 否         |

---

## 参考文献

1. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 1: Digital Systems and Binary Numbers; Chapter 2: Boolean Algebra and Logic Gates.

2. Patterson, D. A., & Hennessy, J. L. (2013). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Weste, N. H. E., & Harris, D. (2010). *CMOS VLSI Design: A Circuits and Systems Perspective* (4th ed.). Addison-Wesley. Chapter 1: Introduction; Chapter 5: Power.

4. Rabaey, J. M., Chandrakasan, A., & Nikolic, B. (2003). *Digital Integrated Circuits: A Design Perspective* (2nd ed.). Prentice Hall. Chapter 5: The CMOS Inverter and Its Static Characteristics.

5. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 2: Combinational Logic Design.
