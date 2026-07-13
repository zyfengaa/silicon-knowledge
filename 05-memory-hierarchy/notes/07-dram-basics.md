# 05-07 DRAM 基础

## DRAM 存储单元

DRAM（Dynamic Random Access Memory）的核心存储单元是一个**电容 + 一个晶体管**：

```
字线 (Word Line) ────┐
                      │
                    ┌─┤
                    │ │ 晶体管
                    └─┤
                      │
位线 (Bit Line) ──────┘
                      │
                    ──┴── 电容（存储电荷表示 1 或 0）
```

- **写**：字线选中时，位线对电容充电（1）或放电（0）
- **读**：字线选中时，检测位线上电容放电产生的微小电压变化
- **破坏性读取**：读操作会放掉电容上的电荷，因此每次读后需要**写回（Restore）**
- **刷新**：电容的电荷会逐渐泄漏，需要周期性**刷新（Refresh）**——约每 64 ms 对所有行重写一次

## DRAM 芯片架构

### 行列结构

DRAM 的存储阵列组织为**行（Row）**和**列（Column）**：

```
行地址 → [行译码器] → ┌─────┬─────┬─────┬─────┐
                       │     │     │     │     │
                       │   行缓冲 (Row Buffer)  │
                       ├─────┴─────┴─────┴─────┤
                       │        存储阵列        │
                       └───────────────────────┘
列地址 → [列译码器] → 选择行缓冲中的列数据输出
```

**一次读操作流程**：

1. **行激活（Row Activation / RAS）**：发送行地址 → 选中行的所有数据复制到**行缓冲（Row Buffer）**（相当于 DRAM 内部的一行缓存）
2. **列选择（Column Access / CAS）**：发送列地址 → 从行缓冲中取出需要的列数据
3. **预充电（Precharge）**：关闭当前行，准备下一次访问

**行冲突**：如果下一次访问的是不同行，需要先 Precharge 再激活新行，延迟较大。连续访问同一行（行缓冲区命中）延迟最低。

```
行缓冲区命中 (同一行): ~10–20 ns
行激活 + 列选择 (不同行): ~50–80 ns
```

### Bank 与 Rank

为了增加并发，DRAM 芯片内部划分为多个独立的 **Bank**（通常 8 或 16 个）。不同 Bank 可以并行激活行和读写数据。

多个 DRAM 芯片并联组成一个 **Rank**（64 位数据位宽）。DIMM（Dual Inline Memory Module）可以包含多个 Rank。

## 同步 DRAM（SDRAM）与 DDR

### SDRAM

同步 DRAM（Synchronous DRAM）与系统时钟同步。所有操作（RAS, CAS, Precharge）在时钟上升沿触发。

### DDR（Double Data Rate）

DDR SDRAM 在时钟的**上升沿和下降沿**都传输数据，因此理论带宽 = 时钟频率 × 2 × 数据位宽。

| 代数 | 时钟频率 (MHz) | 数据传输率 (MT/s) | 单条带宽 (GB/s) | 电压 (V) | 引入年份 |
|------|---------------|-------------------|----------------|---------|---------|
| DDR1 | 100–200 | 200–400 | 1.6–3.2 | 2.5 | 2000 |
| DDR2 | 200–533 | 400–1066 | 3.2–8.5 | 1.8 | 2003 |
| DDR3 | 400–1066 | 800–2133 | 6.4–17.0 | 1.5 | 2007 |
| DDR4 | 800–1600 | 1600–3200 | 12.8–25.6 | 1.2 | 2014 |
| DDR5 | 1600–2800 | 3200–5600 | 25.6–44.8 | 1.1 | 2021 |

### DDR4 与 DDR5 详细对比

| 特性 | DDR4 | DDR5 |
|------|------|------|
| 最大单条容量 | 64 GB (3DS RDIMM) | 512 GB (3DS RDIMM) |
| 最大传输速率 | 3200 MT/s | 6400 MT/s (JEDEC 标准) |
| 标准电压 | 1.2 V | 1.1 V |
| Bank 数 | 16 | 32 (分成 8 Group × 4 Bank) |
| 突发长度 (BL) | 8 | 16 |
| Prefetch | 8n | 16n |
| ECC | 芯片级 (可选) | 片内 ECC (On-Die ECC, 标准) |
| 命令接口 | 单通道 | **双 32-bit 子通道** |
| 训练 | 启动时训练 | 全时训练 (实时反馈均衡) |

**DDR5 的关键改进**：
1. **更高的密度**：3DS 堆叠技术可实现 64 Gb 芯片
2. **更高的带宽**：更高速率，加上双 32-bit 子通道提升了总带宽利用率
3. **片内 ECC**：内部使用部分存储单元作为 ECC，提高了良率和可靠性
4. **双通道**：每个 DIMM 内部有两个独立的 32-bit 子通道，可以同时服务两个请求

## DRAM 控制器的角色

DRAM 控制器（集成在 CPU 或 SoC 中）负责：

1. **地址映射**：将物理地址映射到（Channel, Rank, Bank, Row, Column）
2. **调度**：对多个访问请求进行重排序，优先服务 Row-Hit 请求
3. **时序管理**：满足 DRAM 的时序约束（tRCD, tCAS, tRP, tRAS 等）
4. **刷新**：周期性发送刷新命令

## DRAM 延迟 vs 带宽

现代 DRAM 的**带宽增长远快于延迟改善**：

| 年代 | 典型 DDR | 延迟 (ns) | 带宽 (GB/s) |
|------|---------|-----------|------------|
| 2000 | DDR1-400 | ~100 | 3.2 |
| 2010 | DDR3-1600 | ~80 | 12.8 |
| 2020 | DDR4-3200 | ~70 | 25.6 |
| 2025 | DDR5-6400 | ~65 | 51.2 |

延迟仅改善了约 35%，带宽却提高了 16 倍。这意味着随机访问（小请求、乱序地址）的改善有限，而流式访问（大块连续数据）受益巨大。

## 关键概念

- **DRAM 单元**：1T1C（1 晶体管 + 1 电容），电荷泄漏需要刷新
- **行缓冲**：DRAM 内部"缓存"，连续访问同一行比随机行快数倍
- **DDR**：双倍数据率传输，DDR4 → DDR5 带宽翻倍
- **Bank**：多个独立子阵列，支持并行访问
- **DRAM 控制器**：负责地址映射、调度、时序、刷新

## 参考文献

- Jacob, B. et al., *Memory Systems: Cache, DRAM, Disk*, Morgan Kaufmann, 2008. Chapter 7: DRAM.
- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Section 2.4: Main Memory.
- JEDEC Standard JESD79-4C: DDR4 SDRAM Specification.
- JEDEC Standard JESD79-5: DDR5 SDRAM Specification.
- Mutlu, O., "Memory Scaling: A Systems Perspective", *IEEE International Memory Workshop*, 2017.
- Intel Corporation, *Intel 64 and IA-32 Architectures Optimization Reference Manual*, Section 2.1.7: DRAM.
