# 04 — Warp 执行

> Warp 是 GPU 调度的基本单位。Warp 内的 32 个线程执行同一条指令，但分支会导致线程执行路径分离，带来性能损失。

---

## 1. Warp 调度

### 调度周期

每个 warp 调度器每个时钟周期选择一个就绪的 warp 发射一条指令。H100 每个 SM 有 4 个 warp 调度器，理论上每周期可发射 4 条指令。

```
时钟周期：
     │  Sched 0  │  Sched 1  │  Sched 2  │  Sched 3  │
─────┼───────────┼───────────┼───────────┼───────────┤
Cyc1 │ Warp 0    │ Warp 8    │ Warp 16   │ Warp 24   │
Cyc2 │ Warp 1    │ Warp 9    │ —(stall)  │ Warp 25   │
Cyc3 │ Warp 2    │ Warp 8    │ Warp 16   │ Warp 26   │
Cyc4 │ Warp 0    │ Warp 10   │ Warp 17   │ Warp 24   │
```

每个 warp 调度器维护一个 warp 就绪状态表，记录每个 warp 当前是否具备发射条件：

| Warp | 状态 | 原因 |
|------|------|------|
| 0 | 就绪 | 已就绪，等待发射 |
| 1 | 停顿中 | 等待内存访问结果 |
| 2 | 停顿中 | 等待寄存器读完成 |
| 3 | 就绪 | 已就绪，等待发射 |
| ... | ... | ... |
| 63 | 停顿中 | 等待同步屏障 |

Warp 停顿的常见原因：

- **访存延迟**：等待全局内存/共享内存读取结果
- **同步**：线程块等待 `__syncthreads()` 屏障
- **数据依赖**：下一条指令需要前一条指令的计算结果
- **流水线满载**：执行单元的流水线已满，back-pressure

### 调度策略

NVIDIA GPU 使用**贪心最大占用率调度**配合**公平轮转**策略：

1. **先到先服务**（FCFS）：就绪队列中的 warp 按顺序发射
2. **两个 warp 之间的指令间隔**：如果两个 warp 之间没有数据依赖，可以连续发射
3. **Warp 优先级的动态调整**：在 Kepler 及之后架构中引入

**Dual-Issue（双发射）**：某些架构（如 Turing）允许 warp 调度器在单个周期内发射两条独立指令（如一条算术指令 + 一条访存指令），进一步提升吞吐量。

---

## 2. Warp Divergence（线程束分化）

### 什么是 Warp Divergence

Warp 中的所有线程执行同一程序计数器（PC）指向的指令。当 warp 中的线程遇到条件分支时，如果不同线程走向不同路径，就会发生 warp divergence。

```
没有 divergence 的情况：
┌────────────────────────────┐
│ if (condition) {           │
│     result = a * b;        │ ← warp 中所有线程走此路径
│ }                          │
└────────────────────────────┘

有 divergence 的情况：
┌────────────────────────────────────┐
│ if (threadIdx.x % 2 == 0) {        │
│     result = a * b;                │ ← 一半线程走此路径
│ } else {                           │
│     result = a + b;                │ ← 另一半线程走此路径
│ }                                  │
└────────────────────────────────────┘
```

### Divergence 的处理机制

当 GPU 检测到 warp 内的分支分歧时，硬件会：

1. **执行所有分支路径**：先执行一条路径，然后回退到分歧点，再执行其他路径
2. **使用活动掩码（Active Mask）**：一个 32-bit 掩码标记哪些线程当前活跃
3. **掩蔽非活跃线程**：当前路径中不活跃的线程被"冻结"（不会写回结果）

```
// 代码
if (condition) {
    // 路径 A
} else {
    // 路径 B
}

// 硬件执行
// ── 第一步：执行路径 A ──
// 掩码: 11001100110011001100110011001100 (偶数线程)
// 活跃线程执行, 奇数线程被掩蔽 (结果不写回)
//
// ── 第二步：执行路径 B ──
// 掩码: 00110011001100110011001100110011 (奇数线程)
// 奇数线程执行, 偶数线程被掩蔽
//
// ── 第三步：收敛 ──
// 所有线程统一到同一 PC
```

**性能影响**：如果有 N 个分歧路径，则该 warp 的执行时间将是单一路径的 N 倍。

### Divergence 的代价

```
分支路径数       相对性能
   1             100%
   2              50%
   4              25%
   8             12.5%
  32              3.1%
```

极端情况（每个线程走不同路径）下，warp 退化为 32 个串行执行。

### Divergence 触发条件

以下情况会导致 warp divergence：

**if-else 分支（最常见）**：
```cuda
if (threadIdx.x < 16) {
    // warp 前一半线程走这里
} else {
    // warp 后一半线程走这里
}
// → 2 条路径
```

**循环分支**：
```cuda
for (int i = 0; i < threadIdx.x % 8; i++) {
    // 不同线程循环次数不同
}
// → 最多 8 条路径
```

**switch-case 语句**：
```cuda
switch (threadIdx.x % 4) {
    case 0: ... break;
    case 1: ... break;
    case 2: ... break;
    case 3: ... break;
}
// → 4 条路径
```

**三元运算符**：
```cuda
result = (threadIdx.x < 16) ? a : b;
// 虽不会 divergence，但两路结果都需要计算
```

### 不会触发 Divergence 的情况

**基于线程块 ID 的分支**：
```cuda
if (blockIdx.x % 2 == 0) { ... }
// blockIdx 在 block 内所有线程相同，warp 内一致 → 无 divergence
```

**统一条件**：
```cuda
if (N > 128) { ... }
// 条件不依赖于 threadIdx → 无 divergence
```

---

## 3. 谓词执行（Predicated Execution）

为了避免 warp divergence 的性能代价，编译器可以将短分支编译为谓词执行：

```
// 源代码
if (x > 0) {
    y = a / x;
} else {
    y = 0;
}

// 编译为谓词形式（伪代码）
@p (x > 0) y = a / x;    // P 为真时执行
@!p (x > 0) y = 0;       // P 为假时执行
```

**谓词执行 vs 分支执行**：

| 特性 | 谓词执行 | 分支执行 |
|------|---------|---------|
| 执行路径数 | 始终 1 | 可能 >1 |
| 隐藏代价 | 所有线程执行两条指令 | 串行执行多个路径 |
| 适用条件 | 分支体短（~5 条指令以内） | 分支体长 |
| 编译器决定 | NVIDIA 编译器自动选择 | — |

NVIDIA PTX ISA 支持完整的谓词系统，每条指令都可以加上谓词条件。

---

## 4. 收敛（Convergence）

### 隐式收敛

在 if-else 分支结束后，warp 中的线程会自动收敛，重新执行同一指令。收敛点就是分支融合处（如 if-else 后面的第一条指令）。

```
执行流：
     分支点
     /    \
  路径 A  路径 B
     \    /
     收敛点   ← 所有线程在此处统一 PC
```

### 显式收敛：__syncwarp()

`__syncwarp()` 是 CUDA 中的 warp 级同步操作。强制 warp 内所有线程到达同一个执行点后再继续。

```cuda
__syncwarp();  // warp 内所有线程在此屏障同步
```

与 `__syncthreads()` 不同，`__syncwarp()` 只同步 warp 内的 32 个线程，不涉及其他 warp。由于 warp 内所有线程在物理上已是同步执行，`__syncwarp()` 通常比 `__syncthreads()` 便宜得多。

### 投票与洗牌操作

Warp 提供了几个重要的协作原语，用于 warp 内线程间通信：

```cuda
// 投票函数 (Volta+)
int __all_sync(mask, predicate);   // warp 内所有 predicate 为真？
int __any_sync(mask, predicate);   // warp 内任一 predicate 为真？
int __ballot_sync(mask, predicate);// warp 内 predicate 的位掩码

// 洗牌函数 (Kepler+)
T __shfl_sync(mask, var, srcLane);    // 从 srcLane 线程获取 var
T __shfl_up_sync(mask, var, delta);   // 从 lane-delta 线程获取 var
T __shfl_down_sync(mask, var, delta); // 从 lane+delta 线程获取 var
T __shfl_xor_sync(mask, var, xorLane);// 从 lane ^ xorLane 获取 var
```

---

## 5. 避免 Divergence 的技巧

### 方法 1：数据重排

将需要对等处理的数据放在同一个 warp 中：

```cuda
// 不好的做法：warp 内奇数/偶数线程走不同分支
if (threadIdx.x % 2 == 0) {
    process_even(data[threadIdx.x]);
} else {
    process_odd(data[threadIdx.x]);
}

// 好的做法：warp 内线程数据一致
// 将偶数和奇数数据分别放入相邻 block
if (blockIdx.x % 2 == 0) {
    process_even(data[threadIdx.x + blockIdx.x * blockDim.x / 2]);
} else {
    process_odd(data[threadIdx.x + (blockIdx.x-1) * blockDim.x / 2]);
}
```

### 方法 2：使用 warp 聚合操作

用协作原语替代分支：

```cuda
// 不好的做法：需要知道最大值，用分支更新
float max_val = -INFINITY;
if (threadIdx.x < N) {
    max_val = data[threadIdx.x];
}

// 好的做法：使用 warp 级并行归约
float max_val = data[threadIdx.x];
for (int offset = 16; offset > 0; offset >>= 1) {
    max_val = fmaxf(max_val, __shfl_xor_sync(0xFFFFFFFF, max_val, offset));
}
```

### 方法 3：使用多维 block 划分

利用 block 多维索引特性，将条件编码为数据布局而非显式分支。

---

## 参考文献

- Kirk, D. B. & Hwu, W. W., *Programming Massively Parallel Processors: A Hands-on Approach*, 3rd ed., Chapter 4.5: Warp Scheduling and Divergence, Morgan Kaufmann, 2016.
- NVIDIA, *PTX ISA (Parallel Thread Execution ISA)*, Section 1.4: Predicated Execution.
- NVIDIA, *CUDA C++ Programming Guide*, Section 4.1: Warp Divergence, Section 4.2: Warp Vote and Shuffle Functions.
- NVIDIA, *CUDA C++ Best Practices Guide*, Section 5.4: Branch and Divergence.
- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Chapter 4.5: Warp Scheduling, Morgan Kaufmann, 2018.
- NVIDIA, *Volta V100 Architecture Whitepaper*, 2017. Section: Independent Thread Scheduling.
- Fung, W. L. et al., "Dynamic Warp Formation and Scheduling for Efficient GPU Control Flow", *IEEE/ACM International Symposium on Microarchitecture (MICRO)*, 2007.
