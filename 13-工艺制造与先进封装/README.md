# 13 — 工艺制造与先进封装

> 从一粒石英砂到一颗 AI 加速器：晶体管怎么做出来、怎么连起来、又怎么和 HBM 一起装进同一个封装。理解“算力上限”背后的物理与成本边界。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **从硅到晶圆** | 单晶硅如何长成 300 mm 晶圆，几何、缺陷与良率如何约束后续工艺 |
| 02 | **光刻** | 分辨率 R = k₁·λ/NA 与焦深如何决定最小图形；193i、EUV、High-NA 各自能走多远 |
| 03 | **前道工序 FEOL** | STI、阱、High-k/金属栅、源漏与退火如何在同一份热预算内完成 |
| 04 | **后道工序 BEOL** | 铜大马士革、低-k、RC 延迟、中继器与电迁移如何成为性能约束 |
| 05 | **制程节点解密** | 7nm/5nm/3nm 到底指什么；CPP、MP、单元高度与 SRAM 面积怎么比 |
| 06 | **Chiplet 与 UCIe** | 为什么拆 die；D2D 带宽密度、凸点间距与 UCIe 协议栈 |
| 07 | **2.5D/3D 先进封装** | CoWoS、EMIB、Foveros、混合键合与 HBM 堆叠的密度/成本区间 |
| 08 | **封装为什么成为瓶颈** | 热、翘曲、供电、信号完整性、良率如何共同封顶 GPU 的容量与带宽 |

## 前置知识

- [12 半导体器件与 CMOS 电路](../12-半导体器件与CMOS电路/)（PN 结、MOSFET、短沟道效应、CMOS 功耗）
- [05-08 HBM 与 GDDR](../05-存储层次/notes/08-hbm-and-gddr.md)（HBM 的宽接口、堆叠与带宽口径）
- 可选：[11-03 功耗、能效与芯片热设计](../11-系统分析与性能工程/notes/03-power-thermal.md)（Tj、Rth 与封装热阻）

## 建议学习方式

1. 先读 01–02，建立“晶圆 + 光刻”这条制造地基，记住 300 mm、775 µm、26 × 33 mm 曝光场这几个锚点。
2. 再读 03–04，把 FEOL 的热预算账本和 BEOL 的 RC 账本分开理解；两者约束的是不同尺度。
3. 读 05 时不要背节点名，改用 CPP、MP、track 高度和 SRAM 位单元面积做横向比较。
4. 读 06–07 时始终问三个问题：带宽要多高、边缘有多长、封装愿意付多少钱。
5. 最后用 08 做收口，把热、翘曲、供电、信号完整性和良率放回同一张封装约束图。
6. 完成 `exercises/13-process-q.md` 的八组计算，再用 `papers/01-amd-chiplet.md` 对照真实产品的拆分决策。

## 本模块代码

| 文件 | 内容 |
|------|------|
| `code/python/lithography_resolution.py` | 扫描波长、NA 与 k₁，绘制分辨率与焦深曲线，对比 193i / EUV / High-NA |
| `code/python/interconnect_rc.py` | 计算互连电阻、电容与 RC 延迟，演示线宽缩放和中继器分段的效果 |

> 两个脚本把笔记中的公式变成可调参数的曲线，输出图保存在脚本同目录。运行前请确认 `code/python/` 下已有对应文件；若尚未生成，可按 02 与 04 的公式自行实现。

## 关键产出

- [ ] 能解释 300 mm 晶圆的厚度、平坦度与边缘排除为什么进入光刻预算
- [ ] 能用 R = k₁·λ/NA 和 DOF = k₂·λ/NA² 比较 193i、EUV 与 High-NA
- [ ] 能画出 FEOL 主流程，并说明 Gate-Last 如何重排热预算
- [ ] 能计算一条互连的 R、C、RC 延迟，并解释中继器为什么把 L² 变成近似 L
- [ ] 能用 CPP、MP、track 高度与 SRAM 位单元面积比较两个“nm 级”工艺
- [ ] 能估算 10 TB/s 的 die-to-die 带宽需要多长芯片边缘，并选择封装类型
- [ ] 能解释中介层面积、HBM 堆叠数与凸点间距如何共同封顶 GPU 容量和带宽

## 参考文献

- Plummer, J. D., Deal, M. D., & Griffin, P. B. *Silicon VLSI Technology: Fundamentals, Practice and Modeling*. Prentice Hall, 2000.
- Weste, N. H. E., & Harris, D. *CMOS VLSI Design: A Circuits and Systems Perspective*, 4th ed. Addison-Wesley, 2010.
- Levinson, H. J. *Principles of Lithography*, 4th ed. SPIE Press, 2019.
- UCIe Consortium. *Universal Chiplet Interconnect Express (UCIe) 1.0 Specification*, 2022.
- TSMC. *CoWoS Technology* and *2024 Annual Report*. — 中介层尺寸与封装路线图（公开估算）。
- JEDEC. *JESD238A (HBM3E)* and *JESD270-4 (HBM4)*, 2023–2025.
- Lau, J. H. *Semiconductor Advanced Packaging*. Springer, 2021.
- Naffziger, S. et al. “AMD Chiplet Architecture for High-Performance Desktop and Server Processors.” *ISSCC*, 2020.
- 本仓库 `SPECS.md` §7、§8. — 工艺、封装、良率与成本的课程基线。
