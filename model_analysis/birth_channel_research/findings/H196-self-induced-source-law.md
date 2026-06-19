# H196 - Self-Induced Source Law / Recursive Output-Law Ledger

## Conjecture

```text
Even if H195 cannot compress uniform layers, recursion may make the next layer
non-uniform. If the emitted layer becomes biased toward witness-rich outputs,
Telomere can compress that new layer and maintain drift without external
structure.
```

This is the direct test of the strongest post-H195 escape hatch: maybe the
algorithm creates its own source law.

## Kernel

`H196-self_induced_source_law.py`

The kernel builds the same paid public-lane witness distribution `Q` as H195,
using exact current V1/J3D1 record costs:

```text
Q(x) = (1-q)/2^N + s_x
```

Then it creates shaped next-layer sources:

```text
P_beta(x) proportional to Q(x)^beta
```

and reports:

```text
apparent block gain = N - E_P[-log2 Q(X)]
source-law tax      = N - H(P)
paid net            = apparent gain - source tax
                    = H(P) - E_P[-log2 Q(X)]
                    = -D(P||Q)
```

`beta=0` is the arbitrary uniform input case from H195. `beta=1` is the
optimistic recursive resonance case where the next-layer source law equals the
Telomere witness/fallback law exactly.

## Result

Default rows over the H195 public salt landscape:

```text
N=8,Wmax=8,lanes=4096,beta=0:
  H(P)=8.000000
  CE(P,Q)=8.000005
  appGain=-0.000005239
  srcTax=0
  paidNet=-0.000005239

N=8,Wmax=8,lanes=4096,beta=1:
  H(P)=7.999995
  CE(P,Q)=7.999995
  appGain=+0.000005242
  srcTax=+0.000005242
  paidNet=0

N=8,Wmax=8,lanes=4096,beta=4:
  H(P)=7.999916
  CE(P,Q)=7.999963
  appGain=+0.00003676
  srcTax=+0.00008407
  paidNet=-0.00004731
```

The same pattern appears at `N=12`:

```text
N=12,Wmax=8,lanes=512,beta=1:
  appGain=+0.000524
  srcTax=+0.000524
  paidNet=0

N=12,Wmax=8,lanes=512,beta=2:
  appGain=+0.001611
  srcTax=+0.002158
  paidNet=-0.000547
```

## Bill

The recursive-output idea can create real apparent compression, but only by
making the next layer non-uniform. For arbitrary data, that non-uniformity is
not free:

```text
source-law tax = N - H(P)
```

After paying it:

```text
paid net = -D(P||Q) <= 0
```

The best possible resonance, `P=Q`, ties exactly. More aggressive concentration
creates more apparent block gain and an even larger source-law tax.

## Mutation

Self-induced output bias is not an arbitrary-uniform escape by itself. It is
still useful as a component:

```text
1. in a declared generated/reachable regime where P is truly the source law;
2. as a diagnostic for whether a future recursive codec is just recovering its
   own reversible transform expansion;
3. as a smoothing target inside a bounded referee construction, if one ever
   shows surplus after ambiguity bits.
```

The next new implementation should not be another independent `P_beta` source
shape. It should either test a bounded overfull/referee surplus or turn H183's
generated/reachable positive control into a more Telomere-native developmental
regime while keeping the membership tax explicit.

