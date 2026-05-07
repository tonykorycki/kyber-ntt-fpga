/*
 * ps/ntt_driver.c — PS-side driver for ntt_top HLS IP on PYNQ-Z2 (BRAM interface)
 *
 * Accesses 3 on-chip BRAMs via AXI BRAM Controller and AXI GPIO for control.
 * No CMA required — polynomial data lives in PL BRAM, not PS DDR.
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

#define BRAM_A_PHYS   0x40000000UL
#define BRAM_B_PHYS   0x40002000UL
#define BRAM_C_PHYS   0x40004000UL
#define GPIO_PHYS     0x40010000UL

#define BRAM_MAP_SIZE 0x1000
#define GPIO_MAP_SIZE 0x10000

#define N             256
#define Q             3329

// AXI GPIO register offsets (PG144)
#define GPIO_CH1_DATA  0x00   // output: ap_start on bit 0
#define GPIO_CH1_TRI   0x04   // direction: 0 = output
#define GPIO_CH2_DATA  0x08   // input: ap_done bit 0, ap_idle bit 1
#define GPIO_CH2_TRI   0x0C   // direction: 1 = input

static volatile uint32_t *bram_a;
static volatile uint32_t *bram_b;
static volatile uint32_t *bram_c;
static volatile uint32_t *gpio;

static inline void gwrite(uint32_t off, uint32_t val) { gpio[off >> 2] = val; }
static inline uint32_t gread(uint32_t off)            { return gpio[off >> 2]; }

static long ntt_mul(uint16_t *a, uint16_t *b, uint16_t *c)
{
    struct timespec t0, t1;

    for (int i = 0; i < N; i++) bram_a[i] = (uint32_t)a[i];
    for (int i = 0; i < N; i++) bram_b[i] = (uint32_t)b[i];

    clock_gettime(CLOCK_MONOTONIC, &t0);
    gwrite(GPIO_CH1_DATA, 1);
    gwrite(GPIO_CH1_DATA, 0);
    while (!(gread(GPIO_CH2_DATA) & 0x1))
        ;
    clock_gettime(CLOCK_MONOTONIC, &t1);

    for (int i = 0; i < N; i++) c[i] = (uint16_t)(bram_c[i] & 0xFFFF);

    return (t1.tv_sec - t0.tv_sec) * 1000000000L
         + (t1.tv_nsec - t0.tv_nsec);
}

int main(int argc, char *argv[])
{
    int benchmark = (argc > 1 && strcmp(argv[1], "-t") == 0);
    int batch     = (argc > 1 && strcmp(argv[1], "-b") == 0);
    int raw       = (argc > 1 && strcmp(argv[1], "-r") == 0);

    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) { perror("open /dev/mem"); return 1; }

    bram_a = mmap(NULL, BRAM_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, BRAM_A_PHYS);
    bram_b = mmap(NULL, BRAM_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, BRAM_B_PHYS);
    bram_c = mmap(NULL, BRAM_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, BRAM_C_PHYS);
    gpio   = mmap(NULL, GPIO_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, GPIO_PHYS);

    if (bram_a == MAP_FAILED || bram_b == MAP_FAILED ||
        bram_c == MAP_FAILED || gpio   == MAP_FAILED) {
        perror("mmap"); return 1;
    }

    // Set GPIO direction: Ch1 all outputs, Ch2 all inputs
    gwrite(GPIO_CH1_TRI, 0x0);
    gwrite(GPIO_CH2_TRI, 0x3);

    if (!(gread(GPIO_CH2_DATA) & 0x2))
        fprintf(stderr, "WARNING: HLS IP not idle at startup\n");

    uint16_t a[N], b[N], c[N];

    if (benchmark) {
        for (int i = 0; i < N; i++) a[i] = (uint16_t)(i % Q);
        for (int i = 0; i < N; i++) b[i] = (uint16_t)((i * 7 + 1) % Q);

        long total_ns = 0;
        const int reps = 10;
        for (int r = 0; r < reps; r++)
            total_ns += ntt_mul(a, b, c);
        fprintf(stderr, "avg latency: %ld ns  (%ld us)  over %d reps\n",
                total_ns / reps, total_ns / reps / 1000, reps);
        for (int i = 0; i < N; i++)
            printf("%u\n", (unsigned)(c[i] % Q));

    } else if (raw) {
        while (fread(a, sizeof(uint16_t), N, stdin) == (size_t)N) {
            if (fread(b, sizeof(uint16_t), N, stdin) != (size_t)N) break;
            for (int i = 0; i < N; i++) { a[i] %= Q; b[i] %= Q; }
            ntt_mul(a, b, c);
            for (int i = 0; i < N; i++) c[i] %= Q;
            fwrite(c, sizeof(uint16_t), N, stdout);
            fflush(stdout);
        }

    } else if (batch) {
        unsigned v;
        while (scanf("%u", &v) == 1) {
            a[0] = (uint16_t)(v % Q);
            for (int i = 1; i < N; i++) { scanf("%u", &v); a[i] = (uint16_t)(v % Q); }
            for (int i = 0; i < N; i++) { scanf("%u", &v); b[i] = (uint16_t)(v % Q); }
            ntt_mul(a, b, c);
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

        long ns = ntt_mul(a, b, c);
        fprintf(stderr, "latency: %ld ns\n", ns);
        for (int i = 0; i < N; i++)
            printf("%u\n", (unsigned)(c[i] % Q));
    }

    munmap((void *)bram_a, BRAM_MAP_SIZE);
    munmap((void *)bram_b, BRAM_MAP_SIZE);
    munmap((void *)bram_c, BRAM_MAP_SIZE);
    munmap((void *)gpio,   GPIO_MAP_SIZE);
    close(mem_fd);
    return 0;
}
