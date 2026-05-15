// hls/src/ntt_top.cpp — Top-level HLS function
//
// Sequences the full negacyclic polynomial multiplication pipeline:
//   NTT(a) -> NTT(b) -> mul_ntt(a, b, c) -> INTT(c)
//
// Interface: ap_ctrl_hs for control; ap_memory (ram_1p) for a, b, c.
// Coefficient arrays live in on-chip BRAM. The PS accesses them via AXI BRAM
// Controllers while HLS is idle (ap_idle high), then pulses ap_start to hand off.

#include "ntt_top.h"
#include "ntt_engine.h"
#include "mul_ntt.h"

void ntt_top(coef_t a[N], coef_t b[N], coef_t c[N]) {
#pragma HLS INTERFACE ap_ctrl_hs port=return
#pragma HLS INTERFACE ap_memory port=a storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=b storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=c storage_type=ram_1p

    ntt_engine(a, false);
    ntt_engine(b, false);
    mul_ntt(a, b, c);
    ntt_engine(c, true);
}
