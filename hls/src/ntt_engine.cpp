// hls/src/ntt_engine.cpp — Kyber NTT butterfly engine (FIPS 203 Algorithms 9 / 10)
//
// Forward NTT : Cooley-Tukey  (k increments, len = N/2 down to 2)
// Inverse NTT : Gentleman-Sande (k decrements, len = 2 up to N/2), then scale by INV_N
//
// Twiddle schedule: TWIDDLE[k] = zeta^{brv(k+1)} from twiddle_rom.h.
// INTT uses the same table traversed in reverse — positive twiddles, no negation (FIPS 203 §4).
//
// Pipeline strategies (flags defined in ntt_engine.h or via -D):
//   Default:              PIPELINE II=1 on inner j-loop; pipeline drains between blocks.
//   NTT_FLAT_PIPELINE:    start+j fused into one N/2-iteration loop per stage; no drain gaps.
//   NTT_PREFETCH_READ:    (requires NTT_FLAT_PIPELINE) pre-fetches a[lower] into a register so
//                         each cycle issues a[upper] (bank X) and a[lower_next] (bank Y != X)
//                         concurrently — targets II=1 by eliminating the same-bank read conflict.

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
        // Flat forward NTT: counter-based addressing, no barrel shifters.
        int k = 0;
        for (int len = N/2; len >= 2; len >>= 1) {
            int k_base   = k;
            int n_blocks = N / (2*len);
            int lower    = 0;
            int blk      = 0;
            int j_cnt    = 0;
#ifdef NTT_PREFETCH_READ
            coef_t a_lo_pre = a[0]; // prime: pre-read a[lower_0] before the pipeline starts
#endif
            for (int i = 0; i < N/2; i++) {
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=a inter false
                int upper      = lower + len;
                coef_t zeta    = TWIDDLE[k_base + blk];
                bool end_blk   = (j_cnt == len - 1);
                int lower_next = end_blk ? lower + len + 1 : lower + 1;
#ifdef NTT_PREFETCH_READ
                // Consume pre-fetched lower; issue upper read (bank X) and lower_next
                // read (bank Y != X, since lower_next = lower+1 has opposite parity) together.
                coef_t a_lo    = a_lo_pre;
                coef_t a_hi    = a[upper];
                int lower_safe = (i < N/2 - 1) ? lower_next : 0; // guard last-iter OOB
                a_lo_pre       = a[lower_safe];
#else
                coef_t a_lo    = a[lower];
                coef_t a_hi    = a[upper];
#endif
                coef_t t       = barrett_mul(zeta, a_hi);
                a[upper]       = mod_sub(a_lo, t);
                a[lower]       = mod_add(a_lo, t);
                if (end_blk) { j_cnt = 0; blk++; } else { j_cnt++; }
                lower = lower_next;
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
#pragma HLS DEPENDENCE variable=a inter false
                    coef_t a_lo    = a[start+j];
                    coef_t t       = barrett_mul(zeta, a[start+j+len]);
                    a[start+j+len] = mod_sub(a_lo, t);
                    a[start+j]     = mod_add(a_lo, t);
                }
            }
        }
#endif

    } else {

#ifdef NTT_FLAT_PIPELINE
        // Flat inverse NTT: counter-based addressing, same structure as forward.
        int k = N/2 - 2;
        for (int len = 2; len <= N/2; len <<= 1) {
            int k_start  = k;
            int n_blocks = N / (2*len);
            int lower    = 0;
            int blk      = 0;
            int j_cnt    = 0;
#ifdef NTT_PREFETCH_READ
            coef_t a_lo_pre = a[0];
#endif
            for (int i = 0; i < N/2; i++) {
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=a inter false
                int upper      = lower + len;
                coef_t zeta    = TWIDDLE[k_start - blk];
                bool end_blk   = (j_cnt == len - 1);
                int lower_next = end_blk ? lower + len + 1 : lower + 1;
#ifdef NTT_PREFETCH_READ
                coef_t a_lo    = a_lo_pre;
                coef_t a_hi    = a[upper];
                int lower_safe = (i < N/2 - 1) ? lower_next : 0;
                a_lo_pre       = a[lower_safe];
#else
                coef_t a_lo    = a[lower];
                coef_t a_hi    = a[upper];
#endif
                a[lower]       = mod_add(a_lo, a_hi);
                a[upper]       = barrett_mul(zeta, mod_sub(a_hi, a_lo));
                if (end_blk) { j_cnt = 0; blk++; } else { j_cnt++; }
                lower = lower_next;
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
#pragma HLS DEPENDENCE variable=a inter false
                    coef_t a_lo    = a[start+j];
                    coef_t a_hi    = a[start+j+len];
                    a[start+j]     = mod_add(a_lo, a_hi);
                    a[start+j+len] = barrett_mul(zeta, mod_sub(a_hi, a_lo));
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
