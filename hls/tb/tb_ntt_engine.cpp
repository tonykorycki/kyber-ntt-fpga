// hls/tb/tb_ntt_engine.cpp — HLS C-sim testbench for NTT engine
//
// Tests:
//   1. Forward NTT: ntt_engine(a, OMEGA_TABLE, false) matches expected from golden vectors
//   2. Roundtrip:   ntt_engine then inverse ntt_engine = identity
//
// Reads test vectors from golden/test_vectors.txt (relative path for C-sim).

#include "../src/ntt_engine.h"
#include <cstdio>
#include <cstdlib>

int main() {
    // TODO: load test vectors from ../../golden/test_vectors.txt
    // TODO: for each vector:
    //   - run ntt_engine(a_copy, OMEGA_TABLE, false)
    //   - run ntt_engine(result, INV_OMEGA_TABLE, true) (roundtrip)
    //   - assert roundtrip == original a
    printf("tb_ntt_engine: TODO\n");
    return 0;
}
