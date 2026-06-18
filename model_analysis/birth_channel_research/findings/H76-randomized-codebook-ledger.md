# H76 - Randomized / Best-Of Codebook Ledger

Date: 2026-06-17

## Question

Can randomness or huge compute maintain compression over roughly all
structure-free data?

H76 prices:

- public randomness;
- private encoder randomness;
- best-of public codebooks/profiles;
- randomized schedules/salts;
- checksum/referee selection.

Runnable artifact:

```text
model_analysis/birth_channel_research/H76-randomized_codebook_ledger.py
```

## Public vs Private Randomness

Condition on any public random tape `R=r`. The compressor is then one
deterministic lossless code, so:

```text
Pr_U[L_R(X) <= n-S | R=r] <= 2^-S
```

or under the generous EOF one-shot bound:

```text
Pr_U[L_R(X) <= n-S | R=r] <= 2^(1-S)
```

Averaging over public random tapes does not change the bound.

Private encoder randomness is different: if the decoder cannot derive the
chosen random tape, decode is not lossless; if it can derive or read it, the
random tape is paid selector state.

## Best-of-M Profiles

Unpriced best-of profiles can multiply apparent coverage:

```text
free best-of coverage <= min(1, M * 2^-S)
```

But if the profile identity is paid and the target is net saving `S`:

```text
paid coverage <= M * 2^-(S + log2 M) = 2^-S
```

Representative output:

```text
S=16,M=65536:
  prefix free coverage = 1.000000
  prefix paid coverage = 1.526e-05

S=64,M=65536:
  prefix free coverage = 3.553e-15
  prefix paid coverage = 5.421e-20
```

Profiles needed for `90%` coverage:

```text
P=16,s=1 bit/pass,S=16:
  M prefix = 58983, selector bits = 15.848
  M EOF    = 29492, selector bits = 14.848

P=64,s=1 bit/pass,S=64:
  M prefix = 1.6602069666e19, selector bits = 63.848
  M EOF    = 8.3010348332e18, selector bits = 62.848
```

The selector bits are essentially the savings being hidden.

## Referee Budget

A checksum/referee exposes at most its finite bit budget:

```text
S=64,M=2^32,C=8:
  free prefix coverage    = 2.328e-10
  referee prefix coverage = 1.388e-17
  owed selector bits      = 24
```

So a checksum can disambiguate finite local ambiguity, but it cannot act as an
unbounded profile selector over arbitrary passes.

## Verdict

Randomness and compute do not change the structure-free counting bound.

The legal form is a frozen public distribution `Q`, already tested in H74:
it can create favored strings and source-shaped wins, but under uniform data:

```text
E_U[-log2 Q(X)] = n + KL(U || Q) >= n
```

Per-file best-of randomness/codebooks/schedules are selectors. If their
identity is not paid, they are hidden metadata; if paid, the gain cancels.
