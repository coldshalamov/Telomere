# H29 - Exact cover-equivalence DP

Date: 2026-06-17

## Question

Can the encoder avoid paying one selected cover witness by arithmetic-coding the
decoded layer under the public distribution induced by all possible covers?

Legal mechanism:

```text
cover c = [(arity, seed), ...]
expand(c) = x
Q(x) = sum_{c : expand(c)=x} 2^-L(c)
encode x under public Q
```

The selected cover is latent. The decoder does not need arities, seeds, or a
rank inside `C_x`; it only needs the fixed public profile and an arithmetic
decoder for `Q`.

## Exact tiny kernel

`H29-cover_equivalence_dp.py` enumerates every `N*B`-bit layer in a tiny
universe. For each target `x`, it computes:

- `Q(x)` by summing all cover masses with a DP;
- `min_c L(c)` as the best local selected-cover witness;
- `-log2 Q(x)` as the collective witness cost;
- a raw escape mixture over `alpha*Q + (1-alpha)*U`.

It uses exact current V1/J3D1 record costs for payload widths and a deterministic
toy uniform seed expander for small exhaustive enumeration.

Default run:

```text
N=12 atoms, B=1, K=4, payload_depth=8
seed_count/arity = 509
raw_bits = 12
coverage = 1.000000
total Q mass = 0.000060
avg best local cover bits = 33.455322
avg collective -log2 Q bits = 26.245017
avg duplicate-cover saving = 7.210305
collective gain vs raw = -14.245017
best raw escape mixture alpha = 0.00
```

Denser checks moved in the right direction but stayed above raw:

```text
N=12, D=10: avg collective = 25.349110, duplicate saving = 8.106212
N=10, D=12: avg collective = 20.770670, duplicate saving = 8.297689
```

## Expected uniform edge row

The kernel also computes the expected uniform edge-mass row. If each edge output
is perfectly uniform, then every target `x` has the same mass:

```text
Q(x) = 2^(-N*B) * Z_N
```

For the default run:

```text
Q_expected(x) = 1.46650090813e-08
-log2 Q_expected(x) = 26.023047
expected gain vs raw = -14.023047
```

This explains the sampled result: duplicate cover descriptions are real, but
under a public uniform-law cover distribution, the whole induced code is still
a public source prior. It can make some strings cheaper only by making other
strings more expensive or by leaving mass unused.

## Verdict

Cover-equivalence coding is the cleanest stateless collective witness mode so
far:

- no open/carry channel;
- no birth-pass channel;
- no selected-cover rank;
- no per-file count table;
- duplicate-cover entropy is honestly harvested.

But it does not solve the active goal under the uniform/content-blind
roughly-all-data premise. A public `Q` obeys:

```text
E_uniform[-log2 Q(X)] = N*B + KL(U || Q/Z) - log2 Z >= N*B
```

when `Q` is a subprobability with total mass `Z <= 1`.

So H29 is a real witness-cost improvement lane and a possible source-shaped or
minority-win lane. It is not maintained recursive compression over roughly all
uniform data.

## Artifact

`model_analysis/birth_channel_research/H29-cover_equivalence_dp.py`
