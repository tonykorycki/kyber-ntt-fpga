// hls/tb/tb_pointwise.cpp — HLS C-sim testbench for pointwise multiply
//
// Test: C[i] == (A[i] * B[i]) % Q for all i, multiple random-ish input pairs

#include "../src/pointwise.h"
#include <cstdio>

int main() {
    int failures = 0;
    const int N_TESTS = 8;

    for (int t = 0; t < N_TESTS; t++) {
        coef_t A[N], B[N], C[N];
        for (int i = 0; i < N; i++) {
            A[i] = ((t + 1) * (i + 3) * 7) % Q;
            B[i] = ((t + 3) * (i + 1) * 5) % Q;
        }

        pointwise_mul(A, B, C);

        for (int i = 0; i < N; i++) {
            int expected = ((int)A[i] * (int)B[i]) % Q;
            if ((int)C[i] != expected) {
                printf("FAIL t=%d i=%d: %d * %d = %d, expected %d\n",
                       t, i, (int)A[i], (int)B[i], (int)C[i], expected);
                failures++;
            }
        }
    }

    if (failures == 0)
        printf("tb_pointwise: PASS (%d tests)\n", N_TESTS);
    else
        printf("tb_pointwise: FAIL (%d failures)\n", failures);

    return failures ? 1 : 0;
}
