'''
golden/ntt.py — Python reference implementation for NTT polynomial multiplication

This is the source of truth. All RTL/HLS outputs must match these results.

NTTConfig        dataclass: d, q, psi, omega, and all precomputed inverses/powers
barrett_reduce   (a, b, config) → (a*b) mod q
pre_twist        (a, config) → ã
post_twist       (c_raw, config) → c
bit_reverse      (a) → reordered a    [needed by both ntt_forward and ntt_inverse to bypass splitting manually]
ntt_forward      (ã, config) → A  [Cooley-Tukey]
pointwise_mul    (A, B, config) → C
ntt_inverse      (C, config) → c_raw  [Gentleman-Sande]
ntt_mul          (a, b, config) → c  [full pipeline, calls all above]
schoolbook_nwc   (a, b, config) → c  [naive O(d²), for verification only]
'''

import math
from dataclasses import dataclass
from typing import List
from sympy import primitive_root


@dataclass
class NTTConfig:
    d: int
    q: int
    psi: int
    omega: int
    psi_powers: List[int]
    inv_psi_powers: List[int]
    omega_powers: List[int]
    inv_omega_powers: List[int]
    inv_d: int
    barrett_k: int
    barrett_m: int

    @classmethod
    def from_params(cls, d: int, q: int) -> 'NTTConfig':
        # Compute primitive root and powers
        g = int(primitive_root(q))

        # psi is a primitive 2d-th root of unity: psi = g^((q-1)/2d)
        psi = pow(g, (q - 1) // (2 * d), q)
        assert pow(psi, 2 * d, q) == 1,     "psi is not a 2d-th root of unity"
        assert pow(psi, d, q)     == q - 1, "psi^d must equal -1 mod q"

        # omega = psi^2 is a primitive d-th root of unity
        omega = pow(g, (q - 1) // d, q)
        assert pow(omega, d, q) == 1, "omega is not a d-th root of unity"

        # Precompute powers and inverses
        psi_powers     = [pow(psi,         i, q) for i in range(d)]
        inv_psi        = pow(psi, q - 2, q)   # psi^{-1} via Fermat's little theorem
        inv_psi_powers = [pow(inv_psi,     i, q) for i in range(d)]
        omega_powers   = [pow(omega,       i, q) for i in range(d)]
        inv_omega      = pow(omega, q - 2, q)
        inv_omega_powers = [pow(inv_omega, i, q) for i in range(d)]

        inv_d = pow(d, q - 2, q)   # d^{-1} mod q, used for INTT scaling

        # Barrett reduction parameters (see Section 11 of derivation)
        barrett_k = (q * q).bit_length()
        barrett_m = (1 << (2 * barrett_k)) // q

        return cls(
            d=d, q=q,
            psi=psi, omega=omega,
            psi_powers=psi_powers,
            inv_psi_powers=inv_psi_powers,
            omega_powers=omega_powers,
            inv_omega_powers=inv_omega_powers,
            inv_d=inv_d,
            barrett_k=barrett_k,
            barrett_m=barrett_m,
        )


DEV_CONFIG = NTTConfig.from_params(d=4, q=17)
# KYBER_CONFIG = NTTConfig.from_params(d=256, q=3329) — addressed separately


def barrett_reduce(a: int, b: int, config: NTTConfig) -> int:
    """Return (a * b) mod q using Barrett reduction (eq. 20 of derivation)."""
    q = config.q
    k = config.barrett_k
    m = config.barrett_m

    ab        = a * b
    q_approx  = (ab * m) >> (2 * k)   # approximate quotient floor(ab/q)
    reduced   = ab - q_approx * q     # ab - floor(ab/q)*q, off by at most q

    # Single correction step — fires at most once
    if reduced < 0:
        reduced += q
    elif reduced >= q:
        reduced -= q

    return reduced


def pre_twist(a: List[int], config: NTTConfig) -> List[int]:
    """Return ã where ã[i] = a[i] * psi^i mod q  (eq. 7 / step 15 of derivation)."""
    return [barrett_reduce(a[i], config.psi_powers[i], config) for i in range(config.d)]


def post_twist(a_t: List[int], config: NTTConfig) -> List[int]:
    """Return c where c[i] = ã[i] * psi^{-i} mod q  (eq. 9 / step 19 of derivation)."""
    return [barrett_reduce(a_t[i], config.inv_psi_powers[i], config) for i in range(config.d)]


def bit_reverse(a: List[int], config: NTTConfig) -> List[int]:
    """Permute a by the bit-reversal of each index (Section 5 of derivation).
    Element originally at index j moves to position bitrev(j).
    """
    def brv(x, n):
        return int(''.join(reversed(bin(x)[2:].zfill(n))), 2)

    num_bits = config.d.bit_length() - 1   # log2(d) bits needed
    return [a[brv(i, num_bits)] for i in range(config.d)]


def ntt_forward(a_twisted: List[int], config: NTTConfig) -> List[int]:
    """Forward NTT using Cooley-Tukey butterfly (eq. CT / step 16 of derivation).
    Input:  ã  — pre-twisted coefficient vector
    Output: A  — NTT evaluation form
    """
    d = config.d
    q = config.q
    a = bit_reverse(a_twisted, config)   # bit-reversal permutation before in-place CT

    m = 2           # group size m = 2^s, starts at s=1
    while m <= d:   # log2(d) stages
        m_half = m // 2                      # m/2 — offset to upper butterfly element
        for k in range(0, d, m):             # k: group start indices 0, m, 2m, ...
            for j in range(m_half):          # j: position within lower half of group
                # wm_j = omega_m^j = omega^(j*n/m)
                wm_j = config.omega_powers[j * (d // m)]

                t = barrett_reduce(wm_j, a[k + j + m_half], config)  # t = wm_j * a[k+j+m/2]
                u = a[k + j]
                a[k + j]          = (u + t) % q        # CT eq. (11): a[k+j]     = u + t
                a[k + j + m_half] = (u - t + q) % q   # CT eq. (12): a[k+j+m/2] = u - t
        m *= 2   # next stage

    return a   # now holds A, the NTT of ã


def pointwise_mul(A: List[int], B: List[int], config: NTTConfig) -> List[int]:
    """Return C where C[i] = A[i] * B[i] mod q  (eq. 17 of derivation)."""
    return [barrett_reduce(A[i], B[i], config) for i in range(config.d)]


def ntt_inverse(C: List[int], config: NTTConfig) -> List[int]:
    """Inverse NTT using Gentleman-Sande butterfly (eq. GS / step 18 of derivation).
    Input:  C     — pointwise product in NTT domain
    Output: c_raw — coefficient form before post-twist
    """
    d = config.d
    q = config.q
    a = list(C)   # work on a copy; GS reads natural order, bit-reverses output

    m = d           # group size starts at d, halves each stage
    while m > 1:    # log2(d) stages
        m_half = m // 2                      # m/2 — offset to upper butterfly element
        for k in range(0, d, m):             # k: group start indices
            for j in range(m_half):          # j: position within lower half of group
                # wm_j = omega_m^{-j} = omega^{-(j*n/m)}
                wm_j = config.inv_omega_powers[j * (d//m)]
                t = a[k + j + m_half]
                u = a[k + j]
                a[k + j]          = (u + t) % q                          # GS: a[k+j]     = u + t
                a[k + j + m_half] = barrett_reduce(wm_j, (u - t + q) % q, config)  # GS: a[k+j+m/2] = wm_j * (u - t)
        m //= 2   # next stage

    # GS outputs in bit-reversed order; permute back, then scale by d^{-1}
    a = bit_reverse(a, config)
    return [barrett_reduce(x, config.inv_d, config) for x in a]


def ntt_mul(a: List[int], b: List[int], config: NTTConfig) -> List[int]:
    """Negacyclic polynomial multiplication via NTT (eq. 14 / full pipeline of derivation).
    c = psi^{-•} * INTT( NTT(psi^{•} * a) ⊙ NTT(psi^{•} * b) )
    """
    a_twisted = pre_twist(a, config)
    b_twisted = pre_twist(b, config)

    A = ntt_forward(a_twisted, config)
    B = ntt_forward(b_twisted, config)

    C = pointwise_mul(A, B, config)

    c_twisted = ntt_inverse(C, config)
    c = post_twist(c_twisted, config)

    return c


def schoolbook_nwc(a: List[int], b: List[int], config: NTTConfig) -> List[int]:
    """Negacyclic convolution by schoolbook O(d^2) multiplication.
    Used only to verify ntt_mul produces correct results.
    High-degree terms wrap with a sign flip: x^d = -1  (since modulus is x^d + 1).
    """
    d = config.d
    q = config.q
    tmp = [0] * (2 * d - 1)

    for i in range(d):
        for j in range(d):
            tmp[i + j] = (tmp[i + j] + a[i] * b[j]) % q

    # Reduce mod x^d + 1: terms at index >= d wrap with negation
    for i in range(d, 2 * d - 1):
        tmp[i - d] = (tmp[i - d] - tmp[i]) % q

    return tmp[:d]