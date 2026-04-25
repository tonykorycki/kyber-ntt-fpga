// hls/pointwise.cpp — Pointwise coefficient multiply
//
// C[i] = A[i] * B[i] mod q  (derivation eq. 17)

#include "pointwise.h"
#include "barrett.h"

void pointwise_mul(const coef_t A[N], const coef_t B[N], coef_t C[N]) {
    for (int i = 0; i < N; i++) {
#pragma HLS PIPELINE II=1
        C[i] = barrett_mul(A[i], B[i]);
    }
}
