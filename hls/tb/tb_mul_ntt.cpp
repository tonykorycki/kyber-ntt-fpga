// hls/tb/tb_mul_ntt.cpp — HLS C-sim testbench for base-case mul_ntt multiply
//
// Verifies the per-slot formula in Z_q[x]/(x^2 - gamma_i):
//   C[2i]   = a0*b0 + a1*b1*gamma_i  (mod Q)
//   C[2i+1] = a0*b1 + a1*b0          (mod Q)
//
// Reference is computed with plain long long arithmetic (no Barrett).

#include "../src/mul_ntt.h"
#include "../src/twiddle_rom.h"
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

        mul_ntt(A, B, C);

        for (int i = 0; i < N/2; i++) {
            long long a0 = (int)A[2*i],   a1 = (int)A[2*i+1];
            long long b0 = (int)B[2*i],   b1 = (int)B[2*i+1];
            long long g  = (int)SLOT_ZETA[i];

            int exp_c0 = (int)((a0*b0 + a1*b1*g) % Q);
            int exp_c1 = (int)((a0*b1 + a1*b0)   % Q);

            if ((int)C[2*i] != exp_c0) {
                printf("FAIL t=%d i=%d: C[%d]=%d expected %d\n",
                       t, i, 2*i, (int)C[2*i], exp_c0);
                failures++;
            }
            if ((int)C[2*i+1] != exp_c1) {
                printf("FAIL t=%d i=%d: C[%d]=%d expected %d\n",
                       t, i, 2*i+1, (int)C[2*i+1], exp_c1);
                failures++;
            }
        }
    }

    if (failures == 0)
        printf("tb_mul_ntt: PASS (%d tests)\n", N_TESTS);
    else
        printf("tb_mul_ntt: FAIL (%d failures)\n", failures);

    return failures ? 1 : 0;
}
