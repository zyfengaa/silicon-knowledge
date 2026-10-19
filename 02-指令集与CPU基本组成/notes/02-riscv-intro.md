# 模块 02：指令集与 CPU 基本组成
## 02 — RISC-V 导论

### 为什么选择 RISC-V 来学习？

RISC-V 是学习计算机体系结构（computer architecture）的理想指令集架构（ISA），原因有以下几点：

1. **开放且免费**：与 ARM（专有）和 x86（专有）不同，RISC-V 是一个开放标准，不收取许可费。任何人都可以设计、实现和销售 RISC-V 处理器，而无需支付版税。

2. **模块化设计**：RISC-V 被设计为一个小型的基础整数指令集架构（base integer ISA）加上可选的扩展。这使得最小化的实现（例如用于嵌入式系统）和功能丰富的实现（例如用于应用处理器）能够共享同一套指令集架构。

3. **简洁且精简**：RISC-V 去除了 x86 和 ARM 中积累数十年的历史包袱。基础整数指令集架构（RV32I）只包含 40 条指令，可归入六种简单的格式。

4. **学术基础**：RISC-V 由加州大学伯克利分校（UC Berkeley）的 Krste Asanovic、Andrew Waterman 和 David Patterson（权威计算机体系结构教材的合著者）创建，是一套简洁的开放指令集架构，此后在研究界和教育界得到了广泛采用。

5. **产业采用**：RISC-V 已不再只是学术界的项目。SiFive、Esperanto 和 Microchip 等公司都在生产 RISC-V 芯片。Google、NVIDIA 和 Qualcomm 也在大举投资。

### RISC-V 设计原则

RISC-V 遵循清晰的精简指令集（RISC）理念：

| 原则                       | RISC-V 的实现方式                                              |
|----------------------------|----------------------------------------------------------------|
| 固定指令长度（fixed instruction length） | 32 位指令（RV32I/RV64I）；16 位压缩扩展（compressed extension，RVC） |
| 加载/存储架构（load/store architecture） | 只有 `lw`/`sw`（及其变体）访问内存                             |
| 少量寻址模式（addressing modes） | 寄存器、立即数、基址+偏移                                  |
| 大型寄存器堆（register file） | 32 个寄存器（x0--x31），其中 x0 硬连线为零                  |
| 简单的指令格式             | 六种统一格式（R、I、S、B、U、J）                               |
| 没有条件码（condition codes） | 分支直接比较寄存器（类似 MIPS，不同于 ARM32）                  |

### RISC-V 基础整数指令集架构：RV32I

RV32I 是 32 位 RISC-V 的强制基础。每个 RISC-V 实现都必须包含 RV32I（64 位实现则包含 RV64I）。

关键特性：

- **32 位地址空间**（2^32 字节 = 4 GiB）
- **32 个寄存器**（x0--x31），每个寄存器宽 32 位
- **x0** 硬连线为常量 0
- **PC**（program counter，程序计数器）是一个独立的寄存器，不属于寄存器堆（register file）
- **小端（little-endian）** 字节序
- **指令长度为 32 位**（4 字节），对齐到 4 字节边界

#### 寄存器组

| 寄存器   | ABI 名称 | 描述                           | 保存者   |
|----------|----------|--------------------------------|----------|
| x0       | zero     | 硬连线为零                     | --       |
| x1       | ra       | 返回地址                       | 调用者   |
| x2       | sp       | 栈指针                         | 被调用者 |
| x3       | gp       | 全局指针                       | --       |
| x4       | tp       | 线程指针                       | --       |
| x5       | t0       | 临时寄存器 / 备用链接寄存器    | 调用者   |
| x6--x7   | t1--t2   | 临时寄存器                     | 调用者   |
| x8       | s0/fp    | 已保存寄存器 / 帧指针          | 被调用者 |
| x9       | s1       | 已保存寄存器                   | 被调用者 |
| x10--x11 | a0--a1   | 函数参数 / 返回值              | 调用者   |
| x12--x17 | a2--a7   | 函数参数                       | 调用者   |
| x18--x27 | s2--s11  | 已保存寄存器                   | 被调用者 |
| x28--x31 | t3--t6   | 临时寄存器                     | 调用者   |

ABI（应用二进制接口，Application Binary Interface）名称只是一种约定；硬件只能看到 x0--x31。

### RISC-V 扩展

模块化设计允许实现者选择要包含哪些扩展：

| 扩展     | 名称                        | 描述                                             |
|----------|-----------------------------|--------------------------------------------------|
| M        | 整数乘/除                   | 硬件乘法和除法                                   |
| A        | 原子操作                    | 原子内存操作（LR/SC、AMO）                       |
| F        | 单精度浮点                  | 32 位浮点（IEEE 754）                            |
| D        | 双精度浮点                  | 64 位浮点                                        |
| C        | 压缩                        | 用于提高代码密度的 16 位指令                     |
| Zicsr    | CSR 指令                    | 控制和状态寄存器（CSR）访问                      |
| Zifencei | Fence.I                     | 指令流同步                                       |
| V        | 向量                        | 128 位以上的向量/SIMD 操作                       |

**RV32IMAFDZicsr_Zifencei** 这一组合称为 **RV32G**（通用，General-purpose）。大多数应用处理器实现 RV64G。

### 比较：RV32I 与 ARM 及 x86

| 方面              | RV32I（RISC-V）   | ARMv8-A（AArch32） | x86-64（IA-32e）    |
|-------------------|-------------------|-------------------|--------------------|
| 指令数量          | 40                | ~200+             | ~1000+             |
| 固定长度          | 是（32 位）       | 否（A32 为 32 位；Thumb-2 混合使用 16/32 位） | 否（1--15 字节）   |
| 寄存器            | 31 + x0=0         | 15 + PC           | 16 个通用寄存器（GPR，包括 RSP/RBP） |
| 条件码            | 无                | 有（NZCV）        | 有（RFLAGS）       |
| 寻址模式          | 3                 | 约 9              | 约 10+             |
| 许可费            | 无（开放）        | 有                | 有（交叉许可）     |

### RISC-V 工具链入门

要使用 RISC-V 工具链（toolchain）来试验 RISC-V 汇编（assembly）：

```bash
# Install the GNU RISC-V toolchain (Ubuntu/Debian)
sudo apt install gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu

# Compile a C program
# Note: a riscv64-only toolchain usually has no rv32 multilib. If the command
# below fails, install the multilib package or use riscv32-unknown-elf-gcc.
riscv64-linux-gnu-gcc -march=rv32im -mabi=ilp32 -o prog prog.c

# Disassemble to see instructions
riscv64-linux-gnu-objdump -d prog

# Or use the spike simulator
sudo apt install spike pk
```

此外，在线 [RISC-V 解释器](https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/) 也非常适合学习。

---

### 参考文献

1. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213. Available at: https://riscv.org/technical/specifications/
2. Waterman, A. "Design of the RISC-V Instruction Set Architecture." PhD Dissertation, UC Berkeley, 2016.
3. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 2.
4. Asanovic, K., & Patterson, D. A. "Instruction Sets Should Be Free: The Case for RISC-V." Technical Report No. UCB/EECS-2014-146, EECS Department, University of California, Berkeley, August 2014.
5. SiFive Inc. *RISC-V Core IP Documentation*. https://www.sifive.com/risc-v-core-ip
