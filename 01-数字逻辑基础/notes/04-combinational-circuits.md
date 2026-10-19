# 组合逻辑电路

组合逻辑电路（combinational circuit）是一种输出仅取决于当前输入的电路——它没有存储器或状态。本笔记涵盖数字系统中所使用的基本组合逻辑构建模块：加法器（adder）、多路复用器（multiplexer）、译码器（decoder）、编码器（encoder）和比较器（comparator）[1,2]。

---

## 加法器

### 半加器（half adder）

半加器将两个单比特数相加，产生和（sum）与进位（carry）。

```
Truth Table:
A  B | Sum  Carry
-----|-----------
0  0 |  0    0
0  1 |  1    0
1  0 |  1    0
1  1 |  0    1
```

**布尔表达式**：
- Sum = A XOR B
- Carry = A AND B

### 全加器（full adder）

全加器将三个单比特数 A、B 和进位输入（Carry-in，Cin）相加，产生和（Sum）与进位输出（Carry-out，Cout）。

```
Truth Table:
A  B Cin | Sum  Cout
---------|----------
0  0  0  |  0    0
0  0  1  |  1    0
0  1  0  |  1    0
0  1  1  |  0    1
1  0  0  |  1    0
1  0  1  |  0    1
1  1  0  |  0    1
1  1  1  |  1    1
```

**布尔表达式**：
- Sum = A XOR B XOR Cin
- Cout = (A AND B) OR (A AND Cin) OR (B AND Cin)
  Equivalently: Cout = (A AND B) OR (Cin AND (A XOR B))

### 行波进位加法器（ripple-carry adder，RCA）

行波进位加法器将 N 个全加器级联起来，以相加两个 N 位数。每一级的进位输出馈入下一级的进位输入。

```
4-bit Ripple-Carry Adder:

       A3  B3       A2  B2       A1  B1       A0  B0
       |   |        |   |        |   |        |   |
    +--------+   +--------+   +--------+   +--------+
    |  FA    |   |  FA    |   |  FA    |   |  FA    |
C4--| Cout   |---| Cin    |---| Cin    |---| Cin 0 |
    +--------+   +--------+   +--------+   +--------+
       |            |            |            |
      S3           S2           S1           S0
```

**时序**：进位必须传播通过全部 N 级。最坏情况下的延迟与 N 成正比。

**4 位行波进位加法器示例**：计算 7 (0111) + 5 (0101) = 12 (1100)

```
Bit 0: 1 + 1 = 0, carry 1
Bit 1: 1 + 0 + cin=1 = 0, carry 1
Bit 2: 1 + 1 + cin=1 = 1, carry 1
Bit 3: 0 + 0 + cin=1 = 1, carry 0
Result: 1100 (12)
```

### 超前进位加法器（carry-lookahead adder，CLA）

CLA 使用生成（generate，G）信号和传播（propagate，P）信号并行计算所有进位 [3]：

```
G_i = A_i AND B_i         -- generates a carry regardless of Cin
P_i = A_i XOR B_i         -- propagates Cin to Cout
C_{i+1} = G_i + P_i.C_i
```

**展开后的进位**（全部直接以 C0 表示；在理想的两级与或（AND-OR）模型中，这相当于一个门延迟（gate delay））：

```
C1 = G0 + P0.C0
C2 = G1 + P1.G0 + P1.P0.C0
C3 = G2 + P2.G1 + P2.P1.G0 + P2.P1.P0.C0
```

每个进位都可以写成一个两级与或表达式。在扇入（fan-in）不受限制时，其复杂度为 O(1)；实际门电路的扇入有限，因此真正的 CLA 会构建为前缀树（prefix tree），可实现 O(log N) 的延迟，而 RCA 为 O(N)，代价是使用更多门电路。

---

## 多路复用器（MUX）

多路复用器根据选择线（select line）从多个输入中选择一个。

### 2 选 1 多路复用器（2-to-1 MUX）

```
Truth Table:
S | Y
--|---
0 | D0
1 | D1

Logic: Y = (S'.D0) + (S.D1)
```

### 4 选 1 多路复用器（4-to-1 MUX）

```
Truth Table:
S1 S0 |  Y
------|----
 0  0 | D0
 0  1 | D1
 1  0 | D2
 1  1 | D3

Logic: Y = (S1'.S0'.D0) + (S1'.S0.D1) + (S1.S0'.D2) + (S1.S0.D3)
```

### 多路复用器的应用

- **数据选择**：在多个数据源之间进行选择。
- **函数生成**：使用 2^N 选 1 多路复用器实现任意 N+1 变量布尔函数（Boolean function）。
- **桶形移位器（barrel shifter）**：多路复用器阵列实现位旋转/移位。

---

## 译码器

译码器将 N 位二进制码转换为 2^N 条输出线，其中恰好一条输出有效。

### 2 线至 4 线译码器（2-to-4 decoder）

```
Truth Table:
A1 A0 | Y3 Y2 Y1 Y0
------|--------------
 0  0 |  0  0  0  1
 0  1 |  0  0  1  0
 1  0 |  0  1  0  0
 1  1 |  1  0  0  0

Logic:
  Y0 = A1'.A0', Y1 = A1'.A0, Y2 = A1.A0', Y3 = A1.A0
```

**应用**：存储器地址译码、指令译码、BCD 转七段显示（7-segment display）驱动器。

---

## 编码器

编码器执行译码器的逆操作：它将 2^N 条输入线转换为 N 位二进制码。

### 4 线至 2 线编码器（4-to-2 encoder）

```
Truth Table (assumes exactly one input active):
I3 I2 I1 I0 | A1 A0
------------|------
 0  0  0  1 |  0  0
 0  0  1  0 |  0  1
 0  1  0  0 |  1  0
 1  0  0  0 |  1  1

Logic: A0 = I3 + I1, A1 = I3 + I2
```

### 优先级编码器（priority encoder）

通过优先处理编号最高的输入，来应对多个同时有效的输入。

**4 线至 2 线优先级编码器**（最高索引优先）：

```
Truth Table:
I3 I2 I1 I0 | A1 A0 | V (valid)
------------|-------|---------
 0  0  0  0 |  x  x |   0
 0  0  0  1 |  0  0 |   1
 0  0  1  x |  0  1 |   1
 0  1  x  x |  1  0 |   1
 1  x  x  x |  1  1 |   1

Logic: V = I3+I2+I1+I0, A1 = I3+I2, A0 = I3+I2'.I1
```

---

## 比较器

比较器用于判断两个二进制数是否相等，和/或判断哪一个更大。

### 相等比较器（equality comparator）

对于 N 位数 A 和 B：
```
Equal = (A0 XNOR B0) AND (A1 XNOR B1) AND ... AND (A{N-1} XNOR B{N-1})
```

### 1 位数值比较器（1-bit magnitude comparator）

```
Truth Table:
A B | A>B  A=B  A<B
----|---------------
0 0 |  0    1    0
0 1 |  0    0    1
1 0 |  1    0    0
1 1 |  0    1    0

Logic: A>B = A.B', A=B = A XNOR B, A<B = A'.B
```

N 位数值比较器从最高有效位（MSB，most significant bit）向最低有效位（LSB，least significant bit）逐位比较；第一个不同的位决定结果。

---

## 组合逻辑电路时序

**关键路径（critical path）** 是从任一输入到任一输出的最长路径。电路的工作频率受该延迟限制：

```
F_max <= 1 / t_critical
```

其中 t_critical 是沿关键路径的所有门延迟之和 [2]。

---

## 参考文献

1. Mano, M. M., & Ciletti, M. D. (2018). *Digital Design: With an Introduction to the Verilog HDL, VHDL, and SystemVerilog* (6th ed.). Pearson. Chapter 4: Combinational Logic.

2. Patterson, D. A., & Hennessy, J. L. (2013). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 5: Digital Building Blocks.

4. Weinberger, A., & Smith, J. L. (1958). A Logic for High-Speed Addition. *National Bureau of Standards Circular*, 591, 3-12.

5. Koren, I. (2002). *Computer Arithmetic Algorithms* (2nd ed.). A K Peters/CRC Press. Chapter 5: Fast Addition.
