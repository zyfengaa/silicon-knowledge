# 09 — Google TPU

> 从搜索广告到 Gemini——Google 自研 AI 芯片的演进史。理解每代 TPU 的核心设计决策和 trade-off。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **自研动机** | Google 为什么要自己做 TPU 而不用 NVIDIA GPU |
| 02 | **TPU v1** | 推理专用、65K MAC 脉动阵列、PCIe 卡形态、DDR3 |
| 03 | **TPU v2** | 增加训练能力、BFLOAT16 浮点格式、256-chip 2D Torus Pod |
| 04 | **TPU v3** | v2 增强版、液冷、两倍算力和带宽 |
| 05 | **TPU v4** | 光互连（OCS）、SparseCore、4096 chip pod |
| 06 | **TPU v5p** | 第五代训练加速器；并简述 v5e/v6e/v7 |
| 07 | **核心架构** | MXU（矩阵乘单元）、HBM、编译时内存管理与指令集 |
| 08 | **TPU Pod** | 多 chip 互联拓扑、集合通信优化 |
| 09 | **软件栈** | XLA 编译器、JAX / TensorFlow on TPU |
| 10 | **TPU vs GPU** | 在训练/推理场景的全面对比 |

> TPU Pod 的集群组网、调度与液冷属于系统层，见 [why-ai-cluster](https://github.com/zyfengaa/why-ai-cluster)；本模块聚焦 TPU 芯片内部架构。

## 前置知识

- [08 NPU](../08-NPU神经网络处理器/)（脉动阵列、量化、AI 编译器）

## 建议学习方式

1. 阅读 papers/ 目录下的三篇论文笔记：TPU v1（ISCA'17）、TPU v2/v3（CACM 2020）、TPU v4（ISCA'23）
2. 关注每一代"改了什么东西以及为什么改"
3. 在 Google Colab 上启用 TPU 运行时，运行 JAX 示例
4. 完成 TPU vs GPU 的对比表格

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/jax_tpu_basics.py` | JAX on TPU 基本操作（需 Colab TPU 环境） |
| `python/jax_tpu_perf.py` | 在 TPU 上运行简单训练任务并分析性能 |

## 关键产出

- [ ] 能说出 TPU 每一代的核心改进（v1→v2→v3→v4→v5p）
- [ ] 理解为什么 BF16 对训练如此重要
- [ ] 能解释 MXU 和 GPU Tensor Core 的设计差异
- [ ] 理解 OCS 光互连解决了什么问题
- [ ] 能在 Colab TPU 上运行 JAX 训练代码

## 参考文献

- Jouppi, N. et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *ISCA'17*. (TPU v1)
- Jouppi, N. et al. "A Domain-Specific Supercomputer for Training Deep Neural Networks." *Communications of the ACM*, 63(7), 2020. (TPU v2/v3)
- Jouppi, N. et al. "TPU v4: An Optically Reconfigurable Supercomputer..." *ISCA'23*.
- [Google Cloud TPU 文档](https://cloud.google.com/tpu/docs)
- [JAX 官方文档](https://jax.readthedocs.io/)
