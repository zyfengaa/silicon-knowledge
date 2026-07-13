/**
 * matrix_mul.cu — 矩阵乘法：Naive 全局内存 vs Tiled 共享内存
 *
 * N = 1024（方阵，float）
 * 版本 1 (Naive): 每个线程直接使用全局内存，无优化
 * 版本 2 (Tiled): 使用共享内存的分块（tiling）优化，tile size = 16
 *
 * 对比执行时间和 GFLOPS。
 *
 * 编译：nvcc -o matmul matrix_mul.cu
 * 运行：./matmul
 *
 * 关键概念：
 * - 全局内存的合并访问
 * - 共享内存 tile 的分块策略
 * - __syncthreads() 的正确使用
 */

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define N 1024
#define TILE_SIZE 16

// ============================================================
// 版本 1：Naive 全局内存矩阵乘法
// C = A * B（行主序）
// 每个线程计算 C[row][col]
// ============================================================
__global__ void matmul_naive(const float *A, const float *B, float *C, int n) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < n && col < n) {
        float sum = 0.0f;
        for (int k = 0; k < n; k++) {
            sum += A[row * n + k] * B[k * n + col];
        }
        C[row * n + col] = sum;
    }
}

// ============================================================
// 版本 2：Tiled（分块）共享内存矩阵乘法
// 使用 TILE_SIZE × TILE_SIZE 的 tile
// 每个线程块协作将 tile 加载到共享内存中，
// 减少全局内存访问次数
// ============================================================
__global__ void matmul_tiled(const float *A, const float *B, float *C, int n) {
    __shared__ float s_A[TILE_SIZE][TILE_SIZE];
    __shared__ float s_B[TILE_SIZE][TILE_SIZE];

    int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + threadIdx.x;

    float sum = 0.0f;
    int num_tiles = (n + TILE_SIZE - 1) / TILE_SIZE;

    for (int t = 0; t < num_tiles; t++) {
        // 协作加载 A 和 B 的 tile 到共享内存
        if (row < n && t * TILE_SIZE + threadIdx.x < n)
            s_A[threadIdx.y][threadIdx.x] = A[row * n + t * TILE_SIZE + threadIdx.x];
        else
            s_A[threadIdx.y][threadIdx.x] = 0.0f;

        if (col < n && t * TILE_SIZE + threadIdx.y < n)
            s_B[threadIdx.y][threadIdx.x] = B[(t * TILE_SIZE + threadIdx.y) * n + col];
        else
            s_B[threadIdx.y][threadIdx.x] = 0.0f;

        __syncthreads();

        // 在 tile 内计算乘积
        for (int k = 0; k < TILE_SIZE; k++) {
            sum += s_A[threadIdx.y][k] * s_B[k][threadIdx.x];
        }
        __syncthreads();
    }

    if (row < n && col < n) {
        C[row * n + col] = sum;
    }
}

// ============================================================
// 辅助函数
// ============================================================

void init_matrix(float *mat, int n) {
    for (int i = 0; i < n * n; i++) {
        mat[i] = (float)(rand() % 10) / 1.0f;
    }
}

int verify_result(const float *C, const float *A, const float *B, int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            float expected = 0.0f;
            for (int k = 0; k < n; k++) {
                expected += A[i * n + k] * B[k * n + j];
            }
            if (fabsf(C[i * n + j] - expected) > 1e-2) {
                printf("  Mismatch at [%d,%d]: got %f, expected %f\n",
                       i, j, C[i * n + j], expected);
                return 0;
            }
        }
    }
    return 1;
}

double calculate_gflops(int n, double time_ms) {
    // 2 * n^3 次运算（n^3 次乘法和 n^3 次加法）
    double ops = 2.0 * n * n * n;
    double time_s = time_ms / 1000.0;
    return (ops / time_s) / 1e9;
}

int main() {
    printf("=== 矩阵乘法性能对比 (N=%d) ===\n\n", N);

    size_t bytes = N * N * sizeof(float);

    // 主机内存
    float *h_A = (float *)malloc(bytes);
    float *h_B = (float *)malloc(bytes);
    float *h_C_naive = (float *)malloc(bytes);
    float *h_C_tiled = (float *)malloc(bytes);

    init_matrix(h_A, N);
    init_matrix(h_B, N);

    // 设备内存
    float *d_A, *d_B, *d_C;
    cudaMalloc(&d_A, bytes);
    cudaMalloc(&d_B, bytes);
    cudaMalloc(&d_C, bytes);

    cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice);

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    dim3 block_2d(TILE_SIZE, TILE_SIZE);
    dim3 grid_2d((N + TILE_SIZE - 1) / TILE_SIZE,
                 (N + TILE_SIZE - 1) / TILE_SIZE);

    float ms = 0.0f;

    // ---- 版本 1：Naive ----
    cudaEventRecord(start);
    matmul_naive<<<grid_2d, block_2d>>>(d_A, d_B, d_C, N);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms, start, stop);
    cudaMemcpy(h_C_naive, d_C, bytes, cudaMemcpyDeviceToHost);

    float gflops_naive = (float)calculate_gflops(N, ms);
    printf("版本 1 — Naive Global Memory:\n");
    printf("  时间:   %.2f ms\n", ms);
    printf("  GFLOPS: %.2f\n", gflops_naive);
    printf("  验证:   %s\n\n",
           verify_result(h_C_naive, h_A, h_B, N) ? "PASSED" : "FAILED");

    // ---- 版本 2：Tiled Shared Memory ----
    cudaEventRecord(start);
    matmul_tiled<<<grid_2d, block_2d>>>(d_A, d_B, d_C, N);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms, start, stop);
    cudaMemcpy(h_C_tiled, d_C, bytes, cudaMemcpyDeviceToHost);

    float gflops_tiled = (float)calculate_gflops(N, ms);
    printf("版本 2 — Tiled Shared Memory (Tile=%d):\n", TILE_SIZE);
    printf("  时间:   %.2f ms\n", ms);
    printf("  GFLOPS: %.2f\n", gflops_tiled);
    printf("  验证:   %s\n\n",
           verify_result(h_C_tiled, h_A, h_B, N) ? "PASSED" : "FAILED");

    // ---- 性能总结 ----
    printf("=== 性能总结 ===\n");
    printf("  Naive:   %.0f GFLOPS\n", gflops_naive);
    printf("  Tiled:   %.0f GFLOPS\n", gflops_tiled);
    if (gflops_naive > 0)
        printf("  加速比: %.2f 倍\n", gflops_tiled / gflops_naive);

    // 清理
    cudaFree(d_A);
    cudaFree(d_B);
    cudaFree(d_C);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    free(h_A);
    free(h_B);
    free(h_C_naive);
    free(h_C_tiled);

    return 0;
}
