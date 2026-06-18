# H156 - Completion Seed-Mass Tradeoff

Date: 2026-06-18

## Question

Can the closure problem be solved by completing the prefix grammar with
filler/literal records, so generated intermediates parse cheaply?

Runnable artifact:

```text
model_analysis/birth_channel_research/H156-completion_seed_mass_tradeoff.py
```

## Model

Start with the H151 seed-record grammar. Add filler records at one fixed length
`F` using all remaining Kraft leaves:

```text
seed_kraft + filler_count * 2^-F = 1
```

Then compare:

```text
seed_density       = seed-only valid streams / 2^t
completed_density  = seed+filler valid streams / 2^t
seed|completed     = seed-only valid streams / completed valid streams
```

The identity is the key:

```text
seed_closure_tax = completed_closure_tax + seed_preservation_tax
```

If filler records are literal/raw repair, the layer parses but loses fresh seed
opportunities. If every next-layer record must remain seed-bearing, the
conditional seed preservation tax returns.

## Results

Best-looking completed parse rows:

```text
B1_K16_D4, t=13, F=13:
  seed_kraft = 0.099609
  filler_count = 7376
  seed closure tax = 7.415037 bits
  completed parse tax = 0.142019 bits
  seed|completed = 0.006466
  seed preservation tax = 7.273018 bits
  expected filler fraction = 0.993534

B1_K4_D7, t=16, F=16:
  seed closure tax = 10.607683 bits
  completed parse tax = 0.198494 bits
  seed preservation tax = 10.409189 bits
  expected filler fraction = 0.998635

B4_K32_D16, t=28, F=28:
  seed closure tax = 7.999868 bits
  completed parse tax = 0.500154 bits
  seed preservation tax = 7.499714 bits
  expected filler fraction = 0.989010
```

Longer exact lengths can have renewal resonances, but the same conservation
holds. For example:

```text
B4_K128_D16, t=64:
  seed closure tax = 10.019899 bits
  completed parse tax = 6.763691 bits
  seed preservation tax = 3.256207 bits
  expected filler fraction = 0.296455
```

## Reading

Completion is not a free closure mechanism. It moves the bill:

```text
parseability improves -> seed-bearing fraction collapses
```

A completed grammar can make arbitrary intermediate streams parse, but mostly
as filler/literal records. That may be useful as an escape/repair mechanism for
finite decoding, but it does not maintain recursive fresh hash-match rate.

## Verdict

Prefix completion trades closure tax for freshness loss or literal bloat.

The H155 target remains: find a visible selected-stream grammar where width and
closure are intrinsic to real seed-bearing records, not supplied by filler mass
that stops recursive refresh.
