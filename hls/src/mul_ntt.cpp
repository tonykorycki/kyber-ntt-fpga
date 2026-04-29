// hls/src/mul_ntt.cpp — Base-case quadratic slot multiply
//
// Each NTT output pair (A[2i], A[2i+1]) lives in Z_q[x]/(x^2 - gamma_i)
// where gamma_i = SLOT_ZETA[i] = zeta^{2*brv7(i)+1}.
// Product formula (5 mults per slot):
//   C[2i]   = a0*b0 + a1*b1*gamma
//   C[2i+1] = a0*b1 + a1*b0

#include "mul_ntt.h"
#include "twiddle_rom.h"
#include "barrett.h"

typedef ap_uint<COEF_W + 1> coef_wide_t;

static coef_t mod_add(coef_t a, coef_t b) {
#pragma HLS INLINE
    coef_wide_t s = (coef_wide_t)a + b;
    return s >= Q ? coef_t(s - Q) : coef_t(s);
}

void mul_ntt(const coef_t A[N], const coef_t B[N], coef_t C[N]) {
    for (int i = 0; i < N/2; i++) {
#pragma HLS PIPELINE II=1
        coef_t a0    = A[2*i],   a1 = A[2*i+1];
        coef_t b0    = B[2*i],   b1 = B[2*i+1];
        coef_t gamma = SLOT_ZETA[i];

        coef_t a1b1  = barrett_mul(a1, b1);
        C[2*i]   = mod_add(barrett_mul(a0, b0), barrett_mul(a1b1, gamma));
        C[2*i+1] = mod_add(barrett_mul(a0, b1), barrett_mul(a1,   b0));
    }
}
