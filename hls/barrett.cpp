// hls/barrett.cpp — Barrett modular multiplier
//
// Computes (a * b) mod q using Barrett reduction.
// Factored out for independent unit testing.

#include "barrett.h"


coef_t barrett_mul(coef_t a, coef_t b) {
    #pragma HLS INLINE
    prod_t ab      = (prod_t)a * (prod_t)b;
    prod_t q_approx = (ab * BARRETT_M) >> (2 * BARRETT_K);
    prod_t r       = ab - q_approx * Q;
    if (r >= Q) r -= Q;
    return (coef_t)r;
}