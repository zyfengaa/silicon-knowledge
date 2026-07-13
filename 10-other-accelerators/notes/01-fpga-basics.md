# 01 — FPGA 基础

> FPGA（Field-Programmable Gate Array）是一种可在出厂后通过配置实现任意数字逻辑的半导体器件。与 CPU 的"指令驱动"和 ASIC 的"固定功能"不同，FPGA 的核心特征是**可重构**——你可以把它的硬件逻辑"重写"成任何电路。

---

## 1. FPGA 基本架构

一个现代 FPGA 由三类基本资源构成：

| 组件 | 英文 | 功能 |
|------|------|------|
| **可配置逻辑块** | Configurable Logic Block (CLB) | 实现组合逻辑和时序逻辑的基本单元 |
| **可编程互联** | Programmable Interconnect | 连接不同 CLB 和 I/O 模块的布线网络 |
| **I/O 块** | I/O Block (IOB) | 连接芯片内部逻辑与外部引脚 |

这三部分构成了 FPGA 的"硬件可编程"基础。

---

## 2. CLB 内部结构

每个 CLB 通常包含多个 **Slice**，每个 Slice 由以下元素组成：

### 查找表（LUT — Look-Up Table）

LUT 是 FPGA 实现组合逻辑的核心。一个 **K 输入 LUT** 本质上是一个 2^K × 1 的 SRAM：

```
K-input LUT = 2^K × 1 SRAM
```

- 一个 4 输入 LUT 可以存储 16 个配置位（16×1 SRAM）
- 通过改变这些配置位的值，LUT 可以实现**任意** 4 输入布尔函数
- 比如要实现 F = A·B + C·D，只需要在对应地址位写入 1

| LUT 输入数 | SRAM 大小 | 可实现函数数量 |
|-----------|----------|--------------|
| 4 | 16 bit | 65536 |
| 5 | 32 bit | 2^32 ≈ 4.3e9 |
| 6 | 64 bit | 2^64 ≈ 1.8e19 |

现代 FPGA（Xilinx 7 系列、Ultrascale）通常使用 **6 输入 LUT**，它们可以被拆分为两个 5 输入 LUT 以提高资源利用率。

### 触发器（Flip-Flop）

每个 Slice 中 LUT 之后级联一个 D 触发器，用于存储状态：

```
LUT 输出 → D 触发器 → 输出到互联
        ↓
    可以不使用触发器（纯组合路径）
```

### 多路选择器（Mux）

用于选择不同的输入源，例如：

- LUT 输出 vs. 来自互联的直接输入
- 进位链的输入选择
- 写使能信号选择

---

## 3. 可编程互联

FPGA 内部的可编程互联是使 CLB 能够组成任意复杂电路的关键。

### 互联结构

```
CLB ──→ 交换矩阵（Switch Matrix）──→ 互联线段 ──→ CLB
```

互联资源包括：

| 资源 | 说明 |
|------|------|
| 直接连线 | 相邻 CLB 之间的短连接，延迟最小 |
| 全局布线 | 跨越芯片的长线，用于时钟和复位信号 |
| 交换矩阵 | 可编程的交叉开关，连接水平和垂直布线通道 |

每个交叉点是一个 **可编程开关**（通常用 SRAM 控制的 pass transistor 实现）：

```
      ┌───┐
wire1 ┤   ├── wire3
      │ X │
wire2 ┤   ├── wire4
      └───┘
```

配置位决定开关的通断，从而决定信号的路径。

---

## 4. 配置位流

FPGA 的"可重构"特性来自其配置机制：

### SRAM 基的配置

```
配置位存储 ─→ 写入 SRAM ─→ 控制 LUT 内容 + 开关状态 + I/O 方向
```

1. 上电时，FPGA 从外部存储（Flash / PROM / CPU）加载配置位流
2. 配置位流写入内部 SRAM 单元
3. 每个 SRAM 单元控制一个 LUT 输入、一个互联开关或一个 I/O 方向
4. 配置完成后，FPGA 即成为所设计的电路

### 配置方式

| 方式 | 数据来源 | 特点 |
|------|---------|------|
| 主串模式 | 外部 SPI Flash | FPGA 主动读取 |
| 从串模式 | CPU/MCU | 外部控制器写入 |
| JTAG | 调试器 | 在线调试和编程 |
| SelectMAP | 并行接口 | 快速配置（32/16 bit 并行） |

### 重新配置

- **完全重配置**：重新加载整个位流，电路功能完全改变
- **部分重配置**：只修改 FPGA 的部分区域，其余部分保持运行（高级功能，需要特定器件支持）

---

## 5. FPGA 中的专用硬核

除了 CLB 和互联，现代 FPGA 还集成了多种硬化模块：

| 硬核 | 用途 |
|------|------|
| **DSP Slice** | 乘法器、乘累加（MAC），用于数字信号处理 |
| **块存储器 (BRAM)** | 18kb / 36kb 的双端口 SRAM 块 |
| **PLL / MMCM** | 时钟管理和频率合成 |
| **收发器 (SerDes)** | 高速串行通信（Gbps 级别） |
| **PCIe 硬核** | 实现 PCIe 协议栈 |
| **DDR 控制器** | 与外部 DRAM 的接口 |

这些硬核在面积和功耗上远优于用 LUT 实现同样功能。

---

## 6. FPGA vs. CPU / ASIC

| 维度 | FPGA | CPU | ASIC |
|------|------|-----|------|
| 硬件可重构 | 是 | 否（指令可编程） | 否 |
| 每性能功耗 | 中等 | 差 | 好 |
| 每性能成本 | 中等 | 好 | 差（NRE 极高） |
| 设计周期 | 月级 | 周级 | 年级 |
| 时钟频率 | ~300-500 MHz | ~3-5 GHz | ~1-3 GHz |

FPGA 的优势在于**硬件灵活性**——你可以获得接近 ASIC 的性能和能效，但不需要承担 ASIC 的 NRE（非重复性工程）成本和时间。

---

## 参考文献

1. Xilinx. (2018). "7 Series FPGAs Configurable Logic Block." *UG474*.
2. Xilinx. (2016). "7 Series FPGAs Overview." *DS180*.
3. Altera/Intel. (2020). "Stratix 10 Logic Array Blocks and Adaptive Logic Modules." *User Guide*.
4. Trimberger, S. (2015). "Three Ages of FPGAs." *Proceedings of the IEEE*, 103(4).
5. Kuon, I., & Rose, J. (2007). "Measuring the Gap between FPGAs and ASICs." *IEEE Transactions on CAD*, 26(2).
6. Altera Corporation. (2013). "FPGA Architecture." *White Paper*.
