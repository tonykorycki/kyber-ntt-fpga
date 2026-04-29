// hls/src/ntt_engine.cpp — Kyber NTT butterfly engine (FIPS 203 Algorithms 9 / 10)
//
// Forward NTT : Cooley-Tukey  (k increments, len = N/2 down to 2)
// Inverse NTT : Gentleman-Sande (k decrements, len = 2 up to N/2), then scale by INV_N
//
// Twiddle schedule: TWIDDLE[k] = zeta^{brv(k+1)} from twiddle_rom.h.
// INTT uses the same table traversed in reverse — positive twiddles, no negation (FIPS 203 §4).
//
// Two pipeline strategies (selected by NTT_FLAT_PIPELINE in ntt_engine.h):
//   Default:           PIPELINE II=1 on inner j-loop; pipeline drains between blocks.
//   NTT_FLAT_PIPELINE: start+j fused into one N/2-iteration loop per stage; no drain gaps.

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
    coef_wide_t s = (coef_wide_t)a + Q - b;
    return s >= Q ? coef_t(s - Q) : coef_t(s);
}

void ntt_engine(coef_t a[N], bool inverse) {
#pragma HLS ARRAY_PARTITION variable=a cyclic factor=2 dim=1

    if (!inverse) {

#ifdef NTT_FLAT_PIPELINE
        // Flat forward NTT: one continuous pipeline of N/2 butterflies per stage.
        // log2_len tracks log2(len) so all index arithmetic is shifts and masks.
        //   blk   = i >> log2_len          (i / len)
        //   j     = i & (len - 1)          (i % len)
        //   lower = (blk << (log2_len+1)) | j   (blk*2*len + j; | safe since j < len)
        int k = 0;
        for (int len = N/2, log2_len = LOG2_N - 1; len >= 2; len >>= 1, log2_len--) {
            int k_base   = k;
            int n_blocks = N >> (log2_len + 1);   // N / (2*len)
            for (int i = 0; i < N/2; i++) {
#pragma HLS PIPELINE II=1
                int blk   = i >> log2_len;
                int j     = i & (len - 1);
                int lower = (blk << (log2_len + 1)) | j;
                int upper = lower + len;
                coef_t zeta    = TWIDDLE[k_base + blk];
                coef_t t       = barrett_mul(zeta, a[upper]);
                a[upper]       = mod_sub(a[lower], t);
                a[lower]       = mod_add(a[lower], t);
            }
            k += n_blocks;
        }
#else
        // Standard nested-loop forward NTT (FIPS 203 Algorithm 9).
        int k = 0;
        for (int len = N/2; len >= 2; len >>= 1) {
            for (int start = 0; start < N; start += 2*len) {
                coef_t zeta = TWIDDLE[k++];
                for (int j = 0; j < len; j++) {
#pragma HLS PIPELINE II=1
                    coef_t t       = barrett_mul(zeta, a[start + j + len]);
                    a[start+j+len] = mod_sub(a[start+j], t);
                    a[start+j]     = mod_add(a[start+j], t);
                }
            }
        }
#endif

    } else {

#ifdef NTT_FLAT_PIPELINE
        // Flat inverse NTT: same fusion, twiddle index counts down from k_start.
        int k = N/2 - 2;
        for (int len = 2, log2_len = 1; len <= N/2; len <<= 1, log2_len++) {
            int k_start  = k;
            int n_blocks = N >> (log2_len + 1);   // N / (2*len)
            for (int i = 0; i < N/2; i++) {
#pragma HLS PIPELINE II=1
                int blk   = i >> log2_len;
                int j     = i & (len - 1);
                int lower = (blk << (log2_len + 1)) | j;
                int upper = lower + len;
                coef_t zeta    = TWIDDLE[k_start - blk];
                coef_t t       = a[lower];
                a[lower]       = mod_add(t, a[upper]);
                a[upper]       = barrett_mul(zeta, mod_sub(a[upper], t));
            }
            k -= n_blocks;
        }
#else
        // Standard nested-loop inverse NTT (FIPS 203 Algorithm 10).
        int k = N/2 - 2;
        for (int len = 2; len <= N/2; len <<= 1) {
            for (int start = 0; start < N; start += 2*len) {
                coef_t zeta = TWIDDLE[k--];
                for (int j = 0; j < len; j++) {
#pragma HLS PIPELINE II=1
                    coef_t t       = a[start+j];
                    a[start+j]     = mod_add(t, a[start+j+len]);
                    a[start+j+len] = barrett_mul(zeta, mod_sub(a[start+j+len], t));
                }
            }
        }
#endif

        // Scale by (N/2)^{-1} mod Q — same for both pipeline strategies
        for (int i = 0; i < N; i++) {
#pragma HLS PIPELINE II=1
            a[i] = barrett_mul(a[i], INV_N);
        }
    }
}
