# TPU v2/v3 论文精读：A Scalable Architecture for Cloud TPU (ISCA'18)

## 论文信息

- **标题**: "A Scalable Architecture for Cloud TPU"
- **作者**: Norman Jouppi 等 (Google)
- **会议**: ISCA 2018
- **核心贡献**: 描述 TPU v2 和 v3 的训练能力架构

## 为什么需要训练能力

TPU v1 只是推理加速器。Google 在 2015-2016 年面临的问题是：
1. 深度学习训练需求快速增长，GPU 集群的成本和功耗越来越高
2. Google 内部的训练工作负载规模超出现有 GPU 集群的能力
3. 训练需要浮点精度支持反向传播，v1 的 INT8 无法满足

TPU v2 的设计目标是：**用与 GPU 相当的 TCO，提供 10-100× 的训练性能**。

## BF16 格式的创新

v2 的最重要贡献是设计了 **BFLOAT16（BF16）** 浮点格式。

### 设计动机

- FP32 动态范围 $\pm 3.4 \times 10^{38}$ 对训练是必要的（避免梯度消失/爆炸）
- FP16 动态范围 $\pm 6.55 \times 10^{4}$ 在训练大模型时容易溢出
- 完整 FP32 计算单元面积大、功耗高

### BF16 格式

| 格式 | 符号位 | 指数位 | 尾数位 | 动态范围 |
|------|--------|--------|--------|----------|
| FP32 | 1 | 8 | 23 | $\pm 3.4\times10^{38}$ |
| BF16 | 1 | 8 | 7 | $\pm 3.4\times10^{38}$ |
| FP16 | 1 | 5 | 10 | $\pm 6.55\times10^{4}$ |

BF16 的 8 位指数提供了与 FP32 完全相同的动态范围，这是训练的"安全网"。7 位尾数提供的精度在大多数训练场景中足够。

## TPU v2 架构

### Chip 架构

每个 TPU v2 芯片包含：

- **2 个计算核心**（Tensor Core）
  - 每个核心包含一个 **MXU（Matrix Multiply Unit）**
  - MXU 是 128×256 的二维脉动阵列（约 32,768 个 MAC 单元）
  - 每个核心还有 Vector Unit（向量计算）和 Scalar Unit（标量控制）
- **HBM（High Bandwidth Memory）**：8 GB HBM2
- **Interconnect**：2D torus mesh 接口

### Pod 架构

- **4×4 芯片构成一个 "slice"**（同一机架内）
- v2 slice 通过液冷冷却
- 多个 slice 连接为更大的 2D torus pod

## TPU v3：v2 的增强

TPU v3 在 2018 年推出，与 v2 共享架构的基本结构，但做了以下改进：

| 参数 | TPU v2 | TPU v3 |
|------|--------|--------|
| 制程 | 16nm | 16nm（相同） |
| 每芯片核心数 | 2 | 2 |
| 每核心 MXU 数量 | 1 | 2（翻倍） |
| HBM 容量 | 8 GB | 32 GB（4×） |
| HBM 带宽 | 约 600 GB/s | 约 900 GB/s |
| BF16 算力/芯片 | 180 TFLOPS | 420 TFLOPS（2.3×） |
| TDP | 约 200W | 约 450W（需液冷） |
| 冷却 | 空气/液冷 | 液冷（全标准） |

### v3 的关键改进细节

1. **MXU 翻倍**：每个核心从 1 个 MXU 增加到 2 个 MXU，使 GEMM 算力翻倍
2. **HBM 容量 4× 提升**：从 8GB 增加到 32GB，使更大模型可以在单芯片内存中训练
3. **全液冷**：因 TDP 增加到 450W，所有 v3 pod 必须使用液冷

## 2D Torus 互联

TPU v2/v3 使用 2D torus mesh 互联所有芯片：

- 每个芯片有 4 个方向（北、南、东、西）的链接
- 数据通过 XLA 编译的 collective operations（主要是 all-reduce）在芯片间传输
- 优化的环状 all-reduce（ring all-reduce）使梯度同步的高带宽利用率达到 95% 以上

## 训练性能

TPU v3 在 Google 内部广泛部署：

- 训练 Transformer（翻译模型）的速度比 GPU 快约 8 倍
- 训练 BERT-Large 的速度对比：TPU v3 Pod vs 同等价格的 GPU 集群，算力提升约 4.5 倍
- 支持 Google 的 RankBrain、Smart Reply 等生产系统的训练

## 参考文献

- Jouppi, N. et al. "A Scalable Architecture for Cloud TPU." *ISCA'18*.
- Google. "BFLOAT16: The Secret to High Performance Training on TPUs." *Google Research Blog*, 2019.
- Wang, S. et al. "Training Deep Neural Networks with 8-bit Floating Point Numbers." *NeurIPS*, 2018.
- Google Cloud. "Cloud TPU System Architecture." https://cloud.google.com/tpu/docs/system-architecture
