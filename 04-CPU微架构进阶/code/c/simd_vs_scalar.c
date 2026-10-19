/**
 * simd_vs_scalar.c — Dot product: scalar loop vs AVX intrinsics.
 *
 * Computes the dot product of two float arrays using:
 *   1. A plain scalar loop
 *   2. AVX (256-bit) SIMD intrinsics with horizontal reduction
 *
 * Prints the computed result, a correctness check, and run times.
 *
 * Compile:
 *   gcc -O2 -mavx -mfma -fno-tree-vectorize -o simd_vs_scalar simd_vs_scalar.c
 *
 * -fno-tree-vectorize keeps the scalar baseline scalar; GCC 12+ may
 * otherwise auto-vectorize it at -O2.
 *
 * Note: N = 16M floats means 64 MB per array (128 MB total), so both
 * kernels are largely memory-bandwidth-bound.  The measured speedup is
 * therefore much lower than the 8x vector-width ratio.
 *
 * Run:
 *   ./simd_vs_scalar
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <immintrin.h>   /* AVX intrinsics (_mm256_*) */

#ifndef N
#define N  (1024 * 1024 * 16)    /* 16 million floats */
#endif

/* ------------------------------------------------------------------ */
/*  Double-precision reference                                        */
/* ------------------------------------------------------------------ */
static double
dot_ref(const float *restrict a, const float *restrict b, int n)
{
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        sum += (double)a[i] * (double)b[i];
    }
    return sum;
}

/* ------------------------------------------------------------------ */
/*  Scalar dot product                                                */
/* ------------------------------------------------------------------ */
static float
dot_scalar(const float *restrict a, const float *restrict b, int n)
{
    float sum = 0.0f;
    for (int i = 0; i < n; i++) {
        sum += a[i] * b[i];
    }
    return sum;
}

/* ------------------------------------------------------------------ */
/*  AVX dot product — 8 floats per iteration + horizontal reduction   */
/* ------------------------------------------------------------------ */
static float
dot_avx(const float *restrict a, const float *restrict b, int n)
{
    __m256 vsum = _mm256_setzero_ps();   /* 8 accumulators */
    int i;

    /* Process 8 floats per iteration. */
    for (i = 0; i <= n - 8; i += 8) {
        __m256 va = _mm256_load_ps(&a[i]);
        __m256 vb = _mm256_load_ps(&b[i]);
        vsum = _mm256_fmadd_ps(va, vb, vsum);   /* vsum += va * vb  (FMA) */
    }

    /* Horizontal reduction: sum all 8 lanes into one float. */
    __m128 hi = _mm256_extractf128_ps(vsum, 1);   /* upper 128 bits */
    __m128 lo = _mm256_castps256_ps128(vsum);     /* lower 128 bits */
    __m128 sum128 = _mm_add_ps(lo, hi);           /* 4 + 4 = 4 floats */
    /* Two more shuffles to reduce 4 → 1. */
    sum128 = _mm_hadd_ps(sum128, sum128);          /* (0+1, 2+3, 0+1, 2+3) */
    sum128 = _mm_hadd_ps(sum128, sum128);          /* (0+1+2+3) in lane 0 */
    float sum = _mm_cvtss_f32(sum128);

    /* Tail elements (0 .. 7). */
    for (; i < n; i++) {
        sum += a[i] * b[i];
    }

    return sum;
}

/* ------------------------------------------------------------------ */
/*  High-resolution timer (nanoseconds)                               */
/* ------------------------------------------------------------------ */
static double
time_diff_ns(const struct timespec *start, const struct timespec *end)
{
    return (double)(end->tv_sec - start->tv_sec) * 1.0e9
         + (double)(end->tv_nsec - start->tv_nsec);
}

/* ------------------------------------------------------------------ */
/*  Main                                                              */
/* ------------------------------------------------------------------ */
int
main(void)
{
    struct timespec t1, t2;
    double elapsed_scalar, elapsed_avx;
    float result_scalar, result_avx;

    /* Allocate and initialise arrays. */
    float *a = (float *)aligned_alloc(32, (size_t)N * sizeof(float));
    float *b = (float *)aligned_alloc(32, (size_t)N * sizeof(float));
    if (!a || !b) {
        perror("aligned_alloc");
        return EXIT_FAILURE;
    }

    for (int i = 0; i < N; i++) {
        a[i] = (float)(i + 1) * 0.125f;
        b[i] = (float)(i % 10 + 1);
    }

    /* ---- Reference (double precision) ---- */
    double ref = dot_ref(a, b, N);

    /* ---- Scalar ---- */
    clock_gettime(CLOCK_MONOTONIC, &t1);
    result_scalar = dot_scalar(a, b, N);
    clock_gettime(CLOCK_MONOTONIC, &t2);
    elapsed_scalar = time_diff_ns(&t1, &t2);

    printf("Scalar dot product : %.6f\n", result_scalar);

    /* ---- AVX ---- */
    clock_gettime(CLOCK_MONOTONIC, &t1);
    result_avx = dot_avx(a, b, N);
    clock_gettime(CLOCK_MONOTONIC, &t2);
    elapsed_avx = time_diff_ns(&t1, &t2);

    printf("AVX   dot product : %.6f\n", result_avx);

    /* ---- Correctness (relative error vs double reference) ----
     *
     * 注意：这里比较的是数值结果，不是实现是否正确。标量版本用 float
     * 逐项累加 16M 项，累加和增长到 ~1e14 后每次加法都会丢失低位，
     * 误差可达百分之几；AVX 版本有 8 个独立累加器，误差小得多。
     * 这是 float32 累加的精度特性，不是代码错误，因此使用较宽的容差，
     * 并同时打印两个误差供对比。
     */
    double rel_scalar = fabs((double)result_scalar - ref) / (fabs(ref) + 1.0e-12);
    double rel_avx    = fabs((double)result_avx    - ref) / (fabs(ref) + 1.0e-12);
    printf("Reference (double) : %.6e\n", ref);
    printf("Relative error: scalar=%.3e  AVX=%.3e  %s\n",
           rel_scalar, rel_avx,
           (rel_scalar <= 5.0e-2 && rel_avx <= 1.0e-2) ? "OK" : "MISMATCH");
    printf("(float32 逐项累加误差随 N 增长；标量约 1e-2 属正常，"
           "AVX 多累加器通常低一个数量级)\n");

    /* ---- Performance ---- */
    printf("\n=== Performance ===\n");
    printf("Scalar : %8.2f ms\n", elapsed_scalar / 1.0e6);
    printf("AVX    : %8.2f ms\n", elapsed_avx / 1.0e6);
    printf("Speedup: %.2f x\n", elapsed_scalar / elapsed_avx);

    free(a);
    free(b);
    return 0;
}

/* References:
 *   - Intel Corporation, "Intel 64 and IA-32 Architectures Optimization
 *     Reference Manual", Chapters 9-15.
 *   - Intel Intrinsics Guide,
 *     https://www.intel.com/content/www/us/en/docs/intrinsics-guide/
 *   - Hennessy, J. L. & Patterson, D. A. "Computer Architecture:
 *     A Quantitative Approach", 6th Edition, Chapter 4 (Data-Level
 *     Parallelism in Vector, SIMD, and GPU Architectures).
 *   - Patterson, D. A. & Hennessy, J. L. "Computer Organization and
 *     Design RISC-V Edition", Chapter 6 (Parallel Processors from
 *     Client to Cloud).
 */
