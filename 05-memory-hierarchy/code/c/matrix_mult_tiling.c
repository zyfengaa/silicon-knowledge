/**
 * matrix_mult_tiling.c — Compare naive vs tiled (blocked) matrix multiply.
 *
 * N=512 double-precision square matrices.  The naive version uses the
 * standard ijk loop order.  Tiled versions try tile sizes 16, 32, and
 * 64.  Each run is timed with clock_gettime, and performance is reported
 * in GFLOPS (billions of floating-point operations per second).
 * Correctness is verified by comparing a few output elements.
 *
 * GFLOPS formula:
 *   GFLOPS = (2 * N^3) / elapsed_seconds / 1e9
 *
 * Compile:
 *   gcc -O2 -o matmul_tiling matrix_mult_tiling.c -lm
 *
 * Run:
 *   ./matmul_tiling
 *
 * Reference:
 *   Hennessy & Patterson, "Computer Architecture: A Quantitative
 *   Approach", 6th Ed., Section 2.5 (Cache Optimizations — Blocking).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define N 512 /* matrix dimension */

/* ===================================================================
 * Helper: elapsed seconds from two timespecs
 * =================================================================== */

static double
elapsed_sec(const struct timespec *start, const struct timespec *end)
{
    return (double)(end->tv_sec - start->tv_sec)
         + (double)(end->tv_nsec - start->tv_nsec) * 1.0e-9;
}

/* ===================================================================
 * init_matrix — fill A, B with deterministic values; zero C
 * =================================================================== */

static void
init_matrix(double *A, double *B, double *C)
{
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            A[i * N + j] = (double)(i + j) * 0.5;
            B[i * N + j] = (double)(i - j) * 0.3;
            C[i * N + j] = 0.0;
        }
    }
}

/* ===================================================================
 * matmul_naive — ijk loop order (worst cache behaviour)
 * =================================================================== */

static void
matmul_naive(const double *A, const double *B, double *C)
{
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            double sum = 0.0;
            for (int k = 0; k < N; k++) {
                sum += A[i * N + k] * B[k * N + j];
            }
            C[i * N + j] = sum;
        }
    }
}

/* ===================================================================
 * matmul_tiled — blocked multiply; tile_size is a compile-time choice
 * =================================================================== */

static void
matmul_tiled(const double *A, const double *B, double *C, int tile_size)
{
    memset(C, 0, (size_t)N * N * sizeof(double));

    for (int i = 0; i < N; i += tile_size) {
        int i_max = (i + tile_size < N) ? i + tile_size : N;
        for (int j = 0; j < N; j += tile_size) {
            int j_max = (j + tile_size < N) ? j + tile_size : N;
            for (int k = 0; k < N; k += tile_size) {
                int k_max = (k + tile_size < N) ? k + tile_size : N;

                for (int ii = i; ii < i_max; ii++) {
                    for (int jj = j; jj < j_max; jj++) {
                        double sum = 0.0;
                        for (int kk = k; kk < k_max; kk++) {
                            sum += A[ii * N + kk] * B[kk * N + jj];
                        }
                        C[ii * N + jj] += sum;
                    }
                }
            }
        }
    }
}

/* ===================================================================
 * check_correct — compare C (result) against reference
 *   returns 1 if all elements match within 1e-6, 0 otherwise
 * =================================================================== */

static int
check_correct(const double *ref, const double *result)
{
    for (int i = 0; i < N * N; i++) {
        if (fabs(ref[i] - result[i]) > 1e-6)
            return 0;
    }
    return 1;
}

/* ===================================================================
 * Main
 * =================================================================== */

int
main(void)
{
    /* Allocate matrices */
    double *A    = (double *)aligned_alloc(64, (size_t)N * N * sizeof(double));
    double *B    = (double *)aligned_alloc(64, (size_t)N * N * sizeof(double));
    double *C    = (double *)aligned_alloc(64, (size_t)N * N * sizeof(double));
    double *Cref = (double *)aligned_alloc(64, (size_t)N * N * sizeof(double));

    if (!A || !B || !C || !Cref) {
        fprintf(stderr, "Memory allocation failed.\n");
        free(A); free(B); free(C); free(Cref);
        return 1;
    }

    init_matrix(A, B, C);

    const double total_ops = 2.0 * N * N * N; /* multiplies + adds */
    struct timespec t1, t2;
    double sec, gflops;

    printf("=== Matrix Multiply (N=%d) ===\n\n", N);

    /* ---- Naive ---- */
    clock_gettime(CLOCK_MONOTONIC, &t1);
    matmul_naive(A, B, Cref);
    clock_gettime(CLOCK_MONOTONIC, &t2);
    sec    = elapsed_sec(&t1, &t2);
    gflops = total_ops / sec / 1.0e9;
    printf("Naive (ijk):  %8.3f s   %8.2f GFLOPS\n", sec, gflops);

    /* ---- Tiled ---- */
    int tile_sizes[] = {16, 32, 64};
    int num_tiles    = sizeof(tile_sizes) / sizeof(tile_sizes[0]);

    for (int t = 0; t < num_tiles; t++) {
        int tile = tile_sizes[t];

        clock_gettime(CLOCK_MONOTONIC, &t1);
        matmul_tiled(A, B, C, tile);
        clock_gettime(CLOCK_MONOTONIC, &t2);

        sec    = elapsed_sec(&t1, &t2);
        gflops = total_ops / sec / 1.0e9;

        int ok = check_correct(Cref, C);

        printf("Tiled (tile=%2d): %8.3f s   %8.2f GFLOPS   [%s]\n",
               tile, sec, gflops, ok ? "OK" : "MISMATCH");
    }

    printf("\nTiling improves cache utilisation by reusing data in\n");
    printf("small blocks that fit into L1/L2 cache, reducing misses.\n");

    free(A);
    free(B);
    free(C);
    free(Cref);
    return 0;
}

/* References:
 *   Hennessy, J. L. & Patterson, D. A. "Computer Architecture:
 *     A Quantitative Approach", 6th Ed., Section 2.5.
 *   Lam, M. et al. "The Cache Performance and Optimizations of
 *     Blocked Algorithms", ASPLOS IV, 1991.
 *   Intel Corp. "Intel 64 and IA-32 Optimization Reference Manual",
 *     Section 7.5 (Loop Blocking).
 */
