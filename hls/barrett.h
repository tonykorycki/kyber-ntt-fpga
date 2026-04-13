// hls/barrett.h — Barrett modular multiplier declarations
#ifndef BARRETT_H
#define BARRETT_H

#include "ntt_engine.h"

// Barrett modular multiply: returns (a * b) mod q
coef_t barrett_mul(coef_t a, coef_t b);

#endif // BARRETT_H
