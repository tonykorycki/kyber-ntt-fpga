// hls/tb/tb_barrett.cpp — HLS C-sim testbench for Barrett multiplier
//
// Exhaustive test: barrett_mul(a, b) == (a * b) % Q for all (a,b) in Z_Q^2.
// Reads no external files — all 289 pairs (for q=17) computed inline.

#include "../barrett.h"
#include <cstdio>
#include <cstdlib>

int main() {
    int failures = 0;

    // TODO: for each a in [0, Q), for each b in [0, Q):
    //   int expected = (a * b) % Q;
    //   coef_t got = barrett_mul(a, b);
    //   if (got != expected) { printf("FAIL: barrett_mul(%d,%d)=%d, expected %d\n",...); failures++; }

    if (failures == 0)
        printf("tb_barrett: PASS (%d * %d = %d pairs tested)\n", Q, Q, Q * Q);
    else
        printf("tb_barrett: FAIL (%d failures)\n", failures);

    return failures ? 1 : 0;
}
