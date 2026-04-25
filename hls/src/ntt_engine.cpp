// hls/ntt_engine.cpp — NTT butterfly engine
//
// Forward NTT : Cooley-Tukey  DIT — bit-reversal before butterflies       (derivation §4–5)
// Inverse NTT : Gentleman-Sande DIF — butterflies then bit-reversal + scale (derivation §6)
//
// Architecture is input-agnostic: same pipelined butterfly structure for any (N, Q).
// Dev params (n=4) produce a faithful miniature of the full Kyber (n=256) netlist.
// Pragma strategy: cyclic partition + PIPELINE II=1 on inner loop for all N.

#include "ntt_engine.h"
#include "barrett.h"
#include "twiddle_rom.h"

typedef ap_uint<COEF_W + 1> coef_wide_t;   // one extra bit: holds sums up to 2*(Q-1)

static coef_t mod_add(coef_t a, coef_t b) {
#pragma HLS INLINE
    coef_wide_t s = (coef_wide_t)a + b;
    return s >= Q ? coef_t(s - Q) : coef_t(s);
}

static coef_t mod_sub(coef_t a, coef_t b) {
#pragma HLS INLINE
    coef_wide_t s = (coef_wide_t)a + Q - b;    // a + Q - b avoids going negative
    return s >= Q ? coef_t(s - Q) : coef_t(s);
}
static void bit_reverse_permute(coef_t a[N]) {
#pragma HLS INLINE
    for (int i = 0; i < N; i++) {
#pragma HLS UNROLL
        ap_uint<LOG2_N> rev = 0;
        ap_uint<LOG2_N> idx = i;
        for (int b = 0; b < LOG2_N; b++) {
#pragma HLS UNROLL
            rev = (rev << 1) | (idx & 1);
            idx >>= 1;
        }
        if (rev > (ap_uint<LOG2_N>)i) { // guard prevents each pair swapping twice
            coef_t tmp = a[i];
            a[i]   = a[rev];
            a[rev] = tmp;
        }
    }
}

void ntt_engine(coef_t a[N], const coef_t omega_table[N], bool inverse) {
#pragma HLS ARRAY_PARTITION variable=a cyclic factor=2 dim=1

    if (!inverse) {
        // Cooley-Tukey DIT
        bit_reverse_permute(a);

        for (int m = 2; m <= N; m <<= 1) {     // log2(N) stages; m = group size
#pragma HLS UNROLL
            int m_half = m >> 1;
            for (int k = 0; k < N; k += m) {   // step through groups
#pragma HLS UNROLL
                for (int j = 0; j < m_half; j++) {
#pragma HLS PIPELINE II=1
                    coef_t w = omega_table[j * (N / m)]; // w_m^j = w^(j*N/m)
                    coef_t t = barrett_mul(w, a[k + j + m_half]);
                    coef_t u = a[k + j];
                    a[k + j]          = mod_add(u, t);   // E + w·O
                    a[k + j + m_half] = mod_sub(u, t);   // E - w·O
                }
            }
        }

    } else {
        // Gentleman-Sande DIF
        for (int m = N; m >= 2; m >>= 1) {     // stages reversed: large groups first
#pragma HLS UNROLL
            int m_half = m >> 1;
            for (int k = 0; k < N; k += m) {
#pragma HLS UNROLL
                for (int j = 0; j < m_half; j++) {
#pragma HLS PIPELINE II=1
                    coef_t w = omega_table[j * (N / m)]; // caller passes INV_OMEGA_TABLE
                    coef_t t = a[k + j + m_half];
                    coef_t u = a[k + j];
                    a[k + j]          = mod_add(u, t);               // GS upper: u + t
                    a[k + j + m_half] = barrett_mul(w, mod_sub(u, t)); // GS lower: w·(u-t)
                }
            }
        }

        bit_reverse_permute(a);

        for (int i = 0; i < N; i++) {
#pragma HLS UNROLL
            a[i] = barrett_mul(a[i], INV_N);    // scale by n^-1 mod q
        }
    }
}
