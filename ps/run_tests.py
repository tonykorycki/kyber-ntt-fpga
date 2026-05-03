#!/usr/bin/env python3
# ps/run_tests.py — feed test vectors to ntt_driver and check results

import subprocess
import os
import sys

DRIVER  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ntt_driver')
VECTORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../golden/test_vectors.txt')
N = 256
Q = 3329

def load_vectors(path, max_vectors=3):
    vectors = []
    with open(path, encoding='utf-8', errors='replace') as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    for i in range(0, len(lines) - 2, 3):
        a = list(map(int, lines[i].split()))
        b = list(map(int, lines[i+1].split()))
        c = list(map(int, lines[i+2].split()))
        if len(a) == N and len(b) == N and len(c) == N:
            vectors.append((a, b, c))
        if len(vectors) == max_vectors:
            break
    return vectors

vectors = load_vectors(VECTORS)
if not vectors:
    print('error: no vectors loaded from', VECTORS)
    sys.exit(1)

passed = 0
for idx, (a, b, expected) in enumerate(vectors):
    inp = ' '.join(map(str, a + b))
    r = subprocess.run(['sudo', DRIVER], input=inp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0:
        print(f'vector {idx}: driver error — {r.stderr.strip()}')
        continue
    got = list(map(int, r.stdout.split()))
    latency = r.stderr.strip()
    mismatches = sum(g % Q != e % Q for g, e in zip(got, expected))
    status = 'PASS' if mismatches == 0 else f'FAIL ({mismatches} mismatches)'
    print(f'vector {idx}: {status}  {latency}')
    if mismatches == 0:
        passed += 1

print(f'\n{passed}/{len(vectors)} vectors passed')
sys.exit(0 if passed == len(vectors) else 1)
