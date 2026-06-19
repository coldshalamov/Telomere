# H208 - Public Ensemble / Source-Law Bridge

## Conjecture

```text
Make H205 useful as a universal generated/reachable prior: allocate Kraft mass
to visible-population generated outputs and spend leftover mass on raw fallback.
```

Also test whether many public generated families change the support bill.

## Kernel

`H208-public_ensemble_source_law.py`

For a public ensemble of `E` generated laws:

```text
support_bits <= M*G + log2(E)
paid_bits = M*G + log2(E) + extra_mode_bits
```

For the normalized prior:

```text
s = log2 reachable support
c = paid native witness bits
q = 2^(s-c)

Q(x) = 2^-c + (1-q)2^-N   if x is reachable
Q(x) =        (1-q)2^-N   otherwise
```

The source mixture tested is:

```text
P_alpha = alpha * Uniform(reachable) + (1-alpha) * Uniform(all N-bit)
```

## Result

Public ensembles do not change the bound:

```text
E=65536,M=32,G=16,extra=1
support_bits = 528
paid_bits = 529
paid_net = -1
hidden_mode_net = +16
```

The apparent `+16` row is exactly the hidden family selector.

Normalized visible-population prior rows:

```text
H205-single-high-growth:
  M=1,A=5,G=16,N=500000,s=16,c=27
  q = 2^-11
  raw_overhead = 0.000704613 bits/sample
  threshold_alpha = 1.409e-9

H206-best-finite-miss:
  M=1,A=2,G=1,N=2048,s=1,c=8
  q = 2^-7
  raw_overhead = 0.011315 bits/sample
  threshold_alpha = 5.547e-6

H205-visible-population:
  M=32,A=5,G=16,N=16000000,s=512,c=833
  q = 2^-321
  raw_overhead = 3.377e-97 bits/sample
  threshold_alpha = 2.111e-104
```

At true generated-source mass `alpha=1e-6`:

```text
H205-single-high-growth:
  apparent gain = +0.499268 bits/sample
  source tax = +0.499963
  paid net after source tax = -0.000694

H205-visible-population:
  apparent gain = +15.999167 bits/sample
  source tax = +15.999467
  paid net after source tax = -0.000300
```

## Bill

```text
public ensemble: mode/family rank
hidden ensemble: unpaid selector
source-shaped prior: source entropy tax
```

The normalized prior is useful and honest: it gives near-zero downside on
uniform fallback and huge wins on generated lineages. But after charging the
source law:

```text
paid_net = H(P) - CE(P,Q) = -D(P||Q) <= 0
```

## Mutation

H208 is the best bridge so far between visible-population generated recursion
and a real all-data codec: it is a valid universal prior with vanishing uniform
overhead for large native populations. It is not a roughly-all-uniform-data
breakthrough. A future positive row must either change the source distribution
honestly or find a native mechanism whose induced output law is the source law
without paying the KL tax elsewhere.
