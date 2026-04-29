// hls/mul_ntt.h — Base-case quadratic slot multiply declarations
#ifndef MUL_NTT_H
#define MUL_NTT_H

#include "ntt_engine.h"

// Multiply two NTT-domain polynomials: applies BaseCaseMultiply to all N/2 quadratic slots.
// Each slot i: (A[2i] + A[2i+1]*x) * (B[2i] + B[2i+1]*x) mod (x^2 - SLOT_ZETA[i])
void mul_ntt(const coef_t A[N], const coef_t B[N], coef_t C[N]);

#endif // MUL_NTT_H
