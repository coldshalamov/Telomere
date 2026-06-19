# H210 - Position / Final-Board Channel Converse

## Conjecture

```text
Relative position, final boards, lanes, and modular wrap can make salt/order
visible to a stateless decoder, but the visible state is paid as arrangement
entropy or as match-supply thinning.
```

## Kernel

`H210-position_channel_converse.py`

The kernel reports exact end-state capacities:

```text
unordered occupancy = log2 C(Q,R)
ordered placement   = log2 (Q)_R
fixed pass lanes    = sum_t log2 C(Q_t,r_t)
free lane counts    = log2 C(Q,R)
birth labels        = R log2 P
```

It also reports residual birth ambiguity after occupancy capacity and compares
the bill against a 2-bit-per-record savings budget.

## Result

Representative default rows:

```text
R=1000,Q=1111,rho=0.900,P=64:
  occ/R=0.516089
  birth/R=6
  residual=5483.911082
  netOcc=+1.483911
  netLane=-4

R=1000,Q=2000,rho=0.500,P=4:
  occ/R=1.994191
  birth/R=2
  residual=5.808821
  netOcc=+0.005809
  netLane=0

R=1000,Q=10000,rho=0.100,P=16:
  occ/R=4.683723
  birth/R=4
  residual=0
  netOcc=-2.683723
  netLane=-2
```

Exact selected case:

```text
R=1000,Q=2000,P=16:
  log2 C(Q,R)=1994.191179
  log2 (Q)_R=10523.589
  fixed equal pass lanes=1938.923992
  variable lane counts=1994.191179
  independent birth labels=4000
  residual birth after occupancy=2005.808821
```

## Bill

Dense boards can be cheap enough to carry a finite boundary note, but they do
not carry an unbounded pass/salt ledger.  A public lane restriction costs
`log2 P` bits per record in match supply; a final arrangement carries at most
`log2 |valid final states|` bits and must be stored as end-state entropy.

## Mutation

Final-board ideas remain valuable decode geometry and finite amortization
tools.  They are not a free many-pass salt channel.  The useful next target is a
bounded dense-board construction with an explicit maximum `P` before residual
birth entropy exceeds the per-match margin.
