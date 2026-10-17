# 05-08 HBM 与 GDDR

## 问题背景：传统 DDR 的带宽瓶颈

传统 DDR 内存面临两个根本限制：

1. **引脚有限**：CPU 封装引脚数有限（约 2000–3000），能够分配给 DDR 接口的引脚更少
2. **信号完整性**：高频下 PCB 布线长度限制，更多 DRAM 通道会引入信号完整性问题

对于高性能计算（HPC）、AI 训练、图形渲染等带宽敏感场景，需要远超 DDR5 的带宽。两种主要的高带宽解决方案是 **HBM** 和 **GDDR**。

## HBM（High Bandwidth Memory）

### 核心理念：3D 堆叠 + 宽接口

HBM 将多个 DRAM 芯片垂直堆叠，通过 **TSV（Through-Silicon Via，硅通孔）** 和 **微凸点（Microbump）** 实现芯片间的垂直互联。

```
       ┌──────────────┐
       │  Logic Die   │ ← 控制器/接口逻辑在最底层
       ├──────────────┤
       │  DRAM Die 4  │
       ├──────────────┤
       │  DRAM Die 3  │
       ├──────────────┤
       │  DRAM Die 2  │
       ├──────────────┤
       │  DRAM Die 1  │
       └──────────────┘
              │
     ┌────────┴────────┐
     │  Interposer     │ ← 硅中介层，连接 HBM 和 GPU/CPU
     └──────┬──────────┘
            │
         SoC / GPU
```

**关键特征**：
- **TSV**：在芯片上垂直钻出通孔实现 Die 间互联，每颗 DRAM Die 有数千个 TSV
- **超宽接口**：每个 HBM 堆栈有 **1024 位数据总线**（相比之下 DDR5 只有 64 位）
- **中介层（Interposer）**：硅中介层承载 HBM 堆栈和 GPU/CPU，提供高密度布线

### HBM 各代参数

| 特性 | HBM1 | HBM2 | HBM2e | HBM3 |
|------|------|------|-------|------|
| 最大传输速率 | 1 GT/s | 2 GT/s | 3.2 GT/s | 6.4 GT/s |
| 单堆栈带宽 | 128 GB/s | 256 GB/s | 410 GB/s | 820 GB/s |
| 单堆栈容量 | 1 GB | 8 GB | 16 GB | 16–32 GB（典型 16/24 GB；HBM3E 可达 36 GB） |
| 最大堆栈高度 | 4-Hi | 8-Hi (1 GB/Die) | 12-Hi | 16-Hi |
| 数据总线宽度 | 1024 bit | 1024 bit | 1024 bit | 1024 bit（16 通道 × 64 bit） |
| 电压 | 1.3 V | 1.2 V | 1.2 V | 1.1 V |
| 功耗 | ~4 W/栈 | ~8 W/栈 | ~10 W/栈 | ~12 W/栈 |
| 每引脚带宽效率 | 高 | 高 | 高 | 极高（NRZ，高引脚速率） |

**HBM3 的改进**：
- 采用 **NRZ 信令**，通过提高引脚速率（6.4 Gb/s）获得带宽；PAM-4 等更高阶调制是后续世代的研究方向，并非 HBM3 标准本身
- 支持**伪通道（Pseudo Channel）**：1024 位接口分为 **16 个 64-bit 通道**，每个通道又可拆成 2 个 32-bit 伪通道，降低访问粒度
- 支持更高的堆栈（最高 16-Hi）；按 16 Gb Die 计算，16-Hi 单堆栈为 32 GB；36 GB 属于 12-Hi × 24 Gb 的 HBM3E
- 芯片级 ECC 增强

### HBM 的优势与劣势

| 优势 | 劣势 |
|------|------|
| **超高带宽**：高达 2+ TB/s（4 堆栈 HBM3） | **成本高**：TSV + 中介层制造复杂 |
| **低功耗**：每比特传输能耗远低于 GDDR | **容量受限**：单堆栈容量受堆叠高度与 Die 密度限制（HBM3 最高 32 GB，HBM3E 可达 36 GB） |
| **小尺寸**：2.5D/3D 封装节省 PCB 空间 | **集成复杂**：需要中介层和先进封装 |
| **距离近**：与 GPU/CPU 在同一封装内 | **标准化**：JEDEC 标准，不开放定制 |

## GDDR（Graphics DDR）

### 核心理念：改进 DDR 的高速率版本

GDDR 是专为图形处理优化的 DDR 内存，与传统 DDR 共享基础架构，但针对高带宽进行了优化：

- **更宽的内部总线**：每个 GDDR 芯片 32-bit 数据位宽（DDR 颗粒则有 x4/x8/x16 等配置）
- **更高的时钟频率**：通过更激进的信号技术（如写时钟 WCK）
- **更窄的通道**：适用于 SoC 直连，不兼容标准 DIMM 插槽
- **优化的时序**：牺牲部分延迟换取更高吞吐量

### GDDR 各代参数

| 特性 | GDDR5 | GDDR5X | GDDR6 | GDDR7 |
|------|-------|--------|-------|-------|
| 传输速率 (GT/s) | 6–8 | 10–14 | 14–20 | 28–32 |
| 单芯片带宽 (GB/s) | 24–32 | 40–56 | 56–80 | 112–128 |
| 数据位宽/芯片 | 32-bit | 32-bit | 32-bit | 32-bit |
| 每引脚速率 | NRZ | NRZ | NRZ | PAM-3 |
| 电压 (V) | 1.5 | 1.35 | 1.35 | 1.2 |
| ECC | 无 | 无 | 可选 | 片内 |
| 引入年份 | 2009 | 2015 | 2018 | 2024–2025 |

**GDDR7 的改进**：
- 使用 **PAM-3 信令**（3 级脉冲幅度调制），每个符号传输 1.58 bit
- 支持 **4-Level 错误检测码**
- 独立的数据眼训练，更好的信号完整性

### GDDR 的优势与劣势

| 优势 | 劣势 |
|------|------|
| **成本低**：标准封装，无需 TSV/中介层 | **功耗高**：每比特传输能耗高于 HBM |
| **容量大**：单卡可配 24+ GB | **PCB 面积大**：多芯片排列占用 PCB 空间 |
| **成熟生态**：NVIDIA / AMD 大量使用 | **延迟高**：带宽优先于延迟 |
| **易扩展**：增加芯片数量即可提升容量 | **走线复杂度高**：高频率对布线和阻抗控制要求高 |

## DDR5 vs GDDR6 vs HBM2e vs HBM3 对比

| 特性 | DDR5 | GDDR6 | HBM2e | HBM3 |
|------|------|-------|-------|------|
| **总带宽（典型配置）** | ~38–51 GB/s (单条 DIMM，DDR5-4800–6400) | ~560 GB/s (8 芯片) | ~1.6 TB/s (4 堆栈) | ~3.2 TB/s (4 堆栈) |
| **单接口位宽** | 64-bit | 32-bit | 1024-bit | 1024-bit |
| **容量** | 16–512 GB/DIMM | 1–2 GB/芯片（8/16 Gb）；单卡 2–32 GB | 16 GB/堆栈 | 16–32 GB/堆栈（典型 16/24 GB；HBM3E 36 GB） |
| **延迟** | 低（数十 ns 量级） | 中（约百 ns 量级） | 较高（约百 ns 量级） | 较高（约百 ns 量级） |
| **每 GB 成本** | 低 ($) | 中 ($$) | 高 ($$$$) | 极高 ($$$$$) |
| **每瓦带宽** | 高 | 中 | 高 | 很高 |
| **封装** | DIMM/SODIMM | BGA on PCB | 2.5D 中介层 | 2.5D/3D 中介层 |
| **目标应用** | 通用服务器 | 消费级 GPU | HPC, AI 加速器 | AI, 超算, HPC |
| **标准化组织** | JEDEC | JEDEC (JESD250) | JEDEC (JESD235C) | JEDEC (JESD238) |

> 注：**GDDR6X** 是 NVIDIA 与 Micron 合作的高速变体，采用 PAM-4 信令，并非 JEDEC 标准；不要把它与 JEDEC 的 GDDR6 混为一谈。

## 实际产品中的选择

| 产品 | 内存方案 | 总带宽 | 容量 |
|------|---------|--------|------|
| NVIDIA RTX 4090 | GDDR6X (384-bit) | 1008 GB/s | 24 GB |
| NVIDIA H100 | HBM3 (5 堆栈) | 3.35 TB/s | 80 GB |
| AMD MI300X | HBM3 (8 堆栈) | 5.3 TB/s | 192 GB |
| Intel Xeon (Sapphire Rapids) | DDR5 (8 通道) | 307.2 GB/s（8 × DDR5-4800） | 可达 4 TB |
| Apple M2 Ultra | LPDDR5 (1024-bit) | ~800 GB/s | 192 GB (统一内存) |

## 未来趋势

1. **HBM 持续演进**：HBM4 预计 2026–2027，接口提升到 2048-bit，引脚速率继续提高，Die 密度进入 24/32 Gb 级
2. **GDDR7 普及**：2025 年开始在消费级 GPU 普及
3. **CXL 内存扩展**：通过 CXL 协议连接的池化内存，弥合 DRAM 和 SSD 之间的层次
4. **近内存计算（Processing-in-Memory）**：Samsung HBM-PIM、AIMM 等

## 关键概念

- **HBM**：3D 堆叠 + TSV + 1024-bit 宽接口，带宽最高但成本最贵
- **GDDR**：高速率 DDR 变体，成本/性能平衡，适用于消费级显卡
- **TSV**：垂直互联工艺，HBM 的关键使能技术
- **Interposer**：硅中介层，HBM 和 SoC 的高速互连基板
- **带宽效率**：每瓦带宽、每引脚带宽是重要的比较指标
- **应用驱动选择**：AI/HPC 用 HBM，消费 GPU 用 GDDR，通用服务器用 DDR5

## 参考文献

- JEDEC Standard JESD235B: High Bandwidth Memory (HBM2) Specification.
- JEDEC Standard JESD235C: High Bandwidth Memory 2E (HBM2E) Specification.
- JEDEC Standard JESD238: High Bandwidth Memory 3 (HBM3) Specification.
- JEDEC Standard JESD238A: High Bandwidth Memory 3E (HBM3E) Specification.
- JEDEC Standard JESD250: Graphics Double Data Rate 6 (GDDR6) SDRAM Specification.
- NVIDIA Corporation, "NVIDIA H100 Tensor Core GPU Architecture", Whitepaper, 2022.
- AMD, "AMD CDNA 3 Architecture Instruction Set Architecture", Whitepaper, 2023.
- Hwang, K.-D. et al., "A 16Gb/s/pin 8Gb GDDR6 DRAM with Bandwidth Extension Techniques for High-Speed Applications", *IEEE ISSCC*, 2018, DOI: 10.1109/ISSCC.2018.8310258.
- "A 16Gb 18Gb/s/pin GDDR6 DRAM with Per-Bit Trainable Single-Ended DFE and PLL-less Clocking", *IEEE ISSCC*, 2018, DOI: 10.1109/ISSCC.2018.8310255.
- CXL Consortium, *Compute Express Link Specification* (current revision).
- Samsung, "HBM-PIM: Processing-in-Memory Accelerator", Hot Chips 33, 2021.

> 注：GDDR6X（PAM-4）由 NVIDIA 与 Micron 定义，不属于 JEDEC 标准，因此没有对应的 JEDEC 规范编号。
