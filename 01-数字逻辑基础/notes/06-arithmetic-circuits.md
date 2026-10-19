# 算术运算电路

除基本加法之外，数字系统还需要用于乘法、除法及其他算术运算的硬件。本笔记介绍关键电路架构及其在面积、延迟和吞吐量方面的权衡 [1,2]。

---

## 乘法器

两个 N 位二进制数相乘会产生 2N 位的结果。其基本思路是：生成部分积（partial product），再对它们求和。

**示例**：4 位乘法（3 × 6 = 18）

```
        0011  (3)
      x 0110  (6)
      -------
        0000   (partial product 0)
       0011    (partial product 1, shifted left 1)
      0011     (partial product 2, shifted left 2)
     0000      (partial product 3, shifted left 3)
     --------
     0010010   (18)
```

### 阵列乘法器（array multiplier）

使用与门（AND gate）生成部分积的各个位，并使用加法器将其求和。面积按 O(N^2) 增长，延迟为 O(N)。

### Booth 编码（Booth encoding）

基-2 Booth 编码（radix-2 Booth）不会减少部分积的数量（仍有 N 个）；它减少的是非零部分积的数量，尤其是当乘数（multiplier）中包含较长的连续 1 时。基-4 Booth 编码（radix-4 Booth）则将数量减少到约 N/2 [3]。

**基-2 Booth 编码**：检查当前乘数位 `b_i` 与前一位 `b_{i-1}`（最右侧附加位的初始值为 0）：

| b_i | b_{i-1} | 操作 |
|-----|---------|-----------|
| 0 | 0 | 加 0 |
| 0 | 1 | 加 M |
| 1 | 0 | 加 -M |
| 1 | 1 | 加 0 |

**Booth 示例**：3 × 5（M=0011，乘数=0101）

```
Step 0: (b0,b-1)=(1,0) -> -M      = -3
Step 1: (b1,b0)=(0,1) -> +M << 1  = +6
Step 2: (b2,b1)=(1,0) -> -M << 2  = -12
Step 3: (b3,b2)=(0,1) -> +M << 3  = +24

Sum: -3 + 6 - 12 + 24 = 15. Correct.
```

**基-4 Booth 编码**（改进型 Booth 编码，modified Booth）：检查相互重叠的 3 位组，从而将部分积数量从 N 减少到 N/2。

### 华莱士树乘法器（Wallace tree multiplier）

使用进位保留加法器（carry-save adder, CSA）并行地对部分积求和，将深度从 O(N) 降低到 O(log N) [4]。

每个 CSA 接收 3 个数，并在一个全加器（full adder）延迟内产生和（Sum）与进位（Carry）。该树将 N 行约简为 2 行，然后由最后一级进位传播加法器（carry-propagate adder）产生结果。

**时序比较**（8×8 乘法器）：

| 架构 | 延迟（加法器级数） | 门数量 |
|-------------|---------------------|------------|
| 阵列乘法器 | ~14 | ~500 |
| 华莱士树 | ~8 | ~800 |
| Booth + 华莱士树 | ~6 | ~900 |

---

## 除法器

除法比乘法更难实现。其实现方式从迭代式（速度较慢、面积效率高）到基于查找表（lookup table）的方式（速度快、面积开销大）不等。

### 恢复余数除法（restoring division）

类似于长除法（long division）。每个商位需要做一次判定 [5]。

```
Remainder = Dividend (2N bits)
Divisor = Divisor shifted left by N-1
For i = 0 to N-1:
    Remainder = Remainder - Divisor
    If Remainder >= 0: Qbit = 1
    Else: Qbit = 0, Remainder = Remainder + Divisor (restore)
    Shift Divisor right by 1 bit
```

**示例**：7 / 3（4 位）

```
Initial: R=0111 (7), D=0001_1000 (24, i.e., 3 shifted left by N-1 = 3)
Step 1: R-D < 0, Q=0, restore R=7, D>>1 = 1100 (12)
Step 2: R-D < 0, Q=0, restore R=7, D>>1 = 0110 (6)
Step 3: R-D = 1 >= 0, Q=1, R=1, D>>1 = 0011 (3)
Step 4: R-D < 0, Q=0, restore R=1

Result: Quotient=0010 (2), Remainder=0001 (1). 7/3=2 rem 1.
```

### 不恢复余数除法（non-restoring division）

通过利用商位来决定下一步操作，从而避免恢复步骤：
- 若 R >= 0：R = 2R - D，Qbit = 1
- 若 R < 0：R = 2R + D，Qbit = 0

最终修正：若 R < 0，则 R = R + D。这样每次迭代可省去一次加法。

### SRT 除法（SRT division）

使用冗余数字集（redundant digit set），其中商位取自 {-1, 0, +1}，并结合查找表，每次迭代可确定多位商。大多数现代 CPU 都采用该算法。1994 年的 Intel Pentium FDIV 缺陷（bug）是由 SRT 查找表中缺失五个表项引起的 [1]。

---

## 乘加运算（multiply-accumulate, MAC）

```
MAC: Accumulator = Accumulator + (A x B)
```

它是数字信号处理（digital signal processing, DSP）和矩阵计算的基础。融合乘加（fused multiply-add, FMA）通过一次舍入步骤完成乘法和加法，从而提高精度（IEEE 754-2008 推荐该做法，但并不强制要求）。

---

## 参考文献

1. Koren, I. (2002). *Computer Arithmetic Algorithms* (2nd ed.). A K Peters/CRC Press. Chapter 3: Sequential Algorithms for Multiplication and Division; Chapter 4: Binary Floating-Point Numbers; Chapter 6: High-Speed Multiplication; Chapter 7: Fast Division.

2. Patterson, D. A., & Hennessy, J. L. (2013). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Appendix B: The Basics of Logic Design.

3. Booth, A. D. (1951). A Signed Binary Multiplication Technique. *The Quarterly Journal of Mechanics and Applied Mathematics*, 4(2), 236-240. doi:10.1093/qjmam/4.2.236.

4. Wallace, C. S. (1964). A Suggestion for a Fast Multiplier. *IEEE Transactions on Electronic Computers*, EC-13(1), 14-17. doi:10.1109/PGEC.1964.263830.

5. Harris, S., & Harris, D. (2015). *Digital Design and Computer Architecture* (2nd ed.). Morgan Kaufmann. Chapter 5: Digital Building Blocks.

6. Robertson, J. E. (1958). A New Class of Digital Division Methods. *IRE Transactions on Electronic Computers*, EC-7(3), 218-222. doi:10.1109/TEC.1958.5222579.
