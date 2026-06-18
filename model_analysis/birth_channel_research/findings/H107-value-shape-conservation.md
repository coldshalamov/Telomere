# H107 - Value-Shape Conservation

Date: 2026-06-18

## Question

If arity/rank Kraft mass cannot create positive whole-cover mass, can a biased
seed grammar do it by pointing more generated values into fertile-looking
regions?

Runnable artifact:

```text
model_analysis/birth_channel_research/H107-value_shape_conservation.py
```

## Model

Fix the arity masses:

```text
K=6, N=12, B=1
W_a = 1 / K
```

Change only how each `W_a` is distributed over output values:

```text
uniform_values
zero_attractor
half_fertile
random_lumpy
```

The total description mass should remain the H106 recurrence value:

```text
log2Z = -1.781751
```

## Result

```text
shape            log2Z       reach   CE excess   best alpha   mix excess
uniform_values  -1.781751    1.000   0.000000    0.00         0.000000
zero_attractor  -1.781751    0.000   inf         0.00         0.000000
half_fertile    -1.781751    0.473   inf         0.00         0.000000
random_lumpy    -1.781751    1.000   0.162096    0.00         0.000000
```

Changing the public value law reshapes which strings are favored, but does not
change total witness mass. Under the uniform roughly-all-data premise,
normalized `Q` never beats raw on average. The honest raw/`Q` mixture chooses
raw (`alpha=0`) unless `Q` is exactly uniform.

## Verdict

Biased seed grammars can be useful only as named source-shaped or fertility-cycle
mechanisms whose entropy deficit is paid. They do not supply the H105 missing
witness margin for content-blind roughly-all-data compression.
