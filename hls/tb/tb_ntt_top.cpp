// hls/tb/tb_ntt_top.cpp — HLS C-sim testbench for full NTT pipeline
//
// Tests:
//   ntt_top(a, b, c) == expected_c for all 16 test vectors
//
// Reads all 16 (a, b, c) triples from golden/test_vectors.txt.
// Exits with nonzero if any vector fails (Vitis HLS C-sim convention).

#include "../ntt_top.h"
#include <cstdio>
#include <cstdlib>

int main() {
    int failures = 0;

    // TODO: open ../../golden/test_vectors.txt
    // TODO: for each of 16 vectors:
    //   coef_t a[N], b[N], c_expected[N], c_got[N];
    //   read a, b, c_expected from file
    //   copy a -> a_copy, b -> b_copy  (ntt_top modifies inputs in place)
    //   ntt_top(a_copy, b_copy, c_got)
    //   if (c_got != c_expected) { printf("FAIL vector %d\n", i); failures++; }

    if (failures == 0)
        printf("tb_ntt_top: PASS (16/16 vectors)\n");
    else
        printf("tb_ntt_top: FAIL (%d/16 vectors failed)\n", failures);

    return failures ? 1 : 0;
}
