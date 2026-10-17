# 11 — Hopper 与 Blackwell

> Hopper（2022）和 Blackwell（2024）把 GPU 从"更宽的 SIMT 处理器"推进为"带专用数据搬运与矩阵引擎的异构计算单元"。本篇聚焦这两代架构新增的硬件机制及其编程模型。

---

## 1. Hopper（H100）的关键变化

### 1.1 规格概览

| 项目 | H100 SXM |
|------|----------|
| 计算能力（compute capability） | 9.0 |
| SM 数 | 132 |
| FP32 CUDA Core / SM | 128 |
| Tensor Core / SM | 4（第 4 代，共 528 个） |
| 寄存器 / SM | 65,536 × 32-bit（256 KB） |
| L1 / 共享内存 / SM | 256 KB 统一 SRAM，共享内存最多 228 KB |
| L2 | 50 MB |
| 显存 | 80 GB HBM3，3.35 TB/s |
| NVLink | 第 4 代，900 GB/s（双向） |
| 制造工艺 | TSMC 4N |

H100 每个 SM 仍由 4 个处理分区（processing block）组成，每分区 32 个 FP32 通道、16 个 INT32 通道、16 个 FP64 通道、1 个 Tensor Core 和 8 个 LD/ST 单元。

### 1.2 TMA（Tensor Memory Accelerator）

TMA 是一个**专用的多维数据搬运引擎**，用一条指令完成全局内存与共享内存之间的大块张量拷贝：

- 支持 1D–5D 张量，描述符在主机侧创建（`cuTensorMapEncodeTiled`）；
- 支持 tiled、im2col、multicast 等模式；
- 由 `mbarrier` 完成异步完成通知，不需要每线程计算地址；
- 相比 Ampere 的 `cp.async`（每线程发起、粒度 4/8/16 字节），TMA 大幅减少地址计算和指令开销。

```cuda
// 概念示意（CUDA C++ 的 cuda::memcpy_async / PTX cp.async.bulk）
// 一个线程发起整块拷贝，其余线程等待 mbarrier
if (threadIdx.x == 0) {
    cuda::memcpy_async(smem_tile, gmem_tile, cuda::aligned_size_t<128>(bytes), barrier);
}
barrier.arrive_and_wait();
```

### 1.3 Thread Block Cluster 与 DSMEM

Hopper 引入 **thread block cluster**：一组 block 保证被同时调度到同一 GPC 上，并可通过**分布式共享内存（DSMEM）**直接访问彼此的共享内存：

- 可移植的 cluster 大小最多 8 个 block；通过非可移植属性可申请更大；
- 用 `cluster.sync()` 做簇内同步；
- `cluster.map_shared_rank(ptr, rank)` 取得其他 block 的共享内存地址；
- 适合需要跨 block 复用数据的场景（如大 tile 的矩阵乘、跨 block 归约）。

### 1.4 WGMMA（warpgroup 级矩阵乘）

Hopper 的 Tensor Core 指令从 warp 级 `mma.sync` 扩展为 **warpgroup（128 线程）级 WGMMA**：

- 典型形状 `m64nNk16`（N 可为 8–256 的倍数），一条指令完成更大的矩阵块；
- 操作数可直接来自共享内存（A/B），累加器在寄存器中；
- 与 TMA、warp specialization 配合，形成"生产者 warp 搬数据、消费者 warp 做矩阵乘"的流水线。

### 1.5 Warp Specialization

一个 block 内不同 warp 承担不同角色：

```
Producer warps：TMA 加载 A/B tile → 写入共享内存 → 通知 mbarrier
Consumer warps：等待 mbarrier → 发起 WGMMA → 累加 → 写回
```

这样可以把地址计算、数据搬运和矩阵计算重叠起来，是 Hopper 上 cuBLAS/CUTLASS 高性能 kernel 的常见结构。

### 1.6 FP8 与 Transformer Engine

- 支持 E4M3 与 E5M2 两种 FP8；
- Transformer Engine 在训练中按张量动态选择 FP8/FP16，并维护缩放因子；
- FP8 矩阵乘的吞吐约为 FP16 的 2 倍。

---

## 2. Blackwell（B200）的关键变化

### 2.1 双 die 封装

B200 由**两个计算 die** 通过 NV-HBI 互连组成，对外表现为一颗逻辑 GPU：

| 项目 | B200 |
|------|------|
| 计算能力（compute capability） | 10.0 |
| SM 数 | 148（公开资料存在 148 与约 160 两种说法；NVIDIA 架构 brief 未逐项给出 SM 数。GB100 满配 die 为 160 SM，B300/GB300 为 160 SM） |
| FP32 CUDA Core | 18,944（按 148 SM × 128 FP32/SM 推算） |
| Tensor Core | 第 5 代 |
| L2 | 126 MB |
| 显存 | 192 GB HBM3e，8 TB/s |
| die 间互连 | NV-HBI，10 TB/s |
| NVLink | 第 5 代，1.8 TB/s（双向） |

注意不要把 **NV-HBI**（同一封装内两个 die 之间，10 TB/s）与 **NVLink-C2C**（Grace CPU 与 GPU 之间，Grace Hopper 上 900 GB/s）或 **NVLink**（GPU 之间）混淆。

### 2.2 tcgen05 与 Tensor Memory（TMEM）

Blackwell 的第 5 代 Tensor Core 使用新的 `tcgen05` 指令族：

- 矩阵乘的累加器放在 **TMEM**（Tensor Memory）中，而不是普通寄存器堆；
- 每个 SM 有 256 KB TMEM；
- 支持 **1-SM MMA** 与 **2-SM MMA**（CTA pair）：两个相邻 SM 的 Tensor Core 协同完成更大的矩阵块；
- TMEM 通过 `tcgen05.ld/st` 与寄存器交换数据，矩阵乘期间由 Tensor Core 直接读写。

TMEM 的意义在于把累加器从寄存器压力中解放出来，使更大的 tile 和更深的流水线成为可能。

### 2.3 FP4 / FP6 与第二代 Transformer Engine

- 新增 FP4（含 MXFP4、NVFP4 等带缩放的微缩放格式）和 FP6；
- 第二代 Transformer Engine 支持对 FP4/FP6 的细粒度缩放；
- 低精度格式主要用于推理和大模型训练中的矩阵乘；
- **NF4 不是硬件格式**：它是 QLoRA/bitsandbytes 提出的软件量化格式（NormalFloat 4），与 Blackwell 的 FP4 不是一回事。

### 2.4 其他改进

- 解压引擎（Decompression Engine）：硬件加速 LZ4/Snappy 等压缩数据；
- 更强的 RAS 特性与安全启动；
- 更大的 L2（126 MB）和 HBM3e 带宽（8 TB/s），缓解内存墙。

---

## 3. GB200 NVL72

GB200 NVL72 是一个机架级系统：

- 72 个 Blackwell GPU + 36 个 Grace CPU；
- 通过第 5 代 NVLink/NVSwitch 实现机架内全互联，每 GPU 1.8 TB/s；
- 对软件呈现为一个大的 NVLink 域，可用 NCCL 做跨 72 GPU 的集合通信；
- 与 InfiniBand/Ethernet 的跨机架 scale-out 网络配合使用。

它体现了"scale-up（NVLink 域内） + scale-out（网络）"的两级互连设计。

---

## 4. 编程要点

1. **优先使用库**：cuBLAS、CUTLASS、cuDNN 已经针对 TMA/WGMMA/tcgen05 做了深度优化。
2. **Ampere 代码可移植**：`cp.async`、`mma.sync` 在 Hopper/Blackwell 上仍可用，但拿不到新硬件的全部性能。
3. **Hopper 上手路径**：`cp.async` → TMA + mbarrier → cluster/DSMEM → warp specialization。
4. **Blackwell 上手路径**：先使用 CUTLASS 的 Blackwell kernel；手写 `tcgen05` 需要管理 TMEM 分配、CTA pair 和 mbarrier。
5. **正确性优先**：异步拷贝必须用 `mbarrier`/`cuda::barrier` 建立可见性；跨 block 的 DSMEM 访问需要 cluster 同步。

---

## 参考文献

- NVIDIA, *Hopper H100 GPU Architecture Whitepaper*, 2022.
- NVIDIA, *NVIDIA Blackwell Architecture Technical Brief*, 2024.
- NVIDIA, *CUDA C++ Programming Guide*: Asynchronous Data Copies, TMA, Thread Block Clusters, Warpgroup Matrix Multiply.
- NVIDIA, *PTX ISA*: `cp.async.bulk`, `wgmma`, `tcgen05` 指令说明.
- NVIDIA, *CUTLASS Documentation*: Hopper/Blackwell kernels.
