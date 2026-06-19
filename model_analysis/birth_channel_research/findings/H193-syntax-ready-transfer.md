# H193 - Syntax-Derived Ready-State Transfer

## Conjecture

```text
The stream syntax itself can derive whether the next slot is raw-ready or
witness-ready, removing the local raw/witness mode channel and maintaining
fresh witness supply across passes.
```

This is the first branch after H190-H192 stopped mutating the single-layer
mode codebook.

## Kernel

`H193-syntax_ready_transfer.py`

The kernel builds an exact finite witness inventory using current V1/J3D1 costs,
then tests two public mechanisms:

```text
ready-state DFA:
  q is derived from decoded syntax by public rules such as parity, covered,
  short-covered, or toggle-covered
  each q chooses raw, all-witness mixture, best-witness mixture, or canonical
  partition coding

closed canonical partition:
  C_0 = outputs with canonical witness
  C_{t+1} = outputs whose canonical witness child remains in C_t
  C_t uses witnesses, complement uses public complement rank/fallback mass
```

No open/carry map, birth-pass map, hit map, or final-position ledger is charged.
The state is decoder-derived.

## Result

Representative ready-state rows:

```text
N=16,Wmax=16, rule=short, raw/canonpart:
  pi1U=0.003830, meanU=16.000198, gainU=-0.000198,
  entropy_rate=15.999251, inside_gain=0.000749

N=16,Wmax=16, rule=covered, raw/canonpart:
  pi1U=0.865829, meanU=16.044693, gainU=-0.044693,
  entropy_rate=15.836179, inside_gain=0.163821
```

The inside gain is real only for the syntax-shaped emitted distribution. For
arbitrary uniform next items, the KL/source tax cancels it.

Representative closed-partition rows:

```text
N=16,Wmax=8,t=0: support=505,  gainU=-0.055049
N=16,Wmax=8,t=1: support=9,    gainU=-0.000113
N=16,Wmax=8,t=2: support=0,    gainU=0

N=12,Wmax=8,t=3: support=1,    gainU=-0.000646
```

The nearest nonzero-support miss is:

```text
N=16,Wmax=8,t=1: -0.000113 bits/layer
```

but support has collapsed to `9 / 65536`, so the row is a finite knee, not a
maintained recursive regime.

## Bill

For any public state distribution `P_q` and arbitrary uniform next item:

```text
E_U[-log2 P_q(X)] = N + D(U || P_q) >= N
```

The DFA state is geometry unless it predicts the next target. When it does
predict by construction, that is a source-shaped/reachable law and must pay the
same KL tax from arbitrary uniform data.

Equivalently, the full ready-state decoder induces a semimeasure:

```text
Q_N(x) = sum_{d decodes to x} 2^-L(d)
E_U[-log2 Q_N(X)] = N + D(U || normalized(Q_N)) - log2(sum_x Q_N(x))
```

For valid prefix/arithmetic state-conditioned codebooks, the state transfer
matrix `K_ij = sum_{d:i->j} 2^-L(d)` has row sums `<=1`, hence `rho(K)<=1`.
Rows with `rho>1` are overfull, ambiguous, or source/reachable restricted.

Closed partitions pay by thinning support:

```text
C_{t+1} subset C_t
complement rank/fallback length rises as C_t shrinks
```

## Mutation

Syntax-derived readiness does not create arbitrary-uniform row mass. The next
plausible attack is a finite-state reversible transform/language search: force
all inputs into a public self-delimiting language, price the transform tax
`m-N`, then retest witness supply and closure across passes.
