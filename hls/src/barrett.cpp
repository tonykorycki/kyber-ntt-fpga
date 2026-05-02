// hls/src/barrett.cpp — Barrett modular multiplier
//
// Computes (a * b) mod q using Barrett reduction.
// BARRETT_M is barrett_const_t (ap_uint<2*COEF_W+1>) so the constant initializer
// (1 << 2K) / Q doesn't overflow when COEF_W > 15.  The value always fits in prod_t
// (M = floor(2^{2K}/Q) < 2^{2K}), so we cast it to prod_t for the multiply and let
// HLS widen the product expression to double-width internally.

#include "barrett.h"

coef_t barrett_mul(coef_t a, coef_t b) {
#pragma HLS PIPELINE II=1
    prod_t ab = (prod_t)a * (prod_t)b;
    prod_t q_approx = (prod_t)((ab * (prod_t)BARRETT_M) >> (2 * BARRETT_K));
    prod_t r = ab - q_approx * Q;
    if (r >= (prod_t)Q) r -= Q;
    return (coef_t)r;
}
