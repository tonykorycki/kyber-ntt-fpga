// hls/twist.h — Negacyclic twist declarations
#ifndef TWIST_H
#define TWIST_H

#include "ntt_engine.h"

// Pre-twist:  a[i] = a[i] * psi^i     mod q  (inverse=false)
// Post-twist: a[i] = a[i] * psi^{-i}  mod q  (inverse=true)
void twist(coef_t a[N], const coef_t psi_table[N], bool inverse);

#endif // TWIST_H
