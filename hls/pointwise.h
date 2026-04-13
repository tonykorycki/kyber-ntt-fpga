// hls/pointwise.h — Pointwise coefficient multiply declarations
#ifndef POINTWISE_H
#define POINTWISE_H

#include "ntt_engine.h"

// Pointwise multiply: C[i] = A[i] * B[i] mod q  (eq. 17 of derivation)
void pointwise_mul(const coef_t A[N], const coef_t B[N], coef_t C[N]);

#endif // POINTWISE_H
