'''
golden/test_ntt.py — Golden model correctness tests.
Verifies NTT/INTT/negacyclic_mul against schoolbook multiplication.

To generate test vectors for HLS C-sim / SV simulation:
    python golden/gen_test_vectors.py --n N --q Q --vectors 16

test_barrett         exhaustive for all (a,b) pairs in Z_q
test_pre_post_twist  pre_twist then post_twist = identity
test_ntt_forward     compare CT butterfly against naive O(n^2) definition
test_ntt_roundtrip   ntt_forward then ntt_inverse = identity
test_ntt_mul         compare ntt_mul vs schoolbook_nwc on random inputs
'''

import argparse
import random
from ntt import (
    DEV_CONFIG, NTTConfig,
    barrett_reduce,
    pre_twist, post_twist,
    ntt_forward, ntt_inverse,
    pointwise_mul,
    ntt_mul, schoolbook_nwc
)


# Naive O(n^2) NTT directly from the definition (eq. 1 of derivation):
# A[k] = sum from j=0 to n-1 of a[j] * omega^{jk}  mod q

def naive_ntt(a: list, config: NTTConfig) -> list:
    """O(n^2) NTT by direct evaluation — implements eq. (1) literally."""
    d = config.d
    q = config.q
    return [
        sum(a[j] * pow(config.omega, j * k, q) for j in range(d)) % q
        for k in range(d)
    ]


def naive_intt(a: list, config: NTTConfig) -> list:
    """O(n^2) INTT by direct evaluation — implements eq. (5) literally."""
    d = config.d
    q = config.q
    return [
        config.inv_d * sum(a[k] * pow(config.omega, -(j * k), q) for k in range(d)) % q
        for j in range(d)
    ]

# Random polynomial generation for testing
def rand_poly(config: NTTConfig) -> list:
    """Random polynomial with coefficients in [0, q)."""
    return [random.randint(0, config.q - 1) for _ in range(config.d)]

# tests:

def test_barrett(config: NTTConfig):
    """Exhaustive: barrett_reduce(a, b) == (a*b) % q for all a,b in Z_q."""
    q = config.q
    for a in range(q):
        for b in range(q):
            expected = (a * b) % q
            got = barrett_reduce(a, b, config)
            assert got == expected, f"barrett_reduce({a},{b}) = {got}, expected {expected}"
    print(f"test_barrett: PASS ({q*q} pairs)")


def test_pre_post_twist(config: NTTConfig, n_trials: int = 50):
    """post_twist(pre_twist(a)) == a for random inputs."""
    for trial in range(n_trials):
        a = rand_poly(config)
        recovered = post_twist(pre_twist(a, config), config)
        assert recovered == a, f"twist roundtrip failed: {a} -> {recovered}"
    print(f"test_pre_post_twist: PASS ({n_trials} random polynomials)")


def test_ntt_forward(config: NTTConfig, n_trials: int = 50):
    """ntt_forward matches naive O(n^2) definition (eq. 1) for random inputs."""
    for trial in range(n_trials):
        a = rand_poly(config)
        expected = naive_ntt(a, config)
        got = ntt_forward(a, config)
        assert got == expected, \
            f"ntt_forward mismatch:\n    input: {a}\n    expected: {expected}\n    got: {got}"
    print(f"test_ntt_forward: PASS ({n_trials} random polynomials)")


def test_ntt_roundtrip(config: NTTConfig, n_trials: int = 50):
    """ntt_inverse(ntt_forward(a)) == a for random inputs."""
    for trial in range(n_trials):
        a = rand_poly(config)
        recovered = ntt_inverse(ntt_forward(a, config), config)
        assert recovered == a, f"NTT roundtrip failed:\n    input: {a}\n    recovered: {recovered}"
    print(f"test_ntt_roundtrip: PASS ({n_trials} random polynomials)")


def test_ntt_mul(config: NTTConfig, n_trials: int = 50):
    """ntt_mul(a, b) == schoolbook_nwc(a, b) for random inputs."""
    for trial in range(n_trials):
        a = rand_poly(config)
        b = rand_poly(config)
        expected = schoolbook_nwc(a, b, config)
        got = ntt_mul(a, b, config)
        assert got == expected, \
            f"ntt_mul mismatch:\n    a: {a}\n    b: {b}\n    expected: {expected}\n    got: {got}"
    print(f"test_ntt_mul: PASS ({n_trials} random pairs)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run NTT golden model tests.')
    parser.add_argument('--n', type=int, help='Polynomial degree (default: dev config n=4)')
    parser.add_argument('--q', type=int, help='Modulus (default: dev config q=17)')
    parser.add_argument('--seed', type=int, default=42, help='RNG seed (default: 42)')
    args = parser.parse_args()

    random.seed(args.seed)

    if args.n is not None and args.q is not None:
        cfg = NTTConfig.from_params(d=args.n, q=args.q)
        print(f"Using params: n={args.n}, q={args.q}")
    elif args.n is not None or args.q is not None:
        parser.error("--n and --q must be specified together")
    else:
        cfg = DEV_CONFIG
        print(f"Using dev config: n={cfg.d}, q={cfg.q}")

    test_barrett(cfg)
    test_pre_post_twist(cfg)
    test_ntt_forward(cfg)
    test_ntt_roundtrip(cfg)
    test_ntt_mul(cfg)

    print("\nAll tests passed.")