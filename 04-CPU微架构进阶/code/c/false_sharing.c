/**
 * false_sharing.c — Demonstrate False Sharing on multi-core CPUs.
 *
 * Two threads each increment a counter 10 million times.
 *
 * Version 1 (false sharing):
 *   counters are adjacent in memory — both fall on the same cache line.
 *
 * Version 2 (no false sharing):
 *   counters are separated by 64 bytes of padding so each sits
 *   on its own cache line.
 *
 * The difference in wall-clock time demonstrates the cost of
 * cache-line bouncing induced by false sharing.
 *
 * Compile:
 *   gcc -O2 -o false_sharing false_sharing.c -lpthread
 *
 * Note: -lpthread must come after the source/object that uses it.
 *
 * Note: this assumes a 64-byte cache line (typical on x86).  Apple
 * Silicon uses 128-byte cache lines, so on those machines the "padded"
 * layout can still false-share unless the padding is 128 bytes.
 *
 * Run:
 *   ./false_sharing
 */

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <stdint.h>
#include <stddef.h>

#define ITERATIONS  (10 * 1000 * 1000)   /* 10 million per thread */

/* ---- Shared counters (will be allocated dynamically) ---- */

struct __attribute__((aligned(64))) shared_false {
    volatile unsigned long long counter0;
    volatile unsigned long long counter1;
    /* Both counters sit on the same cache line. */
};
_Static_assert(offsetof(struct shared_false, counter1) < 64,
               "counters should share a cache line");

struct __attribute__((aligned(64))) shared_padded {
    volatile unsigned long long counter0;
    char pad0[64 - sizeof(unsigned long long)];   /* fill rest of line */
    volatile unsigned long long counter1;
    char pad1[64 - sizeof(unsigned long long)];
};
_Static_assert(offsetof(struct shared_padded, counter1) == 64,
               "counter1 should start on the next cache line");
_Static_assert(sizeof(struct shared_padded) % 64 == 0,
               "padded struct should span whole cache lines");

/* ---- Thread routines ---- */

static void *
thread_inc_false(void *arg)
{
    struct shared_false *s = (struct shared_false *)arg;
    for (int i = 0; i < ITERATIONS; i++) {
        s->counter0++;
    }
    return NULL;
}

static void *
thread_inc_false2(void *arg)
{
    struct shared_false *s = (struct shared_false *)arg;
    for (int i = 0; i < ITERATIONS; i++) {
        s->counter1++;
    }
    return NULL;
}

static void *
thread_inc_padded(void *arg)
{
    struct shared_padded *s = (struct shared_padded *)arg;
    for (int i = 0; i < ITERATIONS; i++) {
        s->counter0++;
    }
    return NULL;
}

static void *
thread_inc_padded2(void *arg)
{
    struct shared_padded *s = (struct shared_padded *)arg;
    for (int i = 0; i < ITERATIONS; i++) {
        s->counter1++;
    }
    return NULL;
}

/* ---- Timer utility ---- */

static double
time_diff_ns(const struct timespec *start, const struct timespec *end)
{
    return (double)(end->tv_sec - start->tv_sec) * 1.0e9
         + (double)(end->tv_nsec - start->tv_nsec);
}

/* ---- Main ---- */

int
main(void)
{
    pthread_t t0, t1;
    struct timespec t1m, t2m;
    double elapsed_false, elapsed_nofalse;

    /*
     * ---- Version 1: False Sharing ----
     * Both counters are adjacent in a small struct.
     */
    struct shared_false *sf = (struct shared_false *)
        aligned_alloc(64, 64);   /* C11: size must be a multiple of alignment */
    if (!sf) { perror("aligned_alloc"); return EXIT_FAILURE; }
    sf->counter0 = 0;
    sf->counter1 = 0;

    clock_gettime(CLOCK_MONOTONIC, &t1m);
    if (pthread_create(&t0, NULL, thread_inc_false, sf) != 0 ||
        pthread_create(&t1, NULL, thread_inc_false2, sf) != 0) {
        perror("pthread_create");
        free(sf);
        return EXIT_FAILURE;
    }
    if (pthread_join(t0, NULL) != 0 || pthread_join(t1, NULL) != 0) {
        perror("pthread_join");
        free(sf);
        return EXIT_FAILURE;
    }
    clock_gettime(CLOCK_MONOTONIC, &t2m);
    elapsed_false = time_diff_ns(&t1m, &t2m);

    printf("=== False Sharing ===\n");
    printf("counter0 = %llu, counter1 = %llu\n",
           sf->counter0, sf->counter1);
    printf("Time    : %.2f ms\n", elapsed_false / 1.0e6);

    free(sf);

    /*
     * ---- Version 2: No False Sharing ----
     * counters are separated by padding to occupy different cache lines.
     */
    struct shared_padded *sp = (struct shared_padded *)
        aligned_alloc(64, sizeof(struct shared_padded));
    if (!sp) { perror("aligned_alloc"); return EXIT_FAILURE; }
    sp->counter0 = 0;
    sp->counter1 = 0;

    clock_gettime(CLOCK_MONOTONIC, &t1m);
    if (pthread_create(&t0, NULL, thread_inc_padded, sp) != 0 ||
        pthread_create(&t1, NULL, thread_inc_padded2, sp) != 0) {
        perror("pthread_create");
        free(sp);
        return EXIT_FAILURE;
    }
    if (pthread_join(t0, NULL) != 0 || pthread_join(t1, NULL) != 0) {
        perror("pthread_join");
        free(sp);
        return EXIT_FAILURE;
    }
    clock_gettime(CLOCK_MONOTONIC, &t2m);
    elapsed_nofalse = time_diff_ns(&t1m, &t2m);

    printf("\n=== No False Sharing (padded) ===\n");
    printf("counter0 = %llu, counter1 = %llu\n",
           sp->counter0, sp->counter1);
    printf("Time    : %.2f ms\n", elapsed_nofalse / 1.0e6);

    free(sp);

    /* ---- Comparison ---- */
    printf("\n=== Comparison ===\n");
    printf("False sharing     : %8.2f ms\n", elapsed_false / 1.0e6);
    printf("Padded (no false) : %8.2f ms\n", elapsed_nofalse / 1.0e6);
    printf("Slowdown factor   : %.2f x\n",
           elapsed_false / elapsed_nofalse);

    return 0;
}

/* References:
 *   - Hennessy, J. L. & Patterson, D. A. "Computer Architecture:
 *     A Quantitative Approach", 6th Edition, Chapter 5 (Multiprocessors).
 *   - Bolosky, W. J. & Scott, M. L. "False Sharing and Its Effect on
 *     Shared Memory Performance." USENIX SEDMS, 1993.
 *   - Papamarcos, M. S. & Patel, J. H. "A Low-Overhead Coherence
 *     Solution for Multiprocessors with Private Cache Memories."
 *     ISCA, 1984.
 */
