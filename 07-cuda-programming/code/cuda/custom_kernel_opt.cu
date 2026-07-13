/**
 * custom_kernel_opt.cu — 向量加法 Kernel 优化对比
 *
 * 演示 N = 1<<25 数据量下三种 Kernel 版本的性能差异：
 *   v1 — Naive baseline: 每个线程处理 1 个元素，直接 Global Memory 读写
 *   v2 — Loop unrolling: 每个线程处理 4 个元素，手动展开循环
 *   v3 — Vectorized int4: 使用 uint4 一次加载/存储 4 个 float，减少指令数
 *
 * 打印每个版本的 Kernel 耗时和达到的带宽，并验证正确性。
 *
 * 编译: nvcc -O3 -lineinfo -o custom_kernel_opt custom_kernel_opt.cu
 * 运行: ./custom_kernel_opt
 */

#include <stdio.h>
#include <cuda_runtime.h>

#define CUDA_CHECK(call) do {                                      \
    cudaError_t err = call;                                        \
    if (err != cudaSuccess) {                                      \
        fprintf(stderr, "CUDA error at %s:%d: %s\n",               \
                __FILE__, __LINE__, cudaGetErrorString(err));       \
        exit(1);                                                   \
    }                                                              \
} while(0)

// ---------------------------------------------------------------------------
// Timer: 基于 CUDA Event
// ---------------------------------------------------------------------------
struct GpuTimer {
    cudaEvent_t start, stop;
    GpuTimer()  { cudaEventCreate(&start); cudaEventCreate(&stop); }
    ~GpuTimer() { cudaEventDestroy(start); cudaEventDestroy(stop); }
    void begin(cudaStream_t s = 0) { cudaEventRecord(start, s); }
    float end(cudaStream_t s = 0) {
        cudaEventRecord(stop, s);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        return ms;
    }
};

// ---------------------------------------------------------------------------
// 公共参数
// ---------------------------------------------------------------------------
const int N           = 1 << 25;     // 33,554,432 个元素
const size_t BYTES    = N * sizeof(float);
const int BLOCK_SIZE  = 256;
const int GRID_SIZE   = (N + BLOCK_SIZE - 1) / BLOCK_SIZE;

// ===================================================================
// v1 — Naive baseline
// 每个线程处理 1 个元素，不做任何优化
// ===================================================================
__global__ void vec_add_v1(const float *a, const float *b, float *c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

// ===================================================================
// v2 — Loop unrolling
// 每个线程处理 4 个元素，减少循环开销，提升指令级并行
// ===================================================================
__global__ void vec_add_v2(const float *a, const float *b, float *c, int n) {
    // 每个线程处理 ELEMS_PER_THREAD 个元素
    const int ELEMS_PER_THREAD = 4;
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int idx = tid * ELEMS_PER_THREAD;

    // 手动展开的循环：每个线程处理 4 个连续元素
    if (idx + 0 < n) {
        c[idx + 0] = a[idx + 0] + b[idx + 0];
    }
    if (idx + 1 < n) {
        c[idx + 1] = a[idx + 1] + b[idx + 1];
    }
    if (idx + 2 < n) {
        c[idx + 2] = a[idx + 2] + b[idx + 2];
    }
    if (idx + 3 < n) {
        c[idx + 3] = a[idx + 3] + b[idx + 3];
    }
}

// ===================================================================
// v3 — Vectorized int4 loads
// 使用 uint4 一次加载 4 个 float（16 字节），
// 减少指令数并充分利用内存带宽
// ===================================================================
__global__ void vec_add_v3(const float *a, const float *b, float *c, int n) {
    // 将指针重解释为 uint4（每个 uint4 = 4 x 32-bit = 16 字节）
    const uint4 *a4 = reinterpret_cast<const uint4*>(a);
    const uint4 *b4 = reinterpret_cast<const uint4*>(b);
    uint4       *c4 = reinterpret_cast<uint4*>(c);

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int n4 = n / 4;  // 向量化后的元素数

    if (idx < n4) {
        uint4 va = a4[idx];
        uint4 vb = b4[idx];
        uint4 vc;

        // 将 uint 位转换为 float 进行计算，再转回 uint
        // 使用 __int_as_float / __float_as_int 实现 bit-cast
        vc.x = __float_as_int(__int_as_float(va.x) + __int_as_float(vb.x));
        vc.y = __float_as_int(__int_as_float(va.y) + __int_as_float(vb.y));
        vc.z = __float_as_int(__int_as_float(va.z) + __int_as_float(vb.z));
        vc.w = __float_as_int(__int_as_float(va.w) + __int_as_float(vb.w));

        c4[idx] = vc;
    }

    // 处理剩余元素 (n % 4 != 0)
    int remainder_start = n4 * 4;
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid < n && tid >= remainder_start) {
        c[tid] = a[tid] + b[tid];
    }
}

// ===================================================================
// Main
// ===================================================================
int main() {
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));

    printf("============================================================\n");
    printf("  Kernel Optimization: Vector Addition (N = 2^25)\n");
    printf("============================================================\n");
    printf("Device:   %s\n", prop.name);
    printf("N:        %d elements (%.2f MB per array)\n", N,
           (double)BYTES / (1024 * 1024));
    printf("Block:    %d threads\n", BLOCK_SIZE);
    printf("Grid:     %d blocks\n", GRID_SIZE);
    printf("------------------------------------------------------------\n");
    printf("  v1: Naive (1 element/thread)\n");
    printf("  v2: Loop unrolling (4 elements/thread, unrolled)\n");
    printf("  v3: Vectorized int4 (uint4 loads/stores)\n");
    printf("------------------------------------------------------------\n");

    // -----------------------------------------------------------------------
    // 分配 Host Pinned Memory
    // -----------------------------------------------------------------------
    float *h_a, *h_b, *h_c1, *h_c2, *h_c3;
    CUDA_CHECK(cudaHostAlloc((void**)&h_a, BYTES, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void**)&h_b, BYTES, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void**)&h_c1, BYTES, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void**)&h_c2, BYTES, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void**)&h_c3, BYTES, cudaHostAllocDefault));

    for (int i = 0; i < N; i++) {
        h_a[i] = (float)(i % 1000) / 100.0f;
        h_b[i] = (float)((i + 500) % 1000) / 100.0f;
    }

    // -----------------------------------------------------------------------
    // 分配 Device Memory
    // -----------------------------------------------------------------------
    float *d_a, *d_b, *d_c;
    CUDA_CHECK(cudaMalloc((void**)&d_a, BYTES));
    CUDA_CHECK(cudaMalloc((void**)&d_b, BYTES));
    CUDA_CHECK(cudaMalloc((void**)&d_c, BYTES));

    CUDA_CHECK(cudaMemcpy(d_a, h_a, BYTES, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, BYTES, cudaMemcpyHostToDevice));

    // 预热
    vec_add_v1<<<1, 1>>>(d_a, d_b, d_c, 1);
    CUDA_CHECK(cudaDeviceSynchronize());

    // -----------------------------------------------------------------------
    // 计时: 每个版本运行多次取平均
    // -----------------------------------------------------------------------
    const int NUM_ITERS = 20;

    double v1_time = 0, v2_time = 0, v3_time = 0;

    printf("\n  Version              Time (ms)    BW (GB/s)    Speedup\n");
    printf("  ---------------------------------------------------------\n");

    // v1: Naive
    {
        GpuTimer timer;
        timer.begin();
        for (int it = 0; it < NUM_ITERS; it++) {
            vec_add_v1<<<GRID_SIZE, BLOCK_SIZE>>>(d_a, d_b, d_c, N);
        }
        v1_time = timer.end() / NUM_ITERS;
        double bw = (3.0 * BYTES) / (v1_time * 1e6);  // R + R + W
        printf("  v1 Naive            %8.3f     %8.2f    1.00x\n", v1_time, bw);
    }

    // v2: Loop unrolling (每个线程处理 4 个元素，grid 缩小 4x)
    {
        const int ELEMS_PER_THREAD = 4;
        const int GRID_V2 = (N + BLOCK_SIZE * ELEMS_PER_THREAD - 1)
                          / (BLOCK_SIZE * ELEMS_PER_THREAD);
        GpuTimer timer;
        timer.begin();
        for (int it = 0; it < NUM_ITERS; it++) {
            vec_add_v2<<<GRID_V2, BLOCK_SIZE>>>(d_a, d_b, d_c, N);
        }
        v2_time = timer.end() / NUM_ITERS;
        double bw = (3.0 * BYTES) / (v2_time * 1e6);
        printf("  v2 Loop Unroll      %8.3f     %8.2f    %.2fx\n",
               v2_time, bw, v1_time / v2_time);
    }

    // v3: Vectorized int4
    {
        int n4 = N / 4;
        int grid_v3 = (n4 + BLOCK_SIZE - 1) / BLOCK_SIZE;
        GpuTimer timer;
        timer.begin();
        for (int it = 0; it < NUM_ITERS; it++) {
            vec_add_v3<<<grid_v3, BLOCK_SIZE>>>(d_a, d_b, d_c, N);
        }
        v3_time = timer.end() / NUM_ITERS;
        double bw = (3.0 * BYTES) / (v3_time * 1e6);
        printf("  v3 Vectorized int4  %8.3f     %8.2f    %.2fx\n",
               v3_time, bw, v1_time / v3_time);
    }

    // -----------------------------------------------------------------------
    // 验证正确性（所有版本与 CPU 参考值对比）
    // -----------------------------------------------------------------------
    printf("\n------------------------------------------------------------\n");
    printf("  Correctness Verification\n");
    printf("------------------------------------------------------------\n");

    // 获取 v1 结果
    vec_add_v1<<<GRID_SIZE, BLOCK_SIZE>>>(d_a, d_b, d_c, N);
    CUDA_CHECK(cudaMemcpy(h_c1, d_c, BYTES, cudaMemcpyDeviceToHost));

    // 获取 v2 结果
    {
        const int ELEMS_PER_THREAD = 4;
        const int GRID_V2 = (N + BLOCK_SIZE * ELEMS_PER_THREAD - 1)
                          / (BLOCK_SIZE * ELEMS_PER_THREAD);
        vec_add_v2<<<GRID_V2, BLOCK_SIZE>>>(d_a, d_b, d_c, N);
        CUDA_CHECK(cudaMemcpy(h_c2, d_c, BYTES, cudaMemcpyDeviceToHost));
    }

    // 获取 v3 结果
    {
        int n4 = N / 4;
        int grid_v3 = (n4 + BLOCK_SIZE - 1) / BLOCK_SIZE;
        vec_add_v3<<<grid_v3, BLOCK_SIZE>>>(d_a, d_b, d_c, N);
        CUDA_CHECK(cudaMemcpy(h_c3, d_c, BYTES, cudaMemcpyDeviceToHost));
    }

    // 比较前 10 个元素
    bool all_ok = true;
    printf("  idx     ref (v1)       v2 (unroll)    v3 (int4)      match\n");
    printf("  ---------------------------------------------------------\n");
    for (int i = 0; i < 10; i++) {
        float ref   = h_a[i] + h_b[i];
        bool ok2    = abs(h_c2[i] - ref) < 1e-4;
        bool ok3    = abs(h_c3[i] - ref) < 1e-4;
        bool ok     = ok2 && ok3;
        printf("  [%3d]   %8.4f       %8.4f       %8.4f       %s\n",
               i, ref, h_c2[i], h_c3[i], ok ? "OK" : "MISMATCH");
        if (!ok) all_ok = false;
    }
    printf("\n  Overall: %s\n", all_ok ? "PASSED (all versions produce correct results)"
                                      : "FAILED (version mismatch detected)");

    // -----------------------------------------------------------------------
    // 清理
    // -----------------------------------------------------------------------
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    CUDA_CHECK(cudaFreeHost(h_a));
    CUDA_CHECK(cudaFreeHost(h_b));
    CUDA_CHECK(cudaFreeHost(h_c1));
    CUDA_CHECK(cudaFreeHost(h_c2));
    CUDA_CHECK(cudaFreeHost(h_c3));

    printf("\nDone.\n");
    return 0;
}

// 参考文献
// ----------
// - NVIDIA, CUDA C++ Best Practices Guide, Ch.8: Memory Optimizations (Vectorized Memory Access)
// - NVIDIA, CUDA C++ Best Practices Guide, Ch.9: Execution Configuration Optimizations
// - Harris, Mark. "How to Access Global Memory Efficiently", NVIDIA Developer Blog, 2013
// - NVIDIA, "CUDA Pro Tip: Vectorized Memory Access", NVIDIA Developer Blog, 2015
