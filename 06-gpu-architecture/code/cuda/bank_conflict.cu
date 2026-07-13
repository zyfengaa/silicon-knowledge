/**
 * bank_conflict.cu — 共享内存 Bank Conflict 演示
 *
 * 使用 2D 共享内存数组 s_data[32][32]，对比两种访问模式：
 * 模式 1（无冲突）：s_data[threadIdx.x][threadIdx.y] — 同一 warp 内访问不同 bank
 * 模式 2（有冲突）：s_data[threadIdx.y][threadIdx.x] — 同一 warp 内访问相同 bank
 *
 * 编译：nvcc -o bank_conflict bank_conflict.cu
 * 运行：./bank_conflict
 *
 * 关键概念：
 * - 共享内存的 32 个 Bank，每个 Bank 4 字节宽
 * - Bank 索引 = (地址 / 4) % 32
 * - 行主序 vs 列主序访问的 bank conflict 影响
 * - Padding 消除 bank conflict
 */

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define TILE_SIZE 32
#define WARP_SIZE 32

// ----------------------------------------------------------------
// 模式 1：无 Bank Conflict
// 使用 2D 行主序数组 s_data[32][32]
// 线程 (tx, ty) 访问 s_data[tx][ty]
// 对于 warp 内的线程（tx 相同，ty 变化），
// 地址 = &s_data[tx][0] + ty，ty 从 0..31
// bank = (address / 4) % 32 = (base + ty) % 32 → 对应 bank 0..31
// 每个线程访问不同 bank，无冲突
// ----------------------------------------------------------------
__global__ void no_conflict_kernel(float *output, int n) {
    __shared__ float s_data[TILE_SIZE][TILE_SIZE];

    int tx = threadIdx.x;  // 行索引
    int ty = threadIdx.y;  // 列索引

    s_data[tx][ty] = (float)(tx * TILE_SIZE + ty);
    __syncthreads();

    // 计算每行的和
    float sum = 0.0f;
    for (int i = 0; i < TILE_SIZE; i++) {
        sum += s_data[tx][i];  // 同一行，连续列 — 无冲突（跨步=1）
    }

    if (tx == 0 && ty == 0) {
        *output = sum;
    }
}

// ----------------------------------------------------------------
// 模式 2：有 Bank Conflict
// 线程 (tx, ty) 访问 s_data[ty][tx]（转置访问）
// 对于 warp 内的线程（tx 相同，ty 变化），
// 地址 = &s_data[0][tx] + ty * 32
// bank = (base + ty * 32) % 32 = base → 所有线程访问同一 bank！
// 导致 32 路 bank conflict
// ----------------------------------------------------------------
__global__ void conflict_kernel(float *output, int n) {
    __shared__ float s_data[TILE_SIZE][TILE_SIZE];

    int tx = threadIdx.x;
    int ty = threadIdx.y;

    s_data[tx][ty] = (float)(tx * TILE_SIZE + ty);
    __syncthreads();

    // 按列访问 — 同一 warp 内的线程访问同一列的不同行
    // s_data[0..31][ty]：对于固定 ty，tx 从 0..31
    // bank = (address_of(s_data[0][ty]) + tx * 32 * 4) / 4 % 32
    //       = (base + tx * 32) % 32 = base → 所有线程同 bank！冲突！
    float sum = 0.0f;
    for (int j = 0; j < TILE_SIZE; j++) {
        sum += s_data[j][ty];  // 按列读取 — bank conflict
    }

    if (tx == 0 && ty == 0) {
        *output = sum;
    }
}

// ----------------------------------------------------------------
// 模式 3：Padding 消除 Bank Conflict
// s_data[TILE_SIZE][TILE_SIZE + 1] 每行多一个元素
// 同一列在不同行的地址偏移 = (TILE_SIZE + 1) * 4 = 132 字节
// bank = (base + tx * 33) % 32 = (base + tx) % 32 → 不同 bank
// ----------------------------------------------------------------
#define PADDED_TILE_SIZE (TILE_SIZE + 1)

__global__ void padded_kernel(float *output, int n) {
    __shared__ float s_data[TILE_SIZE][PADDED_TILE_SIZE];

    int tx = threadIdx.x;
    int ty = threadIdx.y;

    s_data[tx][ty] = (float)(tx * TILE_SIZE + ty);
    __syncthreads();

    // 按列读取 — 由于 padding，不同行的同一列在不同 bank
    float sum = 0.0f;
    for (int j = 0; j < TILE_SIZE; j++) {
        sum += s_data[j][ty];
    }

    if (tx == 0 && ty == 0) {
        *output = sum;
    }
}

int main() {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);

    printf("=== 共享内存 Bank Conflict 比较 ===\n\n");
    printf("Device:     %s\n", prop.name);
    printf("Tile size:  %d x %d (1 warp)\n\n", TILE_SIZE, TILE_SIZE);

    float *d_output;
    float h_output;

    cudaMalloc(&d_output, sizeof(float));

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    float ms_conflict = 0, ms_no_conflict = 0, ms_padded = 0;
    int iterations = 10000;  // 重复多次以获得可测量的时间

    dim3 block(TILE_SIZE, TILE_SIZE);  // 32 x 32 = 1024 线程

    // === 测试：无 Bank Conflict（行主序访问） ===
    cudaEventRecord(start);
    for (int i = 0; i < iterations; i++) {
        no_conflict_kernel<<<1, block>>>(d_output, TILE_SIZE);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms_no_conflict, start, stop);
    cudaMemcpy(&h_output, d_output, sizeof(float), cudaMemcpyDeviceToHost);

    printf("模式 1 — 无 Bank Conflict (s_data[tx][ty]):\n");
    printf("  结果:   %f\n", h_output);
    printf("  时间:   %.3f ms (%.3f us/iter)\n\n",
           ms_no_conflict, ms_no_conflict / iterations * 1000);

    // === 测试：有 Bank Conflict（转置访问） ===
    cudaEventRecord(start);
    for (int i = 0; i < iterations; i++) {
        conflict_kernel<<<1, block>>>(d_output, TILE_SIZE);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms_conflict, start, stop);
    cudaMemcpy(&h_output, d_output, sizeof(float), cudaMemcpyDeviceToHost);

    printf("模式 2 — 有 Bank Conflict (s_data[ty][tx]):\n");
    printf("  结果:   %f\n", h_output);
    printf("  时间:   %.3f ms (%.3f us/iter)\n\n",
           ms_conflict, ms_conflict / iterations * 1000);

    // === 测试：Padding 消除 Bank Conflict ===
    cudaEventRecord(start);
    for (int i = 0; i < iterations; i++) {
        padded_kernel<<<1, block>>>(d_output, TILE_SIZE);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms_padded, start, stop);
    cudaMemcpy(&h_output, d_output, sizeof(float), cudaMemcpyDeviceToHost);

    printf("模式 3 — Padding 消除 (s_data[32][33]):\n");
    printf("  结果:   %f\n", h_output);
    printf("  时间:   %.3f ms (%.3f us/iter)\n\n",
           ms_padded, ms_padded / iterations * 1000);

    // === 对比 ===
    printf("=== 性能对比 ===\n");
    printf("  无冲突 (行主序):     %.3f ms\n", ms_no_conflict);
    printf("  有冲突 (列主序):     %.3f ms\n", ms_conflict);
    printf("  Padding 消除冲突:    %.3f ms\n", ms_padded);

    if (ms_no_conflict > 0) {
        printf("\n  冲突 vs 无冲突:      %.2f 倍\n", ms_conflict / ms_no_conflict);
    }
    if (ms_padded > 0) {
        printf("  无冲突 vs Padding:   %.2f 倍\n", ms_no_conflict / ms_padded);
    }

    // 清理
    cudaFree(d_output);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    return 0;
}
