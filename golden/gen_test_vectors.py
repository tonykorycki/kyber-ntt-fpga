#!/usr/bin/env python3
"""
golden/gen_test_vectors.py — Generate test vectors for HLS C-sim and SV simulation.

Output: golden/test_vectors.txt
Format per vector (3 lines):
    a        n space-separated coefficients
    b        n space-separated coefficients
    c=a*b    n space-separated coefficients  (negacyclic product mod q)

Usage:
    python golden/gen_test_vectors.py --n 4   --q 17    --vectors 16
    python golden/gen_test_vectors.py --n 128 --q 3329  --vectors 64
"""

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ntt import NTTConfig, ntt_mul, schoolbook_nwc


def generate_vectors(cfg: NTTConfig, n_vectors: int, out_path: str) -> None:
    with open(out_path, 'w') as f:
        f.write(f'# NTT test vectors: n={cfg.d}, q={cfg.q}\n')
        f.write(f'# Format per vector: a, b, c=ntt_mul(a,b) — one polynomial per line\n')
        for i in range(n_vectors):
            a = [random.randint(0, cfg.q - 1) for _ in range(cfg.d)]
            b = [random.randint(0, cfg.q - 1) for _ in range(cfg.d)]
            c = ntt_mul(a, b, cfg)
            assert c == schoolbook_nwc(a, b, cfg), f'vector {i}: ntt_mul != schoolbook_nwc'
            f.write(f'# vector {i}\n')
            f.write(' '.join(map(str, a)) + '\n')
            f.write(' '.join(map(str, b)) + '\n')
            f.write(' '.join(map(str, c)) + '\n')
    print(f'Wrote {n_vectors} vectors to {out_path}  (n={cfg.d}, q={cfg.q})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate NTT test vectors.')
    parser.add_argument('--n',       type=int, default=4,    help='Polynomial degree (default: 4)')
    parser.add_argument('--q',       type=int, default=17,   help='Modulus (default: 17)')
    parser.add_argument('--vectors', type=int, default=16,   help='Number of vectors (default: 16)')
    parser.add_argument('--seed',    type=int, default=42,   help='RNG seed (default: 42)')
    parser.add_argument('--out',     type=str,
                        default=os.path.join(os.path.dirname(__file__), 'test_vectors.txt'),
                        help='Output file path')
    args = parser.parse_args()

    random.seed(args.seed)
    cfg = NTTConfig.from_params(d=args.n, q=args.q)
    generate_vectors(cfg, args.vectors, args.out)
