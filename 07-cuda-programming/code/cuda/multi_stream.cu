/**
 * multi_stream.cu — 多 Stream 并发执行对比
 *
 * 演示:
 *   启动 4 个计算密集型 Kernel，分别测量：
 *     版本 1: 全部在默认 Stream 上串行执行
 *     版本 2: 每个 Kernel 在独立 Stream 上并发执行
 *   比较两种方式的总耗时，观察 Hyper-Q 带来的并发收益。
 *
 * 编译: nvcc -o multi_stream multi_stream.cu
 * 运行: ./multi_stream
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
// 计算密集型 Kernel: 大量浮点运算，使 Kernel 成为 Compute-Bound
// 每个线程对输入值做多次乘加运算
// ---------------------------------------------------------------------------
__global__ void compute_kernel(const float *in, float *out, int n, int iters) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        float v = in[idx];
        // 大量浮点运算：iters 次迭代，每次包含 3 次 FMA 操作
        #pragma unroll
        for (int i = 0; i < iters; i++) {
            v = v * v + 0.5f;
            v = v * 0.9f + 0.1f;
            v = v * v - 0.3f;
        }
        out[idx] = v;
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
    const int N          = 1 << 24;     // 每 Kernel 16,777,216 个元素
    const int NUM_KERNELS = 4;           // 4 个 Kernel
    const int ITERS       = 128;         // 每元素计算迭代次数
    const size_t BYTES    = N * sizeof(float);
    const int BLOCK_SIZE  = 256;
    const int GRID_SIZE   = (N + BLOCK_SIZE - 1) / BLOCK_SIZE;

    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));

    printf("==============================================================\n");
    printf("  Multi-Stream: Serial vs Concurrent Kernel Execution\n");
    printf("==============================================================\n");
    printf("GPU:                  %s\n", prop.name);
    printf("SM count:             %d\n", prop.multiProcessorCount);
    printf("Max blocks/SM:        %d\n", prop.maxBlocksPerMultiProcessor);
    printf("Concurrent kernels:   %s\n",
           prop.concurrentKernels ? "supported" : "NOT supported");
    printf("\n");
    printf("N per kernel:         %d (%.2f MB)\n", N,
           (double)BYTES / (1024 * 1024));
    printf("Compute iterations:   %d per element\n", ITERS);
    printf("Grid:                 %d blocks, %d threads/block\n",
           GRID_SIZE, BLOCK_SIZE);
    printf("--------------------------------------------------------------\n");

    // -----------------------------------------------------------------------
    // 分配内存 (4 组独立数据，每组包含 in/out)
    // -----------------------------------------------------------------------
    float *h_in[NUM_KERNELS], *h_out[NUM_KERNELS];
    float *d_in[NUM_KERNELS], *d_out[NUM_KERNELS];

    for (int i = 0; i < NUM_KERNELS; i++) {
        CUDA_CHECK(cudaHostAlloc((void**)&h_in[i], BYTES, cudaHostAllocDefault));
        CUDA_CHECK(cudaHostAlloc((void**)&h_out[i], BYTES, cudaHostAllocDefault));
        CUDA_CHECK(cudaMalloc((void**)&d_in[i], BYTES));
        CUDA_CHECK(cudaMalloc((void**)&d_out[i], BYTES));

        for (int j = 0; j < N; j++) {
            h_in[i][j] = (float)((i * N + j) % 100) / 100.0f;
        }
        CUDA_CHECK(cudaMemcpy(d_in[i], h_in[i], BYTES, cudaMemcpyHostToDevice));
    }

    // 预热
    compute_kernel<<<1, 1>>>(d_in[0], d_out[0], 1, 1);
    CUDA_CHECK(cudaDeviceSynchronize());

    // =======================================================================
    // 版本 1: 所有 Kernel 在默认 Stream 上串行执行
    // =======================================================================
    printf("\n[Version 1] All 4 kernels on default stream (serialized)\n");
    {
        GpuTimer timer;
        timer.begin();

        for (int i = 0; i < NUM_KERNELS; i++) {
            compute_kernel<<<GRID_SIZE, BLOCK_SIZE>>>(d_in[i], d_out[i], N, ITERS);
        }

        float ms = timer.end();  // synchronizes default stream
        printf("  Total time (same stream):  %.2f ms\n", ms);
    }

    // =======================================================================
    // 版本 2: 每个 Kernel 在独立 Stream 上并发执行
    // =======================================================================
    printf("\n[Version 2] Each kernel on its own stream (concurrent)\n");
    {
        cudaStream_t streams[NUM_KERNELS];
        for (int i = 0; i < NUM_KERNELS; i++) {
            CUDA_CHECK(cudaStreamCreate(&streams[i]));
        }

        GpuTimer timer;
        timer.begin();

        for (int i = 0; i < NUM_KERNELS; i++) {
            compute_kernel<<<GRID_SIZE, BLOCK_SIZE, 0, streams[i]>>>(
                d_in[i], d_out[i], N, ITERS);
        }

        // 等待所有 Stream 完成
        for (int i = 0; i < NUM_KERNELS; i++) {
            CUDA_CHECK(cudaStreamSynchronize(streams[i]));
        }

        float ms = timer.end();
        printf("  Total time (diff streams): %.2f ms\n", ms);

        for (int i = 0; i < NUM_KERNELS; i++) {
            CUDA_CHECK(cudaStreamDestroy(streams[i]));
        }
    }

    // =======================================================================
    // 精确对比 (多次运行取平均)
    // =======================================================================
    printf("\n--------------------------------------------------------------\n");
    printf("  Detailed Comparison (avg of 5 runs)\n");
    printf("--------------------------------------------------------------\n");

    const int NUM_RUNS = 5;
    float seq_times[NUM_RUNS], conc_times[NUM_RUNS];

    for (int run = 0; run < NUM_RUNS; run++) {
        // Sequential
        {
            GpuTimer timer;
            timer.begin();
            for (int i = 0; i < NUM_KERNELS; i++) {
                compute_kernel<<<GRID_SIZE, BLOCK_SIZE>>>(
                    d_in[i], d_out[i], N, ITERS);
            }
            seq_times[run] = timer.end();
        }

        // Concurrent
        {
            cudaStream_t streams[NUM_KERNELS];
            for (int i = 0; i < NUM_KERNELS; i++) {
                CUDA_CHECK(cudaStreamCreate(&streams[i]));
            }
            GpuTimer timer;
            timer.begin();
            for (int i = 0; i < NUM_KERNELS; i++) {
                compute_kernel<<<GRID_SIZE, BLOCK_SIZE, 0, streams[i]>>>(
                    d_in[i], d_out[i], N, ITERS);
            }
            for (int i = 0; i < NUM_KERNELS; i++) {
                CUDA_CHECK(cudaStreamSynchronize(streams[i]));
            }
            conc_times[run] = timer.end();
            for (int i = 0; i < NUM_KERNELS; i++) {
                CUDA_CHECK(cudaStreamDestroy(streams[i]));
            }
        }
    }

    float seq_avg = 0, conc_avg = 0;
    for (int r = 0; r < NUM_RUNS; r++) {
        seq_avg += seq_times[r];
        conc_avg += conc_times[r];
    }
    seq_avg /= NUM_RUNS;
    conc_avg /= NUM_RUNS;

    printf("  Sequential average:       %.2f ms\n", seq_avg);
    printf("  Concurrent average:       %.2f ms\n", conc_avg);
    if (conc_avg > 0) {
        printf("  Speedup:                  %.2fx\n", seq_avg / conc_avg);
    }

    // 说明并发收益的前提
    printf("\n--------------------------------------------------------------\n");
    printf("  Observations\n");
    printf("--------------------------------------------------------------\n");
    printf("  Concurrency benefit depends on:\n");
    printf("    - GPU SM count (more SMs => more room for concurrent kernels)\n");
    printf("    - Resource usage per kernel (registers, shared memory)\n");
    printf("    - Whether kernels are compute-bound vs memory-bound\n");
    printf("  Hyper-Q (Kepler+) enables multiple hardware work queues,\n");
    printf("  allowing kernels from different streams to run concurrently\n");
    printf("  if sufficient SM resources are available.\n");

    // -----------------------------------------------------------------------
    // 验证正确性
    // -----------------------------------------------------------------------
    printf("\n--------------------------------------------------------------\n");
    printf("  Verification\n");
    printf("--------------------------------------------------------------\n");
    {
        bool all_ok = true;
        for (int i = 0; i < NUM_KERNELS; i++) {
            float *check;
            CUDA_CHECK(cudaHostAlloc((void**)&check, BYTES, cudaHostAllocDefault));
            CUDA_CHECK(cudaMemcpy(check, d_out[i], BYTES, cudaMemcpyDeviceToHost));

            // 用 CPU 验证前 10 个元素
            for (int j = 0; j < 10; j++) {
                float v = h_in[i][j];
                for (int k = 0; k < ITERS; k++) {
                    v = v * v + 0.5f;
                    v = v * 0.9f + 0.1f;
                    v = v * v - 0.3f;
                }
                float expected = v;
                if (abs(check[j] - expected) > 1e-4 &&
                    abs(check[j] - expected) / max(1.0f, abs(expected)) > 1e-4) {
                    printf("  Kernel %d, element %d: got %f, expected %f\n",
                           i, j, check[j], expected);
                    all_ok = false;
                }
            }
            CUDA_CHECK(cudaFreeHost(check));
        }
        printf("  Result: %s\n", all_ok ? "PASSED" : "FAILED (mismatch detected)");
    }

    // -----------------------------------------------------------------------
    // 清理
    // -----------------------------------------------------------------------
    for (int i = 0; i < NUM_KERNELS; i++) {
        CUDA_CHECK(cudaFree(d_in[i]));
        CUDA_CHECK(cudaFree(d_out[i]));
        CUDA_CHECK(cudaFreeHost(h_in[i]));
        CUDA_CHECK(cudaFreeHost(h_out[i]));
    }

    printf("\nDone.\n");
    return 0;
}

// 参考文献
// ----------
// - NVIDIA, CUDA C++ Programming Guide, Ch.3: Stream and Event
// - NVIDIA, "CUDA Pro Tip: How to Overlap Data Transfers and Kernel Execution"
// - NVIDIA, Hyper-Q in Kepler GK110 Architecture Whitepaper
