// hls/src/ntt_engine.h — Parameters, types, and declarations for the NTT engine
//
// Architecture: docs/kyber_ntt_redesign.md — Kyber-native NTT (FIPS 203 Alg 9/10/11)
//
// To retarget (dev → full Kyber or any valid (N,Q) pair):
//   python scripts/gen_twiddle_rom.py --n N --q Q
// That script updates this file and regenerates twiddle_rom.h atomically.
// Nothing else changes — the architecture is input-agnostic.

#ifndef NTT_ENGINE_H
#define NTT_ENGINE_H

#include <ap_int.h>

// Retarget by running gen_twiddle_rom.py — do not edit these manually
#define NTT_N       4       // polynomial degree        (full Kyber: 256)
#define NTT_Q       17      // coefficient modulus      (full Kyber: 3329)
#define NTT_COEF_W  5       // bit width of one coef    (full Kyber: 12)
#define NTT_LOG2_N  2       // log2(NTT_N)              (full Kyber: 8)

// C++ aliases
constexpr int N      = NTT_N;
constexpr int Q      = NTT_Q;
constexpr int COEF_W = NTT_COEF_W;
constexpr int LOG2_N = NTT_LOG2_N;

typedef ap_uint<COEF_W>      coef_t;   // single coefficient
typedef ap_uint<2 * COEF_W>  prod_t;   // intermediate product before Barrett reduction

// Barrett reduction constants
// barrett_const_t is wide enough to hold BARRETT_M without overflow for any COEF_W.
// Using ap_uint<2*COEF_W+1> avoids the overflow that occurs with plain int when COEF_W > 15.
constexpr int BARRETT_K = COEF_W;
typedef ap_uint<2 * COEF_W + 1> barrett_const_t;
static const barrett_const_t BARRETT_M = (barrett_const_t(1) << (2 * BARRETT_K)) / Q;

// Forward NTT  (Cooley-Tukey):   ntt_engine(a, false)
// Inverse NTT  (Gentleman-Sande): ntt_engine(a, true)
// Twiddle tables (TWIDDLE, SLOT_ZETA, INV_N) are in twiddle_rom.h — included by ntt_engine.cpp.
void ntt_engine(coef_t a[N], bool inverse);

#endif // NTT_ENGINE_H
