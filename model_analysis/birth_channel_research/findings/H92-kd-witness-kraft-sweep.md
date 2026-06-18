# H92 - K/D Witness Kraft Sweep

Date: 2026-06-17

## Question

Does the obvious knob the user emphasized, higher arity `K` and deeper search
frontier `D`, move honest witness Kraft mass over `1` in the exact H89 toy
domain?

Runnable artifact:

```text
model_analysis/birth_channel_research/H92-kd_witness_kraft_sweep.py
```

## Scope

Exact finite toy domain:

```text
B=1, N=12
K in {2,4,5,6,8,12}
D in {4,6,8,10,12}
```

Rows with `K<=5` use exact V1 arity costs. Rows with `K>5` use the existing H74
research extension:

```text
ceil(log2(K)) + payload_width
```

That extension is intentionally optimistic: it omits the J3D1 Lotus width
metadata and is not a current V1 wire-format claim.

## Result

Best selected row:

```text
K=12, D=12, log2 Z_best=-0.681489, Z_best=0.623522
```

Best collective row:

```text
K=8, D=12, log2 Z_total=1.001339, Z_total=2.001857
```

Collective crossings appeared in the optimistic `K>5` extension:

```text
K=6,D=10   log2 Z_total=0.208920
K=6,D=12   log2 Z_total=0.820583
K=8,D=10   log2 Z_total=0.395851
K=8,D=12   log2 Z_total=1.001339
K=12,D=10  log2 Z_total=0.093693
K=12,D=12  log2 Z_total=0.541691
```

## Reading

This is useful as a lower-bound scout only. It shows why higher arity and deeper
search are tempting: the collective/all-description family can cross if witness
width metadata is underpriced.

But because the `K>5` rows omit Lotus width overhead, H92 cannot be promoted as
a paid Telomere mechanism. It must be paired with H93.

## Verdict

H92 reopens the higher-arity/deeper-search route as a serious frontier mover,
but its positive rows are not honest paid rows. H93 is the required accounting
check.
