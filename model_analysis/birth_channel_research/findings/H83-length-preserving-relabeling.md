# H83 - Length-Preserving Relabeling

Date: 2026-06-17

## Question

Can a native, Kraft-preserving relabeling make compact visible syntax fertile
without changing code lengths?

Runnable artifact:

```text
model_analysis/birth_channel_research/H83-length_preserving_relabeling.py
```

## Model

On the exact H80 domain, a length-preserving relabeling is a public permutation
of visible words. For a fixed source law `Q` and a fixed class `F`, the optimal
permutation places the largest `|F|` probabilities into `F`.

If `F` is already a top-`Q` class, identity is optimal. If a different class is
chosen after seeing the source/output behavior, that class/profile identity is
visible state.

## Exact Rows

```text
class        f      id Q(F)  opt Q(F)  rand max  log C   c*H7    opt-c*
top10        0.100  0.5323   0.5323    0.1317   1916.7  0.5396  -0.0073
top25        0.250  0.7787   0.7787    0.2869   3316.9  0.7247  +0.0540
F_positive   0.255  0.7839   0.7839    0.2996   3349.7  0.7304  +0.0535
bottom25     0.250  0.0079   0.7787    0.2869   3316.9  invalid invalid
random25     0.250  0.2451   0.7787    0.2869   3316.9  invalid invalid
```

## Reading

For the public top-`Q` classes that matter, identity already achieves the
maximum possible `Q(F)`. Relabeling cannot improve them.

For bottom/random classes, an optimal relabeling can move high-`Q` mass into
the class, but that is just choosing a different public profile/class. If that
choice is adaptive, the profile channel is enormous (`log2 C(4096,1024)` is
about `3316.9` bits for a 25% class).

## Verdict

Length-preserving relabeling is not the missing free mechanism. It remains
valid only as a frozen public design choice, and on the relevant top-`Q`
classes the frozen identity is already optimal.

The native-syntax target remains: a predeclared graded record probability law
whose compact code lengths and visible fertility are aligned.
