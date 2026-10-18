# 12 — 精度与硬件：哪些模块决定了精度、吞吐与成本

> 本篇是跨模块的“精度视角”总结，把 [01 IEEE 754](../../01-digital-logic/papers/01-ieee754-standard.md)、[04 SIMD](../../04-cpu-advanced/notes/05-simd.md)、[07 Tensor Core](07-tensor-core.md)、[08 量化](../../08-npu/notes/04-quantization.md)、[09 TPU MXU](../../09-tpu/notes/07-tpu-arch-core.md) 中的相关知识点串成一条完整的硬件因果链。

---

## 一句话结论

精度不是一个软件标签，而是**一条硬件通路的选择**：

```
数据格式（位宽 / 指数位 / 尾数位）
        │  ISA 暴露为指令（PTX/SASS、AVX、MXU 指令……）
        ▼
执行单元（FP32/FP64 单元、Tensor Core、SIMD、AMX、MXU）
        │  乘法器阵列 + 数据通路位宽
        ▼
累加器（FP16 / FP32 / INT32）与寄存器 / 片上存储
        │  每元素字节数
        ▼
内存层次与互连（HBM / L2 / shared memory / NVLink）
```

同一个“矩阵乘”在不同精度下走的是不同的物理通路。格式能否使用、峰值多高、误差多大，分别由这条链上的不同环节决定：

| 问题 | 由谁决定 |
|------|---------|
| 能不能用这个精度 | ISA 是否暴露该指令 + 执行单元是否支持 + 产品 SKU 是否屏蔽 |
| 峰值吞吐 | 单元数量 × 每周期 MAC 数 × 时钟；每周期 MAC 数取决于乘法器位宽与打包方式 |
| 数值误差 | 指数位（动态范围）+ 尾数位（有效精度）+ 累加器宽度 |
| 实际性能 | 是否真正走到该单元、内存带宽（每元素字节数）、转换与缩放开销 |
| 面积 / 能耗 | 乘法器与累加器位宽、单元数量、存储位宽 |

---

## 1. 各架构中“执行精度”的模块

### 1.1 GPU：CUDA Core 与 Tensor Core 分工

以 H100 为例，一个 SM 的 4 个分区中，不同精度对应不同的物理单元（详见 [03 GPU 硬件组成](03-gpu-hardware.md)）：

| 单元 | H100 每 SM 数量 | 负责的运算 |
|------|----------------|-----------|
| FP32 单元（CUDA Core） | 128 | FP32 标量 FMA |
| INT32 单元 | 64 | INT32 标量运算 |
| FP64 单元 | 64 | FP64 标量运算（FP64:FP32 约为 1:2） |
| Tensor Core | 4 | 矩阵乘加：FP16 / BF16 / TF32 / FP8 / FP4 / INT8 等 |

关键点：**CUDA Core 不是“一个能算所有精度的核”**。FP32、INT32、FP64 在 SM 内是彼此独立的管线。把 FP64 代码跑在 FP64 单元被削减到 1:64 的消费级 GPU 上，瓶颈首先是单元数量，而不是“GPU 天生不擅长双精度”。

Tensor Core 则是另一条通路，它支持的格式随代际扩展：

| 代际 | 架构 | compute capability | 新增的硬件精度支持 |
|------|------|--------------------|-------------------|
| 第 1 代 | Volta (2017) | 7.0 | FP16 输入 + FP32 累加 |
| 第 2 代 | Turing (2018) | 7.5 | INT8、INT4、INT1 |
| 第 3 代 | Ampere (2020) | 8.0（GA100）/ 8.6（GA10x） | BF16、TF32、FP64 |
| 第 4 代 | Hopper (2022) | 9.0 | FP8（E4M3 / E5M2） |
| 第 5 代 | Blackwell (2024) | 10.0 | FP4、FP6（含 MXFP4 / NVFP4 等块缩放格式） |

FP8 从 Ada（8.9）和 Hopper（9.0）才开始有硬件支持；**Ampere（8.0）只有 BF16/TF32，不支持 FP8**。判断某个 dtype 能否使用，先查 compute capability，再查驱动、PTX 版本和 SKU 是否开放。

“架构支持”不等于“每个 SKU 都开放”：同一代芯片会按产品定位屏蔽部分单元或降低频率，具体以产品规格为准。

### 1.2 CPU：标量 FPU + SIMD 位宽 + 矩阵扩展

CPU 上的精度由三层结构共同决定：

1. **标量 FPU**：FP32 / FP64 各有一条（或多条）FMA 管线。所有现代 x86/ARM 服务器核都支持 FP64，区别在端口数量与延迟。
2. **SIMD 通道宽度**：向量寄存器宽度直接决定每条指令能并行处理多少个元素（详见 [04 SIMD](../../04-cpu-advanced/notes/05-simd.md)）：

| 扩展 | 寄存器位宽 | FP32 lanes | FP64 lanes |
|------|-----------|-----------|-----------|
| SSE | 128-bit | 4 | 2 |
| AVX2 | 256-bit | 8 | 4 |
| AVX-512 | 512-bit | 16 | 8 |

因此同一条 AVX-512 指令，FP64 的理论吞吐只有 FP32 的一半——这是**通道数**决定的，不是浮点单元“偏好”单精度。AMD Zen 4 的 AVX-512 采用 256-bit 数据通路双泵送，512-bit 操作的吞吐也因此受限（见 [07 现代 CPU](../../04-cpu-advanced/notes/07-modern-cpus.md)）。

3. **专用矩阵扩展**：Intel AMX 用独立的 tile 单元（8 个 1 KB tile，TMUL 指令）执行 INT8 / BF16 矩阵乘，与 AVX-512 的位宽无关；Apple M4 的 SME 也是类似思路。它们相当于 CPU 里的“小 Tensor Core”。

### 1.3 NPU / TPU：MAC 阵列本身就是精度单元

TPU / NPU 没有“通用 CUDA Core”这一层，**乘加阵列的位宽在流片时就固定了**：

- TPU v1：256×256 的 INT8 MAC 阵列，32-bit 累加，峰值 92 TOPS；
- TPU v2 及之后：BF16 输入 + FP32 累加，以兼顾训练所需的动态范围；
- TPU v5p：进一步支持 FP8；
- 多数 NPU：INT8 / INT4 MAC 阵列 + 向量单元处理非线性运算。

这意味着：**要支持一种新精度，要么换一颗芯片，要么用软件模拟**。软件模拟（例如在 INT8 阵列上拆成多次计算来模拟 FP16）通常带来数倍的开销，这也解释了为什么低精度格式总是与新的硬件代际一起发布。

---

## 2. 为什么位宽越小，吞吐越高

### 2.1 乘法器成本随位宽超线性增长

乘法器的部分积阵列面积大致随位宽平方增长，浮点还要额外的对齐、规格化与舍入逻辑。Horowitz 在 45nm 工艺下的经典数据显示（量级参考，具体实现依工艺库而变）：

- INT8 乘法器的面积约为 FP32 乘法器的 **1/18**；
- INT8 乘加的能耗约为 FP32 的 **1/18**；
- FP16 / BF16 介于两者之间。

因此同样的面积预算下，可以放更多窄位宽乘法器；同样的乘法器数量下，窄位宽可以跑更高频率、更低电压。这是“低精度峰值更高”的物理基础，也是 [08 量化](../../08-npu/notes/04-quantization.md) 中面积/能耗论证的来源。

### 2.2 Tensor Core 如何把位宽变成吞吐

Tensor Core 执行的是矩阵乘加，每条指令隐含一个 **K 维**（归约长度）。在数据通路宽度固定的前提下，**元素越窄，每个周期能打包进阵列的元素就越多**。

Hopper 的 WGMMA 指令形状是公开的间接证据（同一 `m64nN` 输出 tile）：

| 输入格式 | 每条 WGMMA 的 K 维 | 相对每指令 MAC 数 |
|---------|-------------------|------------------|
| TF32 | 8 | 0.5× |
| FP16 / BF16 | 16 | 1× |
| FP8 | 32 | 2× |

这与厂商标称的峰值比例一致：A100 上 TF32 是 FP16 的一半，H100 上 FP8 是 FP16 的两倍，B200 上 FP4 又是 FP8 的两倍。**K 维翻倍，就是吞吐翻倍**——这是“FP8 为什么是 2×”的架构级解释。

> 注意：NVIDIA 未公开 Tensor Core 内部乘法器的具体组织方式，以上是基于公开 ISA 形状与峰值比例的解释，不是电路级细节。

### 2.3 累加器：精度链上最容易被忽略的一环

“输入精度”和“累加精度”是两件事：

| 输入格式 | 典型累加格式 | 原因 |
|---------|-------------|------|
| FP16 / BF16 / FP8 / FP4 | FP32 | 点积的 K 很大，窄累加器会溢出或丢精度 |
| INT8 / INT4 | INT32 | 整数结果需要足够位宽避免溢出 |

累加器宽度直接影响面积、功耗和可用的 K 大小。FP16 累加虽然更省面积，但最大值只有 65504，长点积很容易溢出；FP32 累加器范围大得多，代价是更宽的数据通路。Tensor Core 把累加器做在阵列内部，Blackwell 更进一步把累加器放进 **TMEM**（Tensor Memory），以缓解寄存器压力（见 [11 Hopper 与 Blackwell](11-hopper-blackwell.md)）。

一个常见误区是“输入用 FP8，所以整个计算都是 8-bit”。实际上 FP8 矩阵乘的累加通常仍是 FP32，**精度损失主要来自输入量化，而不是累加**。

### 2.4 一个算例

假设某 Tensor Core 每周期能处理固定宽度的操作数：

- FP16：每条指令 K=16，完成 `64 × N × 16` 次 MAC；
- FP8：每条指令 K=32，完成 `64 × N × 32` 次 MAC。

在指令发射率相同的情况下，FP8 的 MAC 吞吐正好是 FP16 的 2 倍。TF32 的 K=8，因此是 FP16 的一半。这个比例关系在 A100/H100/B200 的规格表上都能对上。

---

## 3. 存储与互连：精度改变“每字节能算多少”

精度不仅影响计算单元，也改变数据在存储层次中的占用：

- **寄存器**：GPU 寄存器宽度为 32-bit；FP64 占用两个相邻寄存器，FP16 可以把两个值打包进一个寄存器（`half2`）。
- **Shared memory**：bank 宽度通常为 32-bit（4 字节）。FP64 的一次访问会跨两个 bank，FP16 的访问模式则要考虑打包与对齐。
- **HBM 带宽**：同样的字节带宽下，元素越窄，每秒能搬运的元素越多。以 H100 的 3.35 TB/s 为例：

| 格式 | 每元素字节 | 理论元素吞吐 |
|------|-----------|-------------|
| FP32 | 4 | ~0.84 T elem/s |
| FP16 / BF16 | 2 | ~1.68 T elem/s |
| FP8 | 1 | ~3.35 T elem/s |
| FP4 | 0.5 | ~6.7 T elem/s |

这正是低精度对 **memory-bound** 推理特别有效的原因：收益不只来自算力，还来自带宽。但它也会改变 Roofline 上的“算术强度”（FLOP/byte），需要重新判断瓶颈（见 [11 Roofline 模型](../../11-system-analysis/notes/01-roofline-model.md)）。

代价是：格式转换、解包、缩放因子读取都要消耗指令和带宽。如果 kernel 把大部分时间花在 FP32 ↔ FP8 转换上，低精度反而可能更慢。

---

## 4. 块缩放格式：FP4 不只是“4-bit 乘法”

FP4 的尾数只有 1 位，动态范围极小（E2M1 的最大正规数只有 6）。如果直接截断，模型几乎必然发散。因此 Blackwell 的 FP4/FP6 依赖**块缩放（block scaling）**：

| 格式 | 元素格式 | 缩放方式 |
|------|---------|---------|
| MXFP4 | E2M1 | 每 32 个元素共享一个 E8M0 指数（scale） |
| NVFP4 | E2M1 | 每 16 个元素一个 E4M3 scale，外加每张量的 FP32 scale |

这要求硬件具备额外的能力：存储/加载 scale factor、按块应用缩放、处理块边界。PTX 的 `tcgen05` 系列指令支持把块缩放因子放在 TMEM 中供矩阵乘使用。**没有这套缩放硬件，FP4 的可用动态范围不足以支撑真实模型。**

FP8 通常也需要缩放（per-tensor 或 per-channel），只是更多由软件完成——例如 Hopper 的 Transformer Engine 会维护 amax 历史并动态选择 FP8/FP16。E4M3 的最大值只有 448，E5M2 也只有 57344，直接表示大激活值会溢出。

再次强调：**NF4 是软件量化格式（QLoRA/bitsandbytes），不是硬件数据类型**；Blackwell 的硬件低精度格式是 FP4/FP6。

---

## 5. 产品分级与软件：有硅片不等于能用

同一条精度链上，还有两个常被忽略的“闸门”：

### 5.1 产品 SKU 分级

| 产品 | FP64:FP32 比例 | 说明 |
|------|---------------|------|
| H100 SXM | 1:2 | 数据中心卡保留较强 FP64 |
| RTX 4090 | ~1:64 | FP64 单元被大幅削减 |
| Apple M2 Ultra | 无 FP64 硬件 | GPU 不提供双精度 |

消费级 CPU 也会屏蔽指令：Alder Lake 在消费级产品上禁用 AVX-512，AMX 只在部分服务器平台上开放。**“架构支持”与“这个 SKU 能用”是两回事。**

### 5.2 ISA、编译器与库

一条精度指令要真正生效，需要整条软件栈配合：

- PTX / SASS 是否暴露该指令（例如 `wgmma`、`tcgen05.mma`）；
- 驱动与 CUDA 版本是否支持目标架构；
- 库是否选择该路径（cuBLAS 的 math mode、cuDNN 的算法选择）；
- 框架开关（PyTorch 的 `torch.backends.cuda.matmul.allow_tf32`、`torch.set_float32_matmul_precision`）；
- 数据布局与 kernel 形状是否满足该指令的要求（tile 对齐、K 维倍数等）。

所以“硬件支持 FP8”只是必要条件。一个 FP8 kernel 没有走原生指令、或者频繁做格式转换，实测可能还不如 FP16。

---

## 6. 排查表：精度相关问题先查什么

| 现象 | 优先检查 |
|------|---------|
| 某个 dtype 报“不支持” | 架构代际（compute capability）、驱动/PTX 版本、库版本、SKU 是否屏蔽 |
| 实测峰值只有标称的一半/四分之一 | 是否真正走 Tensor Core、dense/sparse 口径、累加精度、时钟/功耗限制 |
| 低精度反而更慢 | 格式转换开销、未使用原生指令、kernel 是 memory-bound、tile 形状不匹配 |
| 数值溢出或不收敛 | 累加器精度、scale 选择、loss scaling、指数范围 |
| 带宽利用率低 | 元素字节数、合并访问、bank conflict、tile 复用 |
| 同型号数字对不上 | 单芯片/板卡/整机口径、dense/sparse、是否含稀疏单元 |

---

## 7. 常见误区

1. **“BF16 尾数比 FP16 少，所以 BF16 更差”**——BF16 的指数位与 FP32 相同，动态范围更大；训练中范围通常比尾数精度更关键。
2. **“FP8/FP4 直接截断就行”**——必须配合缩放；否则 E4M3 最大 448、E2M1 最大 6，根本无法表示真实激活值。
3. **“低精度一定更快”**——只有计算受限时才明显；memory-bound 时收益来自带宽；转换和缩放有开销。
4. **“Tensor Core 峰值就是实测性能”**——MFU 受形状、occupancy、带宽、编译质量影响，通常显著低于 100%。
5. **“FP64 在所有 GPU 上比例相同”**——数据中心卡与消费卡的 FP64 单元数量可能差 32 倍以上。
6. **“NF4 是 Blackwell 的硬件格式”**——NF4 是软件量化格式，硬件格式是 FP4/FP6。

---

## 8. 关键概念总结

- **精度 = 格式 + 执行单元 + 累加器 + 存储宽度**，四者缺一不可。
- **执行单元分工**：GPU 的 FP32/INT32/FP64 单元彼此独立，Tensor Core 是另一条矩阵通路；CPU 靠 SIMD 位宽和 AMX/SME；NPU/TPU 的 MAC 阵列位宽在流片时固定。
- **位宽 → 吞吐**：乘法器面积/能耗随位宽增长；Tensor Core 通过增加每指令 K 维打包更多元素（TF32 k=8、FP16 k=16、FP8 k=32）。
- **累加器**：低精度输入通常配 FP32 累加、INT8 配 INT32 累加；累加宽度影响范围、面积和 K 上限。
- **存储**：元素越窄，同样带宽下元素吞吐越高；但转换与缩放有成本。
- **可用性**：ISA、架构代际、SKU 分级、软件栈共同决定一种精度能否真正跑起来。

---

## 9. 思考题

1. 为什么 TF32 的峰值是 FP16 的一半，而不是相同？请从输入位宽与每指令 K 维两个角度解释。
2. 如果输入用 FP8、累加器也用 FP8，会发生什么？为什么硬件通常坚持 FP32 累加？
3. 一个 memory-bound 的推理 kernel 从 FP16 换到 FP8，理论上带宽收益是多少？实际可能受哪些因素限制？
4. 消费级 GPU 的 FP64 比例远低于数据中心 GPU，这是工艺限制还是产品分级？对科学计算选型有什么影响？
5. MXFP4 为什么每 32 个元素共享一个 scale，而不是每个元素一个？这样做对精度和硬件各有什么取舍？

---

## 参考文献

- Horowitz, M. "Computing's Energy Problem (and what we can do about it)." *ISSCC*, 2014.
- NVIDIA, *Volta V100 / Ampere A100 / Hopper H100 / Blackwell Architecture Whitepapers*, 2017–2024.
- NVIDIA, *PTX ISA*（`wgmma`、`tcgen05` 指令形状与块缩放接口）.
- NVIDIA, *CUDA C++ Programming Guide*, Appendix: Compute Capabilities. — 架构代际与 compute capability 的对应关系.
- Micikevicius, P. et al. "FP8 Formats for Deep Learning." *arXiv:2209.05433*, 2022.
- Kalamkar, D. et al. "A Study of BFLOAT16 for Deep Learning Training." *arXiv:1905.12322*, 2019.
- Rouhani, B. D. et al. "Microscaling Data Formats for Deep Learning." *arXiv:2310.10537*, 2023.
- Intel, *Advanced Matrix Extensions (AMX) Programming Reference*.
- Jouppi, N. P. et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." *ISCA*, 2017.
