/**
 * async_copy.cu — 使用 Pinned Memory 和 Stream 实现异步传输与计算重叠
 *
 * 演示:
 *   将 N = 1<<24 个元素分成 3 个 chunk，每个 chunk 在一个独立 Stream 中
 *   执行 H2D 拷贝、Kernel 计算、D2H 拷贝。
 *   比较 Stream 异步执行 vs 同步顺序执行的总时间。
 *
 * 编译: nvcc -o async_copy async_copy.cu
 * 运行: ./async_copy
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
// Kernel: 向量加法
// ---------------------------------------------------------------------------
__global__ void vec_add_kernel(const float *a, const float *b, float *c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

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

int main() {
    // -----------------------------------------------------------------------
    // 配置
    // -----------------------------------------------------------------------
    const int N          = 1 << 24;     // 总共 16,777,216 个元素
    const int NUM_STREAMS = 3;           // 3 个 Stream
    const int CHUNK       = N / NUM_STREAMS;  // 每个 Stream 处理 5,592,405 个元素
    const size_t BYTES_TOTAL = N * sizeof(float);
    const size_t BYTES_CHUNK = CHUNK * sizeof(float);
    const int BLOCK_SIZE = 256;
    const int GRID_CHUNK  = (CHUNK + BLOCK_SIZE - 1) / BLOCK_SIZE;

    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));

    printf("============================================\n");
    printf("  Async Copy: Stream Overlap Demo\n");
    printf("============================================\n");
    printf("Device:        %s\n", prop.name);
    printf("Total N:       %d elements (%.2f MB)\n", N,
           (double)BYTES_TOTAL / (1024 * 1024));
    printf("Streams:       %d\n", NUM_STREAMS);
    printf("Chunk size:    %d elements (%.2f MB)\n", CHUNK,
           (double)BYTES_CHUNK / (1024 * 1024));
    printf("Grid/stream:   %d blocks\n", GRID_CHUNK);
    printf("--------------------------------------------\n");

    // -----------------------------------------------------------------------
    // 分配 Pinned Memory (Host)
    // -----------------------------------------------------------------------
    float *h_a, *h_b, *h_c;
    CUDA_CHECK(cudaHostAlloc((void**)&h_a, BYTES_TOTAL, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void**)&h_b, BYTES_TOTAL, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void**)&h_c, BYTES_TOTAL, cudaHostAllocDefault));

    // 初始化数据
    for (int i = 0; i < N; i++) {
        h_a[i] = (float)(i % 1000) / 100.0f;
        h_b[i] = (float)((i + 500) % 1000) / 100.0f;
    }

    // -----------------------------------------------------------------------
    // 分配 Device Memory
    // -----------------------------------------------------------------------
    float *d_a, *d_b, *d_c;
    CUDA_CHECK(cudaMalloc((void**)&d_a, BYTES_TOTAL));
    CUDA_CHECK(cudaMalloc((void**)&d_b, BYTES_TOTAL));
    CUDA_CHECK(cudaMalloc((void**)&d_c, BYTES_TOTAL));

    // -----------------------------------------------------------------------
    // 创建 Stream
    // -----------------------------------------------------------------------
    cudaStream_t streams[NUM_STREAMS];
    for (int i = 0; i < NUM_STREAMS; i++) {
        CUDA_CHECK(cudaStreamCreate(&streams[i]));
    }

    // 预热
    vec_add_kernel<<<1, 1>>>(d_a, d_b, d_c, 1);
    CUDA_CHECK(cudaDeviceSynchronize());

    // =======================================================================
    // 实验 1: 同步顺序执行 (sequential, no streams)
    // =======================================================================
    printf("\n[Experiment 1] Sequential (synchronous, no streams)\n");
    {
        GpuTimer timer;
        timer.begin();

        for (int i = 0; i < NUM_STREAMS; i++) {
            int offset = i * CHUNK;
            int chunk = (i == NUM_STREAMS - 1) ? (N - offset) : CHUNK;
            size_t chunk_bytes = chunk * sizeof(float);

            // 同步 H2D
            CUDA_CHECK(cudaMemcpy(d_a + offset, h_a + offset, chunk_bytes,
                                  cudaMemcpyHostToDevice));
            CUDA_CHECK(cudaMemcpy(d_b + offset, h_b + offset, chunk_bytes,
                                  cudaMemcpyHostToDevice));

            // Kernel
            int grid = (chunk + BLOCK_SIZE - 1) / BLOCK_SIZE;
            vec_add_kernel<<<grid, BLOCK_SIZE>>>(d_a + offset, d_b + offset,
                                                  d_c + offset, chunk);

            // 同步 D2H
            CUDA_CHECK(cudaMemcpy(h_c + offset, d_c + offset, chunk_bytes,
                                  cudaMemcpyDeviceToHost));
        }

        float ms = timer.end();
        printf("  Sequential time:  %.2f ms\n", ms);

        // 验证
        bool ok = true;
        for (int i = 0; i < 10; i++) {
            float expected = h_a[i] + h_b[i];
            if (abs(h_c[i] - expected) > 1e-4) { ok = false; break; }
        }
        printf("  Verification:     %s\n", ok ? "PASSED" : "FAILED");
    }

    // =======================================================================
    // 实验 2: Stream 异步执行 (overlapped)
    // =======================================================================
    printf("\n[Experiment 2] Async with streams (overlapped)\n");
    {
        GpuTimer timer;
        timer.begin();

        for (int i = 0; i < NUM_STREAMS; i++) {
            int offset = i * CHUNK;
            int chunk = (i == NUM_STREAMS - 1) ? (N - offset) : CHUNK;
            size_t chunk_bytes = chunk * sizeof(float);

            // H2D — async on stream
            CUDA_CHECK(cudaMemcpyAsync(d_a + offset, h_a + offset, chunk_bytes,
                                       cudaMemcpyHostToDevice, streams[i]));
            CUDA_CHECK(cudaMemcpyAsync(d_b + offset, h_b + offset, chunk_bytes,
                                       cudaMemcpyHostToDevice, streams[i]));

            // Kernel — on stream
            int grid = (chunk + BLOCK_SIZE - 1) / BLOCK_SIZE;
            vec_add_kernel<<<grid, BLOCK_SIZE, 0, streams[i]>>>(d_a + offset,
                d_b + offset, d_c + offset, chunk);

            // D2H — async on stream
            CUDA_CHECK(cudaMemcpyAsync(h_c + offset, d_c + offset, chunk_bytes,
                                       cudaMemcpyDeviceToHost, streams[i]));
        }

        // 等待所有 Stream 完成
        for (int i = 0; i < NUM_STREAMS; i++) {
            CUDA_CHECK(cudaStreamSynchronize(streams[i]));
        }

        float ms = timer.end();
        printf("  Streamed time:    %.2f ms\n", ms);

        // 验证
        bool ok = true;
        for (int i = 0; i < 10; i++) {
            float expected = h_a[i] + h_b[i];
            if (abs(h_c[i] - expected) > 1e-4) { ok = false; break; }
        }
        printf("  Verification:     %s\n", ok ? "PASSED" : "FAILED");
    }

    // =======================================================================
    // 比较
    // =======================================================================
    printf("\n============================================\n");
    printf("  Summary\n");
    printf("============================================\n");
    // 重新计时以精确比较
    float seq_ms, async_ms;
    {
        // Sequential
        {
            GpuTimer timer;
            timer.begin();
            for (int i = 0; i < NUM_STREAMS; i++) {
                int offset = i * CHUNK;
                int chunk = (i == NUM_STREAMS - 1) ? (N - offset) : CHUNK;
                size_t chunk_bytes = chunk * sizeof(float);
                CUDA_CHECK(cudaMemcpy(d_a + offset, h_a + offset, chunk_bytes,
                                      cudaMemcpyHostToDevice));
                CUDA_CHECK(cudaMemcpy(d_b + offset, h_b + offset, chunk_bytes,
                                      cudaMemcpyHostToDevice));
                int grid = (chunk + BLOCK_SIZE - 1) / BLOCK_SIZE;
                vec_add_kernel<<<grid, BLOCK_SIZE>>>(d_a + offset, d_b + offset,
                                                      d_c + offset, chunk);
                CUDA_CHECK(cudaMemcpy(h_c + offset, d_c + offset, chunk_bytes,
                                      cudaMemcpyDeviceToHost));
            }
            seq_ms = timer.end();
        }

        // Async
        {
            GpuTimer timer;
            timer.begin();
            for (int i = 0; i < NUM_STREAMS; i++) {
                int offset = i * CHUNK;
                int chunk = (i == NUM_STREAMS - 1) ? (N - offset) : CHUNK;
                size_t chunk_bytes = chunk * sizeof(float);
                CUDA_CHECK(cudaMemcpyAsync(d_a + offset, h_a + offset, chunk_bytes,
                                           cudaMemcpyHostToDevice, streams[i]));
                CUDA_CHECK(cudaMemcpyAsync(d_b + offset, h_b + offset, chunk_bytes,
                                           cudaMemcpyHostToDevice, streams[i]));
                int grid = (chunk + BLOCK_SIZE - 1) / BLOCK_SIZE;
                vec_add_kernel<<<grid, BLOCK_SIZE, 0, streams[i]>>>(d_a + offset,
                    d_b + offset, d_c + offset, chunk);
                CUDA_CHECK(cudaMemcpyAsync(h_c + offset, d_c + offset, chunk_bytes,
                                           cudaMemcpyDeviceToHost, streams[i]));
            }
            for (int i = 0; i < NUM_STREAMS; i++) {
                CUDA_CHECK(cudaStreamSynchronize(streams[i]));
            }
            async_ms = timer.end();
        }
    }

    printf("  Sequential:       %8.2f ms\n", seq_ms);
    printf("  Async (streams):  %8.2f ms\n", async_ms);
    if (async_ms > 0) {
        printf("  Speedup:          %8.2fx\n", seq_ms / async_ms);
    }

    // -----------------------------------------------------------------------
    // 清理
    // -----------------------------------------------------------------------
    for (int i = 0; i < NUM_STREAMS; i++) {
        CUDA_CHECK(cudaStreamDestroy(streams[i]));
    }
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    CUDA_CHECK(cudaFreeHost(h_a));
    CUDA_CHECK(cudaFreeHost(h_b));
    CUDA_CHECK(cudaFreeHost(h_c));

    printf("\nDone.\n");
    return 0;
}

// 参考文献
// ----------
// - NVIDIA, CUDA C++ Programming Guide, Ch.3: Stream and Event
// - NVIDIA, CUDA C++ Best Practices Guide, Ch.6: Asynchronous and Overlapping Transfers
