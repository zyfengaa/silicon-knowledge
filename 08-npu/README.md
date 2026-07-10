# 08 — NPU 神经网络处理器

> AI 时代最关键的加速器。从脉动阵列到量化、稀疏性、AI 编译器——理解专为神经网络设计的处理器如何工作。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **为什么需要 NPU** | AI 工作负载的计算和内存访问特征 |
| 02 | **脉动阵列** | 一维/二维脉动阵列、三种数据流策略（WS/IS/OS） |
| 03 | **映射 GEMM** | 矩阵乘如何映射到脉动阵列的 PE 上 |
| 04 | **量化** | INT8/INT4/BF16/FP16 格式、训练感知量化、校准 |
| 05 | **稀疏性** | 剪枝、zero-skipping、结构化稀疏与非结构化稀疏 |
| 06 | **片上存储** | SRAM Buffer 设计、数据流调度、内存带宽瓶颈 |
| 07 | **AI 编译器** | TVM / MLIR / XLA 如何将计算图降级到 NPU 指令 |
| 08 | **经典 NPU 案例** | Eyeriss、DianNao、Apple Neural Engine、Qualcomm Hexagon、华为昇腾 |

## 前置知识

- [05 存储层次](/05-memory-hierarchy/)（理解带宽和延迟概念）

## 建议学习方式

1. 从"为什么 GPU 还不够"开始理解 NPU 的设计动机
2. 运行脉动阵列模拟器，观察数据如何在 PE 间流动
3. 读 Eyeriss / DianNao 论文笔记，理解学术界的经典思路
4. 理解量化如何影响硬件面积和能耗
5. 对比不同 NPU 的数据流策略差异

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/systolic_sim.py` | 二维脉动阵列的 GEMM 模拟器，支持切换数据流策略 |
| `python/quantization_demo.py` | FP32 ↔ INT8 量化/反量化过程演示 |
| `python/tvm_demo/` | 使用 TVM 编译和推理简单模型的示例 |

## 关键产出

- [ ] 能手画一个 2×2 脉动阵列，并跟踪一次矩阵乘中每个 PE 的状态变化
- [ ] 能解释 WS（Weight Stationary）和 OS（Output Stationary）的区别和适用场景
- [ ] 理解量化为什么能同时降低模型大小、带宽需求和计算功耗
- [ ] 能对比 NPU 和 GPU 在运行同一推理任务时的优劣
- [ ] 理解 AI 编译器在 NPU 生态中的核心作用

## 参考文献

- Kung, H.T. "Why Systolic Architectures?" *IEEE Computer* 1982.
- Chen, Y.H. et al. "Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow..." *ISCA'16*.
- Chen, T. et al. "DianNao: A Small-Footprint High-Throughput Accelerator..." *MICRO'14*.
- Jouppi, N. et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *ISCA'17*.
- [Apache TVM 文档](https://tvm.apache.org/docs/)
