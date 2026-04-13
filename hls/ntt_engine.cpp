// hls/ntt_engine.cpp — NTT butterfly pipeline (Cooley-Tukey radix-2 DIT)
//
// Implements forward NTT and inverse INTT via a flag.
// Uses HLS pragmas for pipelining and unrolling.

#include "ntt_engine.h"
#include "barrett.h"
