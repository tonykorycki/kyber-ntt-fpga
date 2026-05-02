#!/usr/bin/env python3
"""
scripts/gen_twiddle_rom.py — Single retargeting command for any valid (N, Q) parameter set.

Generates / updates:
  hls/src/ntt_engine.h   — #define parameters (NTT_N, NTT_Q, NTT_COEF_W, NTT_LOG2_N)
  hls/src/twiddle_rom.h  — TWIDDLE[N/2], SLOT_ZETA[N/2], INV_N for HLS
  vivado/twiddle.coe     — Vivado BRAM init file (NTT butterfly twiddles)
  vivado/slot_zeta.coe   — Vivado BRAM init file (per-slot gammas)

Usage:
    python scripts/gen_twiddle_rom.py --n 4   --q 17    # dev params
    python scripts/gen_twiddle_rom.py --n 256 --q 3329  # full Kyber

After running, re-run HLS synthesis. Nothing else needs to change.

Requirements:
    q must be prime and n must divide (q - 1).
    (NOT 2n — Kyber NTT requires a primitive N-th root, not 2N-th.)
"""

import argparse
import math
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'golden'))
from kyber_ntt import KyberNTTConfig, bit_revK, zeta_pow


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_params(n: int, q: int) -> None:
    """Abort with a clear message if (n, q) cannot support a Kyber-style NTT."""
    try:
        from sympy import isprime
        q_is_prime = isprime(q)
    except ImportError:
        # Lightweight fallback so bad q values still fail with a clear message
        # instead of propagating a later ValueError/stack trace.
        if q < 2:
            q_is_prime = False
        elif q % 2 == 0:
            q_is_prime = (q == 2)
        else:
            q_is_prime = True
            limit = math.isqrt(q)
            for d in range(3, limit + 1, 2):
                if q % d == 0:
                    q_is_prime = False
                    break

    if not q_is_prime:
        sys.exit(f"Error: q={q} is not prime.")

    if n & (n - 1) != 0 or n < 4:
        sys.exit(f"Error: n={n} must be a power of 2 >= 4.")
    if (q - 1) % n != 0:
        sys.exit(
            f"Error: n={n} does not divide q-1={q-1}. "
            f"No primitive N-th root of unity exists mod q.\n"
            f"Note: Kyber NTT requires n|(q-1), not 2n|(q-1)."
        )


# ---------------------------------------------------------------------------
# Twiddle computation
# ---------------------------------------------------------------------------

def compute_twiddles(cfg: KyberNTTConfig):
    """Return (TWIDDLE, SLOT_ZETA, INV_N) for the given config.

    TWIDDLE[k]   = zeta^{brv(k+1)}      for k = 0..half_n-1  (NTT butterfly twiddles)
    SLOT_ZETA[i] = zeta^{2*brv(i)+1}    for i = 0..half_n-1  (per-slot gammas, base-case mul)
    INV_N        = (N/2)^{-1} mod q                           (INTT scaling, 7 stages -> 2^7=128)
    """
    twiddle   = [zeta_pow(bit_revK(k + 1, cfg), cfg) for k in range(cfg.half_n)]
    slot_zeta = [zeta_pow(2 * bit_revK(i, cfg) + 1, cfg) for i in range(cfg.half_n)]
    inv_n     = cfg.inv_half_n
    return twiddle, slot_zeta, inv_n


def self_test(cfg: KyberNTTConfig, twiddle: list, slot_zeta: list, inv_n: int) -> None:
    """Spot-check generated values against known-good formulas."""
    assert len(twiddle)   == cfg.half_n, f"TWIDDLE length {len(twiddle)} != {cfg.half_n}"
    assert len(slot_zeta) == cfg.half_n, f"SLOT_ZETA length {len(slot_zeta)} != {cfg.half_n}"

    # TWIDDLE[0] = zeta^{brv(1)}
    assert twiddle[0] == zeta_pow(bit_revK(1, cfg), cfg), \
        f"TWIDDLE[0]={twiddle[0]}, expected {zeta_pow(bit_revK(1, cfg), cfg)}"

    # SLOT_ZETA[0] = zeta^{2*brv(0)+1} = zeta^1 = zeta  (brv(0)=0 always)
    assert slot_zeta[0] == cfg.zeta, \
        f"SLOT_ZETA[0]={slot_zeta[0]}, expected {cfg.zeta}"

    # INV_N * (N/2) == 1 mod q
    assert inv_n * cfg.half_n % cfg.q == 1, \
        f"INV_N * (N/2) != 1 mod q  (INV_N={inv_n}, N/2={cfg.half_n}, q={cfg.q})"

    print(f"  self-test: PASS  "
          f"(TWIDDLE[0]={twiddle[0]}, SLOT_ZETA[0]={slot_zeta[0]}, INV_N={inv_n})")


# ---------------------------------------------------------------------------
# ntt_engine.h
# ---------------------------------------------------------------------------

def update_ntt_engine_h(n: int, q: int, hls_dir: str) -> None:
    """Rewrite the four #define lines in ntt_engine.h for the given (n, q)."""
    coef_w = q.bit_length()
    log2_n = int(math.log2(n))

    path = os.path.join(hls_dir, 'ntt_engine.h')
    with open(path, 'r') as f:
        src = f.read()

    for macro, value in [('NTT_N', n), ('NTT_Q', q),
                         ('NTT_COEF_W', coef_w), ('NTT_LOG2_N', log2_n)]:
        src = re.sub(
            rf'(#define\s+{macro}\s+)\d+',
            lambda m, v=str(value): m.group(1) + v,
            src,
        )

    with open(path, 'w') as f:
        f.write(src)
    print(f'Updated  {path}  (N={n}, Q={q}, COEF_W={coef_w}, LOG2_N={log2_n})')


# ---------------------------------------------------------------------------
# twiddle_rom.h
# ---------------------------------------------------------------------------

def gen_twiddle_rom_h(twiddle: list, slot_zeta: list, inv_n: int,
                      n: int, q: int, hls_dir: str) -> None:
    def arr(name: str, values: list, size_expr: str) -> str:
        vals = ', '.join(str(v) for v in values)
        return f'const coef_t {name}[{size_expr}] = {{{vals}}};'

    path = os.path.join(hls_dir, 'twiddle_rom.h')
    with open(path, 'w') as f:
        f.write(f'// hls/src/twiddle_rom.h — Generated by scripts/gen_twiddle_rom.py\n')
        f.write(f'// Parameters: n={n}, q={q}\n')
        f.write(f'// DO NOT EDIT — regenerate with: '
                f'python scripts/gen_twiddle_rom.py --n {n} --q {q}\n')
        f.write(f'#ifndef TWIDDLE_ROM_H\n#define TWIDDLE_ROM_H\n\n')
        f.write(f'#include "ntt_engine.h"\n\n')
        # N/2 entries each — INTT reuses TWIDDLE in reverse (positive, no negation)
        f.write(arr('TWIDDLE',   twiddle,   'N/2') + '\n')
        f.write(arr('SLOT_ZETA', slot_zeta, 'N/2') + '\n')
        stages = int(math.log2(n // 2))
        f.write(f'const coef_t INV_N = {inv_n};'
                f'  // (N/2)^{{-1}} mod Q — {stages} stages -> 2^{stages}={n//2} accumulated factor\n\n')
        f.write(f'#endif // TWIDDLE_ROM_H\n')
    print(f'Wrote    {path}')


# ---------------------------------------------------------------------------
# Vivado .coe files
# ---------------------------------------------------------------------------

def gen_coe_files(twiddle: list, slot_zeta: list, vivado_dir: str) -> None:
    def coe(values: list) -> str:
        lines = ['memory_initialization_radix=10;', 'memory_initialization_vector=']
        lines += [f'{v},' for v in values[:-1]]
        lines += [f'{values[-1]};']
        return '\n'.join(lines)

    os.makedirs(vivado_dir, exist_ok=True)
    for name, values in [('twiddle', twiddle), ('slot_zeta', slot_zeta)]:
        path = os.path.join(vivado_dir, f'{name}.coe')
        with open(path, 'w') as f:
            f.write(coe(values))
        print(f'Wrote    {path}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Retarget the Kyber NTT accelerator to a new (N, Q) parameter set.'
    )
    parser.add_argument('--n',          type=int, default=4,   help='Polynomial degree (default: 4)')
    parser.add_argument('--q',          type=int, default=17,  help='Modulus (default: 17)')
    parser.add_argument('--check-only', action='store_true',
                        help='Validate params and run self-test; do not write any files')
    parser.add_argument('--root',       type=str,
                        default=os.path.join(os.path.dirname(__file__), '..'),
                        help='Repository root (default: parent of scripts/)')
    args = parser.parse_args()

    validate_params(args.n, args.q)

    cfg                     = KyberNTTConfig.from_params(n=args.n, q=args.q)
    twiddle, slot_zeta, inv_n = compute_twiddles(cfg)

    print(f'n={cfg.n}, q={cfg.q}, zeta={cfg.zeta}, INV_N={inv_n}')
    self_test(cfg, twiddle, slot_zeta, inv_n)

    if args.check_only:
        print('\nAll checks passed. (--check-only: no files written)')
        sys.exit(0)

    hls_dir    = os.path.join(args.root, 'hls', 'src')
    vivado_dir = os.path.join(args.root, 'vivado')

    update_ntt_engine_h(args.n, args.q, hls_dir)
    gen_twiddle_rom_h(twiddle, slot_zeta, inv_n, args.n, args.q, hls_dir)
    gen_coe_files(twiddle, slot_zeta, vivado_dir)

    print('\nDone. Re-run HLS synthesis to pick up the new parameters.')
