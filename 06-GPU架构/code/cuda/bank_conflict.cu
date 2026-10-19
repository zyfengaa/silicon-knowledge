/**
 * bank_conflict.cu — 共享内存 Bank Conflict 演示
 *
 * 使用一个 32 线程的线程块（正好是一个 warp），对比三种访问模式：
 * 模式 1（无冲突）：s_data[rep % 32][tx] — 同一 warp 内 32 个线程访问不同 bank
 * 模式 2（有冲突）：s_data[tx][rep % 32] — 32x32 无填充数组的列访问，所有线程同 bank
 * 模式 3（Padding）：s_data[tx][rep % 32] — 32x33 带填充数组的列访问，bank 被打散
 *
 * 编译：nvcc -o bank_conflict bank_conflict.cu
 * 运行：./bank_conflict
 *
 * 关键概念：
 * - 共享内存的 32 个 Bank，每个 Bank 4 字节宽
 * - Bank 索引 = (字地址) % 32
 * - 行主序 vs 列主序访问的 bank conflict 影响
 * - Padding 消除 bank conflict
 *
 * 说明：一个 warp 的 32 个线程在同一个周期访问共享内存。
 * 只有当 32 个线程访问 32 个不同 bank 时才能 1 个周期完成；
 * 若多个线程访问同一 bank 的不同地址，则被串行化为多路。
 */

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define TILE_SIZE 32
#define REPS 1024      // 每个 kernel 内重复读取的次数（放大可测量的时间差）
#define ITERATIONS 1000  // 重复启动 kernel 的次数

// ----------------------------------------------------------------
// 模式 1：无 Bank Conflict（行固定，列 = threadIdx.x）
// 线程 tx 访问 s_data[r][tx]，地址（以字为单位）= r * 32 + tx
// bank = (r * 32 + tx) % 32 = tx % 32
// 32 个线程分别命中 bank 0..31，无冲突
// ----------------------------------------------------------------
__global__ void no_conflict_kernel(float *output) {
    __shared__ float s_data[TILE_SIZE][TILE_SIZE];

    int tx = threadIdx.x;  // 0..31

    // 初始化共享内存
    for (int c = 0; c < TILE_SIZE; c++) {
        s_data[tx][c] = (float)(tx * TILE_SIZE + c);
    }
    __syncthreads();

    float sum = 0.0f;
    for (int rep = 0; rep < REPS; rep++) {
        // 行号固定、列号 = tx：warp 内命中 32 个不同 bank
        sum += s_data[rep & (TILE_SIZE - 1)][tx];
    }

    output[tx] = sum;
}

// ----------------------------------------------------------------
// 模式 2：32 路 Bank Conflict（列访问，无填充）
// 线程 tx 访问 s_data[tx][r]，地址（以字为单位）= tx * 32 + r
// bank = (tx * 32 + r) % 32 = r  → 所有 32 个线程命中同一个 bank，
// 且地址互不相同（不能广播）→ 串行化为 32 路
// ----------------------------------------------------------------
__global__ void conflict_kernel(float *output) {
    __shared__ float s_data[TILE_SIZE][TILE_SIZE];

    int tx = threadIdx.x;

    for (int c = 0; c < TILE_SIZE; c++) {
        s_data[tx][c] = (float)(tx * TILE_SIZE + c);
    }
    __syncthreads();

    float sum = 0.0f;
    for (int rep = 0; rep < REPS; rep++) {
        // 列号固定、行号 = tx：所有线程落在同一个 bank
        sum += s_data[tx][rep & (TILE_SIZE - 1)];
    }

    output[tx] = sum;
}

// ----------------------------------------------------------------
// 模式 3：Padding 消除 Bank Conflict
// s_data[TILE_SIZE][TILE_SIZE + 1]，每行多一个元素
// 线程 tx 访问 s_data[tx][r]，地址 = tx * 33 + r
// bank = (tx * 33 + r) % 32 = (tx + r) % 32
// 对固定的 r，32 个线程的 bank 两两不同 → 无冲突
// ----------------------------------------------------------------
#define PADDED_TILE_SIZE (TILE_SIZE + 1)

__global__ void padded_kernel(float *output) {
    __shared__ float s_data[TILE_SIZE][PADDED_TILE_SIZE];

    int tx = threadIdx.x;

    for (int c = 0; c < TILE_SIZE; c++) {
        s_data[tx][c] = (float)(tx * TILE_SIZE + c);
    }
    __syncthreads();

    float sum = 0.0f;
    for (int rep = 0; rep < REPS; rep++) {
        // 与模式 2 相同的列访问，但 padding 把 bank 打散
        sum += s_data[tx][rep & (TILE_SIZE - 1)];
    }

    output[tx] = sum;
}

int main() {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);

    printf("=== 共享内存 Bank Conflict 比较 ===\n\n");
    printf("Device:     %s\n", prop.name);
    printf("Block:      %d 线程（1 个 warp）\n", TILE_SIZE);
    printf("每 kernel:  %d 次共享内存读取\n\n", REPS);

    float *d_output;
    float h_output[TILE_SIZE];
    cudaMalloc((void **)&d_output, TILE_SIZE * sizeof(float));

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    float ms_no_conflict = 0, ms_conflict = 0, ms_padded = 0;

    // === 测试：无 Bank Conflict（行访问） ===
    cudaEventRecord(start);
    for (int i = 0; i < ITERATIONS; i++) {
        no_conflict_kernel<<<1, TILE_SIZE>>>(d_output);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms_no_conflict, start, stop);
    cudaMemcpy(h_output, d_output, TILE_SIZE * sizeof(float), cudaMemcpyDeviceToHost);
    double no_conflict_sum = 0;
    for (int i = 0; i < TILE_SIZE; i++) no_conflict_sum += h_output[i];

    printf("模式 1 — 无 Bank Conflict (s_data[r][tx]):\n");
    printf("  校验和: %.0f\n", no_conflict_sum);
    printf("  时间:   %.3f ms (%.3f us/iter)\n\n",
           ms_no_conflict, ms_no_conflict / ITERATIONS * 1000);

    // === 测试：有 Bank Conflict（列访问，无填充） ===
    cudaEventRecord(start);
    for (int i = 0; i < ITERATIONS; i++) {
        conflict_kernel<<<1, TILE_SIZE>>>(d_output);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms_conflict, start, stop);
    cudaMemcpy(h_output, d_output, TILE_SIZE * sizeof(float), cudaMemcpyDeviceToHost);
    double conflict_sum = 0;
    for (int i = 0; i < TILE_SIZE; i++) conflict_sum += h_output[i];

    printf("模式 2 — 32 路 Bank Conflict (s_data[tx][r], 宽度 32):\n");
    printf("  校验和: %.0f\n", conflict_sum);
    printf("  时间:   %.3f ms (%.3f us/iter)\n\n",
           ms_conflict, ms_conflict / ITERATIONS * 1000);

    // === 测试：Padding 消除 Bank Conflict ===
    cudaEventRecord(start);
    for (int i = 0; i < ITERATIONS; i++) {
        padded_kernel<<<1, TILE_SIZE>>>(d_output);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms_padded, start, stop);
    cudaMemcpy(h_output, d_output, TILE_SIZE * sizeof(float), cudaMemcpyDeviceToHost);
    double padded_sum = 0;
    for (int i = 0; i < TILE_SIZE; i++) padded_sum += h_output[i];

    printf("模式 3 — Padding 消除 (s_data[tx][r], 宽度 33):\n");
    printf("  校验和: %.0f\n", padded_sum);
    printf("  时间:   %.3f ms (%.3f us/iter)\n\n",
           ms_padded, ms_padded / ITERATIONS * 1000);

    // === 对比 ===
    printf("=== 性能对比 ===\n");
    printf("  无冲突 (行访问):         %.3f ms\n", ms_no_conflict);
    printf("  有冲突 (列访问):         %.3f ms\n", ms_conflict);
    printf("  Padding 消除冲突:        %.3f ms\n", ms_padded);

    if (ms_no_conflict > 0) {
        printf("\n  冲突 / 无冲突:           %.2f 倍\n", ms_conflict / ms_no_conflict);
    }
    if (ms_padded > 0) {
        printf("  Padding / 无冲突:        %.2f 倍\n", ms_padded / ms_no_conflict);
    }
    printf("\n  三个 kernel 的校验和应相同（数据相同，仅访问顺序不同）。\n");

    // 清理
    cudaFree(d_output);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    return 0;
}
