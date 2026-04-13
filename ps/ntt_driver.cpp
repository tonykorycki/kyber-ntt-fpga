// ps/ntt_driver.cpp — PS-side driver for ntt_top HLS IP
//
// Uses PYNQ / Xilinx runtime MMIO to access AXI-Lite registers and BRAMs.
// Register offsets are taken directly from the HLS synthesis report.

#include "ntt_driver.h"

void ntt_mul(const coef_t* a, const coef_t* b, coef_t* c) {
    // TODO:
    // 1. Write a[0..N-1] to BRAM_A via MMIO
    // 2. Write b[0..N-1] to BRAM_B via MMIO
    // 3. Write 0x1 to CTRL register (AP_START)
    // 4. Poll CTRL register until AP_DONE bit is set
    // 5. Read c[0..N-1] from BRAM_C via MMIO
    (void)a; (void)b; (void)c;
}
