# 论文阅读笔记：IEEE 754 浮点运算标准

---

## 元数据

| 字段 | 值 |
|-------|-------|
| **标题** | IEEE Standard for Floating-Point Arithmetic (IEEE Std 754-2019) |
| **作者** | IEEE Microprocessor Standards Committee |
| **年份** | 首次出版于 1985 年；2008 年、2019 年修订 |
| **DOI** | 10.1109/IEEESTD.2019.8766229 |
| **相关文献** | Goldberg (1991), "What Every Computer Scientist Should Know About Floating-Point Arithmetic" |

---

## 问题背景

在 IEEE 754 之前，每家计算机制造商都定义了自己的浮点格式。这导致：

- **表示不兼容（incompatible representations）**：相同的位模式在 IBM、DEC、Cray 机器上表示不同的数值。
- **舍入不一致（inconsistent rounding）**：不同平台的行为存在差异。
- **没有异常处理（exception handling）**：除零、溢出会产生未定义的结果。
- **没有可移植性（portability）**：数值代码必须针对每种体系结构重写。

核心问题在于：数值计算在程序员与硬件之间缺少一份契约。

---

## 关键设计决策

### 1. 二进制与十进制格式

单精度（32 位：1/8/23，偏置（bias）127）与双精度（64 位：1/11/52，偏置（bias）1023）。

### 2. 隐藏位（hidden bit，隐式前导 1）

规格化尾数（normalized mantissa）总是以 1 开头；不存储这一位可以免费获得额外一位精度。

### 3. 偏置指数（biased exponent）

将指数以带偏置的无符号形式存储，使得整数比较器能够处理浮点数的排序（NaN 除外）。

### 4. 非规格化数（denormalized numbers，又称次正规数 subnormals）

当指数全为零时，前导位变为 0，指数固定为 -126（单精度）/ -1022（双精度）。这实现了**渐进下溢（gradual underflow）**，而不是突然跳变到零。

### 5. 正确舍入（correct rounding）

结果按无限精度计算后再进行舍入。共有四种舍入模式：

| 模式 | 行为 |
|------|----------|
| 舍入到最近，平局取偶（round to nearest, ties to even） | 默认（避免统计偏差） |
| 向 +inf 舍入 | 始终向上舍入 |
| 向 -inf 舍入 | 始终向下舍入 |
| 向零舍入 | 截断 |

### 6. 特殊值

- **零（zero）**：带符号（+0 与 -0）
- **无穷大（infinity）**：以可控方式处理溢出
- **NaN（非数，not a number）**：在计算中传播，用于错误检测

共有五种异常类型：无效运算（invalid operation）、除零（division by zero）、溢出（overflow）、下溢（underflow）、不精确（inexact）。

---

## 影响

- **被普遍采用**：Intel 8087（1980 年，在标准正式发布前对草案的实现）、Motorola 68881（1984 年），随后是 SPARC、MIPS、ARM、POWER 和 GPU。
- **可移植性**：相同的仿真在不同体系结构上产生完全相同的结果。
- **算法设计**：有保证的契约使人们能够对误差界（error bounds）进行推理。
- **硬件专门化**：专用浮点运算单元（FPU，floating-point unit）为浮点工作负载带来了显著的性能与能效提升。

### 局限性

- 融合乘加（FMA，fused multiply-add）在 1985 年尚未定义；IEEE 754-2008 将其列为推荐运算，而非强制要求。
- 十进制运算（2008 年）的硬件支持有限。
- 机器学习（ML）工作负载（bfloat16、FP8）超出了该标准的范围。
- 标准本身约有 84 页，但要做到完全符合标准，仍需要谨慎处理舍入、异常和特殊值。

---

## 我的思考

IEEE 754 是精心设计的标准的教科书式范例。关键经验如下：

1. **为实现者而设计**：偏置指数体现了对硬件约束的理解。最好的标准会顺应实现的物理规律。

2. **保留信息**：NaN 载荷（NaN payload）、带符号零、渐进下溢——这些都体现了“不要丢弃信息”的理念。这种保守主义在调试复杂的数值应用时会有回报。

3. **明确的权衡（trade-off）**：每一项选择（精度与范围、硬件成本与软件正确性）都有文档记录，使实现者能够在约定的边界内进行优化。

4. **测试很重要**：Pentium FDIV 缺陷（1994 年，4.75 亿美元（$475M）召回）表明，即使是好的标准也可能被糟糕地实现。标准需要严格的符合性测试（compliance testing）。

5. **谨慎演进**：2008/2019 年的修订在保持向后兼容（backward compatibility）的前提下增加了十进制、FMA 和新格式。破坏性变更会分裂整个生态系统；缓慢的演进使该标准保持了 40 多年的生命力。

总体而言：IEEE 754 是现代计算中默默无闻的支柱之一，从嵌入式传感器到超级计算机，一切皆因其成为可能。

---

## 参考文献

1. IEEE Standard for Floating-Point Arithmetic. (2019). *IEEE Std 754-2019 (Revision of IEEE 754-2008)*, pp.1-84. doi:10.1109/IEEESTD.2019.8766229.

2. Goldberg, D. (1991). What Every Computer Scientist Should Know About Floating-Point Arithmetic. *ACM Computing Surveys*, 23(1), 5-48. doi:10.1145/103162.103163.

3. Kahan, W. (1996). The Baleful Effect of Computer Design on Numerical Analysis. *Lecture Notes, University of California, Berkeley*.

4. Intel Corporation. (1994). FDIV Replacement Program. *Intel White Paper*.

5. Patterson, D. A., & Hennessy, J. L. (2013). *Computer Organization and Design: The Hardware/Software Interface* (5th ed.). Morgan Kaufmann. Chapter 3: Arithmetic for Computers.
