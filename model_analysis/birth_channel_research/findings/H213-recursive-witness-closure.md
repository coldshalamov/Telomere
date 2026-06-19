# H213 - Recursive Witness Closure / Upward Detour

## Conjecture

```text
An optimal recursive seed may not decode directly downward into the final
target. It may first generate a valid intermediate record token, which then
opens to the target.
```

This is the clean two-pass version of the user's non-greedy/upward-detour
intuition:

```text
pass2 seed -> pass1 record token -> N-bit target
```

No selector is stored separately; the final seed names the intermediate token.

## Kernel

`H213-recursive_witness_closure.py`

The kernel enumerates:

```text
first frontier:  pass1 seed records that expand to N-bit targets
token language:  synthetic prefix record tokens of exact paid record length
second frontier: pass2 seed records that expand to pass1 tokens
raw fallback:    N + 1 bits
```

If pass2 may generate several intermediate token lengths, the kernel charges:

```text
class_bits = ceil(log2(number of token length classes))
```

This prices the span-length/boundary channel.

## Result

Default rows have recursive support but no paid wins:

```text
N=8,W1=8,W2=8:
  first_records=509
  token_classes=8
  class_bits=3
  final_token_hits=18
  one_pass_support=225
  two_pass_support=13
  paid_wins=0
  mean_delta_paid=+0.992188
```

Wider rows produce real upward-detour wins:

```text
N=16,W1=10,W2=12:
  final_token_hits=461
  two_pass_support=209
  oracle_wins=8
  paid_wins=1
  mean_delta_oracle=+0.983658
  mean_delta_paid=+0.983856
  hidden_length_bill=0.000198
  best_paid_improvement=2
  support_tax_upper=8.292641

N=16,W1=12,W2=12:
  final_token_hits=517
  two_pass_support=264
  oracle_wins=12
  paid_wins=2
  mean_delta_oracle=+0.983536
  mean_delta_paid=+0.983841
  hidden_length_bill=0.000305
  best_paid_improvement=2
  support_tax_upper=7.955606
```

## Bill

The mechanism is legal:

```text
final seed stores/names the intermediate token
intermediate token opens deterministically
```

The bills are also visible:

```text
intermediate token length class / boundary bits
small recursive support fraction
raw fallback expansion on unsupported targets
```

## Mutation

H213 is not a positive arbitrary-uniform codec, but it is a genuine
non-greedy recursive mechanism. The next attack should extend this from two
passes to a finite recursive closure depth and measure whether support growth
or best-description tails approach the raw boundary after all length-class and
fallback costs.
