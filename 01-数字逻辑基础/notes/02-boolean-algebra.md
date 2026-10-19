# 布尔代数

布尔代数（Boolean algebra）由乔治·布尔（George Boole）于 19 世纪中叶提出，是数字逻辑设计的数学基础。克劳德·香农（Claude Shannon）在 1937 年的硕士论文中首次将其应用于继电器电路，奠定了数字电路设计这一领域 [1]。

---

## 基本公理与运算

布尔代数在二值上运算：0（假）与 1（真）。它定义了三种基本运算：

| 运算 | 记号 | 描述 |
|-----------|----------|-------------|
| 与（AND）       | A . B 或 A B | 仅当 A 与 B 都为真时才为真 |
| 或（OR）        | A + B        | 当 A 或 B（或二者）为真时为真 |
| 非（NOT）       | A' 或 A̅ 或 ~A | 对该值取反 |

### 基本运算的真值表（Truth Tables）

```
AND                OR                 NOT
A  B | A.B         A  B | A+B         A | A'
-----|-----        -----|-----        ---|----
0  0 |  0          0  0 |  0          0 |  1
0  1 |  0          0  1 |  1          1 |  0
1  0 |  0          1  0 |  1
1  1 |  1          1  1 |  1
```

---

## 布尔定律（Boolean Laws）

所有布尔定律都可以通过完全归纳法（perfect induction，即检查输入的所有组合）来证明。

### 基本定律（Fundamental Laws）

| 定律            | 与形式               | 或形式                |
|----------------|------------------------|------------------------|
| 恒等律（identity）       | A . 1 = A              | A + 0 = A              |
| 零元律（null element）   | A . 0 = 0              | A + 1 = 1              |
| 幂等律（idempotent）     | A . A = A              | A + A = A              |
| 互补律（complement）     | A . A' = 0             | A + A' = 1             |
| 对合律（involution）     | (A')' = A              | (A')' = A              |

### 交换律（Commutative Law）

**A . B = B . A** 且 **A + B = B + A**

操作数的顺序不影响结果。

### 结合律（Associative Law）

**(A . B) . C = A . (B . C)** 且 **(A + B) + C = A + (B + C)**

运算的分组方式不影响结果。

### 分配律（Distributive Law）

**A . (B + C) = A . B + A . C**（与对或分配）

**A + (B . C) = (A + B) . (A + C)**（或对与分配）

注意：与普通代数不同，布尔代数中两种分配形式都成立。

### 德摩根定律（De Morgan's Laws）

**(A . B)' = A' + B'** 且 **(A + B)' = A' . B'**

德摩根定律对于电路化简，以及在与/或（AND/OR）实现和与非/或非（NAND/NOR）实现之间进行转换，都至关重要。

用真值表证明 **(A . B)' = A' + B'**：

```
A  B | A.B | (A.B)' | A' | B' | A' + B'
-----|-----|--------|----|----|---------
0  0 |  0  |   1    | 1  | 1  |   1
0  1 |  0  |   1    | 1  | 0  |   1
1  0 |  0  |   1    | 0  | 1  |   1
1  1 |  1  |   0    | 0  | 0  |   0
```

(A.B)' 与 A' + B' 两列在每一行都相符，从而证明了该定律。

### 吸收律（Absorption Laws）

**A + (A . B) = A**

**A . (A + B) = A**

这些定律可用于消去冗余项。

### 一致定理（Consensus Theorem）

**A . B + A' . C + B . C = A . B + A' . C**

项 B . C 是冗余的（即“一致项”）。

---

## 布尔函数表示

### 积之和（Sum of Products，SOP）

用与项（最小项，minterm）的或来表示的布尔函数。

**示例**：F(A, B, C) = A'.B.C + A.B'.C + A.B.C

### 和之积（Product of Sums，POS）

用或项（最大项，maxterm）的与来表示的布尔函数。

**示例**：F(A, B, C) = (A+B+C) . (A+B+C') . (A+B'+C)

### 使用布尔定律进行化简

**示例**：化简 F = A.B + A.B' + A'.B

```
F = A.B + A.B' + A'.B
  = A.(B + B') + A'.B         (Distributive)
  = A.1 + A'.B                (Complement: B + B' = 1)
  = A + A'.B                  (Identity: A.1 = A)
  = (A + A') . (A + B)         (Distributive: A + A'.B = (A+A').(A+B))
  = 1 . (A + B)                (Complement: A + A' = 1)
  = A + B                      (Identity)
```

---

## 卡诺图（Karnaugh Maps，K-Maps）

卡诺图（Karnaugh map，K-map）是一种用于化简布尔表达式的图形化方法。它按格雷码（Gray code）的形式排列真值表的单元格，使相邻单元格恰好只相差一个变量，从而让化简结果在视觉上显而易见 [1,2]。

### 二变量卡诺图

```
        B
        0   1
     +---+---+
A  0 | m0| m1|
     +---+---+
   1 | m2| m3|
     +---+---+
```

相邻单元格只相差一个变量：例如 m0（A'B'）与 m1（A'B）仅在 B 上不同，因此可合并为 A'。

**示例**：F(A,B) = A'B + AB' + AB

```
        B
        0   1
     +---+---+
A  0 | 0 | 1 |  <- m1 = A'B
     +---+---+
   1 | 1 | 1 |  <- m2+m3 = A
     +---+---+
```

分组：A=1 这一行中的两个 1 构成组 A。m1 处孤立的 1 保持为 A'B。
化简结果：**F = A + A'B = A + B**

### 三变量卡诺图

```
         BC
         00  01  11  10
      +----+----+----+----+
A  0  | m0 | m1 | m3 | m2 |
      +----+----+----+----+
   1  | m4 | m5 | m7 | m6 |
      +----+----+----+----+
```

注意：各列采用格雷码（00 -> 01 -> 11 -> 10），因此相邻列仅相差一位。

**示例**：F(A,B,C) = sum(2, 3, 6, 7)

```
         BC
         00  01  11  10
      +----+----+----+----+
A  0  | 0  | 0  | 1  | 1  |
      +----+----+----+----+
   1  | 0  | 0  | 1  | 1  |
      +----+----+----+----+
```

分组：四个 1 构成一个 2x2 的方块，覆盖所有 B=1 的情况（C 和 A 可变）。
化简结果：**F = B**

**示例**：F(A,B,C) = sum(0, 2, 4, 6)

```
         BC
         00  01  11  10
      +----+----+----+----+
A  0  | 1  | 0  | 0  | 1  |
      +----+----+----+----+
   1  | 1  | 0  | 0  | 1  |
      +----+----+----+----+
```

分组：四个角——m0 (000)、m2 (010)、m4 (100)、m6 (110)，即 C=0 的四个角。
化简结果：**F = C'**

### 四变量卡诺图

```
           CD
           00   01   11   10
       +----+----+----+----+
AB 00  | m0 | m1 | m3 | m2 |
       +----+----+----+----+
   01  | m4 | m5 | m7 | m6 |
       +----+----+----+----+
   11  | m12| m13| m15| m14|
       +----+----+----+----+
   10  | m8 | m9 | m11| m10|
       +----+----+----+----+
```

**示例**：F(A,B,C,D) = sum(0, 2, 5, 7, 8, 10, 13, 15)

```
           CD
           00  01  11  10
       +---+---+---+---+
AB 00  | 1 | 0 | 0 | 1 |  <- m0, m2 (A'B'D')
       +---+---+---+---+
   01  | 0 | 1 | 1 | 0 |  <- m5, m7 (A'BD)
       +---+---+---+---+
   11  | 0 | 1 | 1 | 0 |  <- m13, m15 (ABD)
       +---+---+---+---+
   10  | 1 | 0 | 0 | 1 |  <- m8, m10 (AB'D')
       +---+---+---+---+
```

分组：
- m0 + m2 + m8 + m10：B=0，D=0 -> B'D'
- m5 + m7 + m13 + m15：B=1，D=1 -> BD

化简结果：**F = B'D' + BD = (B XOR D)' = XNOR(B, D)**

### 无关项条件（Don't Care Conditions）

在许多电路中，某些输入组合永远不会出现。这些组合可以被视为“无关项”（don't care，X），并可将其赋为 0 或 1，以获得更简单的表达式。

**示例**：BCD 到七段数码管显示译码器。对于 BCD 码（0000-1001），输入 1010-1111 永远不会出现。

```
F(A,B,C,D) = sum(0,1,2,3,4,5,6,7,8,9) + d(10,11,12,13,14,15)
```

在卡诺图中，无关项可用于构成更大的分组，从而得到更简单的项。

---

## 标准形式（Canonical Forms）

### 最小项（Minterms）

最小项（minterm）是一个乘积项，其中每个变量恰好出现一次（以原变量或反变量的形式）。对于 n 个变量，共有 2^n 个最小项。**最小项之和**（sum of minterms）形式的函数写为若干乘积项之和，且每个变量在每一项中都出现。

**示例**：F(A,B) = A'B + AB' + AB = sum(1, 2, 3)

### 最大项（Maxterms）

最大项（maxterm）是一个和项，其中每个变量恰好出现一次。**最大项之积**（product of maxterms）形式的函数是其对偶形式。

**示例**（另一个函数，用于展示非平凡的 POS 形式）：F(A,B) = (A+B) . (A+B') . (A'+B) = product(0, 1, 2) = A.B

任何函数都可以表示为最小项之和或最大项之积——这些就是标准形式。

---

## 实际化简示例

**问题**：为 F(A,B,C,D) = AB + A'C + BC 设计一个电路。

使用一致定理：AB + A'C + BC = AB + A'C（BC 项是冗余的）。

**验证**：
- 当 A=1 时：F = B + 0 + BC = B
- 当 A=0 时：F = 0 + C + BC = C
- 一致项 BC 已被其他项覆盖。

---

## 参考文献

1. Shannon, C. E. (1938). A Symbolic Analysis of Relay and Switching Circuits. *Transactions of the American Institute of Electrical Engineers*, 57(12), 713-723. doi:10.1109/T-AIEE.1938.5057767.

2. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 2: Boolean Algebra and Logic Gates.

3. Patterson, D. A., & Hennessy, J. L. (2013). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

4. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 2: Combinational Logic Design.

5. Karnaugh, M. (1953). The Map Method for Synthesis of Combinational Logic Circuits. *Transactions of the American Institute of Electrical Engineers, Part I: Communication and Electronics*, 72(5), 593-599. doi:10.1109/TCE.1953.6371448.
