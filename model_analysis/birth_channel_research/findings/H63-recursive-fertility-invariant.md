# H63 - Recursive Fertility Invariant

Date: 2026-06-17

## Question

H62 gives the source probability `c*` needed for a public fertility class to
cross a target. But recursion needs more than a one-time source bias. The rewrite
map must keep future layers above the threshold:

```text
c_{t+1} = c_t * p_FF + (1-c_t) * p_OF
```

where:

- `F` is a public high-fertility class;
- `p_FF` is the probability an `F` input rewrites to an `F` output layer;
- `p_OF` is background inflow from non-`F` to `F`.

The threshold is maintained when:

```text
c* * p_FF + (1-c*) * p_OF >= c*
```

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H63-recursive_fertility_invariant.py
```

## Results

With background inflow equal to the public class mass (`p_OF=f`):

```text
H59 atom, f=0.10,a=2,c*=0.1454: min p_FF = 0.4122
H58 atom, f=0.10,a=2,c*=0.1458: min p_FF = 0.4141
H7 atom,  f=0.10,a=2,c*=0.1554: min p_FF = 0.4565

H12 witness, f=0.10,a=8,c*=0.5640: min p_FF = 0.9227
H7 witness,  f=0.10,a=8,c*=0.6822: min p_FF = 0.9534
H7 rare witness, f=0.01,a=64,c*=0.3776: min p_FF = 0.9835
```

If there is no background inflow (`p_OF=0`), then every threshold requires
`p_FF=1.0`. That is a useful adversarial check: a closed high-fertility class
must be nearly perfectly self-renewing unless the surrounding space also feeds
it.

## Reading

The plausible recursive breakthrough shape is now sharper:

```text
whole-cover/public-Q atom-level crossing first
+ recursive fertility invariant around c* ~= 0.145
+ uniform negative controls
```

That is much more plausible than trying to pay the full selected-record witness
gap through source fertility alone, which needs `p_FF ~= 0.95-0.98` in these
toy rows.

## Verdict

H63 does not solve Telomere. It narrows the target:

- use whole-cover/public-Q style accounting for the first crossing;
- define a public fertility class whose encoded outputs remain in-class often
  enough;
- measure `p_FF` and `p_OF` directly;
- require uniform controls to stay negative.

This is the first branch that looks like a concrete scientific route rather
than another hidden-channel variant.
