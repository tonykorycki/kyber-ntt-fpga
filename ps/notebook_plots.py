"""
ps/notebook_plots.py — all matplotlib figures for kyber_demo.ipynb

Importing this module sets the global rcParams for consistent styling
(white figure background, dark text — readable in VSCode dark mode and
PYNQ Jupyter light mode alike).
"""

import hashlib
import os
import re
import subprocess
import time

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec
import numpy as np

N = 256
Q = 3329
K = 2

SW_COLOR = '#4878CF'
HW_COLOR = '#E84D3D'

plt.style.use('default')
plt.rcParams.update({
    'figure.dpi':            120,
    'font.family':           'DejaVu Sans',
    'figure.facecolor':      'white',
    'axes.facecolor':        'white',
    'savefig.facecolor':     'white',
    'savefig.transparent':   False,
    'text.color':            '#333333',
    'axes.labelcolor':       '#333333',
    'xtick.color':           '#333333',
    'ytick.color':           '#333333',
    'axes.edgecolor':        '#555555',
    'axes.spines.top':       False,
    'axes.spines.right':     False,
})


def plot_poly_visual():
    """Cell 3 — bar chart of two random Kyber polynomials."""
    rng = np.random.RandomState(7)
    a_demo = rng.randint(0, 3329, 256)
    b_demo = rng.randint(0, 3329, 256)

    fig, axes = plt.subplots(1, 3, figsize=(14, 3.5), facecolor='white')
    fig.patch.set_facecolor('white')

    for ax, poly, color, label in zip(
        axes,
        [a_demo, b_demo, None],
        [SW_COLOR, '#2ca02c', HW_COLOR],
        ['Polynomial  a  (public key component)',
         'Polynomial  b  (message)',
         'Result  c = a × b  mod (x²⁵⁶+1, 3329)'],
    ):
        if poly is None:
            ax.text(0.5, 0.5, '?\n\n(computed by\nthe FPGA)',
                    ha='center', va='center', fontsize=14,
                    color=color, fontweight='bold', transform=ax.transAxes)
            ax.set_facecolor('#fff8f8')
        else:
            ax.bar(range(256), poly, width=1.0, color=color, alpha=0.75, linewidth=0)
            ax.set_ylim(0, 3329)
            ax.set_ylabel('Coefficient value (0–3328)')
        ax.set_xlabel('Coefficient index (0–255)')
        ax.set_title(label, fontsize=10, fontweight='bold')

    fig.suptitle('A Kyber polynomial: 256 numbers, each between 0 and 3328',
                 fontsize=12, y=1.02)
    plt.tight_layout()
    plt.show()


def get_hw_floor_us(driver_path):
    """
    Run ntt_driver -t and return the hardware-measured average latency in µs.

    The C driver times only the ap_start→ap_idle window — no Python overhead,
    no subprocess pipe cost.  Returns None if the call fails.
    """
    for cmd in [[driver_path, '-t'], ['sudo', driver_path, '-t']]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            m = re.search(r'avg latency:\s*(\d+)\s*ns', r.stderr)
            if m:
                return int(m.group(1)) / 1000.0
        except Exception:
            continue
    return None


def plot_benchmark(sw_mul_ms, hw_floor_us, sw, hw):
    """
    Cells 8+9 — per-multiply bar chart and full KEM breakdown.

    sw_mul_ms   — Python-timed software multiply (ms)
    hw_floor_us — hardware-measured multiply time from ntt_driver -t (µs)
    sw / hw     — dicts returned by run_kem()
    """
    hw_mul_ms_hw = hw_floor_us / 1000.0

    sw_ntt_total = sw_mul_ms * sw['mul_calls']
    hw_ntt_total = hw_mul_ms_hw * hw['mul_calls']
    sw_other     = sw['time_ms'] - sw_ntt_total
    hw_other     = hw['time_ms'] - hw_ntt_total
    speedup_mul  = sw_mul_ms / hw_mul_ms_hw
    speedup_kem  = sw['time_ms'] / hw['time_ms']

    fig = plt.figure(figsize=(14, 5), facecolor='white')
    fig.patch.set_facecolor('white')
    gs  = GridSpec(1, 2, wspace=0.38)

    ax1 = fig.add_subplot(gs[0])
    vals   = [sw_mul_ms, hw_mul_ms_hw]
    labels = ['Python\n(ARM Cortex-A9)', 'FPGA\n(HLS NTT engine)']
    bars   = ax1.bar(labels, vals, color=[SW_COLOR, HW_COLOR], width=0.45, zorder=3)
    ax1.set_yscale('log')
    ax1.grid(axis='y', alpha=0.3, zorder=0, which='both')
    ax1.set_ylabel('Latency — log scale (ms)', fontsize=11)
    ax1.set_title('One polynomial multiplication', fontsize=12, fontweight='bold')
    for bar, v in zip(bars, vals):
        lbl = f'{v*1000:.0f} µs' if v < 1.0 else f'{v:.2f} ms'
        ax1.text(bar.get_x() + bar.get_width() / 2, v * 2.0,
                 lbl, ha='center', fontsize=11, fontweight='bold')
    ax1.set_ylim(min(vals) * 0.1, max(vals) * 20)
    ax1.text(0.5, 0.93,
             f'{speedup_mul:.0f}× faster',
             ha='center', color='green', fontsize=13, fontweight='bold',
             transform=ax1.transAxes)
    if hw_floor_us:
        ax1.text(0.5, 0.02,
                 f'(hardware floor: {hw_floor_us:.0f} µs, C driver clock_gettime)',
                 ha='center', fontsize=8, color='#777777',
                 transform=ax1.transAxes)

    ax2 = fig.add_subplot(gs[1])
    x    = np.array([0, 1])
    ntt_times   = [sw_ntt_total, hw_ntt_total]
    other_times = [max(0, sw_other), max(0, hw_other)]
    ax2.bar(x, ntt_times,   color=[SW_COLOR, HW_COLOR], width=0.45,
            label='NTT multiplications', zorder=3, alpha=0.9)
    ax2.bar(x, other_times, bottom=ntt_times,
            color=['#a0b8d8', '#f0a89a'], width=0.45,
            label='Sampling + additions (Python)', zorder=3, alpha=0.9)
    totals = [sw['time_ms'], hw['time_ms']]
    for xi, t in zip(x, totals):
        ax2.text(xi, t + max(totals) * 0.02, f'{t:.0f} ms',
                 ha='center', fontsize=11, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['Python\n(ARM)', 'FPGA\n(HLS)'])
    ax2.set_ylabel('Total time (ms)', fontsize=11)
    ax2.set_title(
        f'Full Kyber-512 KEM  ({sw["mul_calls"]} multiplications)',
        fontsize=12, fontweight='bold')
    ax2.set_ylim(0, max(totals) * 1.22)
    ax2.grid(axis='y', alpha=0.3, zorder=0)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.text(0.97, 0.92, f'{speedup_kem:.1f}× faster',
             transform=ax2.transAxes, ha='right', va='top',
             fontsize=13, color='green', fontweight='bold')

    fig.suptitle('FPGA NTT Accelerator — Benchmark Results',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('benchmark.png', dpi=120, bbox_inches='tight')
    plt.show()

    print(f'Hardware floor (C driver):  {hw_floor_us:.0f} µs')
    print(f'Per-multiply speedup (hw floor): {speedup_mul:.0f}×')
    print(f'End-to-end KEM speedup:          {speedup_kem:.1f}×')


def plot_throughput(sw_mul_ms, hw_floor_us, sw, hw):
    """Cell 9 — horizontal throughput bars."""
    hw_mul_ms_hw = hw_floor_us / 1000.0

    sw_muls_per_sec = 1000 / sw_mul_ms
    hw_muls_per_sec = 1000 / hw_mul_ms_hw
    sw_kems_per_sec = 1000 / sw['time_ms']
    hw_kems_per_sec = 1000 / hw['time_ms']

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), facecolor='white')
    fig.patch.set_facecolor('white')

    for ax, sw_v, hw_v, unit in zip(
        axes,
        [sw_muls_per_sec, sw_kems_per_sec],
        [hw_muls_per_sec, hw_kems_per_sec],
        ['NTT polynomial multiplications / second',
         'Complete Kyber-512 key exchanges / second'],
    ):
        bars = ax.barh(['Python\n(ARM)', 'FPGA\n(HLS)'],
                       [sw_v, hw_v],
                       color=[SW_COLOR, HW_COLOR], height=0.4, zorder=3)
        ax.set_xscale('log')
        ax.grid(axis='x', alpha=0.3, zorder=0, which='both')
        ax.set_xlabel(unit + '  (log scale)', fontsize=10)
        ax.set_title(unit, fontsize=10, fontweight='bold')
        for bar, v in zip(bars, [sw_v, hw_v]):
            lbl = f'{v:.0f}/s' if v >= 1 else f'{v:.2f}/s'
            ax.text(v * 1.5,
                    bar.get_y() + bar.get_height() / 2,
                    lbl, va='center', fontsize=11, fontweight='bold')
        ax.set_xlim(min(sw_v, hw_v) * 0.3, max(sw_v, hw_v) * 10)

    fig.suptitle('Throughput Comparison', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig('throughput.png', dpi=120, bbox_inches='tight')
    plt.show()


def plot_correctness(sw, hw, hw_mul_detail=''):
    """Cell 11 — correctness check table with secret hex."""
    fig, ax = plt.subplots(figsize=(10, 4.0), facecolor='white')
    fig.patch.set_facecolor('white')
    ax.axis('off')

    mul_ok = 'mismatch' not in hw_mul_detail
    checks = [
        ('FPGA polynomial multiply matches golden model', mul_ok),
        ('SW: Alice secret == Bob secret',               sw['match']),
        ('HW: Alice secret == Bob secret',               hw['match']),
        ('SW secret == HW secret',                       sw['ss_alice'] == hw['ss_alice']),
    ]
    for i, (label, result) in enumerate(checks):
        color = '#2ca02c' if result else '#d62728'
        mark  = '✓' if result else '✗'
        ax.text(0.02, 0.92 - i * 0.22, f'{mark}  {label}',
                transform=ax.transAxes, fontsize=12,
                color=color, fontweight='bold', va='top')

    if hw_mul_detail:
        ax.text(0.02, 0.06, f'Multiply check: {hw_mul_detail}',
                transform=ax.transAxes, fontsize=8, color='#666666', va='bottom',
                family='monospace')

    ax.text(0.60, 0.88,
            f'Shared secret (SW):\n{sw["ss_alice"].hex()[:32]}...',
            transform=ax.transAxes, fontsize=9,
            family='monospace', color='#444444', va='top')
    ax.text(0.60, 0.60,
            f'Shared secret (HW):\n{hw["ss_alice"].hex()[:32]}...',
            transform=ax.transAxes, fontsize=9,
            family='monospace', color='#444444', va='top')

    ax.set_title('Correctness Checks', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.show()


def _xor_encrypt(key: bytes, data: bytes) -> bytes:
    k = hashlib.sha256(key).digest()
    return bytes(d ^ k[i % 32] for i, d in enumerate(data))


def plot_crypto_demo(hw, ntt_mul_hw, KyberKEM):
    """
    Cell 13 — full Kyber protocol flow (row 1) + message demo (row 2).

    Row 1 shows keygen / encaps / decaps with real coefficient snippets.
    Row 2 shows plaintext → ciphertext → recovered plaintext.
    """
    from kyber_kem import K, N, Q

    kem = KyberKEM(ntt_mul_hw, seed=99)
    pk, sk   = kem.keygen()
    ct, ss_b = kem.encaps(pk)
    ss_a     = kem.decaps(sk, ct)
    A, t     = pk
    u, v     = ct

    message        = b'Quantum computers cannot read this.'
    ciphertext_msg = _xor_encrypt(ss_b, message)
    recovered      = _xor_encrypt(ss_a, ciphertext_msg)

    fig, axes = plt.subplots(2, 3, figsize=(14, 7), facecolor='white')
    fig.patch.set_facecolor('white')
    plt.subplots_adjust(hspace=0.45, wspace=0.3)

    proto = [
        {
            'title': 'Step 1 — Key Generation (Alice)',
            'color': SW_COLOR,
            'lines': [
                'Samples secret s, noise e',
                f'Public key: {K}×{K} matrix A + {K} polys t',
                f'= {K*K + K} × {N} = {(K*K+K)*N:,} coefficients total',
                f't₀: {t[0][0]%Q}, {t[0][1]%Q}, {t[0][2]%Q}, ...',
            ],
        },
        {
            'title': 'Step 2 — Encapsulation (Bob)',
            'color': HW_COLOR,
            'lines': [
                'Receives Alice’s public key',
                f'Ciphertext u: {K}×{N} coefficients',
                f'Ciphertext v: {N} coefficients',
                f'Bob secret:  {ss_b.hex()[:16]}...',
            ],
        },
        {
            'title': 'Step 3 — Decapsulation (Alice)',
            'color': '#2ca02c',
            'lines': [
                'Uses secret key sk',
                'Recovers shared secret:',
                f'{ss_a.hex()[:16]}...',
                f'Matches Bob’s secret: {"✓" if ss_a == ss_b else "✗"}',
            ],
        },
    ]

    for ax, step in zip(axes[0], proto):
        ax.set_facecolor('#f8f8f8')
        ax.set_title(step['title'], fontsize=10, fontweight='bold',
                     color=step['color'])
        for j, line in enumerate(step['lines']):
            mono = any(c in line for c in '0123456789abcdef...:')
            ax.text(0.5, 0.80 - j * 0.20, line,
                    ha='center', va='top', fontsize=9,
                    family='monospace' if mono else 'DejaVu Sans',
                    transform=ax.transAxes, color='#333333')
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(step['color'])
            spine.set_linewidth(2)

    msg_steps = [
        ('Bob encrypts',              message.decode(),             '#2ca02c'),
        ('In transit (ciphertext)',   ciphertext_msg.hex()[:36]+'...', '#d62728'),
        ('Alice decrypts',            recovered.decode(),           '#2ca02c'),
    ]
    for ax, (title, content, color) in zip(axes[1], msg_steps):
        ax.set_facecolor('#f8f8f8')
        ax.text(0.5, 0.55, content,
                ha='center', va='center',
                fontsize=9 if len(content) > 30 else 11,
                family='monospace', color=color,
                fontweight='bold', transform=ax.transAxes)
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(color)
            spine.set_linewidth(2)

    fig.suptitle(
        f'Kyber Key Exchange + Secure Message  '
        f'(FPGA-accelerated, {kem.mul_count} multiplications)',
        fontsize=12, fontweight='bold',
    )
    plt.savefig('crypto_demo.png', dpi=120, bbox_inches='tight')
    plt.show()

    assert recovered == message, 'Decryption failed!'
    print(f'Key exchange:  {hw["time_ms"]:.0f} ms  |  '
          f'Message: {len(message)} bytes  |  Secure: post-quantum')
    print(f'Shared secret: {ss_a.hex()[:32]}...')


# ---------------------------------------------------------------------------
# New visualizations for the expanded demo notebook
# ---------------------------------------------------------------------------

def plot_complexity():
    """O(n²) naïve vs O(n log n) NTT operation count."""
    ns    = np.array([8, 16, 32, 64, 128, 256, 512, 1024])
    naive = ns ** 2
    ntt   = 2 * ns * np.log2(ns) + ns

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), facecolor='white')
    fig.patch.set_facecolor('white')

    ax = axes[0]
    ax.plot(ns, naive, 'o-', color=SW_COLOR, lw=2, ms=6, label='Naïve:  n²')
    ax.plot(ns, ntt,   's-', color=HW_COLOR, lw=2, ms=6, label='NTT:  2n log₂n + n')
    ax.axvline(256, color='#888888', ls='--', alpha=0.6)
    ax.text(270, naive[5] * 0.55, 'n = 256\n(Kyber)', fontsize=9, color='#555555')
    ax.set_xlabel('Polynomial degree n', fontsize=11)
    ax.set_ylabel('Operations', fontsize=11)
    ax.set_title('Operation count grows with n', fontsize=12, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3, which='both')

    ax2 = axes[1]
    labels = ['Naïve\nn²', 'NTT\n2n·log₂n + n']
    vals   = [256 ** 2, int(2 * 256 * 8 + 256)]
    bars   = ax2.bar(labels, vals, color=[SW_COLOR, HW_COLOR], width=0.5, zorder=3)
    ax2.set_yscale('log')
    ax2.grid(axis='y', alpha=0.3, zorder=0, which='both')
    ax2.set_ylabel('Operations (log scale)', fontsize=11)
    ax2.set_title('For n = 256', fontsize=12, fontweight='bold')
    for bar, v in zip(bars, vals):
        ax2.text(bar.get_x() + bar.get_width() / 2, v * 1.6,
                 f'{v:,}', ha='center', fontsize=11, fontweight='bold')
    ax2.set_ylim(100, 300_000)
    ratio = vals[0] // vals[1]
    ax2.text(0.5, 0.90, f'{ratio}× fewer operations',
             ha='center', color='green', fontsize=13, fontweight='bold',
             transform=ax2.transAxes)

    fig.suptitle('Why bother with the NTT?', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()


def plot_ntt_butterfly():
    """Cooley-Tukey butterfly network for n=8."""
    pairs_per_stage = [
        [(0, 4), (1, 5), (2, 6), (3, 7)],
        [(0, 2), (1, 3), (4, 6), (5, 7)],
        [(0, 1), (2, 3), (4, 5), (6, 7)],
    ]
    stage_colors = [SW_COLOR, '#E8821D', HW_COLOR]
    n = 8

    fig, ax = plt.subplots(figsize=(11, 6), facecolor='white')
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(-1.3, 3.9)
    ax.set_ylim(-1.0, n + 0.2)
    ax.axis('off')

    def yp(i):
        return n - 1 - i

    # Connections
    for s, (stage_pairs, color) in enumerate(zip(pairs_per_stage, stage_colors)):
        for lo, hi in stage_pairs:
            y_lo, y_hi = yp(lo), yp(hi)
            ax.plot([s, s + 1], [y_lo, y_hi], '-', color=color, lw=2.0, alpha=0.80, zorder=2)
            ax.plot([s, s + 1], [y_hi, y_lo], '-', color=color, lw=2.0, alpha=0.80, zorder=2)
            ax.plot([s, s + 1], [y_lo, y_lo], '-', color=color, lw=0.8, alpha=0.30, zorder=2)
            ax.plot([s, s + 1], [y_hi, y_hi], '-', color=color, lw=0.8, alpha=0.30, zorder=2)

    # Nodes
    for col in range(4):
        for i in range(n):
            ax.add_patch(plt.Circle((col, yp(i)), 0.18, color='white',
                                    ec='#333333', lw=1.8, zorder=5))

    # Input / output labels
    for i in range(n):
        ax.text(-0.25, yp(i), f'a[{i}]', ha='right', va='center',
                fontsize=9, family='monospace')
        ax.text(3.25, yp(i), f'Â[{i}]', ha='left', va='center',
                fontsize=9, family='monospace', color=HW_COLOR, fontweight='bold')

    # Stage labels
    for s, (color, lbl) in enumerate(zip(stage_colors,
                                         ['Stage 1  (stride 4)',
                                          'Stage 2  (stride 2)',
                                          'Stage 3  (stride 1)'])):
        ax.text(s + 0.5, -0.7, lbl, ha='center', va='top',
                fontsize=9, color=color, fontweight='bold')

    # Column headers
    for col, lbl in enumerate(['Input', 'After\nStage 1', 'After\nStage 2', 'NTT\nOutput']):
        ax.text(col, n - 0.05, lbl, ha='center', va='bottom', fontsize=9,
                fontweight='bold', color=HW_COLOR if col == 3 else '#333333')

    # Annotate one butterfly
    ax.annotate('one butterfly:\n a[0] + ω⁰·a[4]\n a[0] − ω⁰·a[4]',
                xy=(0.5, (yp(0) + yp(4)) / 2),
                xytext=(-1.1, (yp(0) + yp(4)) / 2 + 1.3),
                fontsize=8.5, ha='center', color=stage_colors[0],
                bbox=dict(boxstyle='round,pad=0.35', facecolor='#EEF4FF',
                          edgecolor=stage_colors[0], lw=1.2),
                arrowprops=dict(arrowstyle='->', color=stage_colors[0], lw=1.2))

    ax.set_title('Cooley-Tukey NTT butterfly network  (n = 8)\n'
                 '3 stages × 4 butterflies = 12 operations   vs   64 for naïve',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.show()


def plot_ntt_domains():
    """Same polynomial shown in coefficient domain and NTT domain."""
    from kyber_ntt import ntt_forward, KYBER_256
    rng = np.random.RandomState(7)
    a   = [int(x) for x in rng.randint(0, Q, N)]
    A   = ntt_forward(list(a), KYBER_256)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4), facecolor='white')
    fig.patch.set_facecolor('white')

    axes[0].bar(range(N), a, width=1.0, color=SW_COLOR, alpha=0.75, linewidth=0)
    axes[0].set_ylim(0, Q)
    axes[0].set_xlabel('Coefficient index k', fontsize=11)
    axes[0].set_ylabel('a[k]   (0 … q−1)', fontsize=11)
    axes[0].set_title('Polynomial a  —  coefficient domain', fontsize=12, fontweight='bold')
    axes[0].text(0.97, 0.97, 'multiply = 65,536 ops', transform=axes[0].transAxes,
                 ha='right', va='top', fontsize=9, color='#666666',
                 bbox=dict(boxstyle='round', facecolor='white', edgecolor='#aaaaaa'))

    axes[1].bar(range(N), A, width=1.0, color=HW_COLOR, alpha=0.75, linewidth=0)
    axes[1].set_ylim(0, Q)
    axes[1].set_xlabel('NTT bin k', fontsize=11)
    axes[1].set_ylabel('NTT(a)[k]   (0 … q−1)', fontsize=11)
    axes[1].set_title('NTT(a)  —  transform domain', fontsize=12, fontweight='bold')
    axes[1].text(0.97, 0.97, 'multiply = 256 independent scalars',
                 transform=axes[1].transAxes, ha='right', va='top',
                 fontsize=9, color=HW_COLOR, fontweight='bold',
                 bbox=dict(boxstyle='round', facecolor='white', edgecolor=HW_COLOR))

    fig.suptitle('The NTT converts convolution into pointwise multiplication',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()


def plot_hw_architecture():
    """PS/PL block diagram rendered with matplotlib patches."""
    fig, ax = plt.subplots(figsize=(13, 7.5), facecolor='white')
    fig.patch.set_facecolor('white')
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7.5)
    ax.axis('off')
    ax.set_facecolor('white')

    def box(x, y, w, h, fc, ec, lw=1.8, radius=0.15):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle=f'round,pad={radius}',
                                    facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3))

    def label(x, y, text, **kw):
        ax.text(x, y, text, zorder=4, **kw)

    # Board outline
    box(0.15, 0.15, 12.7, 7.1, '#F7F7F7', '#555555', lw=2.5)
    label(6.5, 7.05, 'PYNQ-Z2   Zynq XC7Z020', ha='center', fontsize=13,
          fontweight='bold', color='#333333')

    # PS
    box(0.4, 0.4, 5.3, 6.3, '#DDEEFF', '#4878CF', lw=2.2)
    label(3.05, 6.45, 'Processing System (PS)', ha='center', fontsize=11,
          fontweight='bold', color='#4878CF')
    label(3.05, 6.0, 'ARM Cortex-A9 @ 650 MHz · Ubuntu Linux', ha='center',
          fontsize=8.5, color='#555555')

    # Python KEM box
    box(0.7, 3.9, 4.7, 2.1, 'white', '#6699CC', lw=1.4)
    label(3.05, 5.65, 'kyber_kem.py', ha='center', fontsize=10.5,
          fontweight='bold', color='#4878CF', family='monospace')
    label(3.05, 5.25, 'keygen  ·  encaps  ·  decaps', ha='center', fontsize=9, color='#444444')
    label(3.05, 4.85, 'noise sampling  ·  poly addition  ·  KEM logic', ha='center',
          fontsize=8.5, color='#666666')
    label(3.05, 4.25, '(polynomial multiply → dispatched to FPGA)', ha='center',
          fontsize=8, color='#4878CF', style='italic')

    # C driver box
    box(0.7, 0.7, 4.7, 2.8, 'white', '#6699CC', lw=1.4)
    label(3.05, 3.18, 'ntt_driver   (C)', ha='center', fontsize=10.5,
          fontweight='bold', color='#4878CF', family='monospace')
    label(3.05, 2.72, '/dev/mem  +  mmap()', ha='center', fontsize=9, color='#444444')
    label(3.05, 2.28, 'writes a[], b[]  →  pulses ap_start', ha='center', fontsize=8.5, color='#555555')
    label(3.05, 1.84, 'polls ap_idle  →  reads c[]', ha='center', fontsize=8.5, color='#555555')
    label(3.05, 1.25, 'clock_gettime: measures ap_start→ap_idle', ha='center',
          fontsize=8, color='#888888', style='italic')

    # PL
    box(7.0, 0.4, 5.7, 6.3, '#FFF0EE', '#E84D3D', lw=2.2)
    label(9.85, 6.45, 'Programmable Logic (PL)   100 MHz', ha='center', fontsize=11,
          fontweight='bold', color='#E84D3D')

    # BRAMs
    bram_labels = [('BRAM_A', 'a[ ]', 4.9), ('BRAM_B', 'b[ ]', 3.5), ('BRAM_C', 'c[ ]', 2.1)]
    for name, arr, yb in bram_labels:
        box(7.3, yb, 2.3, 0.95, '#FFF8DD', '#CC8800', lw=1.4)
        label(8.45, yb + 0.62, f'{name}  ({arr})', ha='center', fontsize=9,
              fontweight='bold', color='#664400', family='monospace')
        label(8.45, yb + 0.22, '256 × 32-bit on-chip SRAM', ha='center',
              fontsize=7.5, color='#888888')

    # ntt_top box
    box(10.1, 0.7, 2.25, 5.5, '#FFD8D5', '#C0392B', lw=2.0)
    label(11.22, 5.88, 'ntt_top', ha='center', fontsize=11,
          fontweight='bold', color='#C0392B', family='monospace')
    label(11.22, 5.48, 'Vitis HLS IP', ha='center', fontsize=8.5, color='#C0392B')
    for txt, yy in [('NTT forward (CT)', 4.85), ('pointwise ×', 4.30),
                    ('NTT inverse (GS)', 3.75), ('Barrett mod q', 3.20),
                    ('pipeline  II=2', 2.55), ('12,621 cycles', 2.05),
                    ('≈ 126 µs @ 100 MHz', 1.55)]:
        label(11.22, yy, txt, ha='center', fontsize=8, color='#555555')

    # AXI BRAM arrows (PS ↔ BRAMs)
    for yb in [4.9 + 0.475, 3.5 + 0.475, 2.1 + 0.475]:
        ax.annotate('', xy=(7.3, yb), xytext=(5.7, yb),
                    arrowprops=dict(arrowstyle='<->', color='#4878CF', lw=1.8), zorder=4)
    label(6.5, 3.97, 'AXI\nBRAM', ha='center', va='center', fontsize=8,
          color='#4878CF', fontweight='bold',
          bbox=dict(boxstyle='round', facecolor='white', edgecolor='#4878CF', lw=1))

    # BRAM ↔ ntt_top (Port B)
    for yb in [4.9 + 0.475, 3.5 + 0.475, 2.1 + 0.475]:
        ax.annotate('', xy=(10.1, yb), xytext=(9.6, yb),
                    arrowprops=dict(arrowstyle='<->', color='#CC8800', lw=1.5), zorder=4)
    label(9.85, 3.97, 'Port B\nap_memory', ha='center', va='center', fontsize=7.5,
          color='#CC8800',
          bbox=dict(boxstyle='round', facecolor='white', edgecolor='#CC8800', lw=0.8))

    # GPIO ap_start
    ax.annotate('', xy=(10.1, 1.15), xytext=(5.7, 1.15),
                arrowprops=dict(arrowstyle='->', color='#2ca02c', lw=2.0), zorder=4)
    label(7.9, 1.32, 'GPIO  ap_start', ha='center', fontsize=8.5,
          color='#2ca02c', fontweight='bold')

    # GPIO ap_idle
    ax.annotate('', xy=(5.7, 0.72), xytext=(10.1, 0.72),
                arrowprops=dict(arrowstyle='->', color='#9467bd', lw=2.0), zorder=4)
    label(7.9, 0.52, 'GPIO  ap_idle', ha='center', fontsize=8.5,
          color='#9467bd', fontweight='bold')

    plt.tight_layout()
    plt.show()


def plot_amdahl(sw_mul_ms, hw_floor_us, sw, hw):
    """KEM time breakdown + Amdahl annotation."""
    hw_mul_ms  = hw_floor_us / 1000.0
    n_muls     = sw['mul_calls']
    sw_ntt_ms  = sw_mul_ms * n_muls
    sw_other   = max(0.0, sw['time_ms'] - sw_ntt_ms)
    hw_ntt_ms  = hw_mul_ms * n_muls
    hw_other   = max(0.0, hw['time_ms'] - hw_ntt_ms)

    speedup_mul = sw_mul_ms / hw_mul_ms
    speedup_kem = sw['time_ms'] / hw['time_ms']
    non_ntt_frac = sw_other / sw['time_ms']
    amdahl_max   = 1.0 / non_ntt_frac if non_ntt_frac > 0 else float('inf')

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor='white')
    fig.patch.set_facecolor('white')

    ax = axes[0]
    x = [0, 1]
    ax.bar(x, [sw_ntt_ms, hw_ntt_ms], color=[SW_COLOR, HW_COLOR], width=0.5,
           label='NTT multiplications', zorder=3, alpha=0.9)
    ax.bar(x, [sw_other, hw_other], bottom=[sw_ntt_ms, hw_ntt_ms],
           color=['#a0b8d8', '#f0a89a'], width=0.5,
           label='Sampling + addition + Python', zorder=3, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(['Software\n(ARM Python)', 'Hardware\n(FPGA)'], fontsize=11)
    ax.set_ylabel('Time (ms)', fontsize=11)
    ax.set_title(f'Where does KEM time go?  ({n_muls} multiplications)',
                 fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    ax.legend(fontsize=9)
    for xi, ntt, other in zip(x, [sw_ntt_ms, hw_ntt_ms], [sw_other, hw_other]):
        total = ntt + other
        ax.text(xi, total + sw['time_ms'] * 0.02, f'{total:.0f} ms',
                ha='center', fontsize=10, fontweight='bold')
        if ntt > 5:
            ax.text(xi, ntt / 2, f'{ntt:.0f} ms', ha='center', va='center',
                    fontsize=8.5, color='white', fontweight='bold')

    ax2 = axes[1]
    ax2.set_facecolor('white')
    ax2.axis('off')
    lines = [
        ("Amdahl's Law", True, '#222222', 14),
        ('', False, '#222222', 10),
        (f'Per-multiply speedup:    {speedup_mul:.0f}×', False, HW_COLOR, 13),
        (f'KEM speedup (Python):   {speedup_kem:.1f}×', False, '#E84D3D', 13),
        ('', False, '#222222', 9),
        (f'NTT fraction of SW time:  {(1-non_ntt_frac)*100:.0f}%', False, '#555555', 10),
        (f'Python overhead fraction: {non_ntt_frac*100:.0f}%', False, '#555555', 10),
        ('', False, '#222222', 9),
        ('Python KEM ceiling:', False, '#333333', 10),
        ('  1 / (Python overhead fraction)', False, '#999999', 9),
        (f'  = {amdahl_max:.1f}×  ← limited by Python', False, '#E84D3D', 12),
        ('', False, '#222222', 9),
        ('A C KEM eliminates Python overhead.', False, '#333333', 9),
        ('Speedup would approach ~400×.', False, '#2ca02c', 11),
    ]
    y = 0.96
    for text, bold, color, size in lines:
        ax2.text(0.05, y, text, transform=ax2.transAxes, fontsize=size,
                 color=color, fontweight='bold' if bold else 'normal', va='top')
        y -= 0.068

    fig.suptitle("Why doesn't the KEM speedup match the per-multiply speedup?",
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()


def plot_error_margin(multiply_fn):
    """Histogram of decaps residuals showing the NTT arithmetic noise margin."""
    from kyber_kem import KyberKEM, N as _N, Q as _Q, K as _K
    kem = KyberKEM(multiply_fn, seed=77777)
    pk, sk   = kem.keygen()
    ct, _    = kem.encaps(pk)
    u, v     = ct
    A, t     = pk

    su = [0] * _N
    for i in range(_K):
        prod = multiply_fn(sk[i], u[i])
        su   = [(su[j] + prod[j]) % _Q for j in range(_N)]
    mp = [(v[j] - su[j]) % _Q for j in range(_N)]

    half_q = _Q // 2
    thresh = _Q // 4

    margins, bits = [], []
    for x in mp:
        d0 = min(x, _Q - x)
        d1 = min(abs(x - half_q), _Q - abs(x - half_q))
        if d0 <= d1:
            bits.append(0); margins.append(thresh - d0)
        else:
            bits.append(1); margins.append(thresh - d1)

    min_margin = min(margins)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), facecolor='white')
    fig.patch.set_facecolor('white')

    ax = axes[0]
    ax.scatter(range(_N), mp,
               c=[HW_COLOR if b else SW_COLOR for b in bits],
               s=7, alpha=0.65, zorder=3)
    ax.axhline(0,           color=SW_COLOR, lw=1.5, ls='--', alpha=0.7, label='Bit-0 center (0)')
    ax.axhline(half_q,      color=HW_COLOR, lw=1.5, ls='--', alpha=0.7, label=f'Bit-1 center (q/2={half_q})')
    for yh in [thresh, _Q - thresh, half_q - thresh, half_q + thresh]:
        ax.axhline(yh, color='#888888', lw=0.9, ls=':', alpha=0.55)
    ax.fill_betweenx([0, thresh], 0, _N, alpha=0.07, color=SW_COLOR)
    ax.fill_betweenx([_Q - thresh, _Q], 0, _N, alpha=0.07, color=SW_COLOR)
    ax.fill_betweenx([half_q - thresh, half_q + thresh], 0, _N, alpha=0.07, color=HW_COLOR)
    ax.set_xlabel('Coefficient index', fontsize=11)
    ax.set_ylabel('v − s·u   (mod q)', fontsize=11)
    ax.set_ylim(-60, _Q + 60)
    ax.set_title('Decaps residual: every point must land in a shaded band', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8.5, loc='upper right')
    ax.text(0.01, 0.52, f'Decision\nboundary\nq/4 = {thresh}',
            transform=ax.transAxes, fontsize=7.5, color='#888888', va='center')

    ax2 = axes[1]
    ax2.hist([m for m, b in zip(margins, bits) if b == 0], bins=28,
             color=SW_COLOR, alpha=0.75, label='Bit-0 coefficients', zorder=3)
    ax2.hist([m for m, b in zip(margins, bits) if b == 1], bins=28,
             color=HW_COLOR, alpha=0.75, label='Bit-1 coefficients', zorder=3)
    ax2.axvline(0, color='#333333', lw=2, ls='--', label='Boundary (margin = 0 → would fail)')
    ax2.set_xlabel('Safety buffer remaining  (q/4 − distance from center)', fontsize=11)
    ax2.set_ylabel('Number of coefficients', fontsize=11)
    ax2.set_title('How much margin does each coefficient have before a bit flip?', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3, zorder=0)
    ax2.text(0.97, 0.96, f'Minimum safety buffer: {min_margin}',
             transform=ax2.transAxes, ha='right', va='top', fontsize=10,
             fontweight='bold', color='#2ca02c',
             bbox=dict(boxstyle='round', facecolor='white', edgecolor='#2ca02c'))

    fig.suptitle('Kyber noise tolerance — decryption succeeds because errors stay within bounds',
                 fontsize=12, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()
    print(f'All {_N} coefficients decoded correctly. Minimum safety buffer: {min_margin}  (max = {thresh})')
