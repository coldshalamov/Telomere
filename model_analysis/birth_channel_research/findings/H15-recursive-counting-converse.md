# Avenue H15 - recursive stateless counting converse

Author: Codex continuation. Date: 2026-06-17.
Status: high-arity/recursive limit proof after H14.

## HYPOTHESIS

The remaining hope after H7-H14 is that recursion itself changes the sign:
maybe many stateless Total-Cover passes, best-layer selection, pass count,
public profiles, or high arity can maintain compression over arbitrary passes
even though each paid witness model is slightly negative.

H15 tests the converse: once the final representation contains everything the
decoder needs, all recursive passes collapse into one lossless code. Then the
uniform-source counting bound applies to the final output, not to each pass in
isolation.

## THEOREM

For any stateless lossless codec whose final representation is uniquely
decodable for `n`-bit inputs:

```text
Pr_uniform[L(X) <= n - s] <= 2^-s
E_uniform[L(X)] >= n
```

This remains true if the encoder internally tries many recursive passes,
profiles, salts, schedules, covers, or witness languages. If the decoder needs
to know which pass/profile was selected, that selector is part of `L(X)`.

For any fixed positive compression rate `epsilon`:

```text
Pr_uniform[L(X) <= (1 - epsilon)n] <= 2^(-epsilon n)
```

If the selector is not paid, the apparent advantage is at most:

```text
log2(number_of_choices)
```

Paying the selector restores the ordinary bound.

## KERNEL

Runnable ledger:

- `../H15-recursive_counting_converse.py`

Example command:

```text
python model_analysis\birth_channel_research\H15-recursive_counting_converse.py ^
  --input-bits 1024 ^
  --passes 1 2 4 16 256 65536 ^
  --savings 1 8 32 128
```

Representative rows:

| n | P | target saving s | free-selector bound | selector bits | paid net saving | paid bound |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1024 | 1 | 8 | 0.003906 | 0 | 8 | 0.003906 |
| 1024 | 256 | 8 | 1.000000 | 8 | 16 | 0.000015 |
| 1024 | 65536 | 32 | 0.000015 | 16 | 48 | 3.55e-15 |
| 1024 | 65536 | 128 | 1.93e-34 | 16 | 144 | 4.48e-44 |

Tiny exact-count check:

```text
python model_analysis\birth_channel_research\H15-recursive_counting_converse.py ^
  --input-bits 12 --passes 1 4 16 --savings 1 4 8
```

| n | P | target saving s | selector bits | paid net saving | exact finite paid count |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 12 | 1 | 1 | 0 | 1 | 2048/4096 |
| 12 | 1 | 4 | 0 | 4 | 256/4096 |
| 12 | 4 | 4 | 2 | 6 | 64/4096 |
| 12 | 16 | 8 | 4 | 12 | 1/4096 |

The finite counts use Kraft directly: if every successful codeword saves at
least `s` bits after paid selectors, at most `2^(n-s)` of the `2^n` inputs can
have that much saving.

## RESULT

`uniform-recursive-positive-claim-impossible`

Total-Cover solved the stateless decode problem for birth/open/carry by making
every record open every pass. H15 shows that this is not enough to make
recursive compression positive on roughly all uniform/content-blind inputs.

Any maintained positive compression claim over arbitrary many recursive passes
would imply that most `n`-bit inputs map to final representations shorter than
`n`. There are not enough uniquely-decodable short representations for that.

## WHAT THIS DOES NOT RULE OUT

H15 does not rule out:

- compression of non-uniform sources;
- ordinary pattern/structure compression;
- public interpreters or source-shaped languages with a real non-uniform prior;
- planted controls proving implementation behavior;
- a codec that compresses a minority of uniform inputs while expanding others;
- a Telomere preset that is honestly described as source-specific.

It rules out the specific active goal branch:

```text
content-blind, uniform-law, stateless recursive compression
maintained over arbitrary passes on roughly all data
```

unless "roughly all data" is no longer uniform/content-blind or some selector /
profile / interpreter channel is paid or made public by a non-uniform prior.

## NEXT

Further work should stop trying to make the uniform Total-Cover witness stream
positive by adding more public tables or pass-selection tricks. The remaining
productive directions are:

- define a non-uniform public interpreter/source-shaped seed universe and price
  its prior honestly;
- prove a narrower finite-positive minority regime for uniform inputs;
- build planted or domain-shaped controls without presenting them as
  arbitrary-data compression.
