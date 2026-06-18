# H49 - all-block renormalization kernel

Date: 2026-06-17

## Question

If every pass rewrites every atom, does the match rate stay fresh over many
passes, and does the file shrink once all paid record costs are included?

This is the total-cover recursion premise:

```text
every pass rewrites the whole layer
every output unit is a record
there are no carried records
there is no birth/open/carry channel
the next pass sees the serialized record stream as fresh target bits
```

Under the uniform hash law, freshness is automatic. For any fixed next-layer
target string `y` of length `L`:

```text
Pr[expand(seed)[0..L] = y] = 2^-L
```

That is true whether `y` is raw bytes or serialized seed records. The real
recursive condition is therefore the reproduction number:

```text
rho_t = paid_bits(layer_{t+1}) / padded_bits(layer_t)
need E[log rho_t] < 0
```

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H49-all_block_rg_kernel.py
```

The kernel iterates paid total-cover rewrites. After each pass, the charged
record length becomes the next layer length, re-atomized on the same `B`
boundary. It compares:

- `oracle_free_boundary`: labeled non-parseable lower bound;
- `h7_raw_delta`: paid H7 raw first-hit delta law;
- `h9_fixed_slack0`: paid H9 decoder-derived fixed-width witness.

Default bounded run:

```text
B=4, K=128, D=512
initial atoms=96
passes=5
trials=6
train trials=8
iterations=2
```

## Results

Summary:

```text
oracle_free_boundary:
  mean log2 rho = 0.001801
  geometric rho = 1.001249
  avg final bits = 393.500
  avg total ratio = 1.024740

h7_raw_delta:
  mean log2 rho = 0.011287
  geometric rho = 1.007854
  avg final bits = 410.212
  avg total ratio = 1.068260

h9_fixed_slack0:
  mean log2 rho = 0.011568
  geometric rho = 1.008051
  avg final bits = 410.292
  avg total ratio = 1.068469
```

Representative paid pass rows:

```text
h7 pass 1: rho=1.005205, log2 rho=0.007480
h7 pass 5: rho=1.007084, log2 rho=0.010182

h9 pass 1: rho=1.002988, log2 rho=0.004300
h9 pass 5: rho=1.008920, log2 rho=0.012756
```

## Reading

This directly answers the all-block freshness question for the tested target:

```text
fresh dice: yes
paid recursive compression: no, not in this configuration
```

The paid H7/H9 rows remain above `rho=1`, so repeating them compounds
expansion. This is not because the next layer is stale; it is because the
one-pass paid reproduction number has not crossed below one.

The oracle lower bound was also slightly above one in this small default run.
That should not be overread as a theorem against every oracle setting; earlier
free-boundary rows cross in other `B,K,D` regimes. H49's purpose is to make the
recursive pass criterion explicit and to prevent the false inference that
"fresh every pass" itself implies shrinkage.

## Verdict

Total-cover/all-block rewrite solves the birth/open/salt freshness problem in
the narrow random-oracle sense. It does not by itself solve compression. The
remaining target is a paid one-pass law with:

```text
held-out E[log rho] < 0
```

after arity, width, witness boundary, profile selection, fallback, exceptions,
and any final length/padding channels are paid.

The next systematic H49 use should sweep around the closest paid rows rather
than rerun the same defaults: vary `B,K,D`, slack, and public witness mode, but
score every candidate by `E[log rho]` over repeated total-cover rewrites.
