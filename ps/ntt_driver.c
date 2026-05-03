/*
 * ps/ntt_driver.c — PS-side driver for ntt_top HLS IP
 *
 * Uses udmabuf for physically contiguous DMA buffers and /dev/mem for
 * AXI-Lite CTRL register access.
 *
 * Setup (run once on the board if udmabuf0 doesn't exist):
 *   modprobe u-dma-buf udmabuf0=1536
 *
 * Usage:
 *   echo "<256 a coeffs> <256 b coeffs>" | ./ntt_driver
 *   ./ntt_driver -t        # latency benchmark (10 iterations, random inputs)
 *
 * Output:
 *   stdout — 256 c coefficients, one per line
 *   stderr — latency in nanoseconds
 *
 * Build:
 *   gcc -O2 -o ntt_driver ntt_driver.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <sys/mman.h>

// Hardware constants 
#define CTRL_PHYS   0x40000000UL
#define CTRL_SIZE   0x10000

#define N           256
#define Q           3329

// AXI-Lite CTRL register offsets (from HLS synthesis, ntt_top_CTRL_s_axi.v)
#define OFF_CTRL    0x00
#define OFF_A1      0x10    // lower 32b of array a physical address 
#define OFF_A2      0x14    // upper 32b — always 0 on 32-bit PS 
#define OFF_B1      0x1C
#define OFF_B2      0x20
#define OFF_C1      0x28
#define OFF_C2      0x2C

#define AP_START    0x1
#define AP_DONE     0x2
#define AP_IDLE     0x4

// Buffer layout in one udmabuf allocation: [a:512B][b:512B][c:512B]
#define COEF_BYTES  (N * sizeof(uint16_t))   // 512 bytes per array 
#define TOTAL_BUF   (3 * COEF_BYTES)         // 1536 bytes total 

// MMIO helpers 
static volatile uint32_t *ctrl_regs;

static inline void wreg(uint32_t off, uint32_t val)
{
    ctrl_regs[off >> 2] = val;
}

static inline uint32_t rreg(uint32_t off)
{
    return ctrl_regs[off >> 2];
}

// udmabuf cache sync
static void sync_to_device(void)
{
    // Flushes CPU dcache so device sees fresh data in DDR
    FILE *f = fopen("/sys/class/u-dma-buf/udmabuf0/sync_for_device", "w");
    if (f) { fputs("1", f); fclose(f); }
}

static void sync_to_cpu(void)
{
    // Invalidate CPU dcache
    FILE *f = fopen("/sys/class/u-dma-buf/udmabuf0/sync_for_cpu", "w");
    if (f) { fputs("1", f); fclose(f); }
}

// Core NTT multiply 
/*
 * ntt_mul — run the HLS IP for one polynomial multiplication.
 *
 * a, b : input coefficients (uint16_t, values in [0, Q))
 * c    : output coefficients (uint16_t, values in [0, Q))
 * pa, pb, pc : physical addresses of a, b, c in the udmabuf region
 *
 * Returns wall-clock latency of the HLS execution in nanoseconds.
 */
static long ntt_mul(uint16_t *a, uint16_t *b, uint16_t *c,
                    uint32_t pa, uint32_t pb, uint32_t pc)
{
    struct timespec t0, t1;

    // Flush dcache: HP port bypasses ARM cache, HLS reads from DDR
    sync_to_device();

    // Write pointer registers (64-bit split; upper always 0 on 32-bit PS)
    wreg(OFF_A1, pa);  wreg(OFF_A2, 0);
    wreg(OFF_B1, pb);  wreg(OFF_B2, 0);
    wreg(OFF_C1, pc);  wreg(OFF_C2, 0);

    clock_gettime(CLOCK_MONOTONIC, &t0);
    wreg(OFF_CTRL, AP_START);
    while (!(rreg(OFF_CTRL) & AP_DONE))
        ;
    clock_gettime(CLOCK_MONOTONIC, &t1);

    // Invalidate dcache: HLS wrote c to DDR, cache may hold stale zeros
    sync_to_cpu();

    (void)a; (void)b; (void)c;   // a/b written by caller; c read by caller

    return (t1.tv_sec - t0.tv_sec) * 1000000000L
         + (t1.tv_nsec - t0.tv_nsec);
}

// entry point
int main(int argc, char *argv[])
{
    int benchmark = (argc > 1 && strcmp(argv[1], "-t") == 0);

    // Map CTRL registers 
    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) { perror("open /dev/mem"); return 1; }

    ctrl_regs = mmap(NULL, CTRL_SIZE, PROT_READ | PROT_WRITE,
                     MAP_SHARED, mem_fd, CTRL_PHYS);
    if (ctrl_regs == MAP_FAILED) { perror("mmap ctrl"); return 1; }

    // Read physical address from udmabuf sysfs
    uint32_t phys_base;
    {
        FILE *f = fopen("/sys/class/u-dma-buf/udmabuf0/phys_addr", "r");
        if (!f) {
            fprintf(stderr,
                "udmabuf0 not found. Run:\n"
                "  sudo modprobe u-dma-buf udmabuf0=%u\n", (unsigned)TOTAL_BUF);
            return 1;
        }
        if (fscanf(f, "%x", &phys_base) != 1) {
            fclose(f); fprintf(stderr, "failed to read phys_addr\n"); return 1;
        }
        fclose(f);
    }

    // mmap udmabuf virtual address
    int udma_fd = open("/dev/udmabuf0", O_RDWR | O_SYNC);
    if (udma_fd < 0) { perror("open /dev/udmabuf0"); return 1; }

    uint8_t *virt = mmap(NULL, TOTAL_BUF, PROT_READ | PROT_WRITE,
                         MAP_SHARED, udma_fd, 0);
    if (virt == MAP_FAILED) { perror("mmap udmabuf"); return 1; }

    uint16_t *a = (uint16_t *)(virt + 0 * COEF_BYTES);
    uint16_t *b = (uint16_t *)(virt + 1 * COEF_BYTES);
    uint16_t *c = (uint16_t *)(virt + 2 * COEF_BYTES);

    uint32_t pa = phys_base;
    uint32_t pb = phys_base + COEF_BYTES;
    uint32_t pc = phys_base + 2 * COEF_BYTES;

    // Wait for IP idle
    if (!(rreg(OFF_CTRL) & AP_IDLE)) {
        fprintf(stderr, "WARNING: HLS IP not idle at startup\n");
    }

    if (benchmark) {
        // Latency benchmark: 10 runs with fixed input 
        for (int i = 0; i < N; i++) { a[i] = (uint16_t)(i % Q); }
        for (int i = 0; i < N; i++) { b[i] = (uint16_t)((i * 7 + 1) % Q); }

        long total_ns = 0;
        int reps = 10;
        for (int r = 0; r < reps; r++) {
            memset(c, 0, COEF_BYTES);
            total_ns += ntt_mul(a, b, c, pa, pb, pc);
        }
        fprintf(stderr, "avg latency: %ld ns  (%ld us)  over %d reps\n",
                total_ns / reps, total_ns / reps / 1000, reps);

        // Print last result
        for (int i = 0; i < N; i++)
            printf("%u\n", (unsigned)(c[i] % Q));

    } else {
        // Normal mode: read a/b from stdin, print c to stdout
        for (int i = 0; i < N; i++) {
            unsigned v;
            if (scanf("%u", &v) != 1) {
                fprintf(stderr, "error: expected %d values for a, got %d\n", N, i);
                return 1;
            }
            a[i] = (uint16_t)(v % Q);
        }
        for (int i = 0; i < N; i++) {
            unsigned v;
            if (scanf("%u", &v) != 1) {
                fprintf(stderr, "error: expected %d values for b, got %d\n", N, i);
                return 1;
            }
            b[i] = (uint16_t)(v % Q);
        }
        memset(c, 0, COEF_BYTES);

        long ns = ntt_mul(a, b, c, pa, pb, pc);
        fprintf(stderr, "latency: %ld ns\n", ns);

        for (int i = 0; i < N; i++)
            printf("%u\n", (unsigned)(c[i] % Q));
    }

    munmap((void *)ctrl_regs, CTRL_SIZE);
    munmap(virt, TOTAL_BUF);
    close(mem_fd);
    close(udma_fd);
    return 0;
}
