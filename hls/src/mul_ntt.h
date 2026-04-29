// hls/mul_ntt.h — Base-case quadratic slot multiply declarations
#ifndef MUL_NTT_H
#define MUL_NTT_H

#include "ntt_engine.h"

// Base-case quadratic slot multiply: C[i] = A[i] * B[i] mod q  (eq. 17 of derivation)
void mul_ntt(const coef_t A[N], const coef_t B[N], coef_t C[N]);

#endif // MUL_NTT_H
