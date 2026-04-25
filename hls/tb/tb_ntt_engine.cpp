// hls/tb/tb_ntt_engine.cpp — HLS C-sim testbench for NTT engine
//
// Test 1: ntt_engine(a, OMEGA_TABLE, false) matches naive O(N^2) direct definition
// Test 2: INTT(NTT(a)) == a  (roundtrip)
//
// Self-contained — no file I/O. Test polynomials generated programmatically.

#include "../src/ntt_engine.h"
#include "../src/twiddle_rom.h"
#include <cstdio>

// O(N^2) NTT from definition eq. (1): A[k] = sum_j a[j] * omega^{j*k} mod Q
// OMEGA_TABLE[k] = omega^k, so omega^{j*k} = OMEGA_TABLE[(j*k) % N]
static void naive_ntt_ref(const int a[N], int A[N]) {
    for (int k = 0; k < N; k++) {
        long long s = 0;
        for (int j = 0; j < N; j++)
            s += (long long)a[j] * (int)OMEGA_TABLE[(j * k) % N];
        A[k] = (int)(s % Q);
    }
}

int main() {
    int failures = 0;
    const int N_TESTS = 8;

    for (int t = 0; t < N_TESTS; t++) {
        // Generate a test polynomial — distinct pattern per test
        int a_int[N];
        coef_t a[N];
        for (int i = 0; i < N; i++) {
            a_int[i] = ((t + 1) * (i + 1) * 3 + t * 7) % Q;
            a[i]     = a_int[i];
        }

        // Test 1: forward NTT vs naive O(N^2) reference
        coef_t A[N];
        int    A_ref[N];
        for (int i = 0; i < N; i++) A[i] = a[i];
        ntt_engine(A, OMEGA_TABLE, false);
        naive_ntt_ref(a_int, A_ref);

        for (int i = 0; i < N; i++) {
            if ((int)A[i] != A_ref[i]) {
                printf("FAIL fwd NTT t=%d i=%d: got %d expected %d\n",
                       t, i, (int)A[i], A_ref[i]);
                failures++;
            }
        }

        // Test 2: roundtrip INTT(NTT(a)) == a
        coef_t rt[N];
        for (int i = 0; i < N; i++) rt[i] = a[i];
        ntt_engine(rt, OMEGA_TABLE,     false);
        ntt_engine(rt, INV_OMEGA_TABLE, true);

        for (int i = 0; i < N; i++) {
            if ((int)rt[i] != a_int[i]) {
                printf("FAIL roundtrip t=%d i=%d: got %d expected %d\n",
                       t, i, (int)rt[i], a_int[i]);
                failures++;
            }
        }
    }

    if (failures == 0)
        printf("tb_ntt_engine: PASS (%d tests x forward+roundtrip)\n", N_TESTS);
    else
        printf("tb_ntt_engine: FAIL (%d failures)\n", failures);

    return failures ? 1 : 0;
}
