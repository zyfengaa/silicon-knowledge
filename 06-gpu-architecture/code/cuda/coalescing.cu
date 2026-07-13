/**
 * coalescing.cu — 合并访问 vs 跨步访问带宽对比
 *
 * 对比两种全局内存访问模式：
 * - 合并访问（Coalesced）：线程 i 访问 array[i]（连续地址）
 * - 跨步访问（Strided）：  线程 i 访问 array[i * stride]（stride = 8）
 *
 * 跨步访问使用 8 倍大的数组，保证每个线程执行相同数量的内存操作。
 *
 * 编译：nvcc -o coalescing coalescing.cu
 * 运行：./coalescing
 *
 * 关键概念：
 * - 全局内存合并访问（coalesced memory access）
 * - 缓存行（cache line）利用率
 * - 有效带宽 vs 峰值带宽
 */

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define N (1 << 20)      // 1,048,576 个元素（合并访问数组大小）
#define STRIDE 8
#define BLOCK_SIZE 256

// ----------------------------------------------------------------
// 合并访问 Kernel：线程 i 访问 array[i]
// 一个 warp 内的 32 个线程访问连续的 32 * 4 = 128 字节
// 正好填满一个缓存行（L2 cache line = 128 bytes）
// ----------------------------------------------------------------
__global__ void coalesced_kernel(const float *in, float *out, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        out[idx] = in[idx] * 2.0f;  // 连续访问：完美合并
    }
}

// ----------------------------------------------------------------
// 跨步访问 Kernel：线程 i 访问 array[i * STRIDE]
// 一个 warp 内的 32 个线程访问地址范围 = 32 * STRIDE * 4 字节
// 跨步 = 8 时，需要加载多个缓存行，利用率为 1/STRIDE
// ----------------------------------------------------------------
__global__ void strided_kernel(const float *in, float *out, int n, int stride) {
    int idx = (blockIdx.x * blockDim.x + threadIdx.x) * stride;
    if (idx < n) {
        out[idx] = in[idx] * 2.0f;  // 跨步访问：缓存行浪费
    }
}

int main() {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);

    printf("=== 合并访问 vs 跨步访问带宽对比 ===\n\n");
    printf("Device:       %s\n", prop.name);
    printf("Coalesced N:  %d (%.2f MB)\n", N,
           (double)(N * sizeof(float)) / (1024 * 1024));
    printf("Strided N:    %d (%.2f MB, stride=%d)\n", N * STRIDE,
           (double)(N * STRIDE * sizeof(float)) / (1024 * 1024), STRIDE);
    printf("Block size:   %d\n\n", BLOCK_SIZE);

    // 分配设备内存（合并访问使用 N 个元素，跨步访问使用 N * STRIDE 个元素）
    float *d_in_coal, *d_out_coal;
    float *d_in_stride, *d_out_stride;
    cudaMalloc(&d_in_coal, N * sizeof(float));
    cudaMalloc(&d_out_coal, N * sizeof(float));
    cudaMalloc(&d_in_stride, N * STRIDE * sizeof(float));
    cudaMalloc(&d_out_stride, N * STRIDE * sizeof(float));

    // 初始化设备数据
    cudaMemset(d_in_coal, 1, N * sizeof(float));
    cudaMemset(d_out_coal, 0, N * sizeof(float));
    cudaMemset(d_in_stride, 1, N * STRIDE * sizeof(float));
    cudaMemset(d_out_stride, 0, N * STRIDE * sizeof(float));

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    float ms = 0.0f;

    int threads = BLOCK_SIZE;
    int blocks_coal = (N + threads - 1) / threads;
    int blocks_stride = (N + threads - 1) / threads;  // 相同数量的线程

    // ---- 合并访问 ----
    cudaEventRecord(start);
    coalesced_kernel<<<blocks_coal, threads>>>(d_in_coal, d_out_coal, N);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms, start, stop);

    // 带宽 = 读 N 个 float + 写 N 个 float = 2 * N * sizeof(float)
    double bytes_read_coal = (double)N * sizeof(float);
    double bytes_written_coal = (double)N * sizeof(float);
    double total_bytes_coal = bytes_read_coal + bytes_written_coal;
    double bw_coal = total_bytes_coal / (ms / 1000.0) / 1e9;

    printf("--- Coalesced (stride=1) ---\n");
    printf("  Time:     %.4f ms\n", ms);
    printf("  Grid:     %d blocks\n", blocks_coal);
    printf("  BW:       %.2f GB/s\n", bw_coal);

    // ---- 跨步访问 ----
    cudaEventRecord(start);
    strided_kernel<<<blocks_stride, threads>>>(d_in_stride, d_out_stride, N * STRIDE, STRIDE);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms, start, stop);

    // 带宽 = 读 N 个 float + 写 N 个 float（虽然数组更大，但只访问了 N 个元素）
    double effective_bytes = (double)(N * sizeof(float)) * 2;  // 读 N + 写 N
    double bw_stride = effective_bytes / (ms / 1000.0) / 1e9;

    // 实际从 DRAM 读取的字节数（跨步访问导致缓存行浪费）
    // 每个 warp (32 线程) 跨步 = STRIDE 时，访问地址范围 = 32 * STRIDE * 4 字节
    // 需要 ceil(32 * STRIDE * 4 / 128) 个缓存行
    double actual_read_bytes = (double)(N * STRIDE) * sizeof(float);
    double actual_bw_stride = actual_read_bytes / (ms / 1000.0) / 1e9;

    printf("\n--- Strided (stride=%d) ---\n", STRIDE);
    printf("  Time:         %.4f ms\n", ms);
    printf("  Grid:         %d blocks\n", blocks_stride);
    printf("  Eff. BW:      %.2f GB/s (基于有效数据)\n", bw_stride);
    printf("  Actual BW:    %.2f GB/s (基于实际请求的 DRAM 字节)\n", actual_bw_stride);

    // 相对性能
    double coals_ms = 0, stride_ms = 0;
    cudaEventRecord(start);
    coalesced_kernel<<<blocks_coal, threads>>>(d_in_coal, d_out_coal, N);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&coals_ms, start, stop);

    cudaEventRecord(start);
    strided_kernel<<<blocks_stride, threads>>>(d_in_stride, d_out_stride, N * STRIDE, STRIDE);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&stride_ms, start, stop);

    printf("\n=== 性能对比 ===\n");
    printf("  Coalesced:  %.4f ms, %.2f GB/s\n", coals_ms, bw_coal);
    printf("  Strided:    %.4f ms, %.2f GB/s (eff)\n", stride_ms, bw_stride);
    printf("  时间比:     %.2f 倍 (跨步/合并)\n", stride_ms / coals_ms);
    printf("  BW 比:      %.2f 倍 (跨步/合并)\n", bw_stride / bw_coal);

    // 清理
    cudaFree(d_in_coal);
    cudaFree(d_out_coal);
    cudaFree(d_in_stride);
    cudaFree(d_out_stride);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    return 0;
}
