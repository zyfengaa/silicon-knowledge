# 数字逻辑（Digital Logic）-- 练习题

## 问题（Questions）

### 问题 1：进制转换（Binary Conversion）

将以下数字进行转换：

a) `101101_2` 转换为十进制
b) `42` 转换为二进制
c) `0x3F` 转换为二进制和十进制
d) `101011_2` 转换为十六进制

### 问题 2：补码（Two's Complement）

给定 8 位补码表示：

a) 可表示的数字范围是多少？
b) 用 8 位补码表示 -23。
c) 用 8 位补码计算 (-23) + 15。展示二进制加法过程。是否发生溢出（overflow）？

### 问题 3：IEEE 754

一个 32 位 IEEE 754 浮点数的位模式为 `0x40A00000`。

a) 它的符号位（sign bit）、指数位（exponent bits）和尾数位（mantissa bits）分别是什么？
b) 它的数值是多少（展示计算过程）？
c) -5.75 如何表示为 32 位 IEEE 754 值？

### 问题 4：布尔代数化简（Boolean Simplification）

使用布尔代数定律进行化简。展示每一步。

a) F = A.B + A.B' + A'.B
b) F = (A + B').(A' + B)
c) F = A'.B'.C' + A'.B'.C + A.B'.C' + A.B'.C

### 问题 5：卡诺图（Karnaugh Map）

使用 K-map 化简 F(A,B,C,D) = sum m(0,1,2,4,5,8,9,10)。

a) 展示包含所有条目的 K-map。
b) 确定质蕴含项（prime implicants）。
c) 给出最简与或式（minimal sum-of-products expression）。

### 问题 6：加法器设计（Adder Design）

a) 写出全加器（full adder）的真值表。
b) 推导和（sum）与进位输出（carry-out）的布尔表达式。
c) 解释超前进位（carry-lookahead）如何比行波进位（ripple-carry）更快。
d) 在 CLA 中推导 C2（第 2 位的进位输出）的表达式。

### 问题 7：时序电路（Sequential Circuits）

a) 画出基于 NOR 的 SR 锁存器（SR latch）的电路图。解释禁止状态（forbidden state）。
b) 电平敏感型 D 锁存器（level-sensitive D latch）与边沿触发型 D 触发器（edge-triggered D flip-flop）有什么区别？
c) 解释建立时间（setup time）和保持时间（hold time）。违反时会发生什么？
d) 触发器参数为 t_clk-to-Q=2ns, t_su=1ns, 组合逻辑延迟=5ns。最大时钟频率是多少？

### 问题 8：算术电路（Arithmetic Circuits）

a) 使用 Booth 基-2 算法（Booth's radix-2 algorithm），逐步计算 6 (0110) 乘以 5 (0101)。
b) 解释 Wallace 树乘法器（Wallace tree multiplier）相比阵列乘法器（array multiplier）的优势。
c) 恢复除法（restoring division）与非恢复除法（non-restoring division）的关键区别是什么？

---

## 答案（Answers）

### 答案 1：进制转换

**a)** 101101_2 = 1x32 + 0x16 + 1x8 + 1x4 + 0x2 + 1x1 = 32+8+4+1 = **45**

**b)** 42 转换为二进制：
```
42/2=21r0, 21/2=10r1, 10/2=5r0, 5/2=2r1, 2/2=1r0, 1/2=0r1
从下往上读取余数：101010_2
```

**c)** 0x3F：二进制 00111111_2，十进制 3x16+15 = **63**

**d)** 101011_2 -> 0010 1011 -> **0x2B**

### 答案 2：补码

**a)** 范围：-128 到 +127

**b)** -23：+23 = 00010111。取反：11101000。加 1：**11101001**

**c)** (-23) + 15：11101001 + 00001111 = 11111000。取反：00000111。加 1：00001000 = -8。
进位输入 = 1，进位输出 = 1 -> 无溢出（no overflow）。**答案：-8**

### 答案 3：IEEE 754

**a)** 0x40A00000 = 0100_0000_1010_0000_...
符号位：0，指数位：10000001=129，尾数位：010000...

**b)** S=0, E=129（去偏后=2），尾数=1.01_2 -> 1.01 x 2^2 = 101 = **5.0**

**c)** -5.75：5.75=101.11_2，规格化=1.0111x2^2。S=1, E=129=10000001, M=011100...
位模式：1 10000001 01110000000000000000000 = **0xC0B80000**

### 答案 4：布尔代数化简

**a)** F = A.B + A.B' + A'.B = A.(B+B') + A'.B = A + A'.B = A + B

**b)** F = (A+B').(A'+B) = 0 + A.B + A'.B' + 0 = A.B + A'.B' = A XNOR B

**c)** F = A'.B'.(C'+C) + A.B'.(C'+C) = A'.B' + A.B' = B'.(A'+A) = **B'**

### 答案 5：卡诺图

**a) K-map：**
```
           CD
           00  01  11  10
AB 00  | 1 | 1 | 0 | 1 |
   01  | 1 | 1 | 0 | 0 |
   11  | 0 | 0 | 0 | 0 |
   10  | 1 | 1 | 0 | 1 |
```

**b)** 质蕴含项：A'C' (m0,m1,m4,m5), B'D' (m0,m2,m8,m10), AB'C' (m8,m9)

**c)** 最简与或式：**F = A'C' + B'D' + AB'C'**

### 答案 6：加法器设计

**a)** 全加器真值表：
```
A B Cin | Sum Cout
0 0 0 | 0 0
0 0 1 | 1 0
0 1 0 | 1 0
0 1 1 | 0 1
1 0 0 | 1 0
1 0 1 | 0 1
1 1 0 | 0 1
1 1 1 | 1 1
```

**b)** Sum = A XOR B XOR Cin。Cout = (A.B) + (B.Cin) + (A.Cin)

**c)** CLA 使用 G_i = A_i.B_i 和 P_i = A_i XOR B_i 并行计算进位。C_{i+1} = G_i + P_i.C_i。所有进位可在常数时间（2 级 AND-OR）内得到，与 N 无关。

**d)** C2 = G1 + P1.G0 + P1.P0.C0

### 答案 7：时序电路

**a)** 两个交叉耦合的 NOR 门。禁止状态：S=1,R=1 -> Q=Q'=0，违反 Q != Q'。

**b)** D 锁存器：电平敏感型，使能时透明传输。D 触发器：边沿触发型，仅在时钟边沿采样。

**c)** 建立时间：数据必须在时钟边沿前保持稳定。保持时间：数据必须在时钟边沿后保持稳定。违反 -> 亚稳态（metastability）。

**d)** T_min = 2+5+1 = 8ns。F_max = **125 MHz**

### 答案 8：算术电路

**a)** Booth 算法：M=0110, 乘数=0101。+M(0110), -M(1010)<<1, +M(0110)<<2。和 = 0110 + 10100 + 011000 = 0011110 = **30**

**b)** Wallace 树：延迟为 O(log N)，而阵列乘法器为 O(N)。连线更多，但对于大型乘法器速度更快。

**c)** 恢复除法：在减法失败后恢复（需要 2N 次操作）。非恢复除法：根据符号选择加/减来避免恢复（N 次操作，必要时做最终修正）。

---

## 参考文献（References）

1. Patterson, D. A., & Hennessy, J. L. (2017). *Computer Organization and Design* (第 5 版). Morgan Kaufmann.
2. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design* (第 6 版). Pearson.
3. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (第 2 版). Morgan Kaufmann.
4. IEEE Standard for Floating-Point Arithmetic. (2019). *IEEE Std 754-2019*.
5. Koren, I. (2002). *Computer Arithmetic Algorithms* (第 2 版). A K Peters/CRC Press.
