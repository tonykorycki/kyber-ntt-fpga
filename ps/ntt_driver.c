/*
 * ps/ntt_driver.c — PS-side driver for ntt_top HLS IP
 *
 * Uses /dev/xlnk for CMA buffer allocation (Xilinx kernel driver, standard
 * on PYNQ images) and /dev/mem for AXI-Lite CTRL register access.
 *
 * Usage:
 *   ./ntt_driver -t                              # latency benchmark, 10 iterations
 *   echo "<a0..a255> <b0..b255>" | sudo ./ntt_driver   # single multiply
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
#include <sys/ioctl.h>

// xlnk ioctl interface — from linux/xlnk-ioctl.h (Xilinx kernel tree)
#define XLNK_IOCALLOCBUF   _IOWR('X', 2, struct xlnk_args)
#define XLNK_IOCFREEBUF    _IOWR('X', 3, struct xlnk_args)

struct xlnk_args {
    uint32_t  id;
    uint32_t  flags;
    uint32_t  len;
    uint32_t  phyaddr;
    void     *virt;
    uint32_t  padding[3];
};

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

// 512 bytes per array, 1536 total — one xlnk allocation split into [a][b][c]
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
    __builtin___clear_cache((char *)a, (char *)a + COEF_BYTES);
    __builtin___clear_cache((char *)b, (char *)b + COEF_BYTES);

    wreg(OFF_A1, pa);  wreg(OFF_A2, 0);
    wreg(OFF_B1, pb);  wreg(OFF_B2, 0);
    wreg(OFF_C1, pc);  wreg(OFF_C2, 0);

    clock_gettime(CLOCK_MONOTONIC, &t0);
    wreg(OFF_CTRL, AP_START);
    while (!(rreg(OFF_CTRL) & AP_DONE))
        ;
    clock_gettime(CLOCK_MONOTONIC, &t1);

    __builtin___clear_cache((char *)c, (char *)c + COEF_BYTES);

    return (t1.tv_sec - t0.tv_sec) * 1000000000L
         + (t1.tv_nsec - t0.tv_nsec);
}

int main(int argc, char *argv[])
{
    int benchmark = (argc > 1 && strcmp(argv[1], "-t") == 0);

    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) { perror("open /dev/mem"); return 1; }

    ctrl_regs = mmap(NULL, CTRL_SIZE, PROT_READ | PROT_WRITE,
                     MAP_SHARED, mem_fd, CTRL_PHYS);
    if (ctrl_regs == MAP_FAILED) { perror("mmap ctrl"); return 1; }

    int xlnk_fd = open("/dev/xlnk", O_RDWR);
    if (xlnk_fd < 0) { perror("open /dev/xlnk"); return 1; }

    struct xlnk_args xargs = { .len = TOTAL_BUF, .flags = 0 };
    if (ioctl(xlnk_fd, XLNK_IOCALLOCBUF, &xargs) < 0) {
        perror("xlnk alloc"); return 1;
    }

    void *virt = mmap(NULL, TOTAL_BUF, PROT_READ | PROT_WRITE,
                      MAP_SHARED, xlnk_fd, xargs.phyaddr);
    if (virt == MAP_FAILED) { perror("mmap xlnk buf"); return 1; }

    uint16_t *a = (uint16_t *)((uint8_t *)virt + 0 * COEF_BYTES);
    uint16_t *b = (uint16_t *)((uint8_t *)virt + 1 * COEF_BYTES);
    uint16_t *c = (uint16_t *)((uint8_t *)virt + 2 * COEF_BYTES);

    uint32_t pa = xargs.phyaddr;
    uint32_t pb = xargs.phyaddr + COEF_BYTES;
    uint32_t pc = xargs.phyaddr + 2 * COEF_BYTES;

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

    ioctl(xlnk_fd, XLNK_IOCFREEBUF, &xargs);
    munmap(virt, TOTAL_BUF);
    munmap((void *)ctrl_regs, CTRL_SIZE);
    close(xlnk_fd);
    close(mem_fd);
    return 0;
}
