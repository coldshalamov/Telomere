# Avenue H16 - prior escape ledger

Author: Codex continuation with read-only subagent audit. Date: 2026-06-17.
Status: premise-shift price tag after H15.

## HYPOTHESIS

H15 closes the uniform/content-blind recursive all-data branch. The remaining
escape hatch is not another pass trick; it is a public non-uniform interpreter
or source-shaped seed universe.

H16 asks how much non-uniform prior mass such an interpreter must buy.

## MECHANISM

Runnable ledger:

- `../H16-prior_escape_ledger.py`

For `n`-bit strings, let:

```text
A_s = {x : L(x) <= n - s}
```

Kraft/counting gives:

```text
U(A_s) <= 2^-s
```

where `U` is uniform. If a non-uniform source/prior `Q` gives that same
compressible set mass `c`, then the average likelihood-ratio lift on the
compressible set is at least:

```text
Q(A_s) / U(A_s) >= c * 2^s
```

The exact entropy-deficit lower bound is binary KL:

```text
n - H(Q) = D(Q || U) >= d2(c || 2^-s)
```

This is at least the looser approximation:

```text
max(0, c*s - h2(c))
```

## RESULT

`uniform-escape-requires-real-prior`

Representative 1024-bit rows:

```text
command:
python model_analysis\birth_channel_research\H16-prior_escape_ledger.py ^
  --input-bits 1024 --savings 8 32 128 --coverages 0.5 0.9 0.99
```

| n | saving s | source coverage c | uniform max c | avg lift | min entropy deficit |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1024 | 8 | 0.90 | 0.003906 | 230.4 | 6.732 |
| 1024 | 32 | 0.90 | 2.33e-10 | 3.87e9 | 28.331 |
| 1024 | 128 | 0.90 | 2.94e-39 | 3.06e38 | 114.731 |
| 1024 | 128 | 0.99 | 2.94e-39 | 3.37e38 | 126.639 |

Rate-scale rows:

```text
command:
python model_analysis\birth_channel_research\H16-prior_escape_ledger.py ^
  --input-bits 1000000 --savings 10000 100000 --coverages 0.5 0.9
```

| n | saving s | source coverage c | min entropy deficit | max source entropy |
| ---: | ---: | ---: | ---: | ---: |
| 1000000 | 10000 | 0.5 | 4999.000 | 995001.000 |
| 1000000 | 10000 | 0.9 | 8999.531 | 991000.469 |
| 1000000 | 100000 | 0.5 | 49999.000 | 950001.000 |
| 1000000 | 100000 | 0.9 | 89999.531 | 910000.469 |

So to save `128` bits on `90%` of a 1024-bit source, a public prior must put
that 90% mass on a subset occupying at most `2^-128` of the uniform space,
requiring about `115` bits of entropy deficit. That is a real source prior, not
content-blind all-data compression.

## HIDDEN-CHANNEL WARNINGS

H16 only permits a prior/interpreter as public and predeclared. The following
are metadata unless fixed publicly or paid:

- interpreter/profile chosen after seeing the target;
- source-family ID, transform ID, pass/profile/salt/window/parse map, or hit
  bitmap stored out of band;
- public tables trained on the test file or adjacent corpus leakage;
- checksum/referee bits used as free selectors among candidates;
- file path, MIME type, repository membership, or user context as implicit
  prior;
- adaptive per-file arithmetic counts;
- grinding over multiple interpreters without paying `log2(M)`;
- low entropy that is not aligned with the actual short-code set.

## INTERPRETATION

H16 does not reopen content-blind all-data Telomere. It quantifies the cost of
leaving that premise. If the prior is real and public, the result can be valid
source-shaped compression. It is no longer uniform/content-blind compression on
roughly all arbitrary data.

## NEXT

The remaining constructive path would have to specify a public interpreter or
source-shaped seed universe and price:

- its profile identifier or public-fixed status;
- its prior mass/entropy deficit;
- exact seed witnesses and decode metadata;
- controls proving that wins are source-prior wins, not hidden side channels.

