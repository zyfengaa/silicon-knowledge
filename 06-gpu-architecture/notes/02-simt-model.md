# 02 — SIMT 模型

> SIMT（Single Instruction, Multiple Threads）是 GPU 执行模型的核心概念。理解 SIMT 与 SIMD 的区别是掌握 GPU 编程的关键。

---

## 1. SIMD 与 SIMT

### SIMD（Single Instruction, Multiple Data）

SIMD 是 CPU 中已经存在多年的并行执行模式。一条指令同时操作多个数据元素，数据被打包成**向量**。

**x86 AVX-512 示例**：
```asm
; 计算 C[0..7] = A[0..7] + B[0..7]
vmovdqu32 zmm0, [A]    ; 从内存加载 16 个 32-bit 整数到 zmm0
vmovdqu32 zmm1, [B]    ; 从内存加载 16 个 32-bit 整数到 zmm1
vpaddd   zmm2, zmm0, zmm1  ; 16 个元素并行相加
vmovdqu32 [C], zmm2    ; 写回结果
```

| SIMD 特性 | 说明 |
|-----------|------|
| 显式向量宽度 | 指令中编码了向量长度（如 SSE: 128-bit, AVX2: 256-bit, AVX-512: 512-bit） |
| 数据必须连续 | 加载的数据必须是内存中的连续元素 |
| 无分支独立 | 向量中的每个元素执行完全相同的操作 |
| 编译时确定 | 向量宽度在编写代码/编译器生成时确定 |

SIMD 的局限：

- **数据依赖**：向量内的元素不能相互依赖（如 `a[i] = a[i-1] + 1`）
- **分支问题**：向量中的元素遇到条件分支时，必须执行所有分支然后选择结果（masked execution）
- **宽度固定**：硬件决定了向量宽度，软件必须适配（x86 是固定宽度，ARM SVE 采用可变长度矢量）
- **连续存储要求**：访存需要连续且对齐的数据布局

### SIMT（Single Instruction, Multiple Threads）

SIMT 是 NVIDIA 在 G80 架构中引入的执行模型。一条指令被多个独立线程同时执行，每个线程有自己的程序计数器（PC）和寄存器上下文。

```
┌─────────────────────────────────────────────────────┐
│                   指令流                             │
│  LD R1, [R2]                                       │
│  FADD R3, R1, R4                                   │
│  ST [R5], R3                                       │
└──────────┬──────────────────────────────────────────┘
           │ 一条指令广播给所有线程
           ▼
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ T0  │ T1  │ T2  │ T3  │ ... │ T28 │ T29 │ T30 │ T31 │  ← 32 线程
│ PC  │ PC  │ PC  │ PC  │     │ PC  │ PC  │ PC  │     ← 每个线程独立 PC
│ R0..│ R0..│ R0..│ R0..│     │ R0..│ R0..│ R0..│     ← 每个线程独立寄存器
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

| SIMT 特性 | 说明 |
|-----------|------|
| 隐式并行 | 程序员编写单线程代码，编译器/硬件管理并行 |
| 线程独立 | 每个线程有私有寄存器，可独立决定访存地址 |
| 分支容忍 | 不同线程可走不同分支（导致 divergence） |
| 硬件调度 | warp 由硬件调度器管理，对软件透明 |
| 非连续访存 | 每个线程可独立计算地址，无需连续 |

### SIMT vs SIMD 对比总结

| 对比维度 | SIMD | SIMT |
|---------|------|------|
| 编程模型 | 显式向量操作 | 标量线程集合 |
| 硬件宽度 | 固定（128/256/512 bit） | 固定（32 线程/warp） |
| 寄存器 | 共享向量寄存器 | 每个线程私有 |
| 访存 | 需要连续/对齐 | 每个线程独立地址 |
| 分支处理 | 全向量执行 + 掩码 | 部分线程掩蔽 |
| 数据依赖 | 不支持跨元素依赖 | 线程间独立 |
| 编译器复杂度 | 需要向量化分析 | 简单标量编译 |

---

## 2. CUDA 执行模型的层次结构

CUDA 的线程层次结构对应于 GPU 的物理执行层次：

```
Grid (内核)
  │
  ├── Block (0,0)      ← 分配到同一 SM
  │     │
  │     ├── Thread (0,0,0)    ← 最细粒度
  │     ├── Thread (0,0,1)
  │     ├── ...
  │     └── Thread (N-1)
  │
  ├── Block (1,0)
  │     └── ...
  └── Block (M-1,0)
        └── ...
```

### Thread（线程）

- 最细粒度的执行单元
- 每个线程有自己独立的寄存器文件和指令地址（PC）
- 每个线程执行相同的 kernel 函数，但通过 `threadIdx` 索引区分数据
- 硬件对线程数量没有严格限制（软件层面）

### Warp（线程束）

- **32 个线程**组成一个 warp，是 GPU 调度和执行的基本单位
- Warp 中的 32 个线程在同一**指令周期**执行同一条指令
- Warp 所有线程共享同一个取指和译码单元
- 每个 SM 中的 warp 调度器负责管理 warp 的发射
- Warp 的概念对代码**透明**（程序员通常不直接操作 warp）

```
Warp 结构（32 线程）：
┌─────────────────────────────────────────────────────────────────┐
│ Warp 0: IF | ID | [T0 T1 T2 ... T31] 并行执行 ALU              │
│         T0 的 R0  T1 的 R0  T2 的 R0  ...  T31 的 R0           │
│         T0 的 PC  T1 的 PC  T2 的 PC  ...  T31 的 PC           │
└─────────────────────────────────────────────────────────────────┘
```

### Thread Block（线程块）

- 一组线程（通常为 128-1024 个线程），映射到同一个 SM
- Block 内的线程可以通过**共享内存（shared memory）**通信
- Block 内的线程可以通过**同步（__syncthreads）**进行协作
- 一个 Block 被调度到一个 SM 后，直到执行完成才会释放资源

| 层次 | 硬件对应 | 共享资源 | 同步机制 |
|------|---------|---------|---------|
| Thread | CUDA Core（FP32 单元） | 无（私有寄存器） | 不需要 |
| Warp | Warp Scheduler | 指令单元 | 隐式（SIMT 自动同步） |
| Block | SM | 共享内存、寄存器文件 | `__syncthreads()` |
| Grid | GPU（所有 SM） | 全局内存 | `cudaDeviceSynchronize()` |

---

## 3. Warp 的分配与调度

### 线程块到 warp 的映射

当一个线程块被分配到 SM 时，其中的线程被自动划分为 warp：

```cuda
dim3 blockDim(128);  // 每个 block 128 个线程
// Warp 分配：
// Warp 0: Thread 0-31
// Warp 1: Thread 32-63
// Warp 2: Thread 64-95
// Warp 3: Thread 96-127
```

线程在 warp 内的索引由 `threadIdx.x` 的低 5 位决定（因为 2^5 = 32）：

```c
int warp_id      = threadIdx.x / 32;           // 哪个 warp
int lane_id      = threadIdx.x % 32;           // warp 内的位置
int global_tid   = blockIdx.x * blockDim.x + threadIdx.x;
int global_warp  = global_tid / 32;
```

### Warp 调度

每个 SM 有多个 warp 调度器（H100 有 4 个），每个调度器负责维护一组 warp 的上下文，每个周期选择一个就绪的 warp 发射指令：

```
Warp 调度器状态（简化的就绪向量）：
                Cycle 1   Cycle 2   Cycle 3   Cycle 4
Warp 0 (就绪)   │ RUN │   │    │   │ RUN │   │    │
Warp 1 (等待M)  │    │   │    │   │    │   │    │
Warp 2 (就绪)   │    │   │ RUN │   │    │   │ RUN │
Warp 3 (等待M)  │    │   │    │   │    │   │    │
Warp 4 (就绪)   │    │   │    │   │    │   │    │
              ────────────────────────────────────
               发射Warp0  发射Warp2  发射Warp0  发射Warp2
```

Warp 调度的关键：只要存在足够多的活动 warp，warp 调度器就能在每次访存等待时切换到另一个 warp，从而让计算单元始终忙碌。

### 占用率（Occupancy）

占用率是指每个 SM 上活动的 warp 数量与最大 warp 数量的比值。

```
占用率 = 活动 warp 数 / SM 最大 warp 数
```

- 高占用率增加延迟隐藏能力
- 占用率受寄存器使用量、共享内存使用量、block 大小限制
- CUDA Occupancy Calculator 可以辅助优化

---

## 4. SIMT 模型的优势

1. **编程简便**：程序员以标量方式思考，硬件自动处理并行，无需手动编写向量代码。
2. **可扩展性**：同一代码可运行在不同世代、不同规格的 GPU 上（自动适应 SM 数量）。
3. **访存灵活性**：每个线程独立计算访存地址，支持不规则数据结构和复杂索引。
4. **分支容忍**：虽然分支会导致 divergence，但单个线程可以独立执行条件路径，编程模型更自然。
5. **延迟隐藏**：数千个并发线程为延迟隐藏提供了基础。

---

## 参考文献

- Kirk, D. B. & Hwu, W. W., *Programming Massively Parallel Processors: A Hands-on Approach*, 3rd ed., Chapter 4: CUDA Threads and Memory Hierarchy, Morgan Kaufmann, 2016.
- NVIDIA, *CUDA C++ Programming Guide*, Section 2.2: Thread Hierarchy.
- Lindholm, E. et al., "NVIDIA Tesla: A Unified Graphics and Computing Architecture", *IEEE Micro*, 28(2), 2008, pp. 39-55. doi:10.1109/MM.2008.31
- NVIDIA, *PTX ISA (Parallel Thread Execution ISA)*, Section 1.3: SIMT Architecture.
- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Chapter 4: Vector, SIMD, and GPU Architectures, Section 4.5: NVIDIA GPU Architecture Overview, Morgan Kaufmann, 2018.
- Fog, A., "The Microarchitecture of Intel, AMD, and VIA CPUs", Section: SIMD Instructions, 2023. Available at: https://www.agner.org/optimize/
