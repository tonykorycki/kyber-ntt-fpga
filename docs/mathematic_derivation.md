# NTT-Based Negacyclic Polynomial Multiplication - Mathematical Derivation

**Author:** Tony Korycki  
**Project:** `kyber-ntt-fpga` — NTT polynomial multiplication accelerator for CRYSTALS-Kyber / ML-KEM  
**Target ring:** $\mathbb{Z}_q[x]\,/\,(x^n + 1)$

---

## 1. Problem Statement

We wish to multiply two polynomials $a, b$ in the ring

```math
R = \mathbb{Z}_q[x]\,/\,(x^n + 1)
```

computing $c = a \cdot b \in R$ with coefficients reduced mod $q$. Naïve schoolbook multiplication costs $O(n^2)$ coefficient multiplications. The NTT-based approach reduces this to $O(n \log n)$ by working in the *evaluation domain*.

---

## 2. Foundations

### 2.1 The NTT as polynomial evaluation

The $n$-point **Number Theoretic Transform** of a vector $\mathbf{a} = (a_0, \ldots, a_{n-1}) \in \mathbb{Z}_q^n$ is

```math
\hat{a}_k = \sum_{j=0}^{n-1} a_j \, \omega^{jk} \bmod q, \qquad k = 0, \ldots, n-1
```
(1)

where $\omega \in \mathbb{Z}_q$ is a **primitive $n$-th root of unity**. This is identical in structure to the DFT, with $\mathbb{C}$ replaced by $\mathbb{Z}_q$. Interpreting $\mathbf{a}$ as the coefficient vector of a polynomial $a(x) = \sum_j a_j x^j$, equation (1) says $\hat{a}_k = a(\omega^k)$: the NTT evaluates $a$ at the $n$ distinct points $\omega^0, \omega^1, \ldots, \omega^{n-1}$.

### 2.2 Existence conditions

A primitive $n$-th root of unity $\omega$ exists in $\mathbb{Z}_q$ if and only if

```math
q \text{ is prime}, \qquad n \mid (q - 1).
```

The second condition follows from Fermat's little theorem: the multiplicative group $\mathbb{Z}_q^*$ has order $q - 1$, so $n$-th roots of unity exist iff $n \mid (q-1)$. Given any primitive root $g$ of $\mathbb{Z}_q^*$:

```math
\omega = g^{(q-1)/n} \bmod q.
```

### 2.3 Key properties of $\omega$

The following properties are used throughout:

```math
\omega^n \equiv 1 \pmod{q}
```

```math
\omega^{n/2} \equiv -1 \pmod{q}
```
(3)

```math
\sum_{j=0}^{n-1} \omega^{jk} \equiv \begin{cases} n & k \equiv 0 \pmod{n} \\ 0 & \text{otherwise} \end{cases} \pmod{q}
```
(4)

*Proof of (3).* Since $(\omega^{n/2})^2 = \omega^n = 1$, $\omega^{n/2}$ is a square root of $1$ mod $q$. The only square roots of $1$ mod a prime are $\pm 1$. As $\omega^{n/2} \neq 1$ by primitivity, it must equal $-1$.

*Proof of (4).* For $k \equiv 0 \pmod{n}$, every term is $1$, giving $n$. For $k \not\equiv 0$, the sum is a geometric series with ratio $\omega^k \neq 1$, giving $(\omega^{kn} - 1)/(\omega^k - 1) = 0$.

### 2.4 Inverse NTT

Applying the orthogonality relation (4), the inverse transformation is

```math
a_j = n^{-1} \sum_{k=0}^{n-1} \hat{a}_k \, \omega^{-jk} \bmod q
```

where $n^{-1}$ is the modular inverse of $n$ mod $q$. The INTT is structurally identical to the NTT — same butterfly network — with $\omega$ replaced by $\omega^{-1}$ and a final scaling by $n^{-1}$.

---

## 3. The Twist: Cyclic to Negacyclic

### 3.1 What the plain NTT computes

Equation (1) diagonalises **cyclic convolution** in $\mathbb{Z}_q[x]/(x^n - 1)$:

```math
c_k = \sum_{i+j \equiv k \pmod{n}} a_i b_j \bmod q.
```

High-degree terms wrap positively ($x^n \to 1$). This is the wrong ring for Kyber.

### 3.2 Negacyclic convolution

In $\mathbb{Z}_q[x]/(x^n + 1)$, high-degree terms wrap with a sign flip ($x^n \to -1$):

```math
(a \cdot b)_k = \sum_{i+j \equiv k \pmod{n}} a_i b_j - \sum_{i+j \equiv k+n \pmod{2n}} a_i b_j \bmod q.
```
(7)

### 3.3 The negacyclic twist

Let $\psi$ be a **primitive $2n$-th root of unity** mod $q$, so $\psi^{2n} \equiv 1$ and $\psi^2 = \omega$. Since $\psi$ is a $2n$-th root of unity, $\psi^n \equiv -1 \pmod{q}$ (by the same argument as property (3)).

Define the twisted vectors:

```math
\tilde{a}_j = \psi^j \, a_j \bmod q, \qquad \tilde{b}_j = \psi^j \, b_j \bmod q.
```

**Claim:** the cyclic convolution of $\tilde{\mathbf{a}}$ and $\tilde{\mathbf{b}}$ satisfies

```math
(\tilde{a} \star \tilde{b})_k = \psi^k \, (a \cdot b)_k
```
(8)

where $a \cdot b$ is the negacyclic product in $R$ and $\star$ denotes cyclic convolution.

*Proof.* Compute directly:

```math
(\tilde{a} \star \tilde{b})_k = \sum_{i+j \equiv k \pmod{n}} \psi^i a_i \cdot \psi^j b_j = \sum_{i+j \equiv k} \psi^{i+j} a_i b_j.
```

Split into two groups according to whether $i + j = k$ (no wrap) or $i + j = k + n$ (wrap):

```math
= \psi^k \sum_{i+j = k} a_i b_j + \psi^{k+n} \sum_{i+j = k+n} a_i b_j.
```

Since $\psi^n = -1$, we have $\psi^{k+n} = -\psi^k$, so:

```math
(\tilde{a} \star \tilde{b})_k = \psi^k \left(\sum_{i+j \equiv k} a_i b_j - \sum_{i+j \equiv k+n} a_i b_j\right) = \psi^k \, (a \cdot b)_k. \qquad \square
```

Rearranging (8):

```math
(a \cdot b)_k = \psi^{-k} \, (\tilde{a} \star \tilde{b})_k.
```
(9)

---

## 4. The Cooley-Tukey Factorisation

### 4.1 Even-odd split

Split the NTT sum (1) into even-indexed and odd-indexed terms. Every index $j \in \{0, \ldots, n-1\}$ is uniquely written as $j = 2r$ or $j = 2r+1$ for $r = 0, \ldots, n/2-1$:

```math
\hat{a}_k = \sum_{r=0}^{n/2-1} a_{2r} \, \omega^{2rk} + \sum_{r=0}^{n/2-1} a_{2r+1} \, \omega^{(2r+1)k}.
```

Factor $\omega^{(2r+1)k} = \omega^{2rk} \cdot \omega^k$:

```math
\hat{a}_k = \sum_{r=0}^{n/2-1} a_{2r} \, (\omega^2)^{rk} + \omega^k \sum_{r=0}^{n/2-1} a_{2r+1} \, (\omega^2)^{rk}.
```
(10)

Since $(\omega^2)^{n/2} = \omega^n = 1$ and $\omega^2$ is primitive of order $n/2$ (as $(\omega^2)^m = 1 \Rightarrow n \mid 2m \Rightarrow n/2 \mid m$), each sum in (10) is an $n/2$-point NTT with root $\omega^2$. Writing

```math
E_k = \mathrm{NTT}_{n/2}(\mathbf{a}^{\mathrm{even}})_k, \qquad O_k = \mathrm{NTT}_{n/2}(\mathbf{a}^{\mathrm{odd}})_k,
```

equation (10) becomes:

```math
\hat{a}_k = E_k + \omega^k \, O_k, \qquad 0 \le k < n/2.
```
(11)

### 4.2 The Cooley-Tukey butterfly

For the upper half $k' = k + n/2$, apply $\omega^{k+n/2} = -\omega^k$ (property (3)):

```math
\hat{a}_{k+n/2} = E_k - \omega^k \, O_k.
```
(12)

Equations (11) and (12) together form the **Cooley-Tukey butterfly**:

```math
\boxed{\begin{aligned} \hat{a}_k &= E_k + \omega^k \, O_k \\ \hat{a}_{k+n/2} &= E_k - \omega^k \, O_k \end{aligned}}
```

One butterfly costs one modular multiplication and two modular additions. Computing both output points $\hat{a}_k$ and $\hat{a}_{k+n/2}$ from the same pair $(E_k, O_k)$ is the key efficiency gain.

### 4.3 Complexity

The recurrence $T(n) = 2T(n/2) + O(n)$ solves to $T(n) = O(n \log n)$ by the Master Theorem. There are $\log_2 n$ stages, each performing $n/2$ butterflies.

---

## 5. Bit-Reversal Permutation

### 5.1 Why it appears

The recursive even-odd splits consume the bits of each index $j$ from LSB to MSB. After $\log_2 n$ splits, element originally at index $j$ lands at leaf position $p$ where $j = \mathrm{bitrev}(p)$ — the $\log_2 n$-bit reversal of $p$.

*Example for $n = 8$.* Three splits produce leaf order $[0, 4, 2, 6, 1, 5, 3, 7]$. Leaf position $1$ holds $a[4]$: position $001_2$ reversed is $100_2 = 4$. This holds for every position.

### 5.2 Iterative algorithm

Rather than recurse, permute the input by bit-reversal once, then execute $\log_2 n$ butterfly stages in-place. At stage $s$ with group size $m = 2^s$ and twiddle base $\omega_m = \omega^{n/m}$:

```math
\text{for each group start } k,\; \text{for } j = 0, \ldots, m/2-1: \qquad \begin{cases} t \leftarrow \omega_m^j \cdot a[k+j+m/2] \bmod q \\ a[k+j] \leftarrow a[k+j] + t \bmod q \\ a[k+j+m/2] \leftarrow a[k+j] - t \bmod q \end{cases}
```

Note that the twiddle base satisfies $\omega_m = \omega_{m/2}^2$: each stage uses the square of the previous stage's root, consistent with the recursive squaring in step (10).

---

## 6. Inverse NTT — Gentleman-Sande

The INTT uses the **Gentleman-Sande (GS)** butterfly, the transpose of CT. Stages run in reverse order (large groups first), the twiddle factors use $\omega^{-1}$, and the twiddle multiplies the *difference* rather than one input:

```math
\boxed{\begin{aligned} a[k+j] &\leftarrow a[k+j] + a[k+j+m/2] \bmod q \\ a[k+j+m/2] &\leftarrow \omega_m^{-j} \cdot \bigl(a[k+j] - a[k+j+m/2]\bigr) \bmod q \end{aligned}}
```

After all stages, apply a bit-reversal permutation to the output and scale every coefficient by $n^{-1} \bmod q$.

---

## 7. Main Theorem and Proof

**Theorem.** Let $q$ be prime with $n \mid (q-1)$, $n$ a power of two. Let $\omega$ be a primitive $n$-th root of unity in $\mathbb{Z}_q$ and $\psi$ a primitive $2n$-th root with $\psi^2 = \omega$. Then the negacyclic product $c = a \cdot b$ in $R = \mathbb{Z}_q[x]/(x^n+1)$ is given exactly by

```math
c_k = \psi^{-k} \cdot \mathrm{INTT}\!\left(\mathrm{NTT}(\psi^\bullet \cdot a) \odot \mathrm{NTT}(\psi^\bullet \cdot b)\right)_k
```
(14)

where $(\psi^\bullet \cdot a)_j = \psi^j a_j$ and $\odot$ denotes pointwise multiplication in $\mathbb{Z}_q^n$.

---

**Proof.**

**Step 1 — NTT diagonalises cyclic convolution.** Let $c^{\mathrm{cyc}} = a \star b$ denote the cyclic convolution in $\mathbb{Z}_q[x]/(x^n-1)$. Then:

```math
\widehat{c^{\mathrm{cyc}}}_k = \sum_{m=0}^{n-1} c^{\mathrm{cyc}}_m \, \omega^{mk} = \sum_{m=0}^{n-1} \sum_{i+j \equiv m} a_i b_j \, \omega^{mk} = \sum_{i,j} a_i b_j \, \omega^{(i+j)k} = \hat{a}_k \cdot \hat{b}_k.
```

Therefore $\mathrm{NTT}(a \star b) = \mathrm{NTT}(a) \odot \mathrm{NTT}(b)$, and applying $\mathrm{INTT}$ to both sides:

```math
a \star b = \mathrm{INTT}\!\left(\mathrm{NTT}(a) \odot \mathrm{NTT}(b)\right).
```

**Step 2 — Twist reduces negacyclic to cyclic.** Let $\tilde{a}_j = \psi^j a_j$ and $\tilde{b}_j = \psi^j b_j$. By the calculation in Section 3.3:


```math
(\tilde{a} \star \tilde{b})_k = \psi^k \, (a \cdot b)_k
```

where $a \cdot b$ is the negacyclic product in $R$.

**Step 3 — Combine.** Apply (I) to the twisted vectors:

```math
\tilde{a} \star \tilde{b} = \mathrm{INTT}\!\left(\mathrm{NTT}(\tilde{a}) \odot \mathrm{NTT}(\tilde{b})\right).
```

Substituting into (II) and multiplying both sides by $\psi^{-k}$:

```math
(a \cdot b)_k = \psi^{-k} \cdot \mathrm{INTT}\!\left(\mathrm{NTT}(\tilde{a}) \odot \mathrm{NTT}(\tilde{b})\right)_k.
```

This is exactly equation (14). $\blacksquare$

---

## 8. The Complete Algorithm

**Input:** $a, b \in \mathbb{Z}_q^n$; precomputed tables $\psi^i$, $\psi^{-i}$, $\omega^i$, $\omega^{-i}$ for $i = 0, \ldots, n-1$.

```math
\tilde{a}_i \leftarrow \psi^i \, a_i \bmod q \qquad \text{(pre-twist)}
```
(15)

```math
\tilde{b}_i \leftarrow \psi^i \, b_i \bmod q
```

```math
A \leftarrow \mathrm{NTT}(\tilde{\mathbf{a}}) \qquad \text{(forward NTT via CT butterflies)}
```
(16)

```math
B \leftarrow \mathrm{NTT}(\tilde{\mathbf{b}})
```

```math
C_k \leftarrow A_k \cdot B_k \bmod q, \quad k = 0, \ldots, n-1 \qquad \text{(pointwise multiply)}
```
(17)

```math
\tilde{\mathbf{c}} \leftarrow \mathrm{INTT}(C) \qquad \text{(inverse NTT via GS butterflies)}
```

```math
c_k \leftarrow \psi^{-k} \, \tilde{c}_k \bmod q \qquad \text{(post-twist)}
```

**Complexity:** $O(n \log n)$ modular multiplications total. The pre/post twist and pointwise multiply each cost $O(n)$; the NTT and INTT each cost $O(n \log n)$.

---

## 9. The Full Identity Chain

```math
a \cdot b \;=\; \psi^{-\bullet} \cdot \mathrm{INTT}\!\left(\mathrm{NTT}(\psi^\bullet \cdot a) \;\odot\; \mathrm{NTT}(\psi^\bullet \cdot b)\right)
```

The pre-twist $\psi^\bullet$ converts the negacyclic ring into the cyclic ring by exploiting $\psi^n = -1$. The NTT diagonalises the resulting cyclic convolution into pointwise products. The INTT recovers coefficient form. The post-twist $\psi^{-\bullet}$ restores the correct negacyclic coefficients.

---

## 10. Parameter Instantiation

### Toy / development parameters

| Parameter | Value |
|---|---|
| $n$ | $4$ |
| $q$ | $17$ |
| $g$ (primitive root of $\mathbb{Z}_{17}^*$) | $3$ |
| $\psi = g^{(q-1)/2n}$ | $3^2 = 9$ |
| $\omega = \psi^2$ | $81 \bmod 17 = 13$ |
| $n^{-1} \bmod q$ | $4^{-1} \bmod 17 = 13$ |
| $\psi^{-1} \bmod q$ | $9^{-1} \bmod 17 = 2$ |

Verify: $\psi^8 = 9^8 \bmod 17 = 1$ ✓, $\psi^4 = 9^4 \bmod 17 = 16 = -1$ ✓, $\omega^4 = 13^4 \bmod 17 = 1$ ✓.

### Full Kyber / ML-KEM parameters (FIPS 203)

| Parameter | Value |
|---|---|
| $n$ | $256$ |
| $q$ | $3329$ |
| $\omega$ (primitive 256th root) | $17$ |
| $\psi$ (primitive 512th root) | $\sqrt{17} \bmod 3329$ |
| $n^{-1} \bmod q$ | $3303$ |

Note: Kyber uses a merged twist-NTT representation where the pre-twist and NTT are combined into a single pass using a modified twiddle table. The mathematical content is identical; the implementation fuses steps (15) and (16) for efficiency.

---

## 11. Barrett Reduction

Every butterfly requires a modular multiplication. For hardware, Barrett reduction avoids division by replacing it with multiplications and shifts. Precompute:

```math
k = \lceil \log_2 q \rceil, \qquad \bar{m} = \left\lfloor \frac{4^k}{q} \right\rfloor.
```

Then for $0 \le a, b < q$:

```math
q_{\mathrm{approx}} = \left\lfloor \frac{ab \cdot \bar{m}}{4^k} \right\rfloor
```

```math
r = ab - q_{\mathrm{approx}} \cdot q
```

```math
r \leftarrow r - q \cdot [r \ge q].
```
(20)

The correction step in (20) fires at most once, since the approximation error satisfies $|q_{\mathrm{approx}} - \lfloor ab/q \rfloor| \le 1$, which follows from $ab < q^2 \le 4^k$.
