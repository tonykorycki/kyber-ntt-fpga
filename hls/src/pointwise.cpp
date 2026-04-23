// hls/pointwise.cpp — Pointwise coefficient multiply
//
// C[i] = A[i] * B[i] mod q  (eq. 17 of derivation)
// N independent Barrett reductions — trivially parallelizable.

#include "pointwise.h"
#include "barrett.h"

void pointwise_mul(const coef_t A[N], const coef_t B[N], coef_t C[N]) {
    // TODO: implement
    // #pragma HLS UNROLL
    (void)A; (void)B; (void)C;
}
