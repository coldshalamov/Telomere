# H181 - Finite Referee / Survivor Capacity

## Conjecture

```text
A finite checksum/referee can let stateless decode prune many hidden readings
only by paying the entropy of those readings.
```

This reopens trial-decode, checksum pruning, non-prefix records, and
keep-what-decodes survivor filters under the most favorable model: the true
reading is guaranteed to pass the stored/root referee, while each wrong reading
survives independently with probability `2^-c`.

## Kernel

`H181-finite_referee_survivor_capacity.py`

The kernel separates:

- hidden branch supply: `M = b^(records * passes)`;
- naming/referee cost: `c` checksum or referee bits;
- recursive drift: fixed `c` versus growing `records * passes`;
- exact decode risk: expected false survivors and probability of unique decode.

For `M` possible readings:

```text
E[false survivors] ~= M / 2^c
P(unique) ~= exp(-M / 2^c)
```

Reliable unique decode at target probability `u` requires:

```text
c >= log2(M) - log2(-ln(u))
```

So a 99% uniqueness target needs about `log2(M) + 6.64` bits.

If public structure already filters wrong openings by `E` bits, the local
ambiguity is:

```text
M_eff = 1 + (T - 1) * 2^-E
```

That buys a finite knee, not a free asymptotic channel.

## Result

Representative rows:

```text
b=2,R=8,P=1,c=8:   log2M=8,   Efalse=1, p_unique=0.367879
b=2,R=8,P=1,c=16:  log2M=8,   Efalse=0.003906, p_unique=0.996101
b=2,R=8,P=4,c=32:  log2M=32,  Efalse=1, p_unique=0.367879
b=4,R=32,P=16,c=32: log2M=1024, Efalse=4.186e298, p_unique=0
```

Required 99% rows:

```text
b=2,R=32,P=16: hidden=1 bit/step, c_req=519, paid=1.013672 bits/step
b=4,R=32,P=16: hidden=2 bits/step, c_req=1031, paid=2.013672 bits/step
```

The exact tiny simulation agrees with the formula:

```text
candidates=4096 c=20 measured=0.996000 poisson_pred=0.996101
```

Structural pruning rows:

```text
T=64,E=9.36:    bill/record=0.132082, c_req99=11 for R=32
T=655,E=9.36:   bill/record=0.996577, c_req99=39 for R=32
T=65536,E=9.36: bill/record=6.654372, c_req99=220 for R=32
```

## Bill

A finite referee is not a free stateless birth/open/salt channel.

If the hidden ambiguity contains `log2(M)` bits, then reliable stateless
selection needs about `log2(M)` referee bits plus a reliability margin. Paying
fewer bits leaves exponentially many false readings across records or passes.
Public structural filters reduce `M`, but once `T` grows well past `2^E`, the
slope returns as roughly `log2(T)-E` bits per record.

## Mutation

Close finite checksum/referee pruning as an independent capacity source. Keep
it only for bounded toy regimes or as an audit guard after another mechanism
makes the branch choices public. The next attack should try to make the choices
public by construction, or prove a no-tax recurrent population law with its
source/reachable-set tax explicitly paid.
