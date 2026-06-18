# Avenue H10 — monotone fixed-width tail schedules

Author: Codex continuation with two read-only subagent checks. Date:
2026-06-17.
Status: scalar fixed-width follow-up after H9.

## HYPOTHESIS

H9 showed that a scalar decoder-derived fixed width nearly ties H7 but does not
cross:

```text
width_bits = min(D, arity * B - slack)
slack 0 -> -0.012314 bits/input atom
```

A monotone schedule might do better by using stricter slack in the body, where
the DP has many interval choices, and relaxing slack near the suffix tail, where
full-cover pressure is higher.

## MECHANISM

Runnable kernel:

- `../H10-total_cover_tail_schedule.py`

Public schedule:

```text
slack(remaining) = tail_slack if remaining <= tail_atoms else body_slack
width_bits       = min(D, arity * B - slack(remaining))
```

The decoder derives `remaining` from already decoded arities. No width/delta
stream is sent. The witness names only the first `2^width_bits` seeds. A
schedule selected per file would be metadata, so H10 reports:

- train-selected schedule as the honest public-profile row;
- best held-out schedule only as diagnostic pressure.

## RESULT

`refuted-as-crossover`

Small broad grid:

```text
command: --train-trials 8 --eval-trials 4 --iterations 2
         --body-slacks 0 1 2 --tail-slacks 0 1 --tail-atoms 64 128

train-selected body2_tail1_at64 -> -0.037878 bits/input atom
best held-out diagnostic body0_tail0_at64 -> -0.023648 bits/input atom
```

Narrower stability check:

```text
command: --train-trials 16 --eval-trials 8 --iterations 2
         --body-slacks 0 1 --tail-slacks 0 --tail-atoms 64 128

train-selected body1_tail0_at64 -> -0.027325 bits/input atom
best held-out diagnostic body0_tail0_at64 -> -0.016794 bits/input atom
```

The body-stricter schedules overfit training and lose held-out. Even the best
held-out diagnostic rows do not beat the stronger scalar H9 slack-0 run. This
closes the simple monotone tail-schedule variant.

## ACCOUNTING TRAPS CLOSED

- `tail_atoms`, `body_slack`, and `tail_slack` are free only as frozen public
  profile constants. Per-file schedule choice is metadata.
- Width `W` names only `2^W` seeds. H10 does not use the larger Lotus
  cumulative `payload_width <= W` set for `W` bits.
- Coverage failures are not ignored.
- Arity coding is learned from independent schedule-generated covers, then
  frozen for held-out evaluation.

## NEXT

H7 remains the best stable paid row:

```text
raw first-hit delta law -> -0.011929 bits/input atom
```

H9 scalar slack 0 remains the closest decoder-derived-width row:

```text
fixed slack 0 -> -0.012314 bits/input atom
```

The only low-dimensional selected-delta idea still worth one tiny falsifier is
the public selected-order-statistic law suggested by the residual-law review:

```text
P_sel(W=w | context) =
  S_raw(w-1 | L,D)^m_eff(context) - S_raw(w | L,D)^m_eff(context)
```

where `m_eff(context)` is a frozen public function of decoder-visible values
such as remaining atoms and arity. It must be evaluated held-out and charged as
the delta code. Anything richer starts to look like a frozen table over the
encoder's unchosen alternatives, which the decoder does not know.
