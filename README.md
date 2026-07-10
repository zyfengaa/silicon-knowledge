# Silicon Knowledge ⚡️

> **从晶体管到 TPU，系统性地理解硬件工作逻辑。**
>
> 一个面向软件工程师的硬件学习仓库。不满足于"调 API"，追求知道**代码在硬件上到底怎么跑**。

---

## 🎯 学习目标

读完并动手实践本仓库的内容后，你应该能：

- **写出硬件感知的高性能代码**——知道缓存在哪、SIMD 怎么用、GPU 什么时候划算
- **用工具而不是直觉做性能分析**——能跑 `perf` / `nsys` 找瓶颈，用 Roofline 模型判断是 compute-bound 还是 memory-bound
- **看懂体系结构论文**——能理解 ISCA/MICRO/HPCA 论文的核心思想和技术贡献
- **做知情的硬件选型**——不被厂商峰值 TOPS 忽悠，能从工作负载出发评估 CPU/GPU/NPU/TPU
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

> 建议顺序学习，每个模块的 notes/ 目录下有编号文档，按编号顺序阅读即可。

---

## 📂 仓库结构

```
silicon-knowledge/
├── 01-digital-logic/        # 数字逻辑基础
├── 02-isa-and-cpu-basics/   # ISA 与 CPU 基本组成
├── 03-cpu-pipeline/         # CPU 流水线
├── 04-cpu-advanced/         # CPU 微架构进阶
├── 05-memory-hierarchy/     # 存储层次
├── 06-gpu-architecture/     # GPU 架构
├── 07-cuda-programming/     # CUDA 编程与优化
├── 08-npu/                  # NPU 神经网络处理器
├── 09-tpu/                  # Google TPU
├── 10-other-accelerators/   # 其他加速器
├── 11-system-analysis/      # 系统分析与性能工程
├── projects/                # 综合实践项目
├── GLOSSARY.md              # 术语表
├── ROADMAP.md               # 详细学习路线图
├── STYLEGUIDE.md            # 写作规范
└── tools.md                 # 推荐工具清单
```

每个模块内部遵循统一结构：

```
module-name/
├── README.md        # 本模块学习地图
├── notes/           # 核心笔记（编号文档）
├── code/            # 可运行的代码示例
├── diagrams/        # 架构图（源文件 + PNG）
├── papers/          # 论文阅读笔记
└── exercises/       # 练习题 + 答案
```

---

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/your-username/silicon-knowledge.git
cd silicon-knowledge

# 从第一模块开始
cd 01-digital-logic
# 阅读 notes/ 目录下的笔记，运行 code/ 目录下的代码
```

---

## ✍️ 内容规范

本仓库所有技术内容**必须基于权威参考资料编写**，每篇文章末尾附参考文献列表。

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
| 系统 | *Performance Analysis and Tuning* | 性能分析工具方法论 |

---

## 📄 许可证

本仓库原创内容采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) 协议。
引用的代码和摘录遵循各自原作者的许可证。
