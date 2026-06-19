# H172 - Designed Closed Item-Language Bound

Date: 2026-06-18

## Question

Can a hand-designed public closed item grammar make every pass statelessly
parseable and still produce positive drift on roughly all uniform data?

Runnable artifact:

```text
model_analysis/birth_channel_research/H172-designed_closed_item_language_bound.py
```

## Model

Let a fixed public total-cover record language `G` emit item streams that are
again valid inputs for `G`. Let:

```text
W_a = total Kraft/match mass of all records that emit a items
```

For a uniform arbitrary item stream, the total-cover partition function is:

```text
F_0 = 1
F_n = sum_a W_a * F_{n-a}
```

A prefix-safe stateless grammar has:

```text
sum_a W_a <= 1
```

The asymptotic growth rate `lambda` satisfies:

```text
sum_a W_a * lambda^-a = 1
```

Positive recursive drift requires:

```text
lambda > 1
```

But if `lambda > 1`, then:

```text
sum_a W_a > 1
```

so the grammar is overfull. Public closure solves parseability, not the uniform
capacity gap.

## Exact Rows

```text
grammar                       sumW      lambda    log2(lambda)  valid?  logZ64     result
singleton_valid               1.000000  1.000000  0.000000      true    0.000000   valid break-even only
equal_valid_K5                1.000000  1.000000  0.000000      true   -1.584963   valid break-even only
bundle_only_K5_valid_sparse   1.000000  1.000000  0.000000      true   -inf        valid break-even only
front_loaded_valid_K5         1.000000  1.000000  0.000000      true   -0.526069   valid break-even only
back_loaded_valid_K5          1.000000  1.000000  0.000000      true   -2.211593   valid break-even only
underfull_K5                  0.150000  0.519097 -0.945925      true  -62.332043   valid underfull negative drift
overfull_all_ones_K5          5.000000  1.965948  0.975225      false  61.519901   overfull invalid positive mass
slightly_overfull_K5          1.200000  1.064022  0.089529      false   4.205715   overfull invalid positive mass
```

Finite rows confirm the same result:

```text
valid grammars:    F_n <= 1 for every tested n
overfull grammars: F_n crosses positive
```

The apparent finite `logZ64` penalties for valid multi-arity grammars are
boundary/period effects; their asymptotic `lambda` is still exactly break-even
when `sum W_a = 1`.

## Target Overfull Bill

If a record of average arity `a` must supply `r` missing bits per selected
record, the per-item drift is:

```text
r / a
```

For a single arity, the required Kraft mass is:

```text
(2^(r/a))^a = 2^r
```

So the overfull bill is independent of arity:

```text
target                         arity   r/record   drift/item   needed sumW   overfull bits
H162 K5 D80 post-H165          1       8.112500   8.112500     276.761605   8.112500
H162 K5 D80 post-H165          5       8.112500   1.622500     276.761605   8.112500
H162 K5 D80 post-H165          64      8.112500   0.126758     276.761605   8.112500
H163 K16 D512 post-H165        1      10.926442  10.926442    1946.196951  10.926442
H163 K16 D512 post-H165        16     10.926442   0.682903    1946.196951  10.926442
H163 K16 D512 post-H165        64     10.926442   0.170726    1946.196951  10.926442
```

Higher arity spreads the drift over more items, but it does not reduce the
hidden capacity required per record.

## Verdict

H172 does not solve the goal. It rules out the cleanest fixed public closed
item-language shortcut:

```text
public closure + valid prefix/Kraft grammar => lambda <= 1
positive all-data drift => overfull grammar or hidden capacity
```

A live closed-language branch must therefore add a real non-uniform population
recurrence, a source-shaped law, or a new mechanism that changes the Kraft
accounting without hiding state in the grammar, layout, pass history, or oracle
selection.
