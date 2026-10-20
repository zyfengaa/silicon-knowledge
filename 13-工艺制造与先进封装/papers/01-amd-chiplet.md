# AMD Chiplet 架构论文笔记

> **论文信息**
> - **Title**: “AMD Chiplet Architecture for High-Performance Desktop and Server Processors”
> - **Authors**: Samuel Naffziger, Kevin Lepak, Milam Paraschou, Mahesh Subramony
> - **Venue**: IEEE International Solid-State Circuits Conference (ISSCC), 2020, pp. 44–45
> - **DOI**: 10.1109/ISSCC19947.2020.9063103
> - **对象**: Zen 2 架构的 “Rome”（EPYC 7002 服务器）与 “Matisse”（Ryzen 3000 桌面）产品
> - **引用说明**: 该文常被写作 “ISCA 2020”，实际发表于 ISSCC 2020；更完整的期刊/会议扩展版是 Naffziger et al., “Pioneering Chiplet Technology and Design for the AMD EPYC and Ryzen Processor Families,” *ISCA 2021*, pp. 57–70。本篇以 ISSCC 2020 的架构描述为主，并用 ISCA 2021 补充成本与设计细节。

## 一句话贡献

AMD 把一颗本应越来越大的单体 SoC 拆成“多个 7nm 计算芯粒（CCD）+ 一颗 12nm I/O 芯粒（IOD）”，用成熟封装内的 Infinity Fabric 重新集成，证明了芯粒（Chiplet）不只是良率技巧，而是一种可以跨产品复用的架构与经济策略。

## 背景

2010 年代后期，单片大 die 同时撞上三堵墙。第一是**掩模版（Reticle）**：单次曝光视场约 26 × 33 mm（约 858 mm²），更大的 die 需要拼接曝光，成本和良率迅速恶化。第二是**良率**：泊松模型 `Y = exp(-A·D0)` 下，die 面积越大，碰到致命缺陷的概率越高，而 7nm 晶圆又极其昂贵。第三是**模拟电路不缩放**：DDR PHY、PCIe SerDes、模拟 PLL 和 I/O 在先进节点上几乎不缩小，继续用 7nm 制造它们等于“用最贵的硅做最不划算的事”。

AMD 在 Zen 1（2017）上仍采用单体设计：一个 die 内放多个 4 核 CCX。到了 Zen 2，AMD 做了一个在当时相当激进的决定：把计算与 I/O 彻底分开，计算 die 用 TSMC 7nm，I/O die 用 GlobalFoundries 12nm，再通过封装内的 Infinity Fabric 连接。这个决定后来成为 AMD 服务器与桌面产品线的共同基础。

## 核心概念

### 1. 为什么拆 die：把“面积”换成“可管理的面积”

Zen 2 的 **CCD（Core Chiplet Die，核心芯粒）** 约 74 mm²，7nm，约 39 亿晶体管，包含 8 个 Zen 2 核心、每核 512 KB L2、以及 32 MB 共享 L3（由 2 个 CCX 各 16 MB 组成）。**IOD（I/O Die，I/O 芯粒）** 在服务器 Rome 上约 416 mm²、12nm、约 83 亿晶体管，包含 8 通道 DDR4 控制器与 PHY、128 条 PCIe 4.0 lane、Infinity Fabric、系统管理、安全与测试逻辑；桌面 Matisse 的 IOD 约 125 mm²、约 21 亿晶体管。

Rome 用 8 个 CCD + 1 个 IOD，得到 64 核、总硅面积约 1,008 mm²、约 395 亿晶体管；Matisse 用 1–2 个 CCD + 1 个 IOD，最多 16 核。关键不是“总面积变小了”——芯粒方案的总硅面积反而更大——而是**每一块面积都放在了合适的节点上**，并且每块面积都小到良率可接受。

拆分的收益可以归纳为四条：

1. **节点混搭**：只有计算逻辑用 7nm；DDR/PCIe/模拟用 12nm，按每平方毫米成本计算便宜得多。
2. **良率与损失粒度**：一颗 CCD 只有 74 mm²，坏一颗只损失 74 mm²，而不是一整颗 600 mm² 的 64 核 die；测试通过的 CCD 才进入封装（KGD）。
3. **复用与产品分层**：同一颗 CCD 和同一颗 IOD 可以组合出 16/32/48/64 核多个 SKU；坏掉部分核心的 CCD 可以降级出售，掩模 NRE 被多产品摊薄。
4. **上市时间**：小 die 的物理设计、时序收敛和验证更容易并行；I/O 芯粒可以独立于计算芯粒迭代。

代价也很明确：D2D 接口占用芯片边缘面积和功耗；跨 die 访问延迟高于片内；封装从单 die 变成多 die 模块，组装、测试和电源完整性都更复杂。芯粒不是“免费的分拆”，而是一笔用封装换硅面积的交易。

### 2. Infinity Fabric：把两颗 die 重新粘成一颗 SoC

芯粒之间不能靠普通 PCB 走线，否则带宽和延迟都无法支撑内存与一致性流量。AMD 用 **Infinity Fabric（IF）** 作为封装内互连：它不是简单的“总线”，而是覆盖片内、die 间和 socket 间的可扩展互连家族。Zen 2 的 **IF2** 在 CCD 与 IOD 之间使用源同步的并行链路，论文给出的 IFOP SerDes 数据率约 14.6 GT/s，每链路约 39 条接收 lane、31 条发送 lane，并把总线宽度从上一代的 256-bit 提升到 512-bit（论文公开数据，具体聚合带宽随链路数与时钟变化）。

IF 的工程要点有三条：

- **短距并行**：CCD 与 IOD 在同一有机基板上，距离只有毫米到厘米级，不需要长距 SerDes 的均衡和时钟恢复，延迟与每比特能量都更低。
- **时钟域**：IF 的 FCLK 与内存时钟（MCLK）存在 1:1 或分频关系，桌面平台常用 1:1 模式降低跨时钟域开销；服务器平台则更关注带宽与 NUMA 拓扑。
- **一致性**：IF 承载缓存一致性、内存请求与 I/O 流量；跨 CCD 的访问要经过 IOD，因此延迟高于同 CCX 内访问。操作系统看到的 NUMA 拓扑、BIOS 的内存交织设置，会直接影响跨 CCD 性能。

Rome 的 8 通道 DDR4-3200 提供约 204.8 GB/s 的内存带宽，这些流量都要经过 IOD 和 IF 才能到达 CCD。IF 因此不仅要“连得上”，还要在 8 个 CCD 之间公平分配带宽，并避免某一条链路成为热点。

### 3. 良率/成本 trade-off：芯粒不是自动更便宜

用泊松模型做一个简化比较。假设一颗假想的 600 mm² 单体 7nm 64 核 die，D0 = 0.1 defects/cm²：

```
单体 600 mm²（6 cm²）：Y = exp(−0.6) ≈ 0.549
CCD 74 mm²（0.74 cm²）：Y = exp(−0.074) ≈ 0.929
8 颗 CCD 全好：0.929⁸ ≈ 0.555
```

在“所有 CCD 都必须好”的前提下，整组良率与单体几乎相同——泊松模型下，良率只取决于总面积，拆 die 本身不会凭空提高整组良率。芯粒的真正收益来自另外三处：

1. **损失粒度**：单体坏一个区域可能报废 600 mm²；芯粒坏一颗只报废 74 mm²，其余 CCD 仍可降级或用于其他 SKU。
2. **KGD 与封装成本**：只把测试通过的 CCD 送进封装，避免为坏 die 支付 IOD、基板、组装和测试费用。
3. **节点成本**：416 mm² 的 IOD 放在 12nm 上，每平方毫米成本远低于 7nm；如果把它也做成 7nm，面积和晶圆价格都会让总成本大幅上升。

因此，芯粒的账不能只看“每片晶圆能切多少颗”，而要把节点价格、KGD 测试、封装良率、SKU 分档和 NRE 摊销一起算。AMD 的贡献在于把这笔账做成了可复用的产品平台，而不是只为一颗芯片定制的封装方案。

### 4. 硬件映射：CCD、IOD 与封装

| 项目 | Rome（EPYC 7002） | Matisse（Ryzen 3000） | 口径/来源 |
|------|-------------------|-----------------------|-----------|
| CCD 工艺/面积 | 7nm / 约 74 mm² | 7nm / 约 74 mm² | 公开资料，2019–2020 |
| CCD 内容 | 8 核、2×CCX、32 MB L3、512 KB L2/核 | 同左 | 论文/公开架构资料 |
| IOD 工艺/面积 | 12nm / 约 416 mm² | 12nm / 约 125 mm² | 公开资料，2019–2020 |
| CCD 数量 | 8 | 1–2 | 产品配置 |
| 核心数 | 最高 64 | 最高 16 | 产品规格 |
| 内存 | 8 通道 DDR4-3200，约 204.8 GB/s | 双通道 DDR4-3200，约 51.2 GB/s | 厂商规格 |
| PCIe | 128 lane PCIe 4.0 | 24 lane PCIe 4.0 | 厂商规格 |
| 封装 | 有机基板多 die 模块（MCM） | 有机基板 MCM | 论文/产品资料 |
| 总晶体管 | 约 395 亿 | 依配置 | 公开资料 |

这张表最重要的两行是“封装”和“IOD 工艺”。AMD 的芯粒方案**没有使用硅中介层**，而是把 CCD 和 IOD 直接放在有机基板上，靠 IF 的短距并行链路连接。这使它的封装成本远低于 CoWoS，但互连密度也远低于 2.5D 硅中介层；它适合 CPU 这种“每毫米边缘带宽需求相对可控”的产品，而不是 HBM 那种需要上千根并行线的场景。

### 5. 与 13-06、13-07、14-06 的对应

- **与 [13-06 Chiplet 与 UCIe](../notes/06-chiplet-ucie.md)**：AMD 是“为什么拆 die”的经典案例，但 IF 是私有互连，不是 UCIe。UCIe 后来把 D2D 的物理层、适配层和协议层标准化，解决的问题正是 AMD 当年用私有 IF 解决的问题——互操作、多源供应和生态复用。AMD 的拆分粒度（8 核/CCD）也说明：D2D 开销决定了“拆到哪里为止”。
- **与 [13-07 先进封装](../notes/07-advanced-packaging.md)**：Zen 2 用的是有机基板 MCM，不是 CoWoS-S/L。它的凸点间距在 100–150 µm 量级，带宽密度远低于 25–55 µm 的先进封装；这与 [13-06](../notes/06-chiplet-ucie.md) 中“标准封装 vs 先进封装”的 5–6× 带宽密度差一致。到了 MI300X，AMD 才把 chiplet 与 CoWoS/SoIC 结合，用 2.5D + 3D 封装承载 HBM 和 XCD。
- **与 [14-06 Die 成本](../../14-可靠性与成本模型/notes/06-die-cost.md)**：14-06 的成本公式 `每颗合格 die 成本 ≈ 晶圆价格 /（毛 die 数 × 良率）` 可以直接套在 CCD 和 IOD 上。芯粒方案把“一颗大 die 的良率”拆成“多颗小 die 良率的乘积 + 封装良率”，再用 12nm IOD 拉低每平方毫米成本；NRE 则靠跨 SKU 复用摊薄。把这三项一起算，才是完整的芯粒成本模型。

## 论文的论证方式与关键结果

这是一篇**产品架构论文**，不是受控实验论文。它的证据主要是芯片面积、晶体管数、工艺节点、链路参数和产品配置，而不是在同一 workload 下与 Intel 单体 CPU 的逐项对比。因此读它时要区分三类陈述：

1. **可核验的硬数据**：CCD 74 mm²、7nm、约 39 亿晶体管；Rome IOD 416 mm²、12nm、约 83 亿晶体管；8 CCD + 1 IOD、64 核、约 395 亿晶体管、约 1,008 mm² 总硅面积。
2. **架构参数**：IF2 的 14.6 GT/s IFOP、39 RX/31 TX lane、512-bit 总线宽度；8 通道 DDR4-3200、128 lane PCIe 4.0。这些是论文/厂商公开的设计参数，不是第三方实测。
3. **经济性主张**：小 die 良率更高、12nm IOD 更便宜、KGD 避免浪费、跨 SKU 复用摊薄 NRE。这些主张方向正确，但具体节省比例取决于 D0、晶圆价格、封装良率和产品组合，论文没有给出可直接复现的完整成本表。

论文最有力的“结果”其实是产品线的可扩展性：同一颗 CCD 和同一颗 IOD 覆盖 16–64 核多个 EPYC SKU，以及桌面 6–16 核 Ryzen；这种复用能力是单体大 die 很难做到的。它证明了芯粒不只是“把 die 切小”，而是把**计算、I/O、封装和产品分层**解耦成可组合的模块。

## 局限与边界

- **没有 HBM，也没有硅中介层**：Zen 2 面向 CPU，不是 AI 加速器；它的有机基板 MCM 无法支撑 8 堆 HBM 和 10 TB/s 级 D2D，所以不能把它的封装结论直接套到 GPU 上。
- **跨 die 延迟与 NUMA**：CCD 到 IOD 再到另一颗 CCD 的路径比片内长；NUMA 拓扑和内存交织会显著影响实际性能，论文的架构视角不会替软件把这些成本消掉。
- **私有 IF 的生态代价**：IF 让 AMD 可以自由优化，但也意味着第三方芯粒不能直接复用；UCIe 之后的开放生态是另一条路线。
- **12nm IOD 的面积代价**：Rome 的 IOD 达到 416 mm²，虽然每平方毫米便宜，但绝对面积不小，且模拟/IO 的功耗和良率仍是约束；这不是“把 I/O 挪出去就免费”。
- **引用口径**：本篇按用户指定主题阅读“AMD Chiplet Architecture”，但该标题的实际会议是 ISSCC 2020；把会议写对，是理解“产品论文”与“学术论文”证据强度的第一步。

## 我的反思

第一，芯粒首先是一道**经济学题**，不是封装炫技。AMD 在 2019 年没有等 UCIe，也没有用昂贵的硅中介层，而是用有机基板 + 私有 IF 把成本压到可量产的水平。这说明“先进”不等于“最先进工艺”，而是“在约束下最优的组合”。

第二，芯粒会把一些问题从“片内”推到“系统”：跨 CCD 延迟、NUMA 拓扑、IF 带宽分配、BIOS 调优都会影响实际性能。软件和系统工程师不能只看核心数，还要看数据放在哪个 CCD、内存控制器挂在哪个 IOD 上。

第三，引用要较真。这篇论文常被写成 “ISCA 2020”，但实际是 ISSCC 2020；ISCA 2021 的 Industrial Product 论文才是更完整的版本。仓库写作规范要求“所有内容有据可查”，这次核对本身就是一个很好的练习：**先确认论文的会议、年份和版本，再谈它的结论**。

第四，Zen 2 的方案有明确边界：有机基板 + 私有 IF 适合 CPU，但不适合需要 8 堆 HBM、10 TB/s D2D 的 AI 加速器。这也是为什么 MI300 系列最终转向 CoWoS/SoIC，而 UCIe 在 2022 年后成为芯粒生态的共同语言。芯粒的“拆分粒度”和“互连密度”必须跟着产品带宽需求走，不能照搬。

## 参考文献

1. Naffziger, S., Lepak, K., Paraschou, M., & Subramony, M. “AMD Chiplet Architecture for High-Performance Desktop and Server Processors.” *IEEE ISSCC*, 2020, pp. 44–45. — Zen 2 CCD/IOD、IF2、Rome/Matisse 的架构与封装描述。
2. Naffziger, S., Beck, N., Burd, T., Lepak, K., Loh, G. H., Subramony, M., & White, S. “Pioneering Chiplet Technology and Design for the AMD EPYC and Ryzen Processor Families: Industrial Product.” *ISCA*, 2021, pp. 57–70. — 芯粒成本、良率、KGD 与产品化的扩展讨论。
3. AMD. *AMD EPYC 7002 Series Processors* and *Ryzen 3000 Series* product documentation, 2019–2020. — 核心数、内存通道、PCIe lane 与封装规格。
4. 本仓库 [13-06 Chiplet 与 UCIe](../notes/06-chiplet-ucie.md). — 拆分动机、D2D 带宽密度、UCIe 与私有互连的对比。
5. 本仓库 [13-07 2.5D/3D 先进封装](../notes/07-advanced-packaging.md). — 有机基板 MCM 与 CoWoS/EMIB 的封装密度/成本差异。
6. 本仓库 [14-06 Die 成本](../../14-可靠性与成本模型/notes/06-die-cost.md). — 晶圆价格、良率、NRE 与每颗合格 die 成本模型。
7. UCIe Consortium. *Universal Chiplet Interconnect Express (UCIe) 1.0 Specification*, 2022. — 芯粒互连标准化的后续演进。
