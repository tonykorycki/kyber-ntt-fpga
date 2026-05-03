/*
 * ps/ntt_driver.c — PS-side driver for ntt_top HLS IP on PYNQ-Z2
 *
 * Uses libcma.so (Xilinx CMA allocator) for physically contiguous buffers
 * and /dev/mem for AXI-Lite CTRL register access.
 *
 * Usage:
 *   ./ntt_driver -t                                    # latency benchmark, 10 iterations
 *   echo "<a0..a255> <b0..b255>" | sudo ./ntt_driver   # single multiply
 *
 * Output:
 *   stdout — 256 c coefficients, one per line
 *   stderr — latency in nanoseconds
 *
 * Build:
 *   gcc -O2 -o ntt_driver ntt_driver.c -lcma
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <sys/mman.h>
#include <libxlnk_cma.h>

#define CTRL_PHYS   0x40000000UL
#define CTRL_SIZE   0x10000

#define N           256
#define Q           3329

#define OFF_CTRL    0x00
#define OFF_A1      0x10
#define OFF_A2      0x14
#define OFF_B1      0x1C
#define OFF_B2      0x20
#define OFF_C1      0x28
#define OFF_C2      0x2C

#define AP_START    0x1
#define AP_DONE     0x2
#define AP_IDLE     0x4

// 512 bytes per array, 1536 total — one CMA allocation split into [a][b][c]
#define COEF_BYTES  (N * sizeof(uint16_t))
#define TOTAL_BUF   (3 * COEF_BYTES)

static volatile uint32_t *ctrl_regs;

static inline void wreg(uint32_t off, uint32_t val) { ctrl_regs[off >> 2] = val; }
static inline uint32_t rreg(uint32_t off)           { return ctrl_regs[off >> 2]; }

static long ntt_mul(uint16_t *a, uint16_t *b, uint16_t *c,
                    uint32_t pa, uint32_t pb, uint32_t pc)
{
    struct timespec t0, t1;

    // HP port bypasses ARM L1/L2 — flush a/b before HLS reads, invalidate c after
    cma_flush_cache(a, pa, COEF_BYTES);
    cma_flush_cache(b, pb, COEF_BYTES);

    wreg(OFF_A1, pa);  wreg(OFF_A2, 0);
    wreg(OFF_B1, pb);  wreg(OFF_B2, 0);
    wreg(OFF_C1, pc);  wreg(OFF_C2, 0);

    clock_gettime(CLOCK_MONOTONIC, &t0);
    wreg(OFF_CTRL, AP_START);
    while (!(rreg(OFF_CTRL) & AP_DONE))
        ;
    clock_gettime(CLOCK_MONOTONIC, &t1);

    cma_invalidate_cache(c, pc, COEF_BYTES);

    return (t1.tv_sec - t0.tv_sec) * 1000000000L
         + (t1.tv_nsec - t0.tv_nsec);
}

int main(int argc, char *argv[])
{
    int benchmark = (argc > 1 && strcmp(argv[1], "-t") == 0);
    int batch     = (argc > 1 && strcmp(argv[1], "-b") == 0);

    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) { perror("open /dev/mem"); return 1; }

    ctrl_regs = mmap(NULL, CTRL_SIZE, PROT_READ | PROT_WRITE,
                     MAP_SHARED, mem_fd, CTRL_PHYS);
    if (ctrl_regs == MAP_FAILED) { perror("mmap ctrl"); return 1; }

    // cma_alloc returns a virtual address; cma_get_phy_addr gives the physical address
    void *buf = cma_alloc(TOTAL_BUF, 0);
    if (!buf) { fprintf(stderr, "cma_alloc failed\n"); return 1; }

    uint16_t *a = (uint16_t *)((uint8_t *)buf + 0 * COEF_BYTES);
    uint16_t *b = (uint16_t *)((uint8_t *)buf + 1 * COEF_BYTES);
    uint16_t *c = (uint16_t *)((uint8_t *)buf + 2 * COEF_BYTES);

    uint32_t pa = cma_get_phy_addr(a);
    uint32_t pb = cma_get_phy_addr(b);
    uint32_t pc = cma_get_phy_addr(c);

    if (!(rreg(OFF_CTRL) & AP_IDLE))
        fprintf(stderr, "WARNING: HLS IP not idle at startup\n");

    if (benchmark) {
        for (int i = 0; i < N; i++) a[i] = (uint16_t)(i % Q);
        for (int i = 0; i < N; i++) b[i] = (uint16_t)((i * 7 + 1) % Q);

        long total_ns = 0;
        const int reps = 10;
        for (int r = 0; r < reps; r++) {
            memset(c, 0, COEF_BYTES);
            total_ns += ntt_mul(a, b, c, pa, pb, pc);
        }
        fprintf(stderr, "avg latency: %ld ns  (%ld us)  over %d reps\n",
                total_ns / reps, total_ns / reps / 1000, reps);
        for (int i = 0; i < N; i++)
            printf("%u\n", (unsigned)(c[i] % Q));

    } else if (batch) {
        unsigned v;
        while (scanf("%u", &v) == 1) {
            a[0] = (uint16_t)(v % Q);
            for (int i = 1; i < N; i++) { scanf("%u", &v); a[i] = (uint16_t)(v % Q); }
            for (int i = 0; i < N; i++) { scanf("%u", &v); b[i] = (uint16_t)(v % Q); }
            memset(c, 0, COEF_BYTES);
            ntt_mul(a, b, c, pa, pb, pc);
            for (int i = 0; i < N; i++)
                printf("%u ", (unsigned)(c[i] % Q));
            printf("\n");
            fflush(stdout);
        }

    } else {
        for (int i = 0; i < N; i++) {
            unsigned v;
            if (scanf("%u", &v) != 1) {
                fprintf(stderr, "error reading a[%d]\n", i); return 1;
            }
            a[i] = (uint16_t)(v % Q);
        }
        for (int i = 0; i < N; i++) {
            unsigned v;
            if (scanf("%u", &v) != 1) {
                fprintf(stderr, "error reading b[%d]\n", i); return 1;
            }
            b[i] = (uint16_t)(v % Q);
        }
        memset(c, 0, COEF_BYTES);

        long ns = ntt_mul(a, b, c, pa, pb, pc);
        fprintf(stderr, "latency: %ld ns\n", ns);
        for (int i = 0; i < N; i++)
            printf("%u\n", (unsigned)(c[i] % Q));
    }

    cma_free(buf);
    munmap((void *)ctrl_regs, CTRL_SIZE);
    close(mem_fd);
    return 0;
}
