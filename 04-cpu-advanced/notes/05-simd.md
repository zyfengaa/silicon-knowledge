# 05 — SIMD（Single Instruction, Multiple Data）

## 概述

SIMD（单指令多数据流）属于 **Flynn 分类法** 中的 SIMD 类别。一条指令同时对多个数据元素执行相同的运算操作。

```
标量 (SISD):          SIMD:                     
a1 + b1               a1 a2 a3 a4
                      +  +  +  +
                      b1 b2 b3 b4
                      ==========
                      c1 c2 c3 c4  (一次运算)
```

## SIMD 的发展历程

### x86 架构

| 扩展 | 位宽 | 寄存器数 | 数据类型 | 引入年份 |
|------|------|---------|---------|---------|
| MMX | 64-bit | 8 (复用 FP) | 整数 | 1997 |
| SSE | 128-bit | 8 → 16 (XMM) | 整数 + 单精度浮点 | 1999 |
| SSE2 | 128-bit | 8 → 16 (XMM) | 双精度浮点 + 整数 | 2000 |
| SSE3/SSSE3 | 128-bit | 16 (XMM) | 追加指令（水平操作等） | 2004~2006 |
| SSE4 | 128-bit | 16 (XMM) | 追加指令（字符串、点积等） | 2007~2008 |
| AVX | 256-bit | 16 (YMM) | 浮点 & 整数 | 2011 (Sandy Bridge) |
| AVX2 | 256-bit | 16 (YMM) | 整数操作 + FMA | 2013 (Haswell) |
| AVX-512 | 512-bit | 32 (ZMM) | 浮点 & 整数 + mask | 2016 (Knights Landing) |
| AVX-512 (主流) | 512-bit | 32 (ZMM) | Intel Ice Lake, Rocket Lake | 2019~2021 |

### ARM 架构

| 扩展 | 特点 | 数据宽度 | 引入 |
|------|------|---------|------|
| NEON | 128-bit 固定宽度 SIMD | 128-bit | ARMv7 |
| SVE (Scalable Vector Extension) | 可变宽度向量，支持 128~2048 bit | 软件编译一次，硬件自适应 | ARMv8.2 |
| SVE2 | SVE 的增强版，补全 NEON 功能 | 128~2048 bit | ARMv9 |

## SSE（128-bit）

SSE 有 16 个 128-bit 的 XMM 寄存器（xmm0 ~ xmm15）。

### 数据类型映射

```
128-bit XMM 寄存器:
┌────────┬────────┬────────┬────────┐
│   4 × 32-bit 单精度浮点 (float)    │
├────────┴────────┴────────┴────────┤
│       2 × 64-bit 双精度浮点        │
├────────┬────────┬────────┬────────┤
│       4 × 32-bit 整数 (int)        │
├──────────────┬────────────────────┤
│  16 × 8-bit  │  8 × 16-bit 整数   │
│   (char)     │   (short)          │
└──────────────┴────────────────────┘
```

### SSE Intrinsics 示例

```c
#include <xmmintrin.h>  // SSE

// 4 个 float 的向量加法
__m128 a = _mm_load_ps(&A[0]);    // 加载 4 个 float（对齐）
__m128 b = _mm_load_ps(&B[0]);
__m128 c = _mm_add_ps(a, b);      // 并行加法
_mm_store_ps(&C[0], c);           // 存储结果
```

## AVX（256-bit）

AVX 将 XMM 扩展为 YMM 寄存器（ymm0 ~ ymm15）。

### 数据类型映射

```
256-bit YMM 寄存器:
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│              8 × 32-bit 单精度浮点 (float)                │
├──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┤
│                     4 × 64-bit 双精度浮点                │
├──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┤
│                    8 × 32-bit 整数                      │
├──────────────────────┬──────────────────────────────────┤
│       16 × 16-bit    │        32 × 8-bit                │
└──────────────────────┴──────────────────────────────────┘
```

### AVX Intrinsics 示例

```c
#include <immintrin.h>  // AVX

// 8 个 float 的向量 FMA（乘加）
__m256 a = _mm256_load_ps(&A[0]);
__m256 b = _mm256_load_ps(&B[0]);
__m256 c = _mm256_load_ps(&C[0]);
__m256 d = _mm256_fmadd_ps(a, b, c);  // d = a * b + c
_mm256_store_ps(&D[0], d);
```

## AVX-512（512-bit）

AVX-512 增加 32 个 512-bit 的 ZMM 寄存器（zmm0 ~ zmm31）。

**关键特性**：
- 32 × 32-bit float / 64 × 16-bit int / 8 × 64-bit double
- **掩码寄存器（Mask Registers, k0 ~ k7）**：每条指令可用掩码控制哪些元素生效
- **嵌入的舍入和异常控制**：每条指令可以指定舍入模式
- **冲突检测（AVX-512CD）**：检测向量中的地址冲突

### AVX-512 Intrinsics 示例

```c
#include <immintrin.h>

// 16 个 float 的向量加法
__m512 a = _mm512_load_ps(&A[0]);
__m512 b = _mm512_load_ps(&B[0]);
__m512 c = _mm512_add_ps(a, b);
_mm512_store_ps(&C[0], c);

// 带掩码的加法（只有低 8 个元素相加）
__mmask16 mask = 0x00FF;
__m512 d = _mm512_mask_add_ps(a, mask, b, c);
```

## ARM NEON（128-bit SIMD）

ARM NEON 是 ARMv7 和 ARMv8 的 128-bit SIMD 扩展。

### ARMv8 NEON

```c
#include <arm_neon.h>

// 4 个 float 的向量加法
float32x4_t a = vld1q_f32(&A[0]);
float32x4_t b = vld1q_f32(&B[0]);
float32x4_t c = vaddq_f32(a, b);
vst1q_f32(&C[0], c);
```

## ARM SVE（Scalable Vector Extension）

SVE 是 ARM 为 HPC 和机器学习设计的**可伸缩向量扩展**。

### 核心特性

1. **可伸缩向量长度（Scalable Vector Length, VL）**：硬件实现可选择 128 ~ 2048 bit（步长 128）
2. **程序一次编译，多处运行**：二进制不需要为不同 VL 重新编译
3. **逐向量长度编程（Vector-Length Agnostic, VLA）**：代码自动适应硬件 VL
4. **谓词寄存器（Predicate Registers）**：类似 AVX-512 的掩码，但粒度更细（按字节）
5. **聚集/分散加载（Gather/Scatter）**：高效处理非连续数据
6. **水平操作（Reduce）**：向量求和、最大值/最小值

### SVE 编程模型

```c
#include <arm_sve.h>

// 向量的长度由硬件决定
svfloat32_t a = svld1_f32(svptrue_b32(), &A[0]);
svfloat32_t b = svld1_f32(svptrue_b32(), &B[0]);
svfloat32_t c = svadd_f32_x(svptrue_b32(), a, b);
svst1_f32(svptrue_b32(), &C[0], c);
```

**SVE2**（ARMv9 标准）：在 SVE 基础上新增数据处理指令（加密、NTT、数据重组等）。

## 编译器自动向量化（Auto-Vectorization）

### 工作原理

现代编译器（GCC, Clang, MSVC, ICC）能自动将标量循环转换为 SIMD 代码：

```c
// 原始标量代码
for (int i = 0; i < N; i++) {
    C[i] = A[i] + B[i];
}

// 编译器自动向量化为（概念上）
for (int i = 0; i < N; i += 4) {
    _mm_store_ps(&C[i], _mm_add_ps(
        _mm_load_ps(&A[i]),
        _mm_load_ps(&B[i])
    ));
}
```

### 编译器启用方式

| 编译器 | 标志 |
|--------|------|
| GCC | `-O2 -ftree-vectorize` |
| GCC (GCC 12+) | `-O2`（默认启用） |
| Clang | `-O2 -fvectorize` |
| ICC | `-O2 -xHOST` |
| MSVC | `/O2 /Qvec` |

### 限制条件

编译器无法自动向量化的情况：

1. **非连续内存访问**：`A[idx[i]]`（除非使用 gather 指令）。
2. **数据依赖**：`A[i] = A[i-1] + 1`（循环携带依赖）。
3. **指针别名**：编译器不能判断两个指针是否有重叠（C 中可用 `restrict` 提示）。
4. **复杂控制流**：循环内有复杂分支（可通过条件执行或 `? :` 简化）。
5. **非对齐访问**：未使用对齐分配（如 `_mm_malloc`/`aligned_alloc`/`posix_memalign`）。
6. **函数调用**：循环内调用未知函数（除非函数被内联且可向量化）。

### 检查编译器输出

```bash
# GCC: 生成汇编并检查向量指令
gcc -O3 -fopt-info-vec-missed -S loop.c -o loop.s

# Clang: 报告向量化信息
clang -O3 -Rpass=vectorize -Rpass-missed=vectorize -c loop.c -o loop.o
```

## 何时需要手工向量化？

尽管编译器自动向量化不断进步，以下场景仍需要手工编写 SIMD 代码：

| 场景 | 原因 | 示例 |
|------|------|------|
| 编译器无法解构复杂循环 | 循环结构太复杂 | 多层级反规范化 |
| 需要跨元素操作（水平归约） | 现代编译器基本能自动处理但有例外 | 点积、矩阵乘法变体 |
| 使用特定 SIMD 扩展的特殊指令 | 编译器较少使用 | FMA, SHA, AES-NI |
| 对生成代码有完全控制 | 确定性和性能保证 | 实时系统、数字信号处理 |
| 底层 SIMD 汇编级调优 | 最极致的性能 | HPC 内核（BLAS, FFT） |

### 手工向量化的基本策略

```c
// 步骤 1: 确认循环可以向量化（无循环携带依赖）
// 步骤 2: 确定数据对齐（16/32/64 字节对齐）
// 步骤 3: 处理尾部元素（剩余不足一个向量宽度的元素）

#include <immintrin.h>

void add_arrays_avx(const float* restrict A,
                    const float* restrict B,
                    float* restrict C, int N) {
    int i = 0;
    // AVX: 每次处理 8 个 float
    for (; i <= N - 8; i += 8) {
        __m256 a = _mm256_load_ps(&A[i]);        // 对齐加载
        __m256 b = _mm256_load_ps(&B[i]);
        __m256 c = _mm256_add_ps(a, b);
        _mm256_store_ps(&C[i], c);
    }
    // 尾部处理：标量循环
    for (; i < N; i++) {
        C[i] = A[i] + B[i];
    }
}
```

## SIMD 性能分析

### 理论加速比

```
理论加速比 = SIMD 向量化宽度 / 标量元素大小
```

| 数据类型 | SSE (128) | AVX (256) | AVX-512 |
|---------|-----------|-----------|---------|
| float (32-bit) | 4× | 8× | 16× |
| double (64-bit) | 2× | 4× | 8× |
| int (32-bit) | 4× | 8× | 16× |
| short (16-bit) | 8× | 16× | 32× |

### 实际加速比的影响因素

- 内存带宽限制（内存瓶颈时 SIMD 加速不明显）
- 操作延迟差异（向量指令的延迟可能比标量高）
- 数据移动开销（加载/存储/重排）
- 尾部循环处理开销
- 编译器优化水平

典型范围：1.5× ~ 8×（HPC 计算密集型任务可达 8×+）。

## 关键概念总结

- **SIMD**：一条指令同时处理多个数据
- **SSE (128-bit) → AVX (256-bit) → AVX-512**：Intel SIMD 发展路径
- **NEON → SVE (可伸缩)**：ARM SIMD 路径
- **自动向量化**：编译器自动将标量循环 → SIMD
- **手工向量化**：通过 intrinsics 或汇编手动编写

## 思考题

1. 对一个内存受限（memory-bound）的应用，比如大量不连续的访存，SIMD 还能带来显著的性能提升吗？为什么？
2. 为什么 ARM SVE 采用可伸缩向量长度（VLA）设计？它对软件生态有什么好处？
3. 编译器自动向量化时，`restrict` 关键字的作用是什么？为什么它能帮助编译器生成更好的代码？
4. 数组长度不是向量宽度整数倍时（尾部处理），有哪些高效处理尾部元素的方法？

## 参考文献

- Intel Corporation. *Intel 64 and IA-32 Architectures Optimization Reference Manual*, Chapters 9–15.
- Intel Corporation. *Intel Intrinsics Guide*. https://www.intel.com/content/www/us/en/docs/intrinsics-guide/
- ARM Limited. *ARM Architecture Reference Manual for ARMv8-A*, Chapter A1 (NEON).
- ARM Limited. *ARM Architecture Reference Manual SVE Supplement*, ARMv8.2.
- Patterson, D. A. & Hennessy, J. L. *Computer Organization and Design RISC-V Edition*, Chapter 3: SIMD and Vector Processing.
- Stephens, N. et al. "The ARM Scalable Vector Extension." *IEEE Micro*, 2017.
- Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*, 6th Edition, Chapter 3: Vector SIMD Architectures.
