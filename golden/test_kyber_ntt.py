"""
golden/test_kyber_ntt.py — Unit tests for kyber_ntt.py primitives.

Run: python golden/test_kyber_ntt.py
Each test is small and independent. Tests run in order from primitives to full pipeline.
"""

import argparse
import random
from kyber_ntt import (
    KyberNTTConfig, KYBER_256,
    barrett_reduce,
    bit_revK, zeta_pow,
    ct_butterfly, gs_butterfly,
    ntt_twiddle_schedule, intt_twiddle_schedule,
    ntt_forward, ntt_inverse,
    base_case_mul, poly_mul, schoolbook_mul,
)


def test_barrett(cfg: KyberNTTConfig):
    """barrett_reduce(a, b) == (a*b) % q. Exhaustive for small q, sampled for large q."""
    q = cfg.q
    if q <= 100:
        for a in range(q):
            for b in range(q):
                assert barrett_reduce(a, b, cfg) == (a * b) % q, \
                    f"barrett_reduce({a},{b}) = {barrett_reduce(a,b,cfg)}, expected {(a*b)%q}"
        print(f"test_barrett: PASS ({q*q} pairs, exhaustive)")
    else:
        random.seed(99)
        for _ in range(10_000):
            a = random.randint(0, q - 1)
            b = random.randint(0, q - 1)
            assert barrett_reduce(a, b, cfg) == (a * b) % q
        print(f"test_barrett: PASS (10000 random pairs)")


def test_constants(cfg: KyberNTTConfig):
    """ZETA is a primitive N-th root of unity mod Q."""
    assert pow(cfg.zeta, cfg.n, cfg.q) == 1,               f"ZETA^N != 1"
    assert pow(cfg.zeta, cfg.half_n, cfg.q) == cfg.q - 1,  f"ZETA^(N/2) != -1"
    assert cfg.half_n * cfg.inv_half_n % cfg.q == 1,       f"(N/2)*inv_half_n != 1"
    print("test_constants: PASS")


def test_bit_revK(cfg: KyberNTTConfig):
    """bit_revK is self-inverse for all k in 0..N/2-1."""
    for x in range(cfg.half_n):
        assert bit_revK(bit_revK(x, cfg), cfg) == x, f"bit_revK not self-inverse at {x}"
    if cfg.n == 256:
        for x, expected in {1: 64, 64: 1, 2: 32, 127: 127, 0: 0}.items():
            assert bit_revK(x, cfg) == expected, f"bit_revK({x}) = {bit_revK(x,cfg)}, expected {expected}"
    print(f"test_bit_revK: PASS (all {cfg.half_n} values)")


def test_ct_butterfly(cfg: KyberNTTConfig):
    """CT butterfly: (a + zeta*b, a - zeta*b) mod Q."""
    a, b, zeta = 100, 200, cfg.zeta
    new_a, new_b = ct_butterfly(a, b, zeta, cfg)
    assert new_a == (a + zeta * b) % cfg.q
    assert new_b == (a - zeta * b) % cfg.q
    assert 0 <= new_a < cfg.q and 0 <= new_b < cfg.q
    print("test_ct_butterfly: PASS")


def test_gs_butterfly(cfg: KyberNTTConfig):
    """GS butterfly (FIPS 203 Alg 10): (a+b, zeta*(b-a)) mod Q using POSITIVE twiddle."""
    a, b, zeta = 100, 200, cfg.zeta
    new_a, new_b = gs_butterfly(a, b, zeta, cfg)
    assert new_a == (a + b) % cfg.q
    assert new_b == (zeta * (b - a)) % cfg.q
    # a2 > b2 so (b2 - a2) is negative — tests the +Q guard in gs_butterfly
    a2 = min(3000, cfg.q - 2)
    b2 = min(50,   cfg.q // 3)
    new_a2, new_b2 = gs_butterfly(a2, b2, zeta, cfg)
    assert new_a2 == (a2 + b2) % cfg.q
    assert new_b2 == (zeta * (b2 - a2)) % cfg.q
    assert 0 <= new_b2 < cfg.q
    print("test_gs_butterfly: PASS")


def test_twiddle_schedule_count(cfg: KyberNTTConfig):
    """NTT and INTT each use exactly N/2-1 twiddles."""
    ntt_sched  = ntt_twiddle_schedule(cfg)
    intt_sched = intt_twiddle_schedule(cfg)
    assert len(ntt_sched)  == cfg.half_n - 1
    assert len(intt_sched) == cfg.half_n - 1
    print(f"test_twiddle_schedule_count: PASS ({cfg.half_n - 1} twiddles each)")


def test_twiddle_schedule_values(cfg: KyberNTTConfig):
    """NTT and INTT use the same positive twiddle zeta_pow(bit_revK(k)) for each k."""
    ntt_zetas  = [z for _, _, z in ntt_twiddle_schedule(cfg)]
    intt_zetas = [z for _, _, z in intt_twiddle_schedule(cfg)]
    for i in range(cfg.half_n - 1):
        assert ntt_zetas[i] == intt_zetas[cfg.half_n - 2 - i], f"twiddle mismatch at k={i+1}"
    print("test_twiddle_schedule_values: PASS")


def test_ntt_zero(cfg: KyberNTTConfig):
    """NTT of the zero polynomial is zero."""
    z = [0] * cfg.n
    assert ntt_forward(z, cfg) == z
    assert ntt_inverse(z, cfg) == z
    print("test_ntt_zero: PASS")


def test_ntt_spikes(cfg: KyberNTTConfig):
    """INTT(NTT(e_i)) == e_i for all N standard basis vectors."""
    failures = []
    for pos in range(cfg.n):
        spike = [0] * cfg.n
        spike[pos] = 1
        if ntt_inverse(ntt_forward(spike, cfg), cfg) != spike:
            failures.append(pos)
    assert not failures, f"Spike roundtrip failed at {failures[:10]}{'...' if len(failures)>10 else ''}"
    print(f"test_ntt_spikes: PASS (all {cfg.n} basis vectors roundtrip correctly)")


def test_ntt_linearity(cfg: KyberNTTConfig, n_trials: int = 20):
    """NTT is linear: NTT(a + b) == NTT(a) + NTT(b) mod Q."""
    random.seed(0)
    for _ in range(n_trials):
        a = [random.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        b = [random.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        apb = [(a[i] + b[i]) % cfg.q for i in range(cfg.n)]
        lhs = ntt_forward(apb, cfg)
        rhs = [(ntt_forward(a, cfg)[i] + ntt_forward(b, cfg)[i]) % cfg.q for i in range(cfg.n)]
        assert lhs == rhs
    print(f"test_ntt_linearity: PASS ({n_trials} trials)")


def test_roundtrip(cfg: KyberNTTConfig, n_trials: int = 50):
    """INTT(NTT(f)) == f for random degree-(N-1) polynomials."""
    random.seed(42)
    for trial in range(n_trials):
        f = [random.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        assert ntt_inverse(ntt_forward(f, cfg), cfg) == f, f"Roundtrip failed trial {trial}"
    print(f"test_roundtrip: PASS ({n_trials} random polynomials)")


def test_base_case_mul(cfg: KyberNTTConfig):
    """base_case_mul matches naive polynomial multiply mod (x^2 - gamma)."""
    random.seed(1)
    for _ in range(200):
        a0, a1 = random.randint(0, cfg.q-1), random.randint(0, cfg.q-1)
        b0, b1 = random.randint(0, cfg.q-1), random.randint(0, cfg.q-1)
        gamma  = zeta_pow(random.randint(0, cfg.n - 1), cfg)
        c0, c1 = base_case_mul(a0, a1, b0, b1, gamma, cfg)
        assert c0 == (a0*b0 + a1*b1*gamma) % cfg.q
        assert c1 == (a0*b1 + a1*b0) % cfg.q
    print("test_base_case_mul: PASS (200 random cases)")


def test_poly_mul(cfg: KyberNTTConfig, n_trials: int = 50):
    """poly_mul matches schoolbook negacyclic multiply."""
    random.seed(7)
    for trial in range(n_trials):
        a = [random.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        b = [random.randint(0, cfg.q - 1) for _ in range(cfg.n)]
        assert poly_mul(a, b, cfg) == schoolbook_mul(a, b, cfg), f"poly_mul mismatch trial {trial}"
    print(f"test_poly_mul: PASS ({n_trials} random pairs)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Unit tests for kyber_ntt.py.')
    parser.add_argument('--n',    type=int, default=256, help='Polynomial degree (default: 256)')
    parser.add_argument('--q',    type=int, default=3329, help='Modulus (default: 3329)')
    parser.add_argument('--zeta', type=int, default=None, help='Primitive N-th root (auto if omitted)')
    parser.add_argument('--seed', type=int, default=42,   help='RNG seed (default: 42)')
    args = parser.parse_args()

    cfg = KyberNTTConfig.from_params(args.n, args.q, args.zeta)
    print(f'n={cfg.n}, q={cfg.q}, zeta={cfg.zeta}')

    test_barrett(cfg)
    test_constants(cfg)
    test_bit_revK(cfg)
    test_ct_butterfly(cfg)
    test_gs_butterfly(cfg)
    test_twiddle_schedule_count(cfg)
    test_twiddle_schedule_values(cfg)
    test_ntt_zero(cfg)
    test_ntt_spikes(cfg)
    test_ntt_linearity(cfg)
    test_roundtrip(cfg)
    test_base_case_mul(cfg)
    test_poly_mul(cfg)
    print("\nAll tests passed.")
