# H65 - Public Invariant Exhaustion

Date: 2026-06-17

## Question

Can a fixed board, public permutation, CRT clock, affine/Feistel orbit, canonical
normal form, EOF trim, public lane, or profile schedule be a free invariant that
keeps repeatable stateless compression alive?

H65 reduces all of those to a finite decoder question:

```text
how many final visible states can the decoder distinguish?
```

If a proposal claims more winning inputs than visible final states, the excess
is hidden path/profile/phase information. If the invariant is truly public, it
shows up as lost eligible fraction or match supply.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H65-public_invariant_exhaustion.py
```

The kernel reports:

- visible final-state fraction;
- apparent fraction before charging hidden choices;
- hidden bits;
- finite checksum/referee budget;
- paid selector bits;
- public lane loss;
- charged fraction after those costs.

## Representative Result

For `n=16,P=4,s=1,A=3,lane=0.1,C=16,lambda=4`:

```text
fixed exact public path:          charged fraction 0.062500
EOF visible final states:         charged fraction 0.124985
variable path hidden:             apparent 0.989365, hidden 2.984750, charged 0.124985
variable path with checksum:      charged 0.989365, but consumes finite referee budget
best-of profile path paid:        apparent 1.000000, paid selector 6.339850, charged 0.124985
public lane mask:                 public loss 3.321928, charged 0.012499
```

The checksum row is deliberately finite: it can buy this tiny demo, not
arbitrary recursion. Once the hidden path/profile stream exceeds
`C-lambda`, the same hidden channel returns.

## Verdict

H65 is the finite public-invariant exhaustion test:

```text
extra apparent coverage = hidden decoder state
public derivation = reduced eligible fraction or match supply
finite referee = finite K only
```

No tested invariant beats the counting ledger. A future candidate has to show a
new row where charged fraction exceeds visible fraction without a hidden
selector, and then explain why that row is not just a non-uniform source prior.
