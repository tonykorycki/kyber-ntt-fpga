# Initial Plan: NTT-Based Polynomial Multiplication Accelerator for Post-Quantum Cryptography

**Author:** Tony Korycki
**Repository:** `kyber-ntt-fpga`  
**Target Platform:** PYNQ-Z2 (Zynq-7000 SoC)  
**Design Flow:** Vitis HLS (datapath) + SystemVerilog (control/interface)

---

## 1. IP Definition

### What the IP Does

This project implements a hardware accelerator for **negacyclic polynomial multiplication** in the ring Z_q[x]/(x^n + 1), the core arithmetic primitive of the CRYSTALS-Kyber post-quantum key encapsulation mechanism (NIST PQC Standard, 2024).

Classical public-key cryptography (RSA, ECDH) is vulnerable to quantum computers via Shor's algorithm. Kyber is a lattice-based scheme believed to be quantum-resistant, and is now standardized as ML-KEM (FIPS 203). Its performance bottleneck is repeated polynomial multiplication in the ring Z_3329[x]/(x^256 + 1). A single Kyber key exchange requires on the order of 20–30 such multiplications; each is O(n^2) naively but O(n log n) via the Number Theoretic Transform (NTT).

The IP accelerates this bottleneck using a pipelined NTT-based multiply on the FPGA fabric, offloading the computation from the ARM processor. The PS runs the rest of the Kyber protocol in software; it calls the IP for every polynomial multiplication and receives the result back via shared memory.

The initial implementation targets small, simulation-friendly parameters (n=4, q=17) to enable rapid development and verification. The architecture is parameterized so that it can be scaled to full Kyber parameters (n=256, q=3329) in a subsequent phase.

### How It Interacts with the PS

```
PS (ARM Cortex-A9)                     PL (FPGA Fabric)
─────────────────                      ────────────────
Write a[0..n-1] → shared memory  ──►  
Write b[0..n-1] → shared memory  ──►  
Send START command via AXI-Lite  ──►   NTT-Mul IP
                                        ├── forward NTT on a
Wait for DONE interrupt          ◄──    ├── forward NTT on b
Read c[0..n-1] ← shared memory  ◄──    ├── pointwise multiply mod q
                                        └── inverse NTT → c
```

**Data transferred:**
- Input: two coefficient vectors a[0..n-1] and b[0..n-1], each coefficient a 12-bit unsigned integer (fits q=3329 < 2^12)
- Output: one coefficient vector c[0..n-1], same format
- Control: a start signal and a done/status register, exposed via AXI-Lite

**Interface:**
- AXI-Lite slave: control/status registers (START, DONE, n, q configuration)
- AXI4 master or shared BRAM: bulk data transfer of coefficient arrays

### Mathematical Operations

The algorithm computes c(x) = a(x) · b(x) mod (x^n + 1) mod q using the negacyclic NTT:

**Forward negacyclic NTT:**

```
for i in range(n):
    a_tilde[i] = a[i] * psi^i  mod q        # pre-multiply (negacyclic twist)

A = NTT(a_tilde)                             # standard cyclic NTT with omega = psi^2
```

**NTT butterfly (Cooley-Tukey, log2(n) stages):**

```
for each stage s in 0 .. log2(n)-1:
    half = n >> (s+1)
    for each group:
        for each butterfly (j, j+half):
            t         = twiddle[k] * x[j + half]  mod q
            x[j+half] = x[j] - t                  mod q
            x[j]      = x[j] + t                  mod q
```

where twiddle factors are precomputed powers of omega stored in a ROM.

**Pointwise multiply:**

```
for i in range(n):
    C[i] = A[i] * B[i]  mod q
```

**Inverse NTT + post-scale:**

```
c_raw = INTT(C)                              # same butterfly with omega^-1, scaled by n^-1
for i in range(n):
    c[i] = c_raw[i] * psi_inv^i  mod q      # post-multiply (undo twist)
```

The key hardware operation in every step is **modular multiplication mod q**. For small q (12-bit), this is a multiply followed by a Barrett or Montgomery reduction. Twiddle factor tables (powers of psi and omega) are precomputed and stored in on-chip ROM.

---

## 2. IP Architecture

### Major Sub-Modules

The IP is decomposed into four sub-modules, reflecting the four algorithmic phases:

```
┌─────────────────────────────────────────────────────┐
│                  NTT-Mul IP Core                    │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌─────────────────┐ │
│  │  Pre/Post│   │  NTT     │   │  Pointwise      │ │
│  │  Twist   │──►│  Engine  │──►│  Multiplier     │ │
│  │  Unit    │   │ (HLS)    │   │                 │ │
│  └──────────┘   └──────────┘   └─────────────────┘ │
│       ▲               │                │            │
│       │         ┌─────▼──────┐         │            │
│       │         │  Twiddle   │         │            │
│       │         │  ROM       │         │            │
│       │         └────────────┘         │            │
│  ┌────┴─────────────────────────────────────────┐  │
│  │           AXI-Lite Control / FSM (SV)        │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

#### 1. AXI-Lite Control FSM (SystemVerilog)
Handles the PS interface: exposes control/status registers, sequences the pipeline stages (IDLE → PRE_TWIST → NTT_A → NTT_B → POINTWISE → INTT → POST_TWIST → DONE), and drives start/done handshaking. Written in SystemVerilog for precise timing control and clean integration with Vivado block design.

#### 2. Pre/Post Twist Unit (HLS or SV)
Implements the negacyclic pre-multiplication (a[i] · ψⁱ mod q before NTT) and post-multiplication (c[i] · ψ⁻ⁱ mod q after INTT). These are n independent modular multiplications — trivially parallelizable. The twiddle powers ψⁱ are loaded from the same ROM as the NTT twiddles.

#### 3. NTT Engine (Vitis HLS, C++)
The core butterfly pipeline. Implements the Cooley-Tukey radix-2 DIT NTT across log2(n) stages. Written in HLS to explore loop unrolling and pipelining directives (`#pragma HLS PIPELINE`, `#pragma HLS UNROLL`) without hand-crafting the datapath. The same module is used for both the forward NTT and the inverse INTT (controlled by a flag that selects omega vs omega^-1 and enables the n^-1 scaling).

This is where the HLS/RTL mix is motivated: the butterfly loop structure maps naturally to HLS pragmas, while the control sequencing and AXI interface are cleaner in SystemVerilog.

#### 4. Twiddle Factor ROM (SV)
A precomputed read-only memory containing powers of ψ (for pre/post twist) and ω (for the NTT butterfly), along with their inverses. Generated by a Python script at elaboration time for arbitrary n and q. For n=256, q=3329, this is 512 entries × 12 bits = ~768 bytes, comfortably fitting in a single BRAM tile.

#### 5. Modular Multiplier (HLS, instantiated by NTT Engine)
A standalone modular multiply-reduce unit: given a, b, q, computes (a·b) mod q using Barrett reduction. Factored out as a separate HLS function so it can be independently tested and reused across all four phases.

### Sub-Module Communication

Data flows through a ping-pong BRAM scheme:

```
Shared BRAM A  ──►  Pre-Twist  ──►  NTT Engine  ──►  Shared BRAM B
                                                            │
Shared BRAM B  ──►  NTT Engine (b)  ─────────────────►    │
                                                            ▼
                                                    Pointwise Multiply
                                                            │
                                                            ▼
                                                    Shared BRAM C  ──►  INTT  ──►  Post-Twist  ──►  Output BRAM
```

All inter-module data passes through on-chip BRAMs rather than streaming interfaces, keeping the design simple and debuggable. The FSM controls which BRAM ports are active at each stage. AXI4 or BRAM controller handles PS-side DMA into/out of the shared BRAMs.

### Why This Modularization

Each sub-module has a single, independently testable function:

- The **modular multiplier** can be verified against Python's `(a * b) % q` with exhaustive test vectors.
- The **NTT engine** can be verified against a Python reference NTT on random inputs before integration.
- The **pre/post twist** can be verified as a simple element-wise multiply against Python.
- The **full pipeline** is verified end-to-end by comparing c = NTT_Mul(a, b) against Python's schoolbook negacyclic multiply.

This structure also maps cleanly to the incremental development plan: each module is a milestone that gates the next, so partial progress always yields a working, tested component.

### Parameterization

Key parameters are defined as HLS/SV constants:

| Parameter | Small (dev) | Full Kyber |
|-----------|------------|------------|
| n         | 4          | 256        |
| q         | 17         | 3329       |
| COEF_WIDTH| 5 bits     | 12 bits    |
| LOG2_N    | 2          | 8          |

Switching from dev to full parameters requires only regenerating the twiddle ROM and changing these constants — the architecture is otherwise identical.

---

## Stretch Goal: Kyber Wrapper

Once the NTT multiplication IP is verified, the PS-side Python code will be extended to implement the full Kyber key encapsulation protocol (key generation, encapsulation, decapsulation), calling the hardware IP for every polynomial multiply. This demonstrates end-to-end post-quantum key exchange with hardware-accelerated inner loops, and allows a direct software-only vs hardware-accelerated latency comparison.
