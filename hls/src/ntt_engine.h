// hls/ntt_engine.h — Parameters, types, and declarations for the NTT engine
//
// Architecture decisions: docs/detailed_plan.md §1.2, docs/mathematic_derivation.md §4–6
//
// To retarget (dev → full Kyber or any valid (N,Q) pair):
//   1. Edit the four #defines below
//   2. Run: python scripts/gen_twiddle_rom.py --n N --q Q
//   3. Re-run HLS synthesis
// Nothing else changes — the architecture is input-agnostic.

#ifndef NTT_ENGINE_H
#define NTT_ENGINE_H

#include <ap_int.h>

// Retarget by editing only these four lines
#define NTT_N       4       // polynomial degree        (full Kyber: 256)
#define NTT_Q       17      // coefficient modulus      (full Kyber: 3329)
#define NTT_COEF_W  5       // bit width of one coef    (full Kyber: 12)
#define NTT_LOG2_N  2       // log2(NTT_N)              (full Kyber: 8)

// C++ aliases for the above macros
constexpr int N      = NTT_N;
constexpr int Q      = NTT_Q;
constexpr int COEF_W = NTT_COEF_W;
constexpr int LOG2_N = NTT_LOG2_N;

typedef ap_uint<COEF_W>      coef_t;   // single coefficient
typedef ap_uint<2 * COEF_W>  prod_t;   // intermediate product before Barrett reduction

// Barrett reduction constants
constexpr int BARRETT_K = COEF_W;
constexpr int BARRETT_M = (1 << (2 * BARRETT_K)) / Q;

// Forward NTT  (Cooley-Tukey DIT):    pass OMEGA_TABLE,     inverse=false
// Inverse NTT  (Gentleman-Sande DIF): pass INV_OMEGA_TABLE, inverse=true
void ntt_engine(coef_t a[N], const coef_t omega_table[N], bool inverse);

#endif // NTT_ENGINE_H
