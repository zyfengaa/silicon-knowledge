/**
 * cache_sim.c — Cache simulator with configurable parameters via CLI.
 *
 * Usage:
 *   ./cache_sim -s <sizeKB> -a <associativity> -l <linesize>
 *
 * Example:
 *   ./cache_sim -s 32 -a 4 -l 64
 *
 * The simulator reads a hardcoded address trace (mix of sequential and
 * random accesses) and reports hit/miss statistics.  LRU replacement
 * is implemented with a per-line counter.
 *
 * Compile:
 *   gcc -O2 -o cache_sim cache_sim.c
 *
 * Reference:
 *   Hennessy & Patterson, "Computer Architecture: A Quantitative
 *   Approach", 6th Ed., Chapter 2 (Memory Hierarchy Design).
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

/* ===================================================================
 * Hardcoded address trace — ~20 addresses, mix of sequential and random
 * =================================================================== */

static uint32_t trace[] = {
    0x00000000, 0x00000040, 0x00000080, 0x000000C0,   /* sequential */
    0x00000100, 0x00000140, 0x00000180, 0x000001C0,
    0x00010000, 0x00010040,                             /* far jump   */
    0x00000000, 0x00000040,                             /* reuse near */
    0xABCD1234, 0xDEADBEEF, 0xCAFEBABE, 0x12345678,   /* random-ish */
    0x00010080, 0x000100C0,
    0x00000080, 0x00000100,
    0xABCD1234,                                         /* reuse      */
    0x00000000,                                         /* early addr */
};
static const int trace_len = sizeof(trace) / sizeof(trace[0]);

/* ===================================================================
 * Cache data structures
 * =================================================================== */

struct cache_line {
    unsigned char  valid;         /* 1 if this line holds a valid block */
    unsigned long  tag;           /* address tag */
    unsigned long  lru_counter;   /* incremented on every access; used
                                     for LRU replacement (smaller = older) */
};

typedef struct {
    int   size_kb;       /* total cache size in KB         */
    int   assoc;         /* associativity (ways per set)   */
    int   line_size;     /* cache-line size in bytes       */

    int   num_sets;      /* number of sets                 */
    int   line_bits;     /* log2(line_size)                */
    int   index_bits;    /* log2(num_sets)                 */

    /* Cache organised as a 2-D array: sets x associativity */
    struct cache_line **cache;

    /* Statistics */
    unsigned long  accesses;
    unsigned long  hits;
    unsigned long  misses;

    /* Global LRU clock — incremented on every access     */
    unsigned long  global_clock;
} cache_t;

/* ===================================================================
 * cache_init — allocate and initialise a cache
 * =================================================================== */

static cache_t *
cache_init(int size_kb, int assoc, int line_size)
{
    cache_t *c = (cache_t *)calloc(1, sizeof(cache_t));
    if (!c) return NULL;

    int cache_bytes = size_kb * 1024;
    int num_lines   = cache_bytes / line_size;
    int num_sets    = num_lines / assoc;

    c->size_kb      = size_kb;
    c->assoc        = assoc;
    c->line_size    = line_size;
    c->num_sets     = num_sets;
    c->line_bits    = 0;
    c->index_bits   = 0;
    c->accesses     = 0;
    c->hits         = 0;
    c->misses       = 0;
    c->global_clock = 0;

    /* Compute log2 of line_size and num_sets */
    {
        int tmp = line_size;
        while (tmp > 1) { tmp >>= 1; c->line_bits++; }
    }
    {
        int tmp = num_sets;
        while (tmp > 1) { tmp >>= 1; c->index_bits++; }
    }

    /* Allocate the 2-D array: num_sets rows, each with assoc columns */
    c->cache = (struct cache_line **)
        calloc(num_sets, sizeof(struct cache_line *));
    if (!c->cache) { free(c); return NULL; }

    for (int i = 0; i < num_sets; i++) {
        c->cache[i] = (struct cache_line *)
            calloc(assoc, sizeof(struct cache_line));
        if (!c->cache[i]) {
            for (int j = 0; j < i; j++) free(c->cache[j]);
            free(c->cache); free(c);
            return NULL;
        }
    }

    return c;
}

/* ===================================================================
 * cache_destroy — free all memory used by the cache
 * =================================================================== */

static void
cache_destroy(cache_t *c)
{
    if (!c) return;
    for (int i = 0; i < c->num_sets; i++)
        free(c->cache[i]);
    free(c->cache);
    free(c);
}

/* ===================================================================
 * cache_access — simulate one memory access
 *   Returns 1 on HIT, 0 on MISS.
 * =================================================================== */

static int
cache_access(cache_t *c, uint32_t addr)
{
    unsigned long offset  = addr & ((1u << c->line_bits) - 1);
    (void)offset; /* unused beyond extraction, kept for clarity */

    unsigned long block   = addr >> c->line_bits;
    unsigned long index   = block & ((1u << c->index_bits) - 1);
    unsigned long tag     = block >> c->index_bits;

    struct cache_line *set = c->cache[index];
    int assoc = c->assoc;

    c->accesses++;

    /* ---- Look for a hit ---- */
    for (int i = 0; i < assoc; i++) {
        if (set[i].valid && set[i].tag == tag) {
            /* HIT — update LRU and stats */
            set[i].lru_counter = c->global_clock++;
            c->hits++;
            return 1;
        }
    }

    /* ---- MISS — find LRU victim ---- */
    int victim       = 0;
    unsigned long min_lru = set[0].lru_counter;

    for (int i = 0; i < assoc; i++) {
        if (!set[i].valid) {
            /* Prefer an empty line */
            victim = i;
            break;
        }
        if (set[i].lru_counter < min_lru) {
            min_lru = set[i].lru_counter;
            victim = i;
        }
    }

    set[victim].valid        = 1;
    set[victim].tag          = tag;
    set[victim].lru_counter  = c->global_clock++;

    c->misses++;
    return 0;
}

/* ===================================================================
 * cache_stats — print accumulated statistics
 * =================================================================== */

static void
cache_stats(const cache_t *c)
{
    double hr = (c->accesses > 0)
                ? (100.0 * c->hits) / c->accesses
                : 0.0;

    printf("=== Cache Statistics ===\n");
    printf("  Config    : %d KB, %d-way, %d B lines\n",
           c->size_kb, c->assoc, c->line_size);
    printf("  Sets      : %d\n", c->num_sets);
    printf("  Accesses  : %lu\n", c->accesses);
    printf("  Hits      : %lu\n", c->hits);
    printf("  Misses    : %lu\n", c->misses);
    printf("  Hit rate  : %.2f %%\n", hr);
}

/* ===================================================================
 * print_usage — show command-line syntax
 * =================================================================== */

static void
print_usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s -s <size_kb> -a <associativity> -l <line_size>\n"
            "  -s   Cache size in KB (e.g. 32)\n"
            "  -a   Associativity (e.g. 1, 2, 4, 8)\n"
            "  -l   Cache-line size in bytes (e.g. 64)\n"
            "Example: %s -s 32 -a 4 -l 64\n",
            prog, prog);
}

/* ===================================================================
 * main — parse CLI args and run the simulation
 * =================================================================== */

int
main(int argc, char **argv)
{
    int size_kb   = 0;
    int assoc     = 0;
    int line_size = 0;
    int opt;

    /* ---- Parse CLI arguments ---- */
    while ((opt = getopt(argc, argv, "s:a:l:h")) != -1) {
        switch (opt) {
        case 's': size_kb   = atoi(optarg); break;
        case 'a': assoc     = atoi(optarg); break;
        case 'l': line_size = atoi(optarg); break;
        case 'h':
        default:
            print_usage(argv[0]);
            return (opt == 'h') ? EXIT_SUCCESS : EXIT_FAILURE;
        }
    }

    if (size_kb <= 0 || assoc <= 0 || line_size <= 0) {
        print_usage(argv[0]);
        return EXIT_FAILURE;
    }

    /* ---- Initialise ---- */
    cache_t *c = cache_init(size_kb, assoc, line_size);
    if (!c) {
        fprintf(stderr, "Error: failed to initialise cache.\n");
        return EXIT_FAILURE;
    }

    /* ---- Run the trace ---- */
    for (int i = 0; i < trace_len; i++)
        cache_access(c, trace[i]);

    /* ---- Print results ---- */
    cache_stats(c);
    cache_destroy(c);

    return EXIT_SUCCESS;
}

/* References:
 *   Hennessy, J. L. & Patterson, D. A. "Computer Architecture:
 *     A Quantitative Approach", 6th Edition, Chapter 2.
 *   Handy, J. "The Cache Memory Book", 2nd Edition, Academic Press, 1998.
 *   Drepper, U. "What Every Programmer Should Know About Memory",
 *     Red Hat, 2007.
 */
