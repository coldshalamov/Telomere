# H81 - Output Whitening Versus Fertility

Date: 2026-06-17

## Question

H80 found a real source-shaped public-`Q` fertility lane. Does a normal compact
stateless code output preserve that lane across passes?

Runnable artifact:

```text
model_analysis/birth_channel_research/H81-output_whitening_fertility.py
```

## Exact Domain

Same H80/H74 finite domain:

```text
B=1, N=12, K=6, D=8, domain=4096
raw visible word bits:         12.000000
H(Q):                          10.634978
D(Q||U) source redundancy:      1.365022
D(U||Q) uniform Q-code excess:  1.814795
```

## Class Profiles

```text
class         f=U(F)   Q(F)    c*_H7   pFF need
top10        0.1001   0.5323   0.5396   0.9146
top25        0.2500   0.7787   0.7247   0.9050
F_positive   0.2551   0.7839   0.7304   0.9058
```

## Output Regimes

For `top25`:

```text
regime              next c   gain    shape cost   net    H7?
entropy-coded Q     0.2500   1.365      0.000     1.365   no
visible Q-shaped    0.7787   1.365      1.365     0.000   yes
raw/permutation     0.7787   0.000      0.000     0.000   yes
```

For `F_positive`:

```text
entropy-coded Q     next c=0.2551, net=+1.365, H7? no
visible Q-shaped    next c=0.7839, net=0.000,  H7? yes
raw/permutation     next c=0.7839, net=0.000,  H7? yes
```

## Reading

The compact `Q` code captures the source redundancy, but its visible output is
near-uniform code bits. That drops the next-layer class membership back to the
uniform class mass `f`, below the H7 recurrence threshold.

Making the next visible layer `Q`-shaped again preserves fertility, but the
distribution-shaping slack costs:

```text
D(Q||U) = 1.365022 bits
```

That cancels the finite source saving before Telomere record costs.

Public reversible permutations can preserve `F`, but they do not shrink the
layer.

## Verdict

H81 narrows the remaining breakthrough target:

```text
Do not entropy-code to uniform and then try to recover fertility.
Find a native Telomere record syntax whose compact visible output is already
high-Q/fertile.
```

That is a different target from post-coding reshaping. It has to be tested as a
record-language/source-law mechanism with uniform controls and no hidden
witness-choice channel.
