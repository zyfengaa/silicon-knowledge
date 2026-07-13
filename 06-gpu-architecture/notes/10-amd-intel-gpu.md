# 10 — AMD 与 Intel GPU 架构

> NVIDIA 并非唯一的 GPU 厂商。AMD 的 CDNA 系列和 Intel 的 Xe 系列在 HPC/AI 领域提供了有价值的替代方案。

---

## 1. AMD CDNA 架构

### CDNA（Compute DNA）

AMD 将其 GPU 架构分为两个系列：
- **RDNA（Radeon DNA）**：面向游戏图形
- **CDNA（Compute DNA）**：面向计算/AI/HPC

CDNA 专注于：
- 矩阵运算加速（Matrix Core）
- 高带宽内存（HBM）
- 统一内存架构（Unified Memory Architecture）
- Infinity Architecture（片间互联）

### CDNA 1 (MI100, 2020)

- 基于 **Arcturus** GPU
- **Matrix Core**：专为矩阵乘法设计的硬件单元（类似 Tensor Core）
- FP32 矩阵运算：46.1 TFLOPS
- FP16 矩阵运算：184.6 TFLOPS
- 120 CU（Compute Units），每个 CU 64 个 shader core
- HBM2e：1.2 TB/s 带宽
- **关键特性**：支持 BF16 格式（AI 训练）

### CDNA 2 (MI250, 2021)

- 基于 **Aldebaran** GPU（双 die 封装）
- **Matrix Core 改进**：增加结构化稀疏支持
- FP16/BF16 矩阵运算：383 TFLOPS
- HBM2e：3.27 TB/s
- **Infinity Fabric 3.0**：片间互联
- OAM（OCP Accelerator Module）封装
- 双 die 设计，每 die 112 CU（220 CU 总计）

### CDNA 3 (MI300X, 2023)

- **小芯片设计（Chiplet）**：
  - 4 个 GCD（Graphics Compute Die，5nm），每个 GCD 包含 40 CU
  - 8 个 HBM3 堆栈
  - 通过 Infinity Fabric 互联
- **Matrix Core**：第 3 代，FP8、TF32、Block FP6 支持
- FP32：~163 TFLOPS
- FP16/BF16：~327 TFLOPS（稀疏模式 653 TFLOPS）
- HBM3：5.3 TB/s
- 总显存：192 GB HBM3

```
MI300X 架构示意：
┌─────────────────────────────────┐
│ ┌──────┐  ┌──────┐             │
│ │ GCD0 │  │ GCD1 │  HBM3 x8    │
│ │ 40CU │  │ 40CU │  ………         │
│ └──┬───┘  └──┬───┘             │
│    │Infinity │                 │
│ ┌──▼───┐  ┌──▼───┐             │
│ │ GCD2 │  │ GCD3 │             │
│ │ 40CU │  │ 40CU │             │
│ └──────┘  └──────┘             │
└─────────────────────────────────┘
总 CU: 160（计算单元）
```

### AMD ROCm 软件栈

AMD 的开源 GPU 计算平台，对标 NVIDIA CUDA：

| 组件 | CUDA | ROCm |
|------|------|------|
| 驱动 | NVIDIA Driver | AMDGPU / ROCk |
| 运行时 | CUDA Runtime | HIP Runtime |
| BLAS | cuBLAS | rocBLAS |
| 深度学习 | cuDNN | MIOpen |
| 通信 | NCCL | RCCL |
| 并行库 | Thrust | rocThrust |

**HIP（Heterogeneous Interface for Portability）**：CUDA 代码可以相对容易地移植到 HIP，进而运行在 AMD GPU 上。

---

## 2. Intel Xe 架构

### Xe 系列架构

Intel 将其 GPU 架构分为多个系列：
- **Xe LP**：低功耗（集成 GPU）
- **Xe HPG**：高性能游戏（Arc 系列）
- **Xe HP**：高性能计算（已取消）
- **Xe HPC**：超级计算（Ponte Vecchio / Max 系列）

### Xe Core 基本结构

```
Xe Core 结构（Ponte Vecchio）：
┌─────────────────────────────────────┐
│    Xe Core x8（每 SLICE）           │
│  ┌─────────────────────────────┐   │
│  │  EU（Execution Unit）x16    │   │
│  │  ┌──────┐ ┌──────┐         │   │
│  │  │ FP32 │ │ FP32 │          │   │
│  │  │ INT32│ │ INT32│          │   │
│  │  └──────┘ └──────┘          │   │
│  │  ┌──────┐ ┌──────┐         │   │
│  │  │ XMX  │ │ XMX  │          │   │   ← Xe Matrix eXtensions
│  │  └──────┘ └──────┘          │   │
│  │  Shared Local Memory (SLM)  │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Xe Matrix eXtensions (XMX)

Intel 的 Tensor Core 实现：

- 支持 INT8、INT16、BF16、FP16 矩阵运算
- 与全局和本地内存的紧密集成
- 编程接口：Intel oneAPI DPC++ 和 oneMKL

### Ponte Vecchio (PVC, Xe HPC)

Intel 的小芯片设计超级计算 GPU：

- **复杂的小芯片堆叠**：47 个芯片（tile）组成一个封装
  - 16 个 Xe-HPC 核心（计算）
  - 8 个 Rambo 缓存芯片
  - 16 个 HBM2e 堆栈 + 2 个 Xe Link I/O 芯片
- 总计：128 EU（Execution Units）
- XMX 单元：2048
- FP32：~23 TFLOPS
- FP16/BF16：~90 TFLOPS
- HBM2e：2.45 TB/s
- **XE Link**：Intel 版 NVLink，提供 GPU-GPU 互联

### Intel Max 系列 (2023)

Intel 的 Max 系列 GPU（原 Ponte Vecchio）是 Aurora 超级计算机的核心组件：

| 规格 | Max 1550 |
|------|---------|
| Xe Core 数量 | 128 |
| XMX 单元 | 1024 |
| FP32 TFLOPS | ~16.7 |
| BF16 TFLOPS（密集）| ~67 |
| 显存 | 128 GB HBM2e |
| 显存带宽 | ~3.3 TB/s |
| 封装功耗 | 600 W |

### Intel oneAPI 软件栈

Intel 的统一编程模型，支持 CPU、GPU、FPGA、专用加速器：

```cpp
// SYCL (DPC++) 示例 — Intel oneAPI 的核心
#include <sycl/sycl.hpp>

void vector_add(sycl::queue &q, float *a, float *b, float *c, int N) {
    q.parallel_for(sycl::range<1>(N), [=](sycl::id<1> i) {
        c[i] = a[i] + b[i];
    }).wait();
}
```

oneAPI 通过 Data Parallel C++ (DPC++) 提供跨厂商的统一编程接口，与 CUDA 和 HIP 形成竞争。

---

## 3. 架构特性对比表

| 特性 | NVIDIA H100 | AMD MI300X | Intel Max 1550 |
|------|------------|-----------|---------------|
| **架构** | Hopper | CDNA 3 | Xe HPC |
| **工艺** | TSMC 4N | TSMC 5nm + 6nm | Intel 7 + TSMC 5nm |
| **封装** | 单 die（814 mm²） | 4 GCD + 8 HBM 小芯片 | 47 小芯片堆叠 |
| **FP32** | 67 TFLOPS | 163 TFLOPS | 16.7 TFLOPS |
| **FP16/BF16** | 989 TFLOPS | 1,308 TFLOPS（稀疏） | 67 TFLOPS |
| **INT8** | 1,979 TOPS | 2,615 TOPS（稀疏） | 134 TOPS |
| **专有矩阵单元** | 第 4 代 Tensor Core | 第 3 代 Matrix Core | XMX |
| **显存容量** | 80 GB HBM3 | 192 GB HBM3 | 128 GB HBM2e |
| **显存带宽** | 3.35 TB/s | 5.3 TB/s | 3.3 TB/s |
| **HBM 类型** | HBM3 | HBM3 | HBM2e |
| **GPU 互联** | NVLink 4（900 GB/s） | Infinity FA（896 GB/s） | Xe Link |
| **互联交换机** | NVSwitch | Infinity Hub | N/A |
| **虚拟化** | MIG（最多 7 实例） | SR-IOV | N/A |
| **编程模型** | CUDA | HIP/ROCm | oneAPI/DPC++ |
| **AI 生态** | TensorRT, cuDNN | MIOpen, MIGraphX | oneDNN, OpenVINO |
| **典型应用** | 训练 + 推理 | 训练 + 推理 | HPC + 推理 |

---

## 4. 生态与竞争力分析

### NVIDIA 优势

- **CUDA 生态成熟度最高**：最大量的优化库、工具链、框架支持
- **Tensor Core 持续创新**：每一代都是新的精度/性能标杆
- **NVLink + NVSwitch**：多 GPU 互联能力无可匹敌
- **从训练到推理的一致体验**：同一代码栈覆盖数据中心和边缘

### AMD 优势

- **显存容量优势**：MI300X 192 GB 显存（对 LLM 训练有利）
- **开放性**：ROCm 开源，HIP 兼容 CUDA，支持异构
- **Chiplet 架构**：通过小芯片组合降低 Die 成本
- **Infinity Architecture**：GPU-CPU 统一内存设计（MI300A）

### Intel 优势

- **oneAPI 愿景**：跨平台统一编程模型
- **XMX 矩阵引擎**：功能上与 Tensor Core 对等
- **复杂封装技术**：Foveros 3D 堆叠
- **HPC 领域经验**：Aurora 超级计算项目的深度参与

### 整体趋势

| 趋势 | 说明 |
|------|------|
| **精度降低但保留精度** | FP64 → FP32 → FP16 → FP8 → FP4/FP6 |
| **小芯片化** | 单 die 面积受限，chiplet 多 die 集成 |
| **显存膨胀** | 80GB → 192GB → 288GB（H200/MI325X） |
| **复杂度上升** | 从 ~3B（Fermi）到 ~208B（Blackwell）晶体管 |
| **开放生态竞争** | CUDA vs ROCm vs oneAPI |
| **稀疏计算** | 2:4 结构化稀疏成为标准配置 |

---

## 参考文献

- AMD, *CDNA 3 Architecture Whitepaper*, 2023. Sections: Matrix Core, Infinity Architecture, Chiplet Design.
- AMD, *Instinct MI300X Accelerator Datasheet*, 2023.
- AMD, *ROCm Documentation*, Section: HIP Programming Guide.
- Intel, *Xe HPC (Ponte Vecchio) Architecture Overview*, 2022.
- Intel, *Intel Max Series GPU Datasheet*, 2023.
- Intel, *oneAPI Programming Guide*, Section: Data Parallel C++.
- AMD, *RDNA 3 / CDNA 3 Architecture Release*, 2023. Available at: amd.com
- NVIDIA, *H100 GPU Architecture Whitepaper*, 2022. （作为对比基准）
- Jiang, Z. et al., "Analyzing the Performance of AMD CDNA 2 Architecture for HPC and AI Workloads", *IEEE HPEC*, 2022.
- Intel, "Ponte Vecchio: A Many-Core Processor for HPC and AI", *Hot Chips 33*, 2021.
- AMD, "AMD Instinct MI300 Series Accelerators", *Hot Chips 35*, 2023.
