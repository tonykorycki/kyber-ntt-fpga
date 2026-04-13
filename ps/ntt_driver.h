// ps/ntt_driver.h — PS-side driver for ntt_top HLS IP
//
// Exposes a single function: ntt_mul(a, b, c)
// Writes a and b to BRAM, pulses AP_START, polls AP_DONE, reads c from BRAM.
// AXI-Lite register offsets come from the HLS synthesis report — never hardcoded here.
#ifndef NTT_DRIVER_H
#define NTT_DRIVER_H

#include <cstdint>

// Coefficient type: 12-bit for full Kyber, 5-bit for dev params
typedef uint16_t coef_t;

// Full Kyber parameters
static constexpr int N = 256;

// Perform c = a * b in Z_q[x]/(x^n+1) using the FPGA NTT IP.
// a, b, c are arrays of N coefficients.
void ntt_mul(const coef_t* a, const coef_t* b, coef_t* c);

#endif // NTT_DRIVER_H
