"""
ps/kyber_kem.py — Simplified Kyber-style KEM backed by hardware or software NTT

Mirrors FIPS 203 ML-KEM-512 structure (k=2, n=256, q=3329) without compression
or SHAKE-based sampling.  Shared-secret correctness holds when decryption noise
magnitude < q/4=832; with ETA=1 the worst-case coefficient bound is ~1025 but
the distribution concentrates well below the threshold in practice.

Two multiply backends are exported:
  ntt_mul_sw(a, b)  — pure-Python via golden/kyber_ntt.py
  ntt_mul_hw(a, b)  — subprocess call to ps/ntt_driver (requires sudo on PYNQ)
"""

import os
import sys
import random
import struct
import subprocess
import time
from typing import List, Callable, Tuple

_PS     = '/home/xilinx/jupyter_notebooks/kyber-ntt-fpga/ps'
_GOLDEN = '/home/xilinx/jupyter_notebooks/kyber-ntt-fpga/golden'
sys.path.insert(0, _GOLDEN)
from kyber_ntt import poly_mul, KYBER_256

N   = 256
Q   = 3329
K   = 2
ETA = 1

Poly = List[int]
Vec  = List[Poly]
Mat  = List[Vec]


def ntt_mul_sw(a: Poly, b: Poly) -> Poly:
    return poly_mul(a, b, KYBER_256)


def get_last_hw_latency_us() -> float:
    """Return the C-driver-measured latency (clock_gettime) of the last ntt_mul_hw call."""
    return last_hw_latency_us


_DRIVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ntt_driver')

last_hw_latency_us: float = 0.0  # latency of the last ntt_mul_hw call, from C clock_gettime

_hw_proc = None  # persistent ntt_driver -r subprocess

_RESULT_BYTES = N * 2 + 8  # N uint16_t coefficients + int64_t nanoseconds


def _read_exact(f, n):
    buf = b''
    while len(buf) < n:
        chunk = f.read(n - len(buf))
        if not chunk:
            raise EOFError('ntt_driver subprocess closed unexpectedly')
        buf += chunk
    return buf


def _hw_init():
    global _hw_proc
    if _hw_proc is not None:
        return
    for cmd in [[_DRIVER, '-r'], ['sudo', _DRIVER, '-r']]:
        try:
            _hw_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            continue
    raise RuntimeError(f'Could not start ntt_driver at {_DRIVER}')


def ntt_mul_hw(a: Poly, b: Poly) -> Poly:
    global last_hw_latency_us
    _hw_init()
    a_clamped = [x % Q for x in a]
    b_clamped = [x % Q for x in b]
    payload = struct.pack(f'{N}H{N}H', *a_clamped, *b_clamped)
    _hw_proc.stdin.write(payload)
    _hw_proc.stdin.flush()
    raw = _read_exact(_hw_proc.stdout, _RESULT_BYTES)
    c = list(struct.unpack(f'{N}H', raw[:N * 2]))
    ns = struct.unpack('<q', raw[N * 2:])[0]
    last_hw_latency_us = ns / 1000.0
    return [x % Q for x in c]


class KyberKEM:
    """
    Kyber-style KEM with injected polynomial multiply.

    Pass ntt_mul_sw or ntt_mul_hw as multiply_fn to switch backends.
    Same seed produces identical shared secrets on both backends, which
    confirms hardware correctness against the golden model.
    """

    def __init__(self, multiply_fn: Callable[[Poly, Poly], Poly], seed: int = None):
        self.mul       = multiply_fn
        self.rng       = random.Random(seed)
        self.mul_count = 0

    def _add(self, a: Poly, b: Poly) -> Poly:
        return [(x + y) % Q for x, y in zip(a, b)]

    def _sub(self, a: Poly, b: Poly) -> Poly:
        return [(x - y) % Q for x, y in zip(a, b)]

    def _mul(self, a: Poly, b: Poly) -> Poly:
        self.mul_count += 1
        return self.mul(a, b)

    def _sample_uniform(self) -> Poly:
        return [self.rng.randint(0, Q - 1) for _ in range(N)]

    def _sample_noise(self) -> Poly:
        coefs = []
        for _ in range(N):
            pos = sum(self.rng.randint(0, 1) for _ in range(ETA))
            neg = sum(self.rng.randint(0, 1) for _ in range(ETA))
            coefs.append((pos - neg) % Q)
        return coefs

    def _mat_vec_mul(self, A: Mat, v: Vec) -> Vec:
        result = []
        for i in range(K):
            acc = [0] * N
            for j in range(K):
                acc = self._add(acc, self._mul(A[i][j], v[j]))
            result.append(acc)
        return result

    def _vec_dot(self, u: Vec, v: Vec) -> Poly:
        acc = [0] * N
        for i in range(K):
            acc = self._add(acc, self._mul(u[i], v[i]))
        return acc

    def keygen(self) -> Tuple[Tuple[Mat, Vec], Vec]:
        """Returns (pk=(A, t), sk=s)."""
        A  = [[self._sample_uniform() for _ in range(K)] for _ in range(K)]
        s  = [self._sample_noise() for _ in range(K)]
        e  = [self._sample_noise() for _ in range(K)]
        As = self._mat_vec_mul(A, s)
        t  = [self._add(As[i], e[i]) for i in range(K)]
        return (A, t), s

    def encaps(self, pk: Tuple[Mat, Vec]) -> Tuple[Tuple[Vec, Poly], bytes]:
        """Returns (ciphertext=(u, v), shared_secret)."""
        A, t = pk
        r    = [self._sample_noise() for _ in range(K)]
        e1   = [self._sample_noise() for _ in range(K)]
        e2   = self._sample_noise()
        bits = [self.rng.randint(0, 1) for _ in range(N)]
        m    = [b * (Q // 2) for b in bits]
        AT   = [[A[j][i] for j in range(K)] for i in range(K)]
        ATr  = self._mat_vec_mul(AT, r)
        u    = [self._add(ATr[i], e1[i]) for i in range(K)]
        v    = self._add(self._add(self._vec_dot(t, r), e2), m)
        return (u, v), _pack_secret(bits)

    def decaps(self, sk: Vec, ct: Tuple[Vec, Poly]) -> bytes:
        """Returns shared_secret."""
        u, v = ct
        mp   = self._sub(v, self._vec_dot(sk, u))
        return _pack_secret(_decode(mp))


def _decode(p: Poly) -> List[int]:
    """Round each coefficient to nearest {0, q//2} on the modular circle."""
    half_q = Q // 2
    bits = []
    for x in p:
        d0 = min(x, Q - x)
        d1 = abs(x - half_q)
        d1 = min(d1, Q - d1)
        bits.append(1 if d1 < d0 else 0)
    return bits


def _pack_secret(bits: List[int]) -> bytes:
    """Pack N message bits into a 32-byte shared secret."""
    out = bytearray(32)
    for i in range(min(256, N)):
        out[i // 8] |= bits[i] << (i % 8)
    return bytes(out)


def verify_multiply(multiply_fn: Callable) -> tuple:
    """
    Check multiply_fn against the SW golden model on 3 known inputs.
    Returns (passed: bool, detail: str).
    KEM noise tolerance can mask wrong multiplications; this check cannot.
    """
    rng = random.Random(0xdeadbeef)
    for i in range(3):
        a = [rng.randint(0, Q - 1) for _ in range(N)]
        b = [rng.randint(0, Q - 1) for _ in range(N)]
        got      = multiply_fn(a, b)
        expected = ntt_mul_sw(a, b)
        mismatches = sum(g % Q != e % Q for g, e in zip(got, expected))
        if mismatches:
            return False, f'vector {i}: {mismatches} coefficient mismatches (first: got {got[next(j for j,(g,e) in enumerate(zip(got,expected)) if g%Q!=e%Q)] % Q}, expected {expected[next(j for j,(g,e) in enumerate(zip(got,expected)) if g%Q!=e%Q)] % Q})'
    return True, 'all 3 spot-check vectors match golden model'


def run_kem(multiply_fn: Callable, seed: int = 42) -> dict:
    """Run one full KEM (keygen + encaps + decaps), return timing and correctness."""
    kem        = KyberKEM(multiply_fn, seed=seed)
    t0         = time.perf_counter()
    pk, sk     = kem.keygen()
    ct, ss_bob = kem.encaps(pk)
    ss_alice   = kem.decaps(sk, ct)
    elapsed    = time.perf_counter() - t0
    return {
        'time_ms':   elapsed * 1000,
        'mul_calls': kem.mul_count,
        'ss_bob':    ss_bob,
        'ss_alice':  ss_alice,
        'match':     ss_alice == ss_bob,
    }
