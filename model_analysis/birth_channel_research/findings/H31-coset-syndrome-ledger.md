# H31 - Coset / syndrome / ECC-style witness

Date: 2026-06-17

## Question

Can a seed expansion act as a codeword, with a smaller syndrome/error residual
repairing it to the target?

Mechanism:

```text
target x
seed expands to codeword c
record stores [seed][syndrome/error residual r]
decoder computes c, applies r, recovers x
```

This is statelessly decodable in a Total-Cover/all-open branch. The decoder
knows the code/profile, seed, residual bits, public pass/dither schedule, and
public placement.

## Full syndrome

For an `n`-bit target and `2^k` seed codewords, full lossless support needs
about `n-k` syndrome bits. H31 reports:

```text
n=64,   k=8  -> syndrome=56,  total=64,   net=0
n=64,   k=32 -> syndrome=32,  total=64,   net=0
n=1024, k=32 -> syndrome=992, total=1024, net=0
```

Before ordinary record overhead, full syndrome is exactly raw length.

## Low-weight residual

Low-weight repair looks compressive only on targets near a codeword. H31 uses:

```text
ball_bits = log2(sum_{i<=r} C(n,i))
coverage_log2_fraction = k + ball_bits - n
```

Representative rows:

```text
n=64,   k=16, r=2 -> coverage=-36.977 bits, error=11.023 bits, net_if_hit=36.977
n=64,   k=32, r=4 -> coverage=-12.627 bits, error=19.373 bits, net_if_hit=12.627
n=128,  k=32, r=4 -> coverage=-72.607 bits, error=23.393 bits, net_if_hit=72.607
n=1024, k=32, r=8 -> coverage=-927.327 bits, error=64.673 bits, net_if_hit=927.327
```

The savings on reachable targets are matched by exponentially tiny coverage.
For roughly all uniform data, a raw/fallback escape restores the counting
bound.

## Omitted syndrome / checksum

If the residual is omitted, the decoder has many possible coset members. A
checksum/referee must distinguish them:

```text
log2 false accepts ~= log2(candidate_count) - checksum_bits
```

H31 examples:

```text
log2 candidates=64,  checksum=64  -> false_accept_log2=0
log2 candidates=128, checksum=128 -> false_accept_log2=0
log2 candidates=1024, checksum=256 -> false_accept_log2=768
```

So the referee must scale with the residual entropy. This reduces to H25.

## Recursive residual

For uniform targets, `x XOR c` is uniform unless the codeword choice brings a
paid selector or source prior. Recursively Telomere-compressing the residual
therefore moves the same problem into the residual stream.

The only surviving variant is H26/H28-shaped:

```text
future_value_from_residual > residual_bits
```

or equivalently `gamma > 1`. H31 rows show:

```text
residual=8, gamma=1.0 -> net=0
residual=8, gamma=1.2 -> net=1.6
residual=64, gamma=1.2 -> net=12.8
```

Uniform future value has `gamma=0`, and one-for-one steering only breaks even.

## Verdict

Coset/syndrome witnesses are useful as a stateless repair language, but not as
an all-data compression source:

- full syndrome returns to raw length;
- low-weight residuals cover an exponentially small subset;
- omitted residuals require a scaling referee/checksum;
- recursive residuals remain uniform under the uniform law.

The only reason to keep the idea is as a possible fertility channel in a
predeclared source-shaped/developmental model, with random controls staying
negative.

## Artifact

`model_analysis/birth_channel_research/H31-coset_syndrome_ledger.py`
