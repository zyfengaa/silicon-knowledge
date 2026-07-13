/**
 * simd_add.c — Scalar vs SSE vector addition of two float arrays.
 *
 * Demonstrates the performance difference between a scalar loop and
 * SSE (128-bit SIMD) vector addition on x86 processors.
 *
 * Compile (SSE version):
 *   gcc -O2 -msse -o simd_add simd_add.c
 *
 * Compile (with auto-vectorization hint):
 *   gcc -O2 -msse -fopt-info-vec -o simd_add simd_add.c
 *
 * Run:
 *   ./simd_add
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <xmmintrin.h>  /* SSE intrinsics (_mm_*) */

#ifndef N
#define N  (1024 * 1024 * 64)   /* 64 million floats ~ 256 MB per array */
#endif

/* ------------------------------------------------------------------ */
/*  Scalar addition — one float at a time                             */
/* ------------------------------------------------------------------ */
static void
add_scalar(const float *restrict a,
           const float *restrict b,
           float *restrict c,
           int n)
{
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
}

/* ------------------------------------------------------------------ */
/*  SSE vector addition — 4 floats per iteration                      */
/* ------------------------------------------------------------------ */
static void
add_sse(const float *restrict a,
        const float *restrict b,
        float *restrict c,
        int n)
{
    int i;

    /* Process 4 floats per iteration (128-bit SSE). */
    for (i = 0; i <= n - 4; i += 4) {
        __m128 va = _mm_loadu_ps(&a[i]);   /* unaligned load of 4 floats */
        __m128 vb = _mm_loadu_ps(&b[i]);
        __m128 vc = _mm_add_ps(va, vb);    /* packed single-precision add */
        _mm_storeu_ps(&c[i], vc);          /* unaligned store */
    }

    /* Tail: remaining elements (0 .. 3) handled with scalar code. */
    for (; i < n; i++) {
        c[i] = a[i] + b[i];
    }
}

/* ------------------------------------------------------------------ */
/*  High-resolution wall-clock timer (nanoseconds)                    */
/* ------------------------------------------------------------------ */
static double
time_diff_ns(const struct timespec *start, const struct timespec *end)
{
    return (double)(end->tv_sec - start->tv_sec) * 1.0e9
         + (double)(end->tv_nsec - start->tv_nsec);
}

/* ------------------------------------------------------------------ */
/*  Helper: allocate aligned memory, fill with deterministic data     */
/* ------------------------------------------------------------------ */
static float *
alloc_fill(int n, float base)
{
    float *p = NULL;
    /* Align to 16-byte boundary for SSE. */
    if (posix_memalign((void **)&p, 16, (size_t)n * sizeof(float)) != 0) {
        perror("posix_memalign");
        exit(EXIT_FAILURE);
    }
    for (int i = 0; i < n; i++) {
        p[i] = base + (float)i * 0.5f;
    }
    return p;
}

/* ------------------------------------------------------------------ */
/*  Main                                                              */
/* ------------------------------------------------------------------ */
int
main(void)
{
    struct timespec t1, t2;
    double elapsed_scalar, elapsed_sse;

    printf("Array size : %d floats (%.2f MB per array)\n",
           N, (double)N * sizeof(float) / (1024.0 * 1024.0));

    /* Allocate three arrays. */
    float *a = alloc_fill(N, 1.0f);
    float *b = alloc_fill(N, 2.0f);
    float *c = alloc_fill(N, 0.0f);     /* result */

    /* ---- Scalar ---- */
    clock_gettime(CLOCK_MONOTONIC, &t1);
    add_scalar(a, b, c, N);
    clock_gettime(CLOCK_MONOTONIC, &t2);
    elapsed_scalar = time_diff_ns(&t1, &t2);

    /* Verify a few values. */
    printf("Scalar: c[0]=%.2f  c[1]=%.2f  c[N-1]=%.2f\n",
           c[0], c[1], c[N - 1]);

    /* ---- SSE ---- */
    clock_gettime(CLOCK_MONOTONIC, &t1);
    add_sse(a, b, c, N);
    clock_gettime(CLOCK_MONOTONIC, &t2);
    elapsed_sse = time_diff_ns(&t1, &t2);

    printf("SSE:    c[0]=%.2f  c[1]=%.2f  c[N-1]=%.2f\n",
           c[0], c[1], c[N - 1]);

    /* ---- Results ---- */
    printf("\n=== Performance ===\n");
    printf("Scalar : %8.2f ms\n", elapsed_scalar / 1.0e6);
    printf("SSE    : %8.2f ms\n", elapsed_sse / 1.0e6);
    printf("Speedup: %.2f x\n", elapsed_scalar / elapsed_sse);

    /* ---- Cleanup ---- */
    free(a);
    free(b);
    free(c);

    return 0;
}

/* References:
 *   - Intel Corporation, "Intel 64 and IA-32 Architectures Optimization
 *     Reference Manual", Chapters 9-15.
 *   - Intel Intrinsics Guide,
 *     https://www.intel.com/content/www/us/en/docs/intrinsics-guide/
 *   - Hennessy, J. L. & Patterson, D. A. "Computer Architecture:
 *     A Quantitative Approach", 6th Edition, Chapter 3 (SIMD).
 *   - Patterson, D. A. & Hennessy, J. L. "Computer Organization and
 *     Design RISC-V Edition", Chapter 3.
 */
