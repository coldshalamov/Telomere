# H205 - Visible Population / Neutral-Allele Generated Law

## Conjecture

```text
Instead of storing selected crossover ranks, store a visible final population of
seed records. Decode deterministically derives parent choices, crossover/salt
state, and child seeds from that visible population.
```

This is the strongest genetics-inspired mutation after H202-H204. It changes
the claim boundary from arbitrary residual coverage to a generated/reachable
lineage.

## Kernel

`H205-visible_population_law.py`

Stored layer:

```text
[mode][root_record_1]...[root_record_M]
```

Public decode:

```text
population_t -> deterministic parent choices -> child seed population
child population repeats for P passes
leaf seeds emit B-bit atoms
```

No parent selector, crossover rank, pass birth map, open/carry channel, or final
position note is stored. All lineage choices are inherited visible state.

## Result

Strong generated row:

```text
M=32,G=16,C=8,B=32,A=5,P=6
out_bits = 16000000
paid_bits = 833
root_record_bits = 26
inside_generated_gain = 15999167
reachable_tax_upper = 15999488
uniform_net_upper = -321
min_pass_step_gain = 1888
all_passes_shrink = True
```

Smaller population rows scale the same way:

```text
M=1,G=16:  out=500000,  paid=27,  uniform_net=-11
M=2,G=16:  out=1000000, paid=53,  uniform_net=-21
M=8,G=16:  out=4000000, paid=209, uniform_net=-81
```

The arbitrary-uniform bill is explicit:

```text
support_bits <= M*G
membership_tax >= out_bits - M*G
uniform_net_upper = inside_gain - membership_tax = M*G - paid_bits
```

For `M=32,G=16`, `M*G=512` and `paid=833`, so the arbitrary-uniform upper net is
`-321` bits.

## Neutral-Tail Control

Neutral/equal-cost witnesses can carry only the entropy of their multiplicity.
If a required control state is one of `S` states and same-cost hit multiplicity
is Poisson with mean `lambda`, the chance the required state exists is:

```text
P = 1 - exp(-lambda/S)
miss_tax = -log2(P)
```

Representative rows:

```text
lambda=1,S=16:  success=0.060587, miss_tax=4.044849
lambda=4,S=4:   success=0.632121, miss_tax=0.661728
lambda=16,S=16: success=0.632121, miss_tax=0.661728
```

Near-equal slack can buy more control opportunities, but the slack bits are the
bill.

## Bill

```text
generated lineage: paid visible population records
arbitrary uniform: reachable-set membership tax out_bits - M*G
neutral control: multiplicity entropy or miss tax
```

## Mutation

H205 is a strong stateless recursive generated regime, not an arbitrary-uniform
breakthrough. The next live attack is to combine visible population laws with a
paid source/reachable contract or to search for a genuine population law whose
membership tax is supplied by the data source rather than hidden in the file.
