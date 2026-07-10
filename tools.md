# 推荐工具清单

> 学习本仓库各模块时需要使用到的工具和软件。每个模块标注了会用到的工具。

---

## 通用

| 工具 | 用途 | 安装 | 模块 |
|------|------|------|------|
| **Python 3.10+** | 运行模拟器和可视化脚本 | `apt install python3-pip` | 全部 |
| **Make** | 构建 C/CUDA 代码 | `apt install build-essential` | 全部 |
| **Git** | 版本管理 | `apt install git` | 全部 |
| **VS Code + Markdown Preview** | 阅读和编辑笔记 | 官网下载 | 全部 |

Python 依赖安装：

```bash
pip install numpy matplotlib jupyter
```

---

## 模块 01 — 数字逻辑

| 工具 | 用途 |
|------|------|
| Python 标准库 | 位运算演示（`bin()`、`int()`、`struct` 模块） |

可选（可视化工具）：

| 工具 | 用途 |
|------|------|
| **Logisim Evolution** | 数字逻辑电路图形化设计、仿真（大学教学标准工具） |
| **DigitalJS** | 在线数字电路模拟器（浏览器中运行） |

---

## 模块 02 — ISA 与 CPU 基本组成

| 工具 | 用途 |
|------|------|
| **RISC-V GNU Toolchain** | 将 C 编译为 RISC-V 汇编：`riscv64-unknown-elf-gcc` |
| **Spike** | RISC-V 指令集模拟器（UC Berkeley） |
| **Venus** | 浏览器内 RISC-V 模拟器 + 调试器（[venus.kvakil.me](https:venus.kvakil.me)） |
| **RARS** | RISC-V 汇编 IDE + 模拟器，适合初学者 |
| **Godbolt (Compiler Explorer)** | 在线查看 C → RISC-V / x86 汇编映射 |

---

## 模块 03 — CPU 流水线

| 工具 | 用途 |
|------|------|
| Python 模拟器 (本仓库) | 5 段流水线行为模拟，含冒险检测和转发 |

---

## 模块 04 — CPU 微架构进阶

| 工具 | 用途 |
|------|------|
| **GCC/Clang + `-O2 -march=native`** | 编译 SIMD 向量化代码并对比性能 |
| **`objdump -d`** | 反汇编查看编译器生成的 SIMD 指令 |
| **Intel Intrinsics Guide** | SSE/AVX intrinsics 函数参考（[online](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/)） |
| **`perf stat`** | 统计 IPC、缓存 miss、分支误预测率 |

```bash
# 性能统计示例
gcc -O2 -march=native simd_add.c -o simd_add
perf stat ./simd_add
```

---

## 模块 05 — 存储层次

| 工具 | 用途 |
|------|------|
| Python + Matplotlib | 缓存模拟器结果可视化 |
| **`perf stat -e cache-misses,cache-references`** | 统计真实程序的缓存表现 |
| **Valgrind / Cachegrind** | 模拟缓存行为，分析缓存命中率 |

```bash
# 缓存性能分析
valgrind --tool=cachegrind ./matrix_mult
```

---

## 模块 06 — GPU 架构

| 工具 | 用途 |
|------|------|
| **NVIDIA CUDA Toolkit (≥ 12.x)** | 编译 CUDA 代码（[developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)） |
| **nvcc** | CUDA 编译器 |
| **`nvidia-smi`** | 查看 GPU 型号、显存使用、利用率 |
| **`deviceQuery`** | CUDA 样例程序，查看 GPU 硬件参数 |

```bash
# 查看 GPU 信息
nvidia-smi
```

---

## 模块 07 — CUDA 编程与优化

| 工具 | 用途 |
|------|------|
| **Nsight Compute (`ncu`)** | GPU kernel 性能分析器，查看 occupancy、memory 等指标 |
| **Nsight Systems (`nsys`)** | GPU 全程追踪，查看 kernel launch、数据搬运的时间线 |
| **CUDA Samples** | NVIDIA 官方 CUDA 示例代码 |

```bash
# Kernel 性能分析
ncu --set full ./my_cuda_kernel

# 全局追踪
nsys profile ./my_cuda_kernel
```

---

## 模块 08 — NPU

| 工具 | 用途 |
|------|------|
| **Apache TVM** | AI 编译器，可将模型部署到不同硬件（[tvm.apache.org](https://tvm.apache.org)） |
| **ONNX Runtime** | 跨平台推理引擎，支持多种 NPU 后端 |
| Python + NumPy | 脉动阵列行为模拟 |

```bash
# TVM 快速开始
pip install apache-tvm
```

---

## 模块 09 — TPU

| 工具 | 用途 |
|------|------|
| **Google Colab (TPU 运行时)** | 免费使用 TPU v2-8（[colab.research.google.com](https://colab.research.google.com)） |
| **JAX** | 支持 TPU 的数值计算库（[jax.readthedocs.io](https://jax.readthedocs.io)） |
| **XLA 编译器** | JAX / TensorFlow 编译到 TPU 的底层编译器 |

```python
# Colab 上启用 TPU
import jax
print(jax.devices())  # 应显示 TPU 设备
```

---

## 模块 10 — 其他加速器

| 工具 | 用途 |
|------|------|
| **Vivado (Xilinx)** | FPGA 设计工具（免费 WebPACK 版） |
| **Verilator** | 开源 Verilog 仿真器 |

---

## 模块 11 — 系统分析

| 工具 | 用途 | 安装 |
|------|------|------|
| **`perf`** | Linux 性能计数器采样 | `apt install linux-tools-common` |
| **`flamegraph`** | 火焰图生成 | `git clone https://github.com/brendangregg/FlameGraph.git` |
| **`likwid`** | 细粒度 CPU 性能计数器 | `apt install likwid` |
| **Nsight Compute** | GPU kernel 级分析 | CUDA Toolkit 自带 |
| **Nsight Systems** | GPU 系统级追踪 | CUDA Toolkit 自带 |
| Python + Matplotlib | Roofline 模型绘图 | `pip install matplotlib numpy` |

```bash
# perf 采样示例
perf record -e cycles,instructions,cache-misses ./my_program
perf report
```

---

## 工具安装检查清单

```bash
# 检查已安装的工具
gcc --version
python3 --version
nvcc --version        # 如有 GPU
nvidia-smi            # 如有 GPU
perf --version        # Linux 性能工具
```

---

> 本清单持续更新。如果你发现好用的工具，欢迎补充。
