// hls/tb/tb_ntt_top.cpp — End-to-end C-sim testbench for ntt_top
//
// Reads golden/test_vectors.txt produced by golden/gen_test_vectors.py.
// Each vector: three lines of N space-separated coefficients (a, b, c=poly_mul(a,b)).
// Calls ntt_top(a, b, c_out) and compares c_out against the golden c.
//
// Path to test_vectors.txt is derived from __FILE__ so it works regardless
// of the Vitis HLS C-sim working directory.

#include "../src/ntt_top.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

static std::string vector_path() {
    std::string f = __FILE__;
    // Strip filename to get the directory (hls/tb/)
    size_t sep = f.find_last_of("/\\");
    std::string dir = (sep != std::string::npos) ? f.substr(0, sep) : ".";
    // hls/tb/ -> ../../ -> repo root -> golden/test_vectors.txt
    return dir + "/../../golden/test_vectors.txt";
}

static bool read_poly(FILE *fp, int poly[N]) {
    char line[8192];
    while (true) {
        if (!fgets(line, sizeof(line), fp)) return false;
        if (line[0] != '#' && line[0] != '\n' && line[0] != '\r') break;
    }
    char *p = line;
    for (int i = 0; i < N; i++) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p || *p == '\n' || *p == '\r') return false;
        poly[i] = (int)strtol(p, &p, 10);
    }
    return true;
}

int main() {
    std::string path = vector_path();
    FILE *fp = fopen(path.c_str(), "r");
    if (!fp) {
        printf("FAIL: cannot open %s\n", path.c_str());
        return 1;
    }

    int failures = 0, vectors = 0;
    int ref_a[N], ref_b[N], ref_c[N];

    while (read_poly(fp, ref_a) && read_poly(fp, ref_b) && read_poly(fp, ref_c)) {
        coef_t a[N], b[N], c[N];
        for (int i = 0; i < N; i++) { a[i] = ref_a[i]; b[i] = ref_b[i]; }

        ntt_top(a, b, c);

        for (int i = 0; i < N; i++) {
            if ((int)c[i] != ref_c[i]) {
                printf("FAIL vec=%d i=%d: got %d expected %d\n",
                       vectors, i, (int)c[i], ref_c[i]);
                failures++;
            }
        }
        vectors++;
    }

    fclose(fp);

    if (vectors == 0) {
        printf("FAIL: no vectors read from %s\n", path.c_str());
        return 1;
    }

    if (failures == 0)
        printf("tb_ntt_top: PASS (%d vectors)\n", vectors);
    else
        printf("tb_ntt_top: FAIL (%d failures across %d vectors)\n", failures, vectors);

    return failures ? 1 : 0;
}
