# H185 - Variable-To-One Coalescence Capacity

## Conjecture

```text
Maybe many current records can collapse into fewer emitted survivors, giving
repeatable stateless compression without final-position or source tax.
```

The honest question is whether survivor-count shrinkage can be lossless for
roughly all arbitrary inputs without storing the residual preimage branch.

## Kernel

`H185-coalescence_capacity.py`

For an `N`-bit layer collapsed to `L=N-s` bits over covered fraction `f`, the
kernel charges:

```text
apparent_gain = s
residual_bits >= max(0, s + log2(f))
source_tax = -log2(f)
paid_net = apparent_gain - residual_bits - source_tax
coverage_ceiling = 2^-s
```

It also reports the finite-pass roughly-all coverage ceiling:

```text
coverage <= 2^(-P*s_per_pass)
```

## Result

Representative rows:

```text
N=4096,s=1,f=1.0: residual=1, tax=0, paidNet=0,
                  but fMax=0.5 without residual/source channel
N=4096,s=4,f=0.1: residual=0.678072, tax=3.321928, paidNet=0,
                  but fMax=0.0625 without residual/source channel
N=64,s=1,f=0.5:   residual=0, tax=1, paidNet=0,
                  collapse exactly conserved
```

Tiny occupancy check:

```text
N=12,L=8,covered=4096,cells=256,meanPre=16,residLB=4,gain=4,paidNetLB=0
```

Finite-pass ceiling examples:

```text
s/pass=0.1, target 90% coverage: Pmax=1.520031
s/pass=0.5, target 50% coverage: Pmax=2
s/pass=1.0, target 10% coverage: Pmax=3.321928
```

## Bill

Many-to-one collapse is not lossless by itself. Either the decoder receives the
preimage branch, or the source is restricted to one representative per cell and
pays membership tax.

## Mutation

Keep coalescence as geometry for generated/source-shaped regimes and final-board
scaffolds. It cannot create arbitrary-content maintained drift unless another
mechanism supplies the missing preimage information without violating the row
mass/Kraft bound.
