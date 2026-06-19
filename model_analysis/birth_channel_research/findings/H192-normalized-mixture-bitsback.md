# H192 - Normalized Mixture / Bits-Back Ledger

## Conjecture

```text
Arithmetic coding, ANS, or bits-back can normalize the raw-vs-witness mode and
recover the H190 parse bill across a finite layer.
```

## Kernel

`H192-normalized_mixture_bitsback.py`

For every small `N`-bit output, the kernel sums exact V1/J3D1 witness Kraft mass
landing on that output:

```text
s_x = sum_{w -> x} 2^-cost(w)
q   = sum_x s_x
```

It then tests the normalized mixture:

```text
Q_lambda(x) = (1-lambda) * U(x) + lambda * R(x)
R(x) = s_x / q
```

The exact leftover-Kraft point is included automatically:

```text
lambda = q
Q(x) = (1-q)/2^N + s_x
```

## Result

Representative rows:

```text
N=16,Wmax=16,lambda=0.001: meanLen=16.000247, gain=-0.000247
N=16,Wmax=16,lambda=q=0.076172: meanLen=16.063559, gain=-0.063559
N=16,Wmax=16,lambda=0.5: meanLen=16.663243, gain=-0.663243
N=16,Wmax=16,lambda=1.0: infinite tail because many outputs have no witness mass
```

Best nonzero lambda in the tested grid:

```text
N=8,Wmax=16,lambda=0.001: -0.000002682 bits/layer
```

This approaches a tie only as `lambda -> 0`, which also removes the witness
effect.

## Bill

For arbitrary uniform input:

```text
E_U[-log2 Q(X)] = N + D(U || Q) >= N
```

The H190 oracle used witness mass without shrinking raw code space. H192
normalizes the distribution and shows the exact conservation term.

## Mutation

Local raw/witness mode coding is closed as a positive arbitrary-uniform route.
The next attack must change the object being priced: a closed syntax or
ready-set recurrence that keeps future witness supply alive without hiding a
source restriction or selector.
