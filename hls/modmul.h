// hls/modmul.h — Barrett modular multiplier declarations
#ifndef MODMUL_H
#define MODMUL_H

#include "ntt_engine.h"

// Barrett modular multiply: returns (a * b) mod q
coef_t modmul(coef_t a, coef_t b);

#endif // MODMUL_H
