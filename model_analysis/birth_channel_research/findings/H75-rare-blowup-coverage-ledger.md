# H75 - Rare-Blowup Coverage Ledger

Date: 2026-06-17

## Question

Can Telomere shrink roughly all uniform inputs over many passes if rare inputs
are allowed to expand?

H75 separates two effects:

- rare blowups can balance an average-length ledger;
- rare blowups do not create more short outputs for the majority class.

Runnable artifact:

```text
model_analysis/birth_channel_research/H75-rare_blowup_coverage_ledger.py
```

## Prefix / Bounded-Loss Bound

For a prefix/self-delimiting lossless code, let:

```text
c = claimed winning fraction
S = total saving on winners
B = max expansion on non-winners
D = n - L(x)
```

Kraft gives:

```text
E_U[2^D] <= 1
c * 2^S + (1-c) * 2^-B <= 1
```

So even with very large allowed loser expansion:

```text
c <= 2^-S
```

With no loser expansion (`B=0`), positive-saving coverage is `0` for prefix
codes because the non-winners already fill the Kraft budget.

## EOF One-Shot Bound

The generous EOF/non-prefix one-shot bound remains:

```text
c <= 2^(1-S)
```

This is stronger than a Telomere self-delimiting record stream, but it still
does not support maintained positive-rate recursion.

## Representative Output

Coverage bounds with bounded loser expansion:

```text
S=4,E=64:   prefix max c = 0.062500, EOF max c = 0.125000
S=16,E=64:  prefix max c = 1.526e-05, EOF max c = 3.052e-05
S=64,E=64:  prefix max c = 5.421e-20, EOF max c = 1.084e-19
```

For a claimed `90%` typical shrink:

```text
c=0.90,P=64,s=1 bit/pass:
  S = 64
  loser expansion needed for mean balance = 576 bits
  per-pass bad-tail eps for 90% survival <= 0.001645
  prefix winning coverage bound = 5.421e-20
  EOF winning coverage bound    = 1.084e-19
```

So the bad tail is doing two impossible jobs at once: it must be tiny enough
not to hit most long recursion paths, but large enough to carry enormous
expansion, and it still cannot create enough short outputs for the winning
90%.

## Verdict

Rare blowups do not rescue structure-free maintained compression.

Under Telomere's bounded-loss contract, large rare blowups are not allowed.
Even if allowed, they can only pay the mean; they cannot change the inventory
of short descriptions. Any claim that treats rare blowups as "statistical"
while hiding the bad tail is a reward hack.
