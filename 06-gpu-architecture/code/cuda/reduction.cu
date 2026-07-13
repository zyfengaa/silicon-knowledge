/**
 * reduction.cu — 归约求和：CPU vs GPU 性能对比
 *
 * 对 N = 1<<24 (16,777,216) 个 float 元素求和。
 * CPU 版本：顺序循环归约（基线）
 * GPU 版本：共享内存树形归约 + warp-level 原语
 *
 * 编译：nvcc -o reduction reduction.cu
 * 运行：./reduction
 *
 * 关键概念：
 * - 树形归约（tree reduction）
 * - 共享内存 bank conflict 避免
 * - warp shuffle 指令（__shfl_xor_sync）
 * - 线程发散（thread divergence）
 */

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <sys/time.h>

#define N (1 << 24)      // 16,777,216 个元素
#define BLOCK_SIZE 256

// CPU 顺序归约
float reduce_cpu(const float *data, int n) {
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        sum += data[i];
    }
    return (float)sum;
}

// ----------------------------------------------------------------
// GPU 归约 Kernel
// 阶段 1：共享内存树形归约
// 阶段 2：warp shuffle 原语完成最后归约
// ----------------------------------------------------------------
__global__ void reduce_kernel(const float *in, float *out, int n) {
    extern __shared__ float sdata[];

    unsigned int tid = threadIdx.x;
    unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;

    // 合作加载数据到共享内存
    float val = (idx < n) ? in[idx] : 0.0f;
    sdata[tid] = val;
    __syncthreads();

    // 阶段 1：共享内存树形归约（直到 32 个元素）
    for (unsigned int s = blockDim.x / 2; s > 32; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }

    // 阶段 2：最后 32 个元素使用 warp shuffle 原语
    if (tid < 32) {
        float warp_sum = sdata[tid];
        // 如果 blockDim.x > 32，从共享内存中取第 32+ 个值
        if (blockDim.x > 32) {
            warp_sum += sdata[tid + 32];
        }

        // Warp shuffle 归约
        warp_sum += __shfl_xor_sync(0xFFFFFFFF, warp_sum, 16);
        warp_sum += __shfl_xor_sync(0xFFFFFFFF, warp_sum, 8);
        warp_sum += __shfl_xor_sync(0xFFFFFFFF, warp_sum, 4);
        warp_sum += __shfl_xor_sync(0xFFFFFFFF, warp_sum, 2);
        warp_sum += __shfl_xor_sync(0xFFFFFFFF, warp_sum, 1);

        // 线程 0 输出该 Block 的部分和
        if (tid == 0) {
            out[blockIdx.x] = warp_sum;
        }
    }
}

// 计时辅助函数
double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

int main() {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);

    printf("=== 归约求和：CPU vs GPU ===\n");
    printf("Device:   %s\n", prop.name);
    printf("Elements: %d (%.2f MB)\n\n", N,
           (double)(N * sizeof(float)) / (1024 * 1024));

    // 分配主机内存
    float *h_data = (float *)malloc(N * sizeof(float));

    // 初始化数据
    srand(42);
    for (int i = 0; i < N; i++) {
        h_data[i] = (float)(rand() % 100) / 100.0f;
    }

    // ============ CPU 归约（基线） ============
    double t_start = get_time();
    float cpu_sum = reduce_cpu(h_data, N);
    double t_end = get_time();
    double cpu_time = t_end - t_start;
    printf("CPU 归约结果:   %f\n", cpu_sum);
    printf("CPU 时间:       %.4f ms\n\n", cpu_time * 1000.0);

    // ============ GPU 归约 ============
    float *d_in, *d_out;
    cudaMalloc(&d_in, N * sizeof(float));
    int num_blocks = (N + BLOCK_SIZE - 1) / BLOCK_SIZE;
    cudaMalloc(&d_out, num_blocks * sizeof(float));

    cudaMemcpy(d_in, h_data, N * sizeof(float), cudaMemcpyHostToDevice);

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    // 第一次 Kernel 调用：每个 Block 输出一个部分和
    cudaEventRecord(start);
    reduce_kernel<<<num_blocks, BLOCK_SIZE, BLOCK_SIZE * sizeof(float)>>>(d_in, d_out, N);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float kernel_ms;
    cudaEventElapsedTime(&kernel_ms, start, stop);

    // 将部分和拷贝回主机
    float *h_partial = (float *)malloc(num_blocks * sizeof(float));
    cudaMemcpy(h_partial, d_out, num_blocks * sizeof(float), cudaMemcpyDeviceToHost);

    // 在 CPU 上完成最终归约（num_blocks 个部分和）
    float gpu_sum = 0.0f;
    for (int i = 0; i < num_blocks; i++) {
        gpu_sum += h_partial[i];
    }

    // 验证
    bool pass = (fabs(cpu_sum - gpu_sum) < 1.0f);
    printf("GPU 归约结果:   %f\n", gpu_sum);
    printf("GPU Kernel 时间: %.4f ms\n", kernel_ms);
    printf("验证:           %s\n\n", pass ? "PASSED" : "FAILED");

    // 性能分析
    printf("=== 性能分析 ===\n");
    double cpu_ms = cpu_time * 1000.0;
    printf("CPU 时间:       %.4f ms\n", cpu_ms);
    printf("GPU Kernel 时间: %.4f ms\n", kernel_ms);
    if (kernel_ms > 0) {
        printf("加速比:         %.2f 倍\n", cpu_ms / kernel_ms);
    }

    // 清理
    cudaFree(d_in);
    cudaFree(d_out);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    free(h_data);
    free(h_partial);

    return 0;
}
