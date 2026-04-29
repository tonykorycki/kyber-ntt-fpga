// hls/tb/tb_ntt_engine.cpp — HLS C-sim testbench for ntt_engine
//
// Test 1 (roundtrip):  INTT(NTT(a)) == a  for 8 distinct polynomials
// Test 2 (poly mul):   NTT(a) -> base-case pointwise -> INTT  matches schoolbook negacyclic

#include "../src/ntt_engine.h"
#include "../src/twiddle_rom.h"
#include <cstdio>
#include <cstring>

// Negacyclic schoolbook reference: c = a*b mod (x^N + 1) in Z_Q[x]
static void schoolbook_ref(const int a[N], const int b[N], int c[N]) {
    int tmp[2 * N];
    memset(tmp, 0, sizeof(tmp));
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            tmp[i + j] = (tmp[i + j] + a[i] * b[j]) % Q;
    for (int i = 0; i < N; i++)
        c[i] = (tmp[i] - tmp[i + N] + Q) % Q;
}

// Base-case pointwise multiply using SLOT_ZETA (5 muls per quadratic slot)
static void base_case_pointwise(const coef_t A[N], const coef_t B[N], coef_t C[N]) {
    for (int i = 0; i < N/2; i++) {
        long long a0 = (int)A[2*i],   a1 = (int)A[2*i+1];
        long long b0 = (int)B[2*i],   b1 = (int)B[2*i+1];
        long long g  = (int)SLOT_ZETA[i];
        C[2*i]   = (coef_t)((a0*b0 + a1*b1*g) % Q);
        C[2*i+1] = (coef_t)((a0*b1 + a1*b0)   % Q);
    }
}

int main() {
    int failures = 0;

    // -----------------------------------------------------------------------
    // Test 1 — roundtrip: INTT(NTT(a)) == a
    // -----------------------------------------------------------------------
    const int N_RT = 8;
    for (int t = 0; t < N_RT; t++) {
        int     a_int[N];
        coef_t  a[N];
        for (int i = 0; i < N; i++) {
            a_int[i] = ((t + 1) * (i + 1) * 3 + t * 7) % Q;
            a[i]     = a_int[i];
        }

        ntt_engine(a, false);
        ntt_engine(a, true);

        for (int i = 0; i < N; i++) {
            if ((int)a[i] != a_int[i]) {
                printf("FAIL roundtrip t=%d i=%d: got %d expected %d\n",
                       t, i, (int)a[i], a_int[i]);
                failures++;
            }
        }
    }
    if (failures == 0)
        printf("Test 1 (roundtrip): PASS (%d polynomials)\n", N_RT);

    // -----------------------------------------------------------------------
    // Test 2 — poly mul: NTT(a) -> base-case pointwise -> INTT == schoolbook
    // -----------------------------------------------------------------------
    const int N_MUL = 4;
    for (int t = 0; t < N_MUL; t++) {
        int    a_int[N], b_int[N], c_ref[N];
        coef_t a[N], b[N], c[N];

        for (int i = 0; i < N; i++) {
            a_int[i] = ((t * 5 + i * 3 + 1)) % Q;
            b_int[i] = ((t * 7 + i * 11 + 2)) % Q;
            a[i] = a_int[i];
            b[i] = b_int[i];
        }

        schoolbook_ref(a_int, b_int, c_ref);

        ntt_engine(a, false);
        ntt_engine(b, false);
        base_case_pointwise(a, b, c);
        ntt_engine(c, true);

        for (int i = 0; i < N; i++) {
            if ((int)c[i] != c_ref[i]) {
                printf("FAIL poly_mul t=%d i=%d: got %d expected %d\n",
                       t, i, (int)c[i], c_ref[i]);
                failures++;
            }
        }
    }
    if (failures == 0)
        printf("Test 2 (poly mul):  PASS (%d pairs vs schoolbook)\n", N_MUL);

    if (failures == 0)
        printf("tb_ntt_engine: PASS\n");
    else
        printf("tb_ntt_engine: FAIL (%d failures)\n", failures);

    return failures ? 1 : 0;
}
