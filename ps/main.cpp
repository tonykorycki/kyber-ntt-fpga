// ps/main.cpp — PYNQ-Z2 demo: NTT-accelerated polynomial multiply
//
// Runs ntt_mul() on the FPGA, measures latency, compares to schoolbook software.

#include "ntt_driver.h"
#include <cstdio>
#include <ctime>

int main() {
    // TODO:
    // 1. Initialize random test polynomials a[], b[]
    // 2. Run hardware ntt_mul(a, b, c_hw) and measure cycles
    // 3. Run software schoolbook_nwc(a, b, c_sw) and measure cycles
    // 4. Assert c_hw == c_sw
    // 5. Print speedup

    printf("NTT accelerator demo — TODO\n");
    return 0;
}
