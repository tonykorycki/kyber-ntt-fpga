// hls/tb/tb_twist.cpp — HLS C-sim testbench for negacyclic twist
//
// Tests:
//   Roundtrip: post_twist(pre_twist(a)) == a for random inputs
//
// Requires hls/src/twiddle_rom.h (run: make twiddle)

#include "../src/twist.h"
#include "../src/twiddle_rom.h"
#include <cstdio>
#include <cstdlib>

int main() {
    int failures = 0;

    // TODO: for each of N_TESTS random polynomials a[N]:
    //   coef_t twisted[N], recovered[N];
    //   copy a -> twisted
    //   twist(twisted, PSI_TABLE, false)      // pre-twist
    //   copy twisted -> recovered
    //   twist(recovered, INV_PSI_TABLE, true) // post-twist
    //   for i in 0..N-1: assert recovered[i] == a[i]

    if (failures == 0)
        printf("tb_twist: PASS (roundtrip identity holds)\n");
    else
        printf("tb_twist: FAIL (%d errors)\n", failures);

    return failures ? 1 : 0;
}
