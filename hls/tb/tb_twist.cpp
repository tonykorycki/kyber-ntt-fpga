// hls/tb/tb_twist.cpp — HLS C-sim testbench for negacyclic twist
//
// Test 1: post_twist(pre_twist(a)) == a  (roundtrip = identity)
// Test 2: pre_twist output matches manual a[i] * PSI_TABLE[i] % Q

#include "../src/twist.h"
#include "../src/twiddle_rom.h"
#include <cstdio>

int main() {
    int failures = 0;
    const int N_TESTS = 8;

    for (int t = 0; t < N_TESTS; t++) {
        int a_int[N];
        coef_t a[N];
        for (int i = 0; i < N; i++) {
            a_int[i] = ((t + 2) * (i + 1) * 5 + t * 3) % Q;
            a[i]     = a_int[i];
        }

        // Test 1: roundtrip
        coef_t twisted[N], recovered[N];
        for (int i = 0; i < N; i++) twisted[i] = a[i];
        twist(twisted, PSI_TABLE,     false);   // pre-twist
        for (int i = 0; i < N; i++) recovered[i] = twisted[i];
        twist(recovered, INV_PSI_TABLE, true);  // post-twist

        for (int i = 0; i < N; i++) {
            if ((int)recovered[i] != a_int[i]) {
                printf("FAIL roundtrip t=%d i=%d: got %d expected %d\n",
                       t, i, (int)recovered[i], a_int[i]);
                failures++;
            }
        }

        // Test 2: pre-twist values match manual multiply
        for (int i = 0; i < N; i++) {
            int expected = ((long long)a_int[i] * (int)PSI_TABLE[i]) % Q;
            if ((int)twisted[i] != expected) {
                printf("FAIL pre-twist t=%d i=%d: got %d expected %d\n",
                       t, i, (int)twisted[i], expected);
                failures++;
            }
        }
    }

    if (failures == 0)
        printf("tb_twist: PASS (%d tests x roundtrip+values)\n", N_TESTS);
    else
        printf("tb_twist: FAIL (%d failures)\n", failures);

    return failures ? 1 : 0;
}
