// hls/twist.cpp — Negacyclic twist
//
// Pre-twist:  ã[i] = a[i] * psi^i    mod q  (eq. 7 of derivation)
// Post-twist: c[i] = c̃[i] * psi^{-i} mod q  (eq. 9 of derivation)
//
// N independent modular multiplications — trivially parallelizable.

#include "twist.h"
#include "barrett.h"

void twist(coef_t a[N], const coef_t psi_table[N], bool inverse) {
    // TODO: implement
    // #pragma HLS UNROLL
    (void)a; (void)psi_table; (void)inverse;
}
