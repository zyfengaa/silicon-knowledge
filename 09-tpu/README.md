# 09 — Google TPU

> 从搜索广告到 Gemini——Google 自研 AI 芯片的演进史。理解每代 TPU 的核心设计决策和 trade-off。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **自研动机** | Google 为什么要自己做 TPU 而不用 NVIDIA GPU |
| 02 | **TPU v1** | 推理专用、65K MAC 脉动阵列、PCIe 卡形态、DDR3 |
| 03 | **TPU v2** | 增加训练能力、BFLOAT16 浮点格式、4×4 chip 拓扑 |
| 04 | **TPU v3** | v2 增强版、液冷、两倍算力和带宽 |
| 05 | **TPU v4** | 光互连（OCS）、SparseCore、4096 chip pod |
| 06 | **TPU v5p** | 最新一代：进一步扩展计算和互联能力 |
| 07 | **核心架构** | MXU（矩阵乘单元）、HBM 统一内存、指令集 |
| 08 | **TPU Pod** | 多 chip 互联拓扑、集合通信优化 |
| 09 | **软件栈** | XLA 编译器、JAX / TensorFlow on TPU |
| 10 | **TPU vs GPU** | 在训练/推理场景的全面对比 |

## 前置知识

- [08 NPU](/08-npu/)（脉动阵列、量化、AI 编译器）

## 建议学习方式

1. 阅读 TPU v1~v4 的四篇 ISCA 论文笔记（papers/ 目录）
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
- Jouppi, N. et al. "A Scalable Architecture for Cloud TPU." *ISCA'18*. (TPU v2/v3)
- Jouppi, N. et al. "TPU v4: An Optically Reconfigurable Supercomputer..." *ISCA'21*.
- [Google Cloud TPU 文档](https://cloud.google.com/tpu/docs)
- [JAX 官方文档](https://jax.readthedocs.io/)
