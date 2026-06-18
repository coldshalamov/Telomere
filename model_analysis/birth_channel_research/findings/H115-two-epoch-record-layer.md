# H115 - Two-Epoch Record-Layer Accounting

Date: 2026-06-18

## Question

H114 crossed on fixed raw atoms with:

```text
visible two-epoch seed class + frozen public delta law
B4_K32_D128, slack=4, global context
held-out = -0.020876 bits/atom
```

Does that survive when the layer is a stream of self-delimiting variable-length
items and old records must refresh before parity aliases?

Runnable artifact:

```text
model_analysis/birth_channel_research/H115-two_epoch_record_layer.py
```

## Model

Items carry:

```text
bit length
represented raw-bit length
age: literal / new record / old record
```

Candidate target length is now heterogeneous:

```text
target_bits = sum(item.bits for items in interval)
```

Modes:

- `no_expiry_lower_bound`: lets old records survive past parity alias. This is
  an intentionally invalid lower bound.
- `force_refresh`: age-1 records cannot be skipped; every due old record must
  be covered by a new record.
- `expire_raw_lower_bound`: old records may expand to raw bits without literal
  marker cost. This is also a lower bound.
- `expire_literal_items`: old records expand to literal-marked block items.

The kernel also tests `public_lane_*` rows where the visible seed-class bit is
removed from the witness. Those rows are optimistic positional-class targets and
need a separate proof that lane membership is public.

## Results

One-pass calibration can still reproduce a tiny raw-atom lower-bound crossing:

```text
H114_raw_lower, P=1, global:
  -0.005424 bits/atom
```

But across four passes with the two-epoch rule and no extra rewrite quota:

```text
H114_raw_lower, force_refresh, global:
  +0.020909 bits/atom/pass

H114_raw_lower, force_refresh, arity_bucket:
  +0.023516 bits/atom/pass

H114_raw_lower, no_expiry lower bound:
  -0.014058 bits/atom/pass

H114_raw_lower, expire_literal_items:
  +0.020281 bits/atom/pass
```

The invalid `no_expiry` row crosses because it hides the age channel. Forced
due-cohort refresh removes that hidden channel and goes positive.

Removing the visible class bit with a public-lane lower bound did not rescue the
frozen law in the focused repeat:

```text
public_lane_raw, force_refresh, global:
  +0.011262 bits/atom/pass

public_lane_raw, force_refresh, arity_bucket:
  +0.021096 bits/atom/pass
```

However, the due-refresh geometry is not impossible under an oracle. With the
same record-layer transition but local payload width:

```text
H114_raw_lower, local oracle, force_refresh:
  -0.047175 bits/atom/pass

public_lane_raw, local oracle, force_refresh:
  -0.085214 bits/atom/pass
```

## Interpretation

H115 finds the hidden cost H114 was most likely missing:

```text
q >= 0.50 is not the same as refreshing every due old record
```

Once old compact records are real stream items, the frozen delta law trained on
fixed raw-atom covers no longer prices the heterogeneous target lengths well
enough. The current public law spends the H114 margin.

This is not a final no-go for the branch. The local oracle remains negative,
especially under the public-lane local-class lower bound. The next live target
is therefore narrower:

```text
forced due-cohort refresh
+ heterogeneous item-length public width law
+ public lane/local seed class if the lane membership can be made derivable
```

## Verdict

H114 should be downgraded from "paid crossing target" to "fixed-atom lower-bound
crossing." It did not reward-hack with H2 or a per-file histogram, but it did
underprice the record-layer age/length problem.

The new next target is a heterogeneous due-cohort public width law. Any future
positive row must pass `force_refresh` with zero stale exceptions, not merely a
global rewrite fraction.
