# 硬件规格基线（SPECS）

> 本文件是仓库内硬件数字的**单一事实来源**。各模块笔记引用规格时应与本表一致；
> 若需要更细的架构解释，请回到对应模块。
>
> **读表前先看口径**：
> - **单芯片 / 单板卡 / 单 Pod** 是三种完全不同的口径，表中逐项标注。
> - **dense（稠密）** 与 **sparse（稀疏，通常 2:4）** 是两种峰值口径，未标注时默认 dense。
> - **GB**（10⁹ 字节）与 **GiB**（2³⁰ 字节）不同；厂商标称常混用，表中保留其原始口径。
> - 峰值算力是**硬件理论上限**，实际可达性能取决于 kernel、精度路径、内存带宽与并行策略。
> - 标注“约/量级”的数字是工程估算，不应作为采购或验收依据。
> - 精度格式（FP16/BF16/TF32/FP8/FP4……）与执行单元、累加器的对应关系见 [06-12 精度与硬件](06-GPU架构/notes/12-precision-hardware.md)。

---

## 1. NVIDIA 数据中心 GPU

| 项目 | V100 SXM | A100 SXM 80GB | H100 SXM | H200 SXM | B200 | B300/GB300 | Rubin（路线图） |
|------|----------|---------------|----------|----------|------|------------|----------------|
| 架构 | Volta | Ampere | Hopper | Hopper | Blackwell | Blackwell Ultra | Vera Rubin |
| 工艺 | TSMC 12nm | TSMC 7nm | TSMC 4N | TSMC 4N | TSMC 4NP（双 die） | TSMC 4NP（双 die） | 未公开（公开报道称 3nm） |
| SM 数 | 84 | 108 | 132 | 132 | 148（公开资料另有约 160 之说） | 160 | 未公开 |
| FP32 CUDA Core | 5,376 | 6,912 | 16,896 | 16,896 | 18,944（按 148 SM 推算） | 20,480（按 160 SM 推算） | 未公开 |
| L2 | 6 MB | 40 MB | 50 MB | 50 MB | 126 MB | 126 MB（沿用 GB100） | 未公开 |
| 显存 | 32 GB HBM2 | 80 GB HBM2e | 80 GB HBM3 | 141 GB HBM3e | 192 GB HBM3e | 288 GB HBM3e | HBM4（容量未公开；公开报道 288 GB 级） |
| 显存带宽 | 900 GB/s | 2,039 GB/s | 3.35 TB/s | 4.8 TB/s | 8 TB/s | 8 TB/s | ~13 TB/s（厂商口径） |
| FP32 | 15.7 TFLOPS | 19.5 TFLOPS | 67 TFLOPS | 67 TFLOPS | ~80 TFLOPS（推算） | ~86 TFLOPS（推算） | 未公开 |
| FP16/BF16 Tensor（dense） | 125 TFLOPS | 312 TFLOPS | 989 TFLOPS | 989 TFLOPS | 2,250 TFLOPS | 未公开（按 SM 数推算约 1.1×） | 未公开（官方只给相对口径） |
| FP8 Tensor（dense） | — | — | 1,979 TFLOPS | 1,979 TFLOPS | 4,500 TFLOPS | 未公开（按 SM 数推算约 1.1×） | 未公开 |
| FP4 Tensor（dense） | — | — | — | — | 9,000 TFLOPS | 约 B200 的 1.5×（厂商口径） | 未公开 |
| GPU 间互联 | NVLink 2 | NVLink 3 | NVLink 4 | NVLink 4 | NVLink 5 | NVLink 5 | NVLink 6（路线图） |
| TDP | 300 W | 400 W | 700 W | 700 W | 1,000 W | 1,400 W | ~1,800 W（厂商口径） |

B200 由两个计算 die 通过 **NV-HBI（10 TB/s）** 组成一个逻辑 GPU。NVIDIA 的架构 brief 未逐项确认 B200 的 SM 数，公开资料存在 148 与约 160 两种说法；B300/GB300 为 160 SM。表中 B200 行按 148 SM 计。

B300/GB300 与 Rubin 的数字来自厂商发布和公开路线图。Rubin 尚未量产，绝对算力、容量与功耗应以最终产品规格为准；NVIDIA 对 Rubin 主要给出“相对 Blackwell 约 3.3×（推理）”这类相对口径。

消费级参考：RTX 4090 为 16,384 CUDA Core、24 GB GDDR6X、384-bit、1,008 GB/s。

---

## 2. AMD / Intel 数据中心加速器

| 项目 | AMD MI250X | AMD MI300X | Intel Max 1550 |
|------|------------|------------|----------------|
| 计算单元 | 220 CU（2 die × 110） | 304 CU（8 XCD × 38） | 128 Xe Core |
| 矩阵单元 | 2 × 2 Matrix Core/CU | Matrix Core | 1,024 XMX |
| 显存 | 128 GB HBM2e | 192 GB HBM3 | 128 GB HBM2e |
| 显存带宽 | 3.2 TB/s | 5.3 TB/s | 3.2 TB/s |
| FP32 | 47.9 TFLOPS | 163.4 TFLOPS | 52.4 TFLOPS |
| FP16/BF16（dense） | 383 TFLOPS | 1,307.4 TFLOPS | 832 TFLOPS |
| FP8（dense） | — | 2,614.9 TFLOPS | 1,664 TFLOPS |
| FP64 | 47.9 TFLOPS | 81.7 TFLOPS | 52.4 TFLOPS |

MI300X 不支持 FP6。MI300X 的 FP16/BF16 稀疏峰值为 2,614.9 TFLOPS，FP8 稀疏峰值为 5,229.8 TFLOPS。

---

## 3. Google TPU

| 项目 | v1 | v2 | v3 | v4 | v5p | v5e | v6e (Trillium) | v7 (Ironwood) |
|------|----|----|----|----|-----|-----|----------------|---------------|
| 发布 | 2015 | 2017 | 2018 | 2021 | 2023 | 2023 | 2024 | 2025 |
| MXU 组织 | 1 × 256×256 | 2 × 128×128 | 4 × 128×128 | 8 × 128×128 | 8 × 128×128 | — | 256×256 级 | — |
| MAC 数/芯片 | 65,536 | 32,768 | 65,536 | 131,072 | 131,072 | — | — | — |
| 峰值（单芯片） | 92 TOPS INT8 | 45 TFLOPS BF16 | 123 TFLOPS BF16 | 275 TFLOPS BF16 | 459 TFLOPS BF16/FP8 | 197 TFLOPS BF16 | 918 TFLOPS BF16 | 4,614 TFLOPS FP8 |
| 片上存储 | 28 MiB | 约 64 MiB（估算） | 约 64 MiB（估算） | 未公开 | 未公开 | — | — | — |
| 显存 | 8 GB DDR3 | 16 GB HBM2 | 32 GB HBM2 | 32 GiB HBM2e | 95 GiB HBM3 | 16 GB HBM2e | 32 GB HBM | 192 GB HBM3E |
| 显存带宽 | ~34 GB/s | ~600 GB/s | ~900 GB/s | ~1.2 TB/s | 2,765 GB/s | ~819 GB/s | — | — |
| 互联 | PCIe | 2D torus | 2D torus | OCS 3D torus | OCS | OCS | OCS | OCS |
| Pod 规模 | — | 256 | 1,024 | 4,096 | 8,960 | 256 | 256 | 9,216 |
| Pod 峰值 | — | 11.5 PFLOPS | ~126 PFLOPS | ~1.1 EFLOPS | ~4.5 EFLOPS（厂商口径） | — | — | ~42.5 EFLOPS FP8 |

关键澄清：

- **v4/v5p 的单个 MXU 仍是 128×128**，不是 128×256；单 MXU 升级到 256×256 是 v6e（Trillium）。
- v4/v5p 每芯片 2 个 TensorCore × 4 个 MXU = 8 个 MXU；131,072 MAC × 2 × 频率即为峰值。
- v4 约 1.05 GHz → 275 TFLOPS；v5p 约 1.75 GHz → 459 TFLOPS。
- 128³ 矩阵乘在**单个** 128×128 MXU 上需要 K=128 个周期；芯片级 16 周期是 8 个 MXU 并行处理不同输出块的**聚合吞吐**口径。
- v2-4 板卡的 180 TFLOPS、v3-8 板卡的 420 TFLOPS 是**板卡合计**，不是单芯片。
- v1 的 28 MiB = 24 MiB 统一缓冲 + 4 MiB 权重 FIFO。
- v4 没有原生 FP8，也不支持 FP64。

---

## 4. NPU 与其他加速器

| 产品 | 计算资源 | 片上存储 | 外部存储 | 峰值 | 功耗 |
|------|---------|---------|---------|------|------|
| Google TPU v1 | 256×256 MXU | 28 MiB | 8 GB DDR3 | 92 TOPS INT8 | 75 W |
| Apple ANE (M4) | 16 核 | 未公开 | 统一内存 | 38 TOPS | SoC 内 |
| Apple ANE (M2 Ultra) | 32 核 | 未公开 | 统一内存 800 GB/s | 31.6 TOPS | SoC 内 |
| Qualcomm Hexagon HVX | 1024-bit 向量 | 未公开 | LPDDR | 未公开 | SoC 内 |
| 华为 Ascend DaVinci | Cube/Vector/Scalar | 未公开 | HBM | 依型号 | 依型号 |
| Cerebras WSE-2 | 850K cores | 40 GB SRAM | — | 未统一口径 | ~23 kW（系统） |
| Cerebras WSE-3 | 900K cores | 44 GB SRAM | — | 125 PFLOPS FP16 | ~23 kW（系统） |
| Groq LPU | 向量/MAC 阵列 | 230 MB SRAM | — | 188 TFLOPS FP16 | 215 W |
| Graphcore IPU | ~1,472 tiles | ~624 KB/tile | — | ~250 TFLOPS | ~300 W |
| SambaNova SN40L | RDU | 520 MB SRAM | 64 GB HBM + 1.5 TB DDR | 未统一口径 | 依系统 |

WSE-2/WSE-3 的功耗是**整机系统**口径，不是单芯片；不同来源对“算力”的精度口径不一致，表中保留最常见口径并注明。

---

## 5. 存储与互连

### 5.1 内存

| 类型 | 引脚速率 | 位宽 | 单器件/单堆栈带宽 | 典型容量 | 备注 |
|------|---------|------|------------------|---------|------|
| DDR5 | 4,800–6,400 MT/s | 64-bit/DIMM | ~38–51 GB/s/DIMM | 16–512 GB/DIMM | 通用服务器 |
| GDDR6 | 14–20 Gb/s | 32-bit | 56–80 GB/s/芯片 | 1–2 GB/芯片 | 显卡 |
| GDDR6X | 19–21 Gb/s | 32-bit | ~76–84 GB/s/芯片 | 1–2 GB/芯片 | PAM-4，非 JEDEC 标准 |
| GDDR7 | 28–32 Gb/s | 32-bit | 112–128 GB/s/芯片 | 2–3 GB/芯片 | PAM-3 |
| HBM2e | 3.2 Gb/s | 1024-bit | ~410 GB/s/堆栈 | 8–16 GB/堆栈 | 2.5D 封装 |
| HBM3 | 6.4 Gb/s | 1024-bit | ~820 GB/s/堆栈 | 16–32 GB/堆栈 | NRZ，16×64-bit 通道 |
| HBM3E | 8–9.6 Gb/s | 1024-bit | ~1.2 TB/s/堆栈 | 24–36 GB/堆栈 | 12-Hi × 24 Gb 可达 36 GB |
| HBM4 | 8 Gb/s（JEDEC 基线） | 2048-bit | ~2 TB/s/堆栈 | 24–64 GB/堆栈 | 16-Hi，24/32 Gb die；CoWoS-L/混合键合 |

### 5.2 互连

| 互连 | 每链路单向 | 每链路双向 | 链路数/设备 | 设备总带宽（双向） |
|------|-----------|-----------|-------------|-------------------|
| PCIe 4.0 x16 | ~25 GB/s | ~50 GB/s | — | ~50 GB/s |
| PCIe 5.0 x16 | ~50 GB/s | ~100 GB/s | — | ~100 GB/s |
| PCIe 6.0 x16 | ~100 GB/s | ~200 GB/s | — | ~200 GB/s（PAM4 + FLIT + FEC） |
| NVLink 2 (V100) | 25 GB/s | 50 GB/s | 6 | 300 GB/s |
| NVLink 3 (A100) | 25 GB/s | 50 GB/s | 12 | 600 GB/s |
| NVLink 4 (H100) | 25 GB/s | 50 GB/s | 18 | 900 GB/s |
| NVLink 5 (B200) | 50 GB/s | 100 GB/s | 18 | 1.8 TB/s |
| TPU v4 ICI | 50 GB/s | 100 GB/s | 6 | ~600 GB/s |
| TPU v5p ICI | — | — | — | 1,200 GB/s |
| NVLink-C2C (Grace Hopper) | — | — | — | 900 GB/s |

PCIe 1.0–5.0 使用 128b/130b 编码；PCIe 6.0 改用 PAM4、FLIT 和 FEC。表中 PCIe 数字为**原始线路速率折算后的有效载荷近似值**，不同编码与开销会带来差异。

### 5.3 NVSwitch 与 NVLink 域

| 项目 | NVSwitch 3 | NVSwitch 4 |
|------|-----------|-----------|
| 端口数 | 64 | 72 |
| 单端口双向带宽 | 50 GB/s | 100 GB/s |
| 单芯片聚合带宽 | ~3.2 TB/s | ~7.2 TB/s |
| 典型部署 | DGX H100：4 颗 | GB200/GB300 NVL72：18 颗（9 个托盘） |
| 单 NVLink 域上限 | 8 GPU | 72 GPU |

NVLink 域上限随代际扩大：H100 8 卡、NVL72 72 卡、Rubin NVL144、Rubin Ultra NVL576（后两者为路线图）。域内走 NVLink/NVSwitch，域间走 InfiniBand 或以太网；DGX SuperPOD 的 256 卡是 32 个 8 卡节点经 IB 互联，不是 256 卡 NVLink 全互联。

UALink 1.0 的端口速率为 800 Gb/s（100 GB/s 单向），ESUN 是 OCP 下基于以太网的 scale-up 工作流；两者都是 NVLink 之外的开放方案。NVLS（NVLink SHARP）在 NVSwitch 内完成集合通信归约，跨机的对应能力是 InfiniBand SHARP（NCCL 中的 CollNet）。

---

## 6. 常用性能分析常量

| 常量 | 取值 | 说明 |
|------|------|------|
| H100 SXM FP16 峰值 | 989 TFLOPS | dense，Tensor Core |
| H100 SXM HBM 带宽 | 3.35 TB/s | 80 GB HBM3 |
| H100 SXM 功耗 | 700 W | SXM 形态 |
| A100 SXM FP16 峰值 | 312 TFLOPS | dense |
| A100 SXM HBM 带宽 | 2,039 GB/s | 80 GB 版本 |
| TPU v4 BF16 峰值 | 275 TFLOPS | 单芯片 |
| TPU v5p BF16/FP8 峰值 | 459 TFLOPS | 单芯片 |
| 典型 CPU 内存延迟 | ~80–120 ns | 本地 NUMA，量级 |
| 典型 GPU 全局内存延迟 | ~400–800 周期 | 量级，依架构 |
| 典型 shared memory 延迟 | ~20–30 周期 | 量级 |
| 典型 L2 延迟 | ~200 周期 | 量级 |

---

## 7. 使用建议

1. **先问口径**：单芯片、板卡、Pod、整机，数字可能差一个数量级。
2. **先问精度**：FP16、BF16、FP8、FP4、INT8 的峰值不可直接比较。
3. **先问 dense/sparse**：2:4 稀疏峰值通常是 dense 的 2 倍。
4. **峰值不等于实测**：用 Roofline 判断瓶颈，用 `ncu`/`perf` 验证；MFU 常显著低于 100%。
5. **找不到可靠来源时写“未公开”**，不要用一个看起来合理的数字填空。

---

## 参考文献

- NVIDIA, *Volta V100 / Ampere A100 / Hopper H100 / Blackwell Architecture Whitepapers*, 2017–2024.
- NVIDIA, *CUDA C++ Programming Guide* and *PTX ISA*.
- AMD, *CDNA 2 / CDNA 3 Architecture Whitepapers*, 2021–2023.
- Intel, *Intel Data Center GPU Max Series Product Brief*, 2023.
- Google Cloud, *TPU v4 / v5p / v5e / Trillium / Ironwood Documentation*, 2023–2025.
- Jouppi, N. P. et al., “In-Datacenter Performance Analysis of a Tensor Processing Unit,” ISCA 2017.
- Jouppi, N. P. et al., “A Domain-Specific Supercomputer for Training Deep Neural Networks,” CACM 2020.
- Jouppi, N. P. et al., “TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings,” ISCA 2023.
- JEDEC, *JESD238 (HBM3)*, *JESD238A (HBM3E)*, *JESD250 (GDDR6)*, *DDR5 SDRAM*.
- Cerebras, *WSE-2 / WSE-3 Product Documentation*; Groq, *LPU Architecture*; Graphcore, *IPU Architecture*; SambaNova, *SN40L*.
