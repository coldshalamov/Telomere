# H174 - Final-Board Salt Capacity

Date: 2026-06-18

## Question

Reopen the final-position / egg-carton idea in the intended form:

- large fixed or virtual board;
- records may move, bundle, wrap modulo, and use position as salt;
- only final surviving records and final positions are stored once;
- if survivor count shrinks, the final position note may become cheaper.

Does optimal end-state entropy beat the missing birth/open/salt channel, or does
it secretly store the same information?

Runnable artifact:

```text
model_analysis/birth_channel_research/H174-final_board_salt_capacity.py
```

## End-State Entropy

For `R` final survivors in coordinate space `Q`:

```text
unordered occupancy: log2 C(Q,R)
ordered positions:   log2 (Q)_R
valid arrangements:  log2 |E_valid|
```

If the encoder hides adaptive salt, birth, open/carry, or ordering choices in
the final arrangement, the decoder can observe at most:

```text
log2 |E_valid|
```

bits from that arrangement. If the arrangement is stored, those bits are in the
file. If the arrangement is public/deterministic, the adaptive channel has zero
entropy.

## Shrinking Survivors

With `Q=N=1,000,000`, unordered final occupancy has:

```text
R/Q     pos/orig   pos/R   2-pos/R   <2b?
0.990   0.080785   0.082    1.918    yes
0.900   0.468986   0.521    1.479    yes
0.750   0.811268   1.082    0.918    yes
0.500   0.999990   2.000    0.000    yes
0.250   0.811268   3.245   -1.245     no
0.100   0.468986   4.690   -2.690     no
0.030   0.194383   6.479   -4.479     no
0.010   0.080785   8.079   -6.079     no
0.001   0.011401  11.401   -9.401     no
```

This confirms the user's suspicion in one sense: shrinking `R` can make the
final-position note cheap per original atom. But it becomes expensive per
surviving record. The board is below a 2-bit per-survivor budget only when the
final board is dense, roughly `R/Q >= 0.5`.

## Birth-Pass Ledger Comparison

For arbitrary `P`-way birth labels, the naive ledger is:

```text
R log2 P
```

A `Q=N` occupancy board can be cheaper than that ledger:

```text
P     R/Q    pos/R  log2P  can encode all?  cheaper?
256   0.500  2.000  8.000              no       yes
256   0.100  4.690  8.000              no       yes
256   0.030  6.479  8.000              no       yes
256   0.010  8.079  8.000             yes        no

4096  0.500  2.000 12.000              no       yes
4096  0.100  4.690 12.000              no       yes
4096  0.030  6.479 12.000              no       yes
4096  0.010  8.079 12.000              no       yes
4096  0.001 11.401 12.000              no       yes
```

The key reading is subtle:

- if final occupancy is cheaper than `R log2 P`, it does not have enough states
  to encode arbitrary independent `P`-way birth labels;
- it can still be useful if the codec only permits a restricted history subset,
  or if the arrangement bits were already needed for placement.

An expanded `Q=N*P` board does have enough coordinates for ready subset plus
birth class, but it costs essentially that same information:

```text
P     R/Q0   C(NP,R)/R   ready+birth/R   extra/R
256   0.100      12.764          12.690     0.074
256   0.030      14.501          14.479     0.022
4096  0.100      16.765          16.690     0.075
4096  0.030      18.501          18.479     0.022
```

## Position-As-Salt

For a 2-bit per-survivor salt request:

```text
R/Q     visible/R  request/R  delivered/R  net/R
0.900       0.521      2.000        0.521  0.000
0.750       1.082      2.000        1.082  0.000
0.500       2.000      2.000        2.000  0.000
0.250       3.245      2.000        2.000 -1.245
0.100       4.690      2.000        2.000 -2.690
0.030       6.479      2.000        2.000 -4.479
0.010       8.079      2.000        2.000 -6.079
```

When `visible/R < request/R`, the state cannot carry all requested salt choices.
When `visible/R > request/R`, the state can carry them but costs more than the
salt budget. At equality, it breaks even as an information channel. It does not
create positive all-data capacity by itself.

## Public Pass/Lane Classes

If the board is split into public pass or lane classes, the final-state count is
not guessed per record. It is:

```text
fixed lane counts:   log2 product_p C(Q_p, r_p)
variable counts:     log2 sum_{sum r_p=R} product_p C(Q_p, r_p)
```

For equal lane capacities, the variable-count row reduces to `log2 C(Q,R)` by
Vandermonde's identity.

With `Q=1,000,000`, `R=100,000`, and `8` equal lanes:

```text
case                         state/R  lost/R  d1 loss  d4 loss
free counts over all lanes     4.690   0.000   -0.000   -0.000
balanced fixed lane counts     4.689   0.001   -0.000   -0.000
two public active lanes        2.427   2.263    2.000    0.549
one public active lane         0.902   3.788    3.000    1.273
```

Public lanes trade state entropy against match supply. Fixed balanced counts
barely reduce entropy. Concentrating into one or two active lanes lowers
final-state entropy, but then the encoder pays public-lane supply loss unless
it has enough independent public choices.

## Ordering

If stream order is not otherwise public, ordering is a major extra bill:

```text
R/Q    occ/R   log2 R!/R   ordered/R
0.500  2.000       17.489      19.489
0.100  4.690       15.167      19.857
0.030  6.479       13.430      19.910
0.010  8.079       11.846      19.924
```

Orderless decode is therefore only free for a true bag/confluent source, or
when public child placement restores order without adaptive choices.

## PCTB Mechanical Check

The existing PCTB kernel:

```text
python model_analysis/proof_kernel/pctb_ledger.py
```

confirms that board mechanics and salted reverse opens are reversible:

```text
M=24, B=8, passes=3, maxk=2
final eggs: 22
ROUND-TRIP EXACT: True
```

But carry-only final boards are not bounded-loss. For `M=1000`, `B=8`,
`maxk=5`, the carry-only row reaches:

```text
P=64: pos bits 166871, total/raw 21.867
```

Dense collapse can overcome the position bill in that toy:

```text
rho=0.10, P=64: net vs raw +5051
rho=0.30, P=16: net vs raw +16124
```

That supports the narrow claim: final boards can amortize a bad pass diary after
real survivor collapse. It does not support treating final positions as free.

## Verdict

Final boards are still alive as a decode-geometry tool:

```text
public or stored final positions
+ position-derived salt
+ public child placement
+ restricted history subset or near-total dense board
```

They can beat a naive per-pass diary. They can also piggyback birth/salt facts
onto placement bits if a board codec already has to store those positions.

They do not provide a free extra channel. The exact cost is:

```text
log2(valid final arrangements)
```

The best surviving target is therefore not a sparse survivor board. It is a
dense or near-total board where:

```text
final occupancy cost per survivor < measured salted gain per survivor
```

and the next proof obligation is to show that the salted match gain exceeds
that exact end-state bill under current Telomere witness costs.
