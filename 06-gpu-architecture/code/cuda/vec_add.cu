/**
 * vec_add.cu — 向量加法：CPU vs GPU 性能对比
 *
 * 计算两个长度为 N 的 float 向量相加，对比 CPU 和 GPU 的执行时间。
 * N = 1<<20 = 1,048,576
 *
 * 编译：nvcc -o vec_add vec_add.cu
 * 运行：./vec_add
 *
 * 关键概念：
 * - CPU 顺序循环 vs GPU 并行 kernel
 * - cudaMemcpy 的时间开销（H2D、D2H）
 * - 线程块/网格大小设置
 */

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <sys/time.h>

#define N (1 << 20)  // 1,048,576 个元素

// CPU 版本：简单循环
void vec_add_cpu(const float *a, const float *b, float *c, int n) {
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
}

// GPU Kernel：每个线程添加一个元素
__global__ void vec_add_gpu(const float *a, const float *b, float *c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

// 计时辅助函数（秒级精度）
double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

// 验证前几个元素
int check_result(const float *cpu_c, const float *gpu_c, int n) {
    for (int i = 0; i < n && i < 10; i++) {
        if (fabs(cpu_c[i] - gpu_c[i]) > 1e-5) {
            printf("  ERROR at [%d]: CPU=%f, GPU=%f\n", i, cpu_c[i], gpu_c[i]);
            return 0;
        }
    }
    return 1;
}

int main() {
    printf("=== 向量加法对比：CPU vs GPU ===\n");
    printf("向量长度 N = %d (%.2f MB)\n\n", N, (double)(N * sizeof(float)) / (1024 * 1024));

    // 分配主机内存
    float *h_a = (float *)malloc(N * sizeof(float));
    float *h_b = (float *)malloc(N * sizeof(float));
    float *h_c_cpu = (float *)malloc(N * sizeof(float));
    float *h_c_gpu = (float *)malloc(N * sizeof(float));

    // 初始化数据
    for (int i = 0; i < N; i++) {
        h_a[i] = (float)(rand() % 100) / 10.0f;
        h_b[i] = (float)(rand() % 100) / 10.0f;
    }

    // === CPU 版本 ===
    double t_start = get_time();
    vec_add_cpu(h_a, h_b, h_c_cpu, N);
    double t_end = get_time();
    double cpu_time = t_end - t_start;
    printf("CPU 时间:        %8.4f ms\n", cpu_time * 1000.0);

    // === GPU 版本 ===
    // 分配设备内存
    float *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, N * sizeof(float));
    cudaMalloc(&d_b, N * sizeof(float));
    cudaMalloc(&d_c, N * sizeof(float));

    // 计时：包含数据拷贝 + kernel 执行
    t_start = get_time();

    // H2D：主机 → 设备
    cudaMemcpy(d_a, h_a, N * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, N * sizeof(float), cudaMemcpyHostToDevice);

    // 执行 kernel
    int threads_per_block = 256;
    int blocks = (N + threads_per_block - 1) / threads_per_block;
    vec_add_gpu<<<blocks, threads_per_block>>>(d_a, d_b, d_c, N);
    cudaDeviceSynchronize();

    // D2H：设备 → 主机
    cudaMemcpy(h_c_gpu, d_c, N * sizeof(float), cudaMemcpyDeviceToHost);

    t_end = get_time();
    double gpu_total_time = t_end - t_start;

    // 仅计算 kernel 执行时间（使用 CUDA Event）
    cudaEvent_t start_event, stop_event;
    cudaEventCreate(&start_event);
    cudaEventCreate(&stop_event);

    cudaEventRecord(start_event);
    vec_add_gpu<<<blocks, threads_per_block>>>(d_a, d_b, d_c, N);
    cudaEventRecord(stop_event);
    cudaEventSynchronize(stop_event);

    float kernel_ms = 0;
    cudaEventElapsedTime(&kernel_ms, start_event, stop_event);

    printf("GPU 总时间 (含拷贝):  %8.4f ms\n", gpu_total_time * 1000.0);
    printf("GPU Kernel 时间:      %8.4f ms\n", kernel_ms);

    // 单独测量拷贝时间
    t_start = get_time();
    cudaMemcpy(d_a, h_a, N * sizeof(float), cudaMemcpyHostToDevice);
    t_end = get_time();
    double h2d_time = t_end - t_start;

    t_start = get_time();
    cudaMemcpy(h_c_gpu, d_c, N * sizeof(float), cudaMemcpyDeviceToHost);
    t_end = get_time();
    double d2h_time = t_end - t_start;
    printf("H2D 拷贝时间:         %8.4f ms\n", h2d_time * 1000.0);
    printf("D2H 拷贝时间:         %8.4f ms\n", d2h_time * 1000.0);

    // 验证
    printf("\n>>> 验证（前 10 个元素）<<<\n");
    for (int i = 0; i < 10 && i < N; i++) {
        printf("  [%d] CPU=%8.2f  GPU=%8.2f  %s\n",
               i, h_c_cpu[i], h_c_gpu[i],
               (fabs(h_c_cpu[i] - h_c_gpu[i]) < 1e-5) ? "OK" : "MISMATCH");
    }
    int pass = check_result(h_c_cpu, h_c_gpu, N);
    printf("\n  整体: %s\n", pass ? "PASSED" : "FAILED");

    // 加速比分析
    printf("\n=== 性能分析 ===\n");
    printf("CPU 时间:                %.2f ms\n", cpu_time * 1000.0);
    printf("GPU 总时间 (含拷贝):     %.2f ms\n", gpu_total_time * 1000.0);
    printf("GPU Kernel 时间:         %.2f ms\n", kernel_ms);

    double cpu_ms = cpu_time * 1000.0;
    if (kernel_ms > 0) {
        printf("Kernel 加速比 (CPU/Kernel):  %.2f 倍\n", cpu_ms / kernel_ms);
    }
    if (gpu_total_time > 0) {
        printf("总加速比 (CPU/含拷贝):       %.2f 倍\n", cpu_ms / (gpu_total_time * 1000.0));
    }

    printf("\n注意：当 N 较小时，PCIe 拷贝开销会主导 GPU 执行时间。\n");
    printf("N 越大，GPU 的并行优势越明显。\n");

    // 清理
    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);
    cudaEventDestroy(start_event);
    cudaEventDestroy(stop_event);
    free(h_a);
    free(h_b);
    free(h_c_cpu);
    free(h_c_gpu);

    return 0;
}
