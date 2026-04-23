// hls/tb/tb_pointwise.cpp — HLS C-sim testbench for pointwise multiply
//
// Tests:
//   pointwise_mul(A, B, C): C[i] == (A[i] * B[i]) % Q for all i

#include "../src/pointwise.h"
#include <cstdio>
#include <cstdlib>

int main() {
    int failures = 0;

    // TODO: for each of N_TESTS random pairs (A[N], B[N]) in Z_Q^N:
    //   coef_t C[N];
    //   pointwise_mul(A, B, C)
    //   for i in 0..N-1: assert C[i] == (A[i] * B[i]) % Q

    if (failures == 0)
        printf("tb_pointwise: PASS\n");
    else
        printf("tb_pointwise: FAIL (%d errors)\n", failures);

    return failures ? 1 : 0;
}
