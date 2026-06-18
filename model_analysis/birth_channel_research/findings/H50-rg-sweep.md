# H50 - repeated-pass reproduction sweep

Date: 2026-06-17

## Question

H49 introduced the recursive score:

```text
rho_t = paid_bits(layer_{t+1}) / padded_bits(layer_t)
need held-out E[log rho_t] < 0
```

H50 sweeps this score over nearby high-arity Total-Cover configurations. This
is a bounded proof-kernel sweep, not a large compression test.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H50-rg_sweep.py
```

Modes:

- `oracle_free_boundary`: labeled non-parseable lower bound;
- `h7_raw_delta`: paid H7 raw first-hit delta law;
- `h9_fixed_slack{s}`: paid H9 fixed-width witness with slack `s`.

The pass/fail condition is a parseable paid row with:

```text
mean log2 rho < 0
```

## Compact default sweep

Default bounded run:

```text
passes=3
trials=3
train trials=4
iterations=1
configs:
  B=4,K=64,D=256,atoms=96
  B=4,K=96,D=384,atoms=96
  B=4,K=128,D=512,atoms=96
  B=8,K=64,D=512,atoms=64
h9 slacks=-8,-4,0,2
```

Best rows:

```text
best paid:
  B=4,K=128,D=512,h7_raw_delta
  mean log2 rho = +0.010475
  geometric rho = 1.007287

best oracle:
  B=4,K=64,D=256
  mean log2 rho = -0.013557
  geometric rho = 0.990647
```

Every paid row in the compact default sweep expanded.

## Corrected high-arity sweep

A scout correctly noted that `atoms=96` clips `K=128+`. The targeted follow-up
therefore used `atoms >= K`:

```text
passes=3
trials=2
train trials=4
iterations=1
configs:
  B=4,K=128,D=448,atoms=160
  B=4,K=128,D=512,atoms=160
  B=4,K=192,D=672,atoms=192
  B=4,K=192,D=768,atoms=192
h9 slacks=0,1
```

Results:

```text
B=4,K=128,D=448:
  oracle = -0.004500
  h7     = +0.015741
  h9 s0  = +0.016565
  h9 s1  = +0.009166

B=4,K=128,D=512:
  oracle = -0.007947
  h7     = +0.014601
  h9 s0  = +0.004884
  h9 s1  = +0.014554

B=4,K=192,D=672:
  oracle = -0.002221
  h7     = +0.010381
  h9 s0  = +0.008074
  h9 s1  = +0.007749

B=4,K=192,D=768:
  oracle = +0.003740
  h7     = +0.005161
  h9 s0  = +0.013468
  h9 s1  = +0.007313
```

Best paid row in the corrected high-arity sweep:

```text
B=4,K=128,D=512,h9_fixed_slack0
mean log2 rho = +0.004884
geometric rho = 1.003391
```

Best oracle lower bound:

```text
B=4,K=128,D=512
mean log2 rho = -0.007947
geometric rho = 0.994507
```

## Reading

The corrected high-arity sweep is the cleanest answer so far to "if K goes
higher, does all-block recursion flip?"

```text
free-boundary/oracle: yes, several rows are compressive
paid H7/H9 rows: no, still expanding
closest measured paid gap: +0.004884 mean log2 rho
```

That is a very small repeated-pass gap, but it is still positive. The missing
piece is not pass freshness or birth/open metadata. It is still the paid
witness boundary / selector channel.

## Verdict

H50 did not find a paid maintained-recursion crossing. It did improve the
scientific map:

- all-block rewrite keeps fresh dice;
- high arity helps and can make oracle recursion compressive;
- giving `K=128/192` enough atoms does not make H7/H9 paid recursion cross;
- the nearest measured paid target is now `B=4,K=128,D=512,H9 slack0` with
  `mean log2 rho=+0.004884`.

The next genuinely different paid witness to test is the normalized
collective-cover `Q(x)` route from H29/H44, not another arity syntax variant.
That lane must report `E_uniform[-log2 Q(X)] - n` as the source/prior lift
needed, because normalized `Q` cannot beat uniform on average without a
non-uniform premise or hidden channel.

## Guardrail

A theorem scout pointed out a scoring trap. Repeated total-cover passes collapse
to one final lossless code once every choice and length channel is paid:

```text
Pr_uniform[L(X) <= n-s] <= 2^-s
E_uniform[L(X)] >= n
```

Also:

```text
sum_t log rho_t = log(L_T / n)
```

So a negative `E[log rho]` is a useful search signal only when the internal
stream is prefix/length-complete and padding/EOF constants are paid. Tiny
negative log drift from EOF, zero-length pathologies, or virtual padding is
bookkeeping dust, not a recursive engine. Future H49/H50 rows must therefore
report expected bits/excess alongside log drift whenever variable whole-file
length is involved.
