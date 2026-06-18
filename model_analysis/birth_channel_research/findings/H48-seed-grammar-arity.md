# H48 - seed-grammar arity embedding

Date: 2026-06-17

## Question

Can the decoder derive arity from the seed witness itself, removing the
explicit arity stream?

Candidate mechanism:

```text
seed universe = disjoint public arity/type classes
arity(seed) = class(seed)
record = [seed witness]
```

If arity `a` gets public seed-space fraction `q_a`, then arity `a` only gets
that fraction of all candidate seeds. Under the uniform hash law:

```text
E_hits(a) = q_a * 2^D * 2^(-aB)
E[log2 first_rank_a] ~= aB + log2(1/q_a) - 0.833
```

So removing explicit arity bits adds a seed-space thinning penalty:

```text
class tax = -log2(q_a)
```

The minimum expected class tax is the selected arity entropy `H(A)` when the
public grammar mass matches the selected arity law. That is arithmetic-coded
arity in another form.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H48-seed_grammar_arity.py
```

Modes:

- `arity_seed_fixed_lower`: optimistic lower bound. It removes explicit arity
  and charges the thinned fixed-width seed rank, but assumes the decoder knows
  the exact witness width. Not parseable by itself.
- `arity_seed_j3d1`: parseable seed-only record. It charges the thinned global
  rank as a self-delimiting J3D1 seed field and removes explicit arity.
- `arity_width_grammar`: arity and width both live in the seed grammar. This is
  seed-space thinning plus local payload bits, equivalent to paying a public
  `(arity,width)` distribution.

Default run:

```text
B=4, K=128, D=512
atoms=128
train trials=16
eval trials=8
iterations=3
alpha=0.02
```

## Results

```text
arity_seed_fixed_lower/global:
  parseable = false
  eval gain = +0.217773 bits/input atom
  records/atom = 0.286133
  avg arity = 3.49
  seed penalty/record = 2.770
  cost/record = 13.218

arity_seed_j3d1/global:
  parseable = true
  eval gain = -0.128906 bits/input atom
  missing = 7.333 bits/record
  records/atom = 0.017578
  avg arity = 56.89
  seed penalty/record = 2.302
  cost/record = 234.889

arity_seed_j3d1/remaining:
  parseable = true
  eval gain = -0.127930 bits/input atom
  missing = 7.706 bits/record
  records/atom = 0.016602
  avg arity = 60.24
  seed penalty/record = 1.448
  cost/record = 248.647

arity_width_grammar/remaining:
  parseable = true
  eval gain = -0.124392 bits/input atom
  missing = 9.798 bits/record
  records/atom = 0.012695
  avg arity = 78.77
  seed penalty/record = 13.491
  cost/record = 324.875
```

## Reading

The lower bound crosses, so the idea is probing a real pressure point. But the
crossing row is not a legal stateless stream because the decoder does not know
how many witness bits to read.

Once the seed witness is self-delimiting, the row misses. The arity class is
indeed derivable, but the missing arity bits return as:

- lost seed supply `-log2(q_class)`;
- self-delimiting witness-width overhead;
- J3D1 payload cap pressure near `D=512`;
- or, if width is also embedded, a larger `(arity,width)` class tax.

This matches the scout theorem:

```text
E[-log2 q_A] = H(A) + KL(P_A || q)
```

Minimum class tax equals arithmetic-coded arity. A grammar chosen after seeing
the file is model metadata.

## Verdict

Seed-grammar arity embedding is useful as a way to see the boundary bill, but
it is not a new free stateless channel under the uniform hash law. It can
replace a bad fixed arity alphabet with a better public arity law, but that is
the same response-surface axis already tested by the public/factored arity
models.

The live problem after H48 is not "how does the decoder know arity?" It can
know arity from the witness. The remaining problem is "how does the decoder
know the witness boundary and selected cover cheaply enough?" The next target
should therefore measure the all-block reproduction number over passes:

```text
rho_t = paid_bits(next_layer) / raw_bits(current_layer)
need E[log rho_t] < 0
```

with every arity/width/profile/exception selector paid.
