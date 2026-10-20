# Silicon Knowledge ⚡️

> **从半导体器件到 TPU，系统性地理解一颗芯片为什么这样设计。**
>
> 一个面向软件工程师的芯片知识仓库。不满足于"调 API"，追求知道**代码在芯片上到底怎么跑，以及芯片为什么这样造、为什么贵、为什么会坏**。

> **范围说明**：本仓库以**芯片内部**为主线：半导体器件 → CMOS 电路 → 数字逻辑 → CPU/GPU/NPU/TPU 架构 → 工艺/封装 → 可靠性/成本。
> 集群组网、并行训练、调度运维等系统层内容不在本仓库，见兄弟仓库 [why-ai-cluster](https://github.com/zyfengaa/why-ai-cluster)。

---

## 🎯 学习目标

读完并动手实践本仓库的内容后，你应该能：

- **写出硬件感知的高性能代码**——知道缓存在哪、SIMD 怎么用、GPU 什么时候划算
- **用工具而不是直觉做性能分析**——能跑 `perf` / `nsys` 找瓶颈，用 Roofline 模型判断是 compute-bound 还是 memory-bound
- **看懂体系结构论文**——能理解 ISCA/MICRO/HPCA 论文的核心思想和技术贡献
- **理解芯片的物理底座**——知道 MOSFET 如何开关、工艺节点数字意味着什么、封装为什么成为瓶颈
- **算清芯片的成本与风险**——能解释良率、die 成本、电迁移与老化如何影响产品
- **跨层对话**——能用芯片工程师的语言描述你的性能问题

---

## 🗺️ 学习路线

| 模块 | 主题 | 前置依赖 | 预估时间 |
|------|------|---------|---------|
| 01 | 数字逻辑基础 | 无 | 1-2 周 |
| 02 | 指令集与 CPU 基本组成 | 模块 01 | 2-3 周 |
| 03 | CPU 流水线 | 模块 02 | 2 周 |
| 04 | CPU 微架构进阶 | 模块 03 | 2-3 周 |
| 05 | 存储层次 | 模块 02 | 2-3 周 |
| 06 | GPU 架构 | 模块 03 | 3-4 周 |
| 07 | CUDA 编程与优化 | 模块 06 | 2-3 周 |
| 08 | NPU 神经网络处理器 | 模块 05 | 2-3 周 |
| 09 | Google TPU | 模块 08 | 1-2 周 |
| 10 | 其他加速器 | 模块 08 | 1-2 周 |
| 11 | 系统分析与性能工程 | 模块 01~10 | 3-4 周 |
| 12 | 半导体器件与 CMOS 电路 | 模块 01 | 3-4 周 |
| 13 | 工艺制造与先进封装 | 模块 12 | 3-4 周 |
| 14 | 可靠性与成本模型 | 模块 12、13 | 3-4 周 |

> **两条线**：01~10 是"架构主线"（代码如何在硬件上跑）；12~14 是"芯片纵深线"（芯片如何被造出来、为什么贵、为什么坏）。11 是两条线的汇合点，建议在学完 12-07 后再读 11-08。

> 建议顺序学习，每个模块的 notes/ 目录下有编号文档，按编号顺序阅读即可。

---

## 📂 仓库结构

```
silicon-knowledge/
├── 01-数字逻辑基础/              # 数字逻辑基础
├── 02-指令集与CPU基本组成/       # ISA 与 CPU 基本组成
├── 03-CPU流水线/                 # CPU 流水线
├── 04-CPU微架构进阶/             # CPU 微架构进阶
├── 05-存储层次/                  # 存储层次
├── 06-GPU架构/                   # GPU 架构
├── 07-CUDA编程与优化/            # CUDA 编程与优化
├── 08-NPU神经网络处理器/         # NPU 神经网络处理器
├── 09-Google-TPU/                # Google TPU
├── 10-其他加速器/                # 其他加速器
├── 11-系统分析与性能工程/        # 系统分析与性能工程
├── 12-半导体器件与CMOS电路/      # 半导体器件与 CMOS 电路
├── 13-工艺制造与先进封装/        # 工艺制造与先进封装
├── 14-可靠性与成本模型/          # 可靠性与成本模型
├── 专题/                         # 跨模块专题索引（精度/HBM/片间互连/成本）
├── 综合实践项目/                 # 综合实践项目
├── SPECS.md                      # 硬件规格基线（数字口径的单一事实来源）
├── GLOSSARY.md                   # 术语表
├── ROADMAP.md                    # 详细学习路线图
├── STYLEGUIDE.md                 # 写作规范
└── tools.md                      # 推荐工具清单
```

每个模块内部遵循统一结构：

```
module-name/
├── README.md        # 本模块学习地图
├── notes/           # 核心笔记（编号文档）
├── code/            # 可运行的代码示例
├── diagrams/        # 架构图（可选，部分模块提供）
├── papers/          # 论文阅读笔记
└── exercises/       # 练习题 + 答案
```

---

## 🧭 与 why-ai-cluster 的分工

| 主题 | 本仓库 | [why-ai-cluster](https://github.com/zyfengaa/why-ai-cluster) |
|------|--------|-------------------------------------------------------------|
| 半导体器件、CMOS 电路、工艺、封装 | ✅ 原理与约束 | 仅保留选型/采购结论 |
| CPU/GPU/NPU/TPU 微架构 | ✅ 架构机制与代际 | 仅保留"为什么选它" |
| 可靠性、良率、die 成本 | ✅ 失效物理与成本模型 | 仅保留集群 TCO 视角 |
| 集群组网、并行策略、调度运维 | 仅边界链接 | ✅ 完整覆盖 |
| 机柜液冷、PUE、万卡集群 | 仅芯片热设计接口 | ✅ 完整覆盖 |

跨仓库链接使用 GitHub 绝对 URL；本地并排克隆时对应 `../why-ai-cluster/<路径>`。

---

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/zyfengaa/silicon-knowledge.git
cd silicon-knowledge

# 如需阅读跨仓库边界内容，建议并排克隆兄弟仓库
git clone https://github.com/zyfengaa/why-ai-cluster.git ../why-ai-cluster

# 从第一模块开始
cd 01-数字逻辑基础
# 阅读 notes/ 目录下的笔记，运行 code/ 目录下的代码
```

---

## ✍️ 内容规范

本仓库所有技术内容**必须基于权威参考资料编写**，每篇文章末尾附参考文献列表。
硬件规格数字（算力、带宽、容量、功耗）统一以 [SPECS.md](SPECS.md) 为基线，并注明单芯片/板卡/Pod 口径。

详见 [STYLEGUIDE.md](STYLEGUIDE.md)。

---

## 📖 推荐配套教材

| 难度 | 书名 | 侧重 |
|------|------|------|
| 入门 | *Computer Organization and Design RISC-V Edition* (Patterson & Hennessy) | 完整的体系结构概论 |
| 进阶 | *Computer Architecture: A Quantitative Approach* (Hennessy & Patterson) | 定量分析方法论 |
| GPU | *Programming Massively Parallel Processors* (Kirk & Hwu) | CUDA + GPU 架构 |
| GPU | *Professional CUDA C Programming* (Cheng & Grossman) | CUDA 工程实践 |
| NPU | Eyeriss / DianNao 系列论文 | NPU 经典架构 |
| TPU | Google TPU 系列论文 (v1~v4) | 最一手的设计思路 |
| 器件 | *CMOS VLSI Design* (Weste & Harris) | 器件、电路、功耗与延迟 |
| 器件 | *Digital Integrated Circuits* (Rabaey et al.) | 门延迟、功耗、VTC |
| 工艺 | *Silicon VLSI Technology* (Plummer et al.) | 前道/后道制造流程 |
| 封装 | *Heterogeneous Integration Roadmap* / UCIe 规范 | 2.5D/3D、Chiplet、芯粒互连 |
| 可靠性 | JEDEC JEP122 / JEP148 | 失效机制与可靠性认证 |
| 系统 | *Systems Performance* (Brendan Gregg) | 性能分析与工具方法论 |

---

## 📄 许可证

本仓库原创内容采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) 协议。
引用的代码和摘录遵循各自原作者的许可证。
