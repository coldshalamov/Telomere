# H182 - Transfer-Matrix Population Law

## Conjecture

```text
A decoder-visible record/class population can preserve fresh witness supply
across passes only if its public weighted transfer law has spectral radius
greater than one after all witness, selector, width, rank, and class costs.
```

This is the strongest no-tax recurrent-population version after H181. It does
not use open/carry, birth-pass ledgers, hit maps, or final-position notes. The
only state is a public visible class law over emitted records.

## Kernel

`H182-transfer_matrix_population_law.py`

The kernel models a public weighted transfer matrix:

```text
W_ij = paid witness/Kraft mass for visible class i to emit class j
asymptotic no-tax margin = log2(rho(W))
```

If every row of `W` has paid mass `<= 1`, Perron-Frobenius gives
`rho(W) <= 1`. Positive recurrent drift therefore requires overfull hidden
mass, real source bias, or a generated/reachable restriction whose membership
tax is paid.

## Result

Representative rows:

```text
v1_flat_rank_one:        rho=0.875000, log2rho=-0.192645, valid
fixed_K8_flat:           rho=1.000000, log2rho=0, valid critical
fixed_K8_strict_s1:      rho=0.500000, log2rho=-1.000000, valid
balanced_rare_rank_one:  rho=1.000000, log2rho=0, valid critical
overfull_rare_rank_one:  rho=1.700000, log2rho=0.765535, invalid overfull
closed_fertile_valid:    rho=1.000000, log2rho=0, valid critical
closed_fertile_overfull: rho=1.080000, log2rho=0.111031, invalid overfull
```

The independent visible-class variational check confirms the KL bill:

```text
balanced_rare_fertile:
  equality population = 0.2 ordinary / 0.8 fertile
  KL = 1.966015 bits
  visible value = 1.966015 bits
  net = 0
```

Random substochastic controls did not cross:

```text
controls=1000,size=4,max_rho=0.912875,log2(max_rho)=-0.131511
```

Generated/reachable regimes remain real only inside the generated class:

```text
G=12, phenotype=8192: inside_gain=8180, reachable_tax=8180, uniform_net=0
G=24, phenotype=16384, header=64: inside_gain=16296, reachable_tax=16360, uniform_net=-64
```

## Bill

For arbitrary roughly uniform data, a frozen public recurrent class law has
positive no-tax drift only if:

```text
rho(W) > 1
```

But with honest paid row mass:

```text
max_i sum_j W_ij <= 1  =>  rho(W) <= 1
```

The surplus in positive rows is exactly overfull hidden capacity. If a source
really starts in the high-fertility population, the cost is source KL or
reachable-set membership.

## Mutation

Close frozen public transfer laws as an independent arbitrary-content engine.
The next attack should not merely assign fertility to visible classes; it must
change the paid row-mass bound itself, produce a bounded positive generated
regime with all source tax charged, or find a genuinely non-Kraft witness
inventory that is still prefix/stateless decodable.
