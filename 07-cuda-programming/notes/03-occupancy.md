# 03 — Occupancy 与 Launch Configuration

> Occupancy 衡量 SM 的"忙碌程度"。合理的 Launch Configuration 可以在资源限制与计算需求之间找到平衡。

## 什么是 Occupancy

**Occupancy** 定义为一个 SM 上活跃的 Warp 数与 SM 能够支持的最大 Warp 数之比：

```
Occupancy = 活跃 Warp 数 / 最大 Warp 数
```

- **100% Occupancy**：SM 被 Warp 完全填满，在任何时刻都有最多的 Warp 可调度
- **低 Occupancy**：可能由于资源限制（寄存器、共享内存、线程数）导致 SM 只能运行少量 Block

## 限制 Occupancy 的因素

### 1. 每线程寄存器数 (Registers per Thread)

编译器根据 kernel 的变量使用情况分配寄存器。可以通过编译器标志限制：

```bash
nvcc --maxrregcount=32 mykernel.cu    # 限制每线程最多 32 个寄存器
```

**寄存器与 Occupancy 的关系：**

每个 SM 的寄存器池是固定的。每线程使用的寄存器越多，每个 Block 可以使用的 Block 数越少。

```
SM 寄存器池: 65536
Block Size: 256

每线程 32 寄存器:
  Block 所需寄存器 = 32 × 256 = 8192
  可容纳 Block = 65536 / 8192 = 8

每线程 64 寄存器:
  Block 所需寄存器 = 64 × 256 = 16384
  可容纳 Block = 65536 / 16384 = 4
```

### 2. 每 Block 共享内存 (Shared Memory per Block)

使用 `__shared__` 或动态共享内存时，每个 Block 消耗 SM 的共享内存资源。

```cuda
__shared__ float cache[256];  // 静态：1 KB / Block

// 动态：通过 kernel launch 参数指定
kernel<<<grid, block, shared_mem_bytes>>>(...);
```

```
SM 共享内存: 48 KB
每 Block 共享内存: 16 KB
可容纳 Block = 48 / 16 = 3
```

### 3. 最大 Block 数 (Max Blocks per SM)

GPU 硬件对每个 SM 的最大 Block 数有硬性限制：

| GPU 架构 | Max Blocks / SM |
|----------|----------------|
| Volta (V100) | 32 |
| Turing (T4) | 32 |
| Ampere (A100) | 32 |
| Hopper (H100) | 32 |

### 4. 最大 Warp 数 (Max Warps per SM)

| GPU 架构 | Max Warps / SM | Max Threads / SM |
|----------|----------------|-------------------|
| Volta / Turing | 64 | 2048 |
| Ampere | 64 | 2048 |
| Hopper | 64 | 2048 |

### 综合计算公式

```python
# 每个 Block 需要的 Warp 数
warps_per_block = ceil(block_size / 32)

# 受寄存器限制
max_blocks_by_regs = regs_per_sm // (regs_per_thread * block_size)

# 受共享内存限制
max_blocks_by_shmem = shmem_per_sm // shmem_per_block

# 受最大线程数限制
max_blocks_by_threads = max_threads_per_sm // block_size

# 受最大 Block 数限制（硬件硬性限制）
max_blocks_by_hw = max_blocks_per_sm

# 实际同时运行的 Block 数是以上值的最小值，不能超过从 Warp 角度来看的限制
max_blocks_by_warps = max_warps_per_sm // warps_per_block

active_blocks = min(max_blocks_by_regs, max_blocks_by_shmem,
                    max_blocks_by_threads, max_blocks_by_hw,
                    max_blocks_by_warps)

active_warps = active_blocks * warps_per_block
occupancy = active_warps / max_warps_per_sm
```

## CUDA Occupancy Calculator

NVIDIA 提供了 **CUDA Occupancy Calculator**（电子表格），输入 kernel 参数即可计算理论 Occupancy。

### 使用步骤

1. 选择 GPU 架构（根据编译 Target）
2. 输入 Block Size
3. 输入每线程寄存器数（可通过 `--ptxas-options=-v` 编译选项查看）
4. 输入每 Block 共享内存使用量
5. 查看 Occupancy 结果和限制因素

```
Occupancy Calculator Output (示例):

Device: Compute Capability 8.0 (Ampere A100)
Block Size: 256
Registers/Thread: 32
Shared Memory/Block: 0

Occupancy: 100%
Limiting Factor: Registers (Block limit = 8)
Active Blocks/SM: 8
Active Warps/SM: 64
```

### 实际寄存器占用查看

编译时添加 verbose 选项可以查看 kernel 的寄存器使用：

```bash
nvcc -Xptxas=-v mykernel.cu
```

输出示例：

```
ptxas info: Used 32 registers, 4096 bytes smem
```

## Launch Configuration 调优

### 一般原则

1. **Block Size 选择 32 的倍数**
   - 推荐值：128、256、512
   - 总是 32 的倍数，避免 Warp 浪费

2. **每个 SM 至少 4-6 个 Active Warp**
   - 足够覆盖指令延迟和内存延迟
   - 计算密集型 kernel 可以接受更低 Occupancy

3. **Grid Size 足够大**
   - Grid 至少比 SM 数量大一个数量级
   - 允许好的负载均衡

### 经验法则

| Kernel 类型 | 建议 Occupancy | 建议 Block Size |
|-------------|----------------|-----------------|
| 计算密集型（矩阵乘） | 25-50% | 128-256 |
| 内存带宽密集型 | 75-100% | 256-512 |
| 延迟密集型（间接寻址） | 100% | 256 |

## 示例：H100 SXM 上的 Matrix Multiply Kernel

### H100 SXM 规格

| 规格 | H100 SXM |
|------|----------|
| SM Count | 132 |
| CUDA Cores / SM | 128 |
| Max Warps / SM | 64 |
| Max Threads / SM | 2048 |
| Registers / SM | 65536 |
| Shared Memory / SM | 228 KB |
| Max Blocks / SM | 32 |

### Matrix Multiply Kernel 假设

```cuda
// 使用 16x16 的 tile，每线程多个元素
#define TILE_SIZE 16

__global__ void matmul_kernel(float *A, float *B, float *C, 
                               int M, int N, int K) {
    __shared__ float As[TILE_SIZE][TILE_SIZE];
    __shared__ float Bs[TILE_SIZE][TILE_SIZE];
    
    int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + threadIdx.x;
    
    float sum = 0.0f;
    for (int t = 0; t < K / TILE_SIZE; t++) {
        As[threadIdx.y][threadIdx.x] = A[row * K + t * TILE_SIZE + threadIdx.x];
        Bs[threadIdx.y][threadIdx.x] = B[(t * TILE_SIZE + threadIdx.y) * N + col];
        __syncthreads();
        
        for (int k = 0; k < TILE_SIZE; k++) {
            sum += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        }
        __syncthreads();
    }
    C[row * N + col] = sum;
}
// 调用: matmul_kernel<<<grid, dim3(TILE_SIZE, TILE_SIZE)>>>(...)
// Block Size: 256
```

### Occupancy 计算

**假设编译器为 kernel 分配 40 个寄存器，每 Block 使用 2 KB 共享内存（As+Bs 各 16x16 float）：**

```
Block Size: 256
Warps / Block: ceil(256 / 32) = 8

1. 寄存器限制:
   max_blocks_by_regs = 65536 / (40 * 256) = 65536 / 10240 = 6

2. 共享内存限制:
   max_blocks_by_shmem = 228 KB / 2 KB = 114  // As, Bs 各 256 float
   但实际上 As 和 Bs 各 16×16=256 float = 2×256×4=2048 bytes = 2 KB
   // 注意 __shared__ float As[TILE_SIZE][TILE_SIZE] = 16*16*4 = 1024 bytes
   // 所以总共 2048 bytes = 2 KB
   // 228 KB / 2 KB = 114

3. 线程限制:
   max_blocks_by_threads = 2048 / 256 = 8

4. Warp 限制:
   max_blocks_by_warps = 64 / 8 = 8

5. Block 数硬件限制:
   max_blocks_by_hw = 32

Active_Blocks = min(6, 114, 8, 8, 32) = 6
Active_Warps = 6 * 8 = 48
Occupancy = 48 / 64 = 75%
```

**这意味着 SM 上有 6 个 Block 同时运行，共 48 个 Warp，75% Occupancy。**

如果通过编译器选项将寄存器限制到 32：

```
max_blocks_by_regs = 65536 / (32 * 256) = 65536 / 8192 = 8
Active_Blocks = min(8, 114, 8, 8, 32) = 8
Active_Warps = 8 * 8 = 64
Occupancy = 64 / 64 = 100%
```

但寄存器限制可能导致寄存器溢出（Spill），使用 Local Memory（Global Memory）来存储，反而会降低性能。需要权衡。

### 使用 Occupancy API

CUDA 提供运行时 API 来计算 Occupancy，无需手动计算：

```cuda
int min_grid_size, block_size;

// 1. 给定 block size 下的最大 active blocks
cudaOccupancyMaxActiveBlocksPerMultiprocessor(
    &num_blocks,          // output: active blocks per SM
    my_kernel,            // kernel function
    256,                  // block size
    0                     // dynamic shared memory bytes
);

// 2. 自动建议 block size
cudaOccupancyMaxPotentialBlockSize(
    &min_grid_size,       // output: min grid size for full SM utilization
    &block_size,          // output: suggested block size
    my_kernel,            // kernel function
    0,                    // dynamic shared memory bytes
    0                     // block size limit (0 = no limit)
);
```

## 总结

| 因素 | 描述 | 调优方法 |
|------|------|----------|
| 每线程寄存器 | 每个线程占用的寄存器数 | 使用 `--maxrregcount` 限制 |
| 共享内存 / Block | 每个 Block 需要的共享内存 | 减少共享内存或重构 kernel |
| Block Size | 线程块中的线程数 | 选择 32 的倍数，128-512 为宜 |
| Grid Size | Grid 中的 Block 数 | 至少 SM 数量的数倍 |

## 参考文献

- NVIDIA. *CUDA Occupancy Calculator*. https://docs.nvidia.com/cuda/cuda-occupancy-calculator/index.html
- NVIDIA. *CUDA C++ Best Practices Guide*. "Chapter 9: Execution Configuration Optimizations." https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#execution-configuration-optimizations
- NVIDIA. *CUDA C++ Programming Guide*. "Chapter 10: Device Characteristics." https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#compute-capabilities
- NVIDIA. "CUDA Pro Tip: Occupancy API Simplifies Launch Configuration." *NVIDIA Developer Blog*, 2017. https://developer.nvidia.com/blog/cuda-pro-tip-occupancy-api-simplifies-launch-configuration/
- Volkov, Vasily. "Better Performance at Lower Occupancy." *GPU Technology Conference*, 2010. http://www.nvidia.com/content/sc/volkov/sc_volkov.pdf
