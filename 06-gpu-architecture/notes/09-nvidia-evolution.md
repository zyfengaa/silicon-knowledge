# 09 — NVIDIA GPU 架构演进

> 从 CUDA 的初步构想到 H100/B200 的万亿晶体管时代，NVIDIA 的 GPU 架构经历了 15 年的持续演进。

---

## 1. 架构演进总览

### 性能演进曲线（FP32 TFLOPS）

| 架构 | 发布 | 工艺 | 晶体管 | 代表 GPU | FP32 TFLOPS |
|------|------|------|--------|---------|-------------|
| Tesla | 2007 | 90nm | 0.68B | G80 | 0.35 |
| Fermi | 2010 | 40nm | 3.0B | GF100 | 1.28 |
| Kepler | 2012 | 28nm | 7.1B | GK104 | 4.5 |
| Maxwell | 2014 | 28nm | 8.0B | GM204 | 6.2 |
| Pascal | 2016 | 16nm | 15.3B | GP100 | 10.6 |
| Volta | 2017 | 12nm | 21.1B | GV100 | 15.7 |
| Turing | 2018 | 12nm | 18.6B | TU102 | 16.3 |
| Ampere | 2020 | 7nm | 54.2B | GA100 | 19.5 |
| Hopper | 2022 | 4N | 80B | GH100 | 67 |
| Blackwell | 2024 | 4NP | 208B | GB100 | 90 |

(注：数据中心级 SKU；消费级数字不同。)

---

## 2. 各架构详解

### Tesla (G80, 2007) — 统一架构之父

- 首次提出统一着色器架构（Unified Shader Architecture）
- 首次引入 CUDA（Compute Unified Device Architecture）
- 将顶点着色器和像素着色器统一为通用计算单元
- 引入 SIMT 执行模型（但 NVIDIA 尚未公开此术语）
- 8 个着色器核心（SP, Shader Processor），16 KB 共享内存
- **历史意义**：证明了 GPU 可以用于通用计算

### Fermi (GF100, 2010) — 第一次重大升级

- **完整 ECC 支持**：显存和缓存都有 ECC 保护
- **缓存层次**：引入 L1/L2 缓存结构
- **双精度**：FP64 性能提升（FP32 的 1/2）

| 规格 | Fermi (GF100) |
|------|---------------|
| SM 数量 | 16 |
| CUDA Core / SM | 32 |
| 总计 CUDA Core | 512 |
| 共享内存 / SM | 16-48 KB（可配置） |
| L2 缓存 | 768 KB |
| 寄存器 / SM | 32,768 (128 KB) |
| 双精度支持 | 1/2 FP32 |

### Kepler (GK104/GK110, 2012) —— 效率和并行度提升

- **SMX**：新的 SM 设计，每个 SM 包含 192 个 CUDA Core
- **Hyper-Q**：64 个硬件工作队列，允许多个 CPU 核心同时向 GPU 提交任务
- **动态并行（Dynamic Parallelism）**：GPU kernel 可以在 GPU 上启动子 kernel（递归式并行）
- **改进的功耗效率**：动态时钟和电压管理
- **Grid Management Unit (GMU)**：更灵活的工作调度

### Maxwell (GM204, 2014) —— 能效优化

- **改进的 SM 设计 (SMM)**：将 SM 分为 4 个独立分区，每个分区 32 个 CUDA Core
- **共享内存 + L1 分割**：共享内存和 L1 可独立配置（不再争用同一物理存储）
- **三级缓存**：引入 unified L1/texture cache
- **功耗大幅优化**：同性能下功耗仅为 Kepler 的 1/2
- **深度学习的硬件准备**：FP16 存储支持

### Pascal (GP100, 2016) —— HBM 和 NVLink

- **HBM2**：首次使用高带宽内存（4096-bit 总线，720 GB/s）
- **NVLink 1.0**：GPU-GPU 直连（160 GB/s 双向）
- **统一内存（Unified Memory）**：CPU/GPU 虚拟地址空间统一
- **FP16 计算**：原生 FP16 指令（2× FP32 吞吐量）
- **更灵活的子线程调度**

### Volta (GV100, 2017) —— Tensor Core 诞生

- **Tensor Core**：新增 4×4 矩阵乘加专用硬件
- **独立线程调度**：每个线程独立 PC 和栈（previous arch warp 内线程共享 PC）
- **改进的 Volta SM**：每个 SM 64 个 CUDA Core + 8 个 Tensor Core
- **更大的共享内存**：96 KB/SM
- **混合精度训练**：FP16 输入 + FP32 累加
- **NVLink 2.0**：300 GB/s 双向

### Turing (TU102, 2018) —— 实时光线追踪

- **RT Core**：实时光线追踪专用硬件（BVH 遍历 + 三角形求交）
- **Tensor Core 2.0**：INT8、INT4 支持，加速推理
- **并发计算+图形执行**：同时执行计算和图形任务
- **Mesh Shader**：新的几何处理管线
- **改进的内存压缩**：色彩压缩效率提高 40%

### Ampere (GA100, 2020) —— MIG 和结构化稀疏

- **MIG（Multi-Instance GPU）**：将一个 A100 切分为最多 7 个独立 GPU 实例
- **第三代 Tensor Core**：TF32、BF16、FP64 Tensor Core 支持
- **结构化稀疏**：2:4 稀疏模式，TFLOPS 翻倍
- **NVLink 3.0**：600 GB/s 双向
- **HBM2e**：2.0 TB/s 带宽
- **L2 缓存大幅提升**：40 MB（V100 的 6.7×）

| 规格 | A100 (GA100) |
|------|--------------|
| 晶体管数 | 54.2B |
| SM 数量 | 108 |
| Tensor Core / SM | 4 |
| 总计 Tensor Core | 432 |
| L2 缓存 | 40 MB |
| HBM2e 带宽 | 2.0 TB/s |
| MIG | 最多 7 实例 |
| NVLink | 12 × 50 GB/s = 600 GB/s |

### Hopper (GH100, 2022) —— Transformer 专优化

- **Transformer Engine**：自动检测、切换 FP8/FP16 精度
- **第四代 Tensor Core**：FP8 支持，TF32 改进
- **DPX 指令**：加速动态规划（Floyd-Warshall、Smith-Waterman）
- **Async Copy**：从全局内存到共享内存的硬件 DMA
- **NVLink 4.0**：900 GB/s 双向
- **NVSwitch 3.0**：全互联数据中心
- **改进的 L2 缓存**：50 MB，partitioned into 24 segments
- **CUDA Graph 改善**：减少 kernel launch 开销

| 规格 | H100 (GH100) |
|------|--------------|
| 晶体管数 | 80B |
| SM 数量 | 132 |
| Tensor Core / SM | 8 |
| 总计 Tensor Core | 1,056 |
| FP8 TFLOPS | 1,979 |
| L2 缓存 | 50 MB |
| HBM3 带宽 | 3.35 TB/s |

### Blackwell (GB100, 2024) —— 新一代

- **第五代 Tensor Core**：FP4、FP6、NF4 支持
- **第二代 Transformer Engine**：更高精度灵活性
- **NVLink 5.0**：1.8 TB/s 双向
- **MIG 增强**：更多分区灵活性
- **208B 晶体管**（TSMC 4NP）：GPU 历史上最复杂的芯片
- **单个芯片集成两个 die**：通过 NVLink-C2C 互联

---

## 3. 代表性 GPU 规格对比

| 架构 | Tesla | Fermi | Kepler | Maxwell | Pascal | Volta | Turing | Ampere | Hopper | Blackwell |
|------|-------|-------|--------|---------|--------|-------|--------|--------|--------|-----------|
| 首发 | 2007 | 2010 | 2012 | 2014 | 2016 | 2017 | 2018 | 2020 | 2022 | 2024 |
| 工艺 | 90nm | 40nm | 28nm | 28nm | 16nm | 12nm | 12nm | 7nm | 4N | 4NP |
| 晶体管 | 0.68B | 3B | 7.1B | 8B | 15.3B | 21.1B | 18.6B | 54.2B | 80B | 208B |
| SM | 16 | 16 | 16 | 16 | 60 | 84 | 72 | 108 | 132 | 168 |
| Core/SM | 8 | 32 | 192 | 128 | 64 | 64 | 64 | 64 | 128 | 128 |
| 总 Core | 128 | 512 | 3072 | 2048 | 3840 | 5376 | 4608 | 6912 | 16896 | 21504 |
| Tensor Core | — | — | — | — | — | 8/SM | 8/SM | 4/SM | 8/SM | 8/SM |
| L2 | 64KB | 768KB | 512KB | 2MB | 4MB | 6MB | 6MB | 40MB | 50MB | ~100MB |
| 带宽 | 86.4 | 177 | 288 | 336 | 720 | 900 | 672 | 2000 | 3350 | ~4000 |
| NVLink | — | — | — | — | v1 | v2 | — | v3 | v4 | v5 |

---

## 参考文献

- NVIDIA, *Fermi GF100 Architecture Whitepaper*, 2010.
- NVIDIA, *Kepler GK110 Architecture Whitepaper*, 2012.
- NVIDIA, *Maxwell GM204 Architecture Whitepaper*, 2014.
- NVIDIA, *Pascal GP100 Architecture Whitepaper*, 2016.
- NVIDIA, *Volta V100 GPU Architecture Whitepaper*, 2017.
- NVIDIA, *Turing T102 GPU Architecture Whitepaper*, 2018.
- NVIDIA, *Ampere A100 GPU Architecture Whitepaper*, 2020.
- NVIDIA, *Hopper H100 GPU Architecture Whitepaper*, 2022.
- NVIDIA, *Blackwell B200 GPU Architecture Whitepaper*, 2024.
- Lindholm, E. et al., "NVIDIA Tesla: A Unified Graphics and Computing Architecture", *IEEE Micro*, 28(2), 2008, pp. 39-55.
- Kanter, D., "NVIDIA's Fermi: The First Complete GPU Computing Architecture", *The Real World Tech*, 2009.
- Kirk, D. B. & Hwu, W. W., *Programming Massively Parallel Processors: A Hands-on Approach*, 3rd ed., Appendix: GPU Architecture History, Morgan Kaufmann, 2016.
- Foley, D. & Danskin, J., "Ultra-Performance Pascal GPU and NVLink", *IEEE Micro*, 2017.
- NVIDIA, *GPU Architecture Timeline*, 2024. Available at: developer.nvidia.com
