// hls/ntt_engine.h — Types, parameters, and function declarations for NTT engine
#ifndef NTT_ENGINE_H
#define NTT_ENGINE_H

#include <ap_int.h>

// Dev parameters (change for full Kyber: N=256, Q=3329, COEF_W=12, LOG2_N=8)
constexpr int N       = 4;
constexpr int Q       = 17;
constexpr int COEF_W  = 5;
constexpr int LOG2_N  = 2;

typedef ap_uint<COEF_W>      coef_t;
typedef ap_uint<2 * COEF_W>  prod_t;

// Barrett reduction constants (derived from Q and COEF_W)
constexpr int BARRETT_K = COEF_W;                        // ceil(log2(q)) == COEF_W by construction
constexpr int BARRETT_M = (1 << (2 * BARRETT_K)) / Q;   // floor(4^k / q)

#endif // NTT_ENGINE_H
