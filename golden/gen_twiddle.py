# golden/gen_twiddle.py — Twiddle factor ROM generator
#
# Computes powers of psi (2n-th root of unity) and omega (n-th root of unity)
# for any (n, q) pair. Outputs .mem file for $readmemh in SystemVerilog.
#
# Usage: python gen_twiddle.py [--n 4 --q 17] [--n 256 --q 3329]
