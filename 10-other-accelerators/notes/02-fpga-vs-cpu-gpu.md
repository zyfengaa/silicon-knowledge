# 02 — FPGA vs CPU / GPU

> 在加速器选型中，FPGA 常被视为 CPU 和 GPU 之外的"第三条路"。它的优势不在峰值算力，而在**深度流水线**、**确定性的低延迟**和**优秀的能效比**。本章通过具体场景分析 FPGA 的适用边界。

---

## 1. 架构对比概览

| 维度 | CPU | GPU | FPGA |
|------|-----|-----|------|
| 计算模型 | 指令驱动（Von Neumann） | SIMT + SIMD | 数据流（Dataflow） |
| 控制开销 | 高（取指 + 译码 + OOO） | 中（Warp 调度） | 无（指令开销为零） |
| 并行粒度 | 线程级（~10 核） | 线程级（数千核） | 流水线级（自定义深度） |
| 时钟频率 | 3-5 GHz | 1.5-2 GHz | 200-500 MHz |
| 峰值 TFLOPS (FP32) | ~1-2 | ~30-80 | ~1-10（DSP 受限） |
| 延迟 | 微秒级（中断/调度） | 数十微秒（Kernel 启动） | 纳秒级（纯硬件） |
| 每瓦性能 | 低 | 中 | 高 |
| 编程难度 | 低 | 中 | 高（HDL / HLS） |

---

## 2. FPGA 的核心优势

### 2.1 深度流水线

在 FPGA 中，你可以为每个计算阶段创建一个独立的硬件流水线级：

```
CPU 实现 FIR 滤波器:          for(i=0;i<N;i++) sum += x[i]*h[i];  // 串行 N 次乘加
FPGA 实现 FIR 滤波器:         x[n] → [×h0]→[+]→[×h1]→[+]→[×h2]→[+]→ ... 输出
                              x[n-1] → [×h0]→[+]→[×h1]→[+]→ ...
                              x[n-2] → [×h0]→[+]→ ...
```

- CPU 每周期只能执行一条指令
- GPU 需要启动 kernel 并调度 warp
- FPGA 的每个乘法器和加法器都在独立硬件中并行工作，**没有指令取指/译码/调度开销**

### 2.2 极低延迟

FPGA 的延迟由**组合逻辑深度**和**寄存器级数**决定，而不是由指令调度和缓存层次决定：

| 操作 | CPU 延迟 | GPU 延迟 | FPGA 延迟 |
|------|---------|---------|----------|
| 简单数学运算 | ~3-5 ns | ~1-10 μs | ~5-10 ns |
| 网络包处理 | ~1-10 μs | 不适用 | ~100 ns |
| AI 推理 (小批次) | ~1-10 ms | ~100 μs-1 ms | ~1-10 μs |

### 2.3 能效比

FPGA 在相同功耗下往往能提供更高的每瓦性能：

```
FPGA 优势来源:
1. 无指令开销 → 无取指/译码功耗
2. 定制数据位宽 → 不需要 32/64 位宽运算
3. 定制存储层次 → 不需要 cache 一致性协议
4. 深度流水线 → 每个计算单元每周期都有用
```

---

## 3. FPGA 的劣势

### 3.1 峰值算力

FPGA 的时钟频率（约 300 MHz）远低于 GPU（约 1.5-2 GHz）。对于可以同时启动大量线程的大规模并行计算，GPU 在峰值 FLOPS 上有数量级优势：

| 器件 | 时钟 | DSP/核心数 | TFLOPS (FP32) |
|------|------|-----------|--------------|
| Xilinx VU9P | ~300 MHz | 6840 DSP | ~4.2 (INT8) |
| NVIDIA A100 | 1.4 GHz | 6912 CUDA | 19.5 |
| NVIDIA H100 | 1.8 GHz | 18432 CUDA | 67 |

### 3.2 编程难度

| 方法 | 难度 | 开发效率 | 性能上限 |
|------|------|---------|---------|
| HDL (Verilog/VHDL) | 高 | 低 | 最高 |
| HLS (Vivado HLS, Vitis) | 中 | 中 | 中-高 |
| OpenCL (Intel FPGA SDK) | 中 | 中-高 | 中 |
| 普通 C/C++ | 低 | 高 | —（不能用于 FPGA） |

HDL 需要考虑硬件并行、时序、面积等概念，开发者需要额外的硬件思维转换。

---

## 4. FPGA 胜出的场景

### 4.1 网络数据包处理

```
场景: 100 Gbps 线速包处理
需求: 每个包到达后必须在纳秒级做出转发/过滤/标记决策
```

FPGA 可以创建一个完整的包处理流水线：

```
网口 → MAC → 解析器 → 流表查找 → 修改器 → 队列 → 网口
       ↓                   ↓
    物理层           匹配处理
```

GPU 不适合：需要先将包批量收集再处理，引入额外延迟。CPU 不适合：中断 + 协议栈开销导致吞吐不足。

### 4.2 超低延迟推理

```
场景: 高频交易中的 AI 推理
需求: 端到端延迟 < 1 微秒，确定性要求极高
```

FPGA 可以将整个推理模型转化为固定延迟的流水线：

```
输入 → Layer1 → Layer2 → ... → LayerN → 输出
      1周期     1周期           1周期
```

GPU 的 kernel 启动延迟（数十微秒）在这个场景中不可接受。

### 4.3 传感器信号处理

```
场景: 软件无线电（SDR），雷达信号处理
需求: ADC 采样后实时处理，带宽数百 MHz
```

FPGA 的并行性和低延迟使其成为射频和模拟前端之后的默认选择。

### 4.4 原型验证

```
场景: ASIC 流片前的功能验证
需求: 模拟 ASIC 行为，运行真实软件
```

FPGA 可以以接近 ASIC 的速度运行设计，比仿真快几个数量级。

---

## 5. FPGA 不适合的场景

| 场景 | 原因 |
|------|------|
| 通用服务器应用 | IO 瓶颈，开发成本高 |
| 稠密矩阵乘法（大 batch） | GPU 的 Tensor Core 算力远超 FPGA |
| 不规则控制流多的程序 | 硬件调度分支开销大 |
| 需要快速迭代的算法 | HDL 开发周期长 |

---

## 6. FPGA + GPU 异构系统

现代数据中心常采用 FPGA + GPU 的混合方案：

```
FPGA: 预处理（协议解析、数据过滤、压缩/解压）
GPU: 计算核心（模型推理、矩阵运算）
```

例如：
- 百度将 FPGA 用于排序和预处理，GPU 用于深度学习训练
- 微软 Catapult 项目在数据中心部署 FPGA 用于 Bing 搜索排序和网络加速
- AWS F1 实例允许用户自定义 FPGA 加速器

---

## 参考文献

1. Nurvitadhi, E., et al. (2017). "Can FPGAs Beat GPUs in Accelerating Next-Generation Deep Neural Networks?" *FPGA 2017*.
2. Ovtcharov, K., et al. (2015). "Accelerating Deep Convolutional Neural Networks Using Specialized Hardware." *Microsoft Research*.
3. Putnam, A., et al. (2014). "A Reconfigurable Fabric for Accelerating Large-Scale Datacenter Services." *ISCA 2014* (Microsoft Catapult).
4. Caulfield, A. M., et al. (2016). "A Cloud-Scale Acceleration Architecture." *MICRO 2016*.
5. Xilinx. (2020). "Vitis AI User Guide." *UG1414*.
6. Intel. (2021). "Intel FPGA Acceleration Platform." *White Paper*.
