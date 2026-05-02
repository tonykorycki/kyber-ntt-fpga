"""
golden/kyber_ntt.py — Parametric Kyber-style NTT (FIPS 203 Algorithms 9/10/11)

Requires a primitive N-th root of unity ZETA satisfying:
    ZETA^N  = 1      (mod Q)
    ZETA^(N/2) = Q-1 (mod Q)   [i.e. -1]

Unlike ntt.py which uses a 2N-th root of unity for the twist trick, this uses
the N-th root directly — same structure as FIPS 203 for N=256, Q=3329, ZETA=17.

KyberNTTConfig   dataclass: n, q, zeta, and all precomputed values
bit_revK         (x, config) -> bit-reversed x (BITS-wide)
zeta_pow         (k, config) -> ZETA^k mod Q
ct_butterfly     (a, b, zeta, config) -> CT butterfly pair
gs_butterfly     (a, b, zeta, config) -> GS butterfly pair
ntt_forward      (f, config) -> NTT(f)  [FIPS 203 Alg 9]
ntt_inverse      (f, config) -> INTT(f) [FIPS 203 Alg 10]
base_case_mul    (a0,a1,b0,b1,gamma,config) -> quadratic-slot multiply
poly_mul         (a, b, config) -> negacyclic multiply via NTT
schoolbook_mul   (a, b, config) -> O(N^2) reference
-- Compatibility wrappers (same signatures as ntt.py Kyber functions) --
kyber_ntt        (f, q=3329) -> ntt_forward
kyber_intt       (f, q=3329) -> ntt_inverse
kyber_poly_mul   (a, b, q=3329) -> poly_mul
kyber_schoolbook (a, b, q=3329) -> schoolbook_mul
"""

import argparse
import os
import random
from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class KyberNTTConfig:
    n: int           # polynomial degree (power of 2, >= 4)
    q: int           # prime modulus
    zeta: int        # primitive N-th root of unity mod Q
    half_n: int      # n // 2  —  number of quadratic slots
    bits: int        # log2(half_n)  —  bit-reversal width
    inv_half_n: int  # (n/2)^{-1} mod q  —  INTT scaling factor
    barrett_k: int   # bit-width parameter for Barrett reduction
    barrett_m: int   # Barrett multiplier: floor(2^{2k} / q)

    @classmethod
    def from_params(cls, n: int, q: int, zeta: int = None) -> 'KyberNTTConfig':
        """Build a config for (N, Q). Finds ZETA automatically if not given."""
        if zeta is None:
            zeta = _find_zeta(n, q)
        _validate(n, q, zeta)
        half_n    = n // 2
        bits      = n.bit_length() - 2   # log2(n/2)
        barrett_k = q.bit_length()          # matches HLS: BARRETT_K = COEF_W
        barrett_m = (1 << (2 * barrett_k)) // q  # matches HLS: BARRETT_M = (1<<2K)/Q
        return cls(
            n=n, q=q, zeta=zeta,
            half_n=half_n,
            bits=bits,
            inv_half_n=pow(half_n, q - 2, q),
            barrett_k=barrett_k,
            barrett_m=barrett_m,
        )


def _prime_factors(n: int) -> list:
    factors, d = [], 2
    while d * d <= n:
        if n % d == 0:
            factors.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def _find_zeta(n: int, q: int) -> int:
    """Return the primitive N-th root of unity mod Q.

    For N=256, Q=3329 returns 17 (FIPS 203 / ML-KEM specified value).
    For all other valid (N, Q) pairs, derives from the smallest primitive root of Z_Q.
    """
    if (q - 1) % n != 0:
        raise ValueError(f"N={n} does not divide Q-1={q-1}; no N-th root of unity exists")
    if n == 256 and q == 3329:
        return 17
    factors = _prime_factors(q - 1)
    for g in range(2, q):
        if all(pow(g, (q - 1) // p, q) != 1 for p in factors):
            break
    zeta = pow(g, (q - 1) // n, q)
    if pow(zeta, n, q) != 1 or pow(zeta, n // 2, q) != q - 1:
        raise ValueError(f"Could not find valid ZETA for N={n}, Q={q}")
    return zeta


def _is_prime(q: int) -> bool:
    try:
        from sympy import isprime
        return isprime(q)
    except ImportError:
        if q < 2:
            return False
        if q < 4:
            return True
        if q % 2 == 0 or q % 3 == 0:
            return False
        i = 5
        while i * i <= q:
            if q % i == 0 or q % (i + 2) == 0:
                return False
            i += 6
        return True


def _validate(n: int, q: int, zeta: int) -> None:
    if not _is_prime(q):
        raise ValueError(f"Q={q} is not prime")
    if n < 4 or (n & (n - 1)) != 0:
        raise ValueError(f"N must be a power of 2 >= 4, got {n}")
    if (q - 1) % n != 0:
        raise ValueError(f"N={n} must divide Q-1={q-1}")
    if pow(zeta, n, q) != 1:
        raise ValueError(f"ZETA^N != 1 (ZETA={zeta}, N={n}, Q={q})")
    if pow(zeta, n // 2, q) != q - 1:
        raise ValueError(f"ZETA^(N/2) != -1; not a primitive N-th root (ZETA={zeta})")


# Default Kyber-256 config (FIPS 203 / ML-KEM)
KYBER_256 = KyberNTTConfig.from_params(n=256, q=3329, zeta=17)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def barrett_reduce(a: int, b: int, config: KyberNTTConfig) -> int:
    """Return (a * b) mod q using Barrett reduction. Mirrors the HLS barrett.cpp logic."""
    ab       = a * b
    q_approx = (ab * config.barrett_m) >> (2 * config.barrett_k)
    reduced  = ab - q_approx * config.q
    if reduced >= config.q:
        reduced -= config.q
    return reduced


def bit_revK(x: int, config: KyberNTTConfig) -> int:
    """config.bits-wide bit reversal of x."""
    return int(bin(x)[2:].zfill(config.bits)[::-1], 2)


def zeta_pow(k: int, config: KyberNTTConfig) -> int:
    """Return ZETA^k mod Q."""
    return pow(config.zeta, k % config.n, config.q)


def ct_butterfly(a: int, b: int, zeta: int, config: KyberNTTConfig) -> tuple:
    """Cooley-Tukey butterfly (FIPS 203 NTT inner step).
    (a, b) -> (a + zeta*b, a - zeta*b)  mod Q
    """
    t = zeta * b % config.q
    return (a + t) % config.q, (a - t + config.q) % config.q


def gs_butterfly(a: int, b: int, zeta: int, config: KyberNTTConfig) -> tuple:
    """Gentleman-Sande butterfly (FIPS 203 Algorithm 10 inner step).
    Uses the POSITIVE twiddle — see FIPS 203 §4 for why negation is not used.
    (a, b) -> (a + b,  zeta * (b - a))  mod Q
    """
    return (a + b) % config.q, (zeta * (b - a + config.q)) % config.q


# ---------------------------------------------------------------------------
# FIPS 203 Algorithm 9 — NTT forward
# ---------------------------------------------------------------------------

def ntt_forward(f: List[int], config: KyberNTTConfig = KYBER_256) -> List[int]:
    """Forward NTT (FIPS 203 Algorithm 9). Returns a new N-element list."""
    assert len(f) == config.n
    f = list(f)
    k = 1
    length = config.half_n
    while length >= 2:
        start = 0
        while start < config.n:
            zeta = zeta_pow(bit_revK(k, config), config)
            k += 1
            for j in range(start, start + length):
                f[j], f[j + length] = ct_butterfly(f[j], f[j + length], zeta, config)
            start += 2 * length
        length //= 2
    return f


# ---------------------------------------------------------------------------
# FIPS 203 Algorithm 10 — NTT inverse
# ---------------------------------------------------------------------------

def ntt_inverse(f: List[int], config: KyberNTTConfig = KYBER_256) -> List[int]:
    """Inverse NTT (FIPS 203 Algorithm 10). Returns a new N-element list."""
    assert len(f) == config.n
    f = list(f)
    k = config.half_n - 1
    length = 2
    while length <= config.half_n:
        start = 0
        while start < config.n:
            zeta = zeta_pow(bit_revK(k, config), config)
            k -= 1
            for j in range(start, start + length):
                f[j], f[j + length] = gs_butterfly(f[j], f[j + length], zeta, config)
            start += 2 * length
        length *= 2
    return [x * config.inv_half_n % config.q for x in f]


# ---------------------------------------------------------------------------
# FIPS 203 Algorithm 11 — BaseCaseMultiply
# ---------------------------------------------------------------------------

def base_case_mul(a0: int, a1: int, b0: int, b1: int,
                  gamma: int, config: KyberNTTConfig = KYBER_256) -> tuple:
    """Multiply (a0 + a1*x)(b0 + b1*x) mod (x^2 - gamma) in Z_Q[x].
    Returns (c0, c1) where result = c0 + c1*x.
    """
    q = config.q
    return (a0 * b0 + a1 * b1 * gamma) % q, (a0 * b1 + a1 * b0) % q


def poly_mul(a: List[int], b: List[int],
             config: KyberNTTConfig = KYBER_256) -> List[int]:
    """Negacyclic polynomial multiply in Z_Q[x]/(x^N+1) via Kyber NTT."""
    assert len(a) == len(b) == config.n
    a_hat = ntt_forward(a, config)
    b_hat = ntt_forward(b, config)
    c_hat = [0] * config.n
    for i in range(config.half_n):
        gamma = zeta_pow(2 * bit_revK(i, config) + 1, config)
        c_hat[2*i], c_hat[2*i+1] = base_case_mul(
            a_hat[2*i], a_hat[2*i+1],
            b_hat[2*i], b_hat[2*i+1],
            gamma, config,
        )
    return ntt_inverse(c_hat, config)


def schoolbook_mul(a: List[int], b: List[int],
                   config: KyberNTTConfig = KYBER_256) -> List[int]:
    """Negacyclic schoolbook multiply: a*b mod (x^N+1) in Z_Q[x]. O(N^2)."""
    n, q = config.n, config.q
    tmp = [0] * (2 * n)
    for i in range(n):
        for j in range(n):
            tmp[i + j] = (tmp[i + j] + a[i] * b[j]) % q
    result = tmp[:n]
    for i in range(n, 2 * n - 1):
        result[i - n] = (result[i - n] - tmp[i]) % q
    return result


# ---------------------------------------------------------------------------
# Compatibility wrappers — same signatures as ntt.py Kyber functions
# ---------------------------------------------------------------------------

def kyber_ntt(f: List[int], q: int = 3329) -> List[int]:
    assert q == 3329, "kyber_ntt is only defined for q=3329"
    return ntt_forward(f, KYBER_256)


def kyber_intt(f: List[int], q: int = 3329) -> List[int]:
    assert q == 3329, "kyber_intt is only defined for q=3329"
    return ntt_inverse(f, KYBER_256)


def kyber_poly_mul(a: List[int], b: List[int], q: int = 3329) -> List[int]:
    assert q == 3329, "kyber_poly_mul is only defined for q=3329"
    return poly_mul(a, b, KYBER_256)


def kyber_schoolbook(a: List[int], b: List[int], q: int = 3329) -> List[int]:
    assert q == 3329, "kyber_schoolbook is only defined for q=3329"
    return schoolbook_mul(a, b, KYBER_256)


# ---------------------------------------------------------------------------
# Twiddle schedules (for inspection / testing)
# ---------------------------------------------------------------------------

def ntt_twiddle_schedule(config: KyberNTTConfig = KYBER_256) -> list:
    """Return the N/2-1 (len, start, zeta) triples in NTT order."""
    schedule = []
    k = 1
    length = config.half_n
    while length >= 2:
        start = 0
        while start < config.n:
            schedule.append((length, start, zeta_pow(bit_revK(k, config), config)))
            k += 1
            start += 2 * length
        length //= 2
    return schedule


def intt_twiddle_schedule(config: KyberNTTConfig = KYBER_256) -> list:
    """Return the N/2-1 (len, start, zeta) triples in INTT order (k decrements)."""
    schedule = []
    k = config.half_n - 1
    length = 2
    while length <= config.half_n:
        start = 0
        while start < config.n:
            schedule.append((length, start, zeta_pow(bit_revK(k, config), config)))
            k -= 1
            start += 2 * length
        length *= 2
    return schedule


# ---------------------------------------------------------------------------
# Test vector generation
# ---------------------------------------------------------------------------

def generate_vectors(n_vectors: int, out_path: str, seed: int = 42,
                     config: KyberNTTConfig = KYBER_256) -> None:
    """Write N_VECTORS poly_mul test vectors to out_path."""
    rng = random.Random(seed)
    with open(out_path, 'w') as fh:
        fh.write(f'# Kyber NTT test vectors: n={config.n}, q={config.q}, zeta={config.zeta}\n')
        fh.write(f'# Format per vector: a, b, c=poly_mul(a,b) — one polynomial per line\n')
        for i in range(n_vectors):
            a = [rng.randint(0, config.q - 1) for _ in range(config.n)]
            b = [rng.randint(0, config.q - 1) for _ in range(config.n)]
            c = poly_mul(a, b, config)
            assert c == schoolbook_mul(a, b, config), f'vector {i}: poly_mul != schoolbook_mul'
            fh.write(f'# vector {i}\n')
            fh.write(' '.join(map(str, a)) + '\n')
            fh.write(' '.join(map(str, b)) + '\n')
            fh.write(' '.join(map(str, c)) + '\n')
    print(f'Wrote {n_vectors} vectors to {out_path}  (n={config.n}, q={config.q}, zeta={config.zeta})')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Kyber-style NTT golden model — self-test and test vector generation.'
    )
    parser.add_argument('--n',       type=int, default=256,
                        help='Polynomial degree, power of 2 with N|(Q-1) (default: 256)')
    parser.add_argument('--q',       type=int, default=3329,
                        help='Prime modulus (default: 3329)')
    parser.add_argument('--zeta',    type=int, default=None,
                        help='Primitive N-th root of unity mod Q (auto-detected if omitted)')
    parser.add_argument('--vectors', type=int, default=0,
                        help='Generate this many test vectors (default: 0 = skip)')
    parser.add_argument('--out',     type=str,
                        default=os.path.join(os.path.dirname(__file__), 'test_vectors.txt'),
                        help='Output path for test vectors')
    parser.add_argument('--seed',    type=int, default=42,
                        help='RNG seed for test vectors (default: 42)')
    parser.add_argument('--trials',  type=int, default=50,
                        help='Random trials per test (default: 50)')
    args = parser.parse_args()

    cfg = KyberNTTConfig.from_params(args.n, args.q, args.zeta)
    print(f'n={cfg.n}, q={cfg.q}, zeta={cfg.zeta}, inv_half_n={cfg.inv_half_n}')

    # --- run tests ---
    rng = random.Random(args.seed)

    assert pow(cfg.zeta, cfg.n, cfg.q) == 1
    assert pow(cfg.zeta, cfg.half_n, cfg.q) == cfg.q - 1
    assert cfg.half_n * cfg.inv_half_n % cfg.q == 1
    print('constants: PASS')

    z = [0] * cfg.n
    assert ntt_forward(z, cfg) == z and ntt_inverse(z, cfg) == z
    print('ntt_zero: PASS')

    failures = [pos for pos in range(cfg.n)
                if ntt_inverse(ntt_forward([1 if j == pos else 0 for j in range(cfg.n)], cfg), cfg)
                != [1 if j == pos else 0 for j in range(cfg.n)]]
    assert not failures, f'spike roundtrip failed at {failures[:10]}'
    print(f'ntt_spikes: PASS (all {cfg.n} basis vectors)')

    for _ in range(args.trials):
        f = [rng.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        assert ntt_inverse(ntt_forward(f, cfg), cfg) == f
    print(f'ntt_roundtrip: PASS ({args.trials} random polynomials)')

    for _ in range(args.trials):
        a = [rng.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        b = [rng.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        assert poly_mul(a, b, cfg) == schoolbook_mul(a, b, cfg)
    print(f'poly_mul: PASS ({args.trials} random pairs)')

    print(f'\nAll tests passed  (n={cfg.n}, q={cfg.q}, zeta={cfg.zeta})')

    if args.vectors > 0:
        generate_vectors(args.vectors, args.out, args.seed, cfg)
