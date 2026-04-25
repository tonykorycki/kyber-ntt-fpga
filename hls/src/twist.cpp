// hls/twist.cpp — Negacyclic twist
//
// Pre-twist:  ã[i] = a[i] * ψ^i    mod q  (derivation eq. 7)
// Post-twist: c[i] = c̃[i] * ψ^{-i} mod q  (derivation eq. 9)
//
// The correct table (PSI_TABLE or INV_PSI_TABLE) is selected by the caller.
// The inverse flag is informational only — index is always psi_table[i].

#include "twist.h"
#include "barrett.h"

void twist(coef_t a[N], const coef_t psi_table[N], bool inverse) {
    (void)inverse;
    for (int i = 0; i < N; i++) {
#pragma HLS PIPELINE II=1
        a[i] = barrett_mul(a[i], psi_table[i]);
    }
}
