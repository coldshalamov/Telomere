# Telomere Birth-Channel Results

Date: 2026-06-14

Scope: this report prices candidate mechanisms for maintaining fresh salted
hash-match opportunities across recursive or multi-pass Telomere operation while
keeping decode stateless except for a fixed/root/end header. It does not run
corpus compression or large seed searches. It uses counting, entropy ledgers,
and small deterministic Python kernels.

## Reopened Status

There is **no completed arbitrary-content winner**. The previous TST/STF/BBL
stack is useful evidence, but it does not satisfy the reopened success bar:

- TST/STF are generated/reachable positive controls with stateless decode.
- BBL is a finite bundle-only ledge that prices wrong-pass ambiguity.
- None proves that arbitrary or unshaped content keeps matching at useful
  density under the uniform hash law.
- Under the updated finish condition, a completed answer would need a
  configuration that maintains compression over many passes and can
  theoretically reach about 50% compression on arbitrary/random data. Nothing
  in this report has met that bar.

The active kernel for the reopened search is:

```text
model_analysis/birth_channel_research/arbitrary_freshness_kernels.py
```

It attacks the three requested families directly:

### Family 1: Decoder-known nonce channels

Visible nonce bits are known to the decoder before expansion, so the toy
round-trips statelessly. But the nonce is stored in the record and is therefore
paid as address width:

```text
k nonce  record   gross      hit p  E win/window  random hits
      0      12       4    0.01562       0.06250     2/256
      1      13       3    0.03125       0.09375     7/256
      2      14       2    0.06250       0.12500    15/256
      3      15       1    0.12500       0.12500    34/256
      4      16       0    0.25000       0.00000     0/256
      5      17      -1    0.50000       0.00000     0/256
```

Result: visible nonces are a paid seed-depth tradeoff, not a free
birth/freshness channel.

The public-lane mutation stores no lane id. The encoder tries `K` public lanes;
the decoder tries them all and pays for surviving readings:

```text
lanes final items  records payload bits   candidates  ambig bits orig in set   net vs raw
    1          23        1          117            1       0.000        True      -21.000
    2          23        1          117            1       0.000        True      -21.000
    4          22        2          114            3       1.585        True      -19.585
    8          19        5          105      200000+      17.610     unknown    <=-26.610
```

Result: public lanes increase search supply without stored metadata, but wrong
lanes often parse. The bill reappears as surviving decode ambiguity unless a
stronger self-dating grammar can reject wrong lanes without thinning true
arbitrary targets.

The neighbor-context mutation tried to make the nonce visible from local stream
geometry. The full left/right-neighbor version failed as a codec because the
right neighbor is not stable: a later adjacent replacement can change what the
decoder sees. The stable mutation uses only left neighbor plus packed output
position:

```text
round_trips_or_capped=20/20 exact_present=20/20 capped=0
pass  avg windows  avg matches  hit/window   avg gain
   1        19.00        0.250     0.01316      0.750
   2        17.33        0.000     0.00000      0.000
mean candidate count before checksum=1.05
mean payload gain vs original raw=-19.250 bits
mean lower-bound charged gain=-19.300 bits
```

Result: left-context/position is a real decoder-known nonce channel with exact
round trip and low ambiguity in this toy, but it did not sustain arbitrary
match supply or beat raw payload accounting.

The self-consistent output-derived nonce mutation stores no nonce. Decoder tries
nonce values and keeps only expansions whose output hashes back to the nonce:

```text
nonce   book  record   gross      hit p       hits  mean cand  E net/window
    0   1019      12       4    0.01555    2/256        1.000       0.06219
    1   1050      12       4    0.01602    2/256        1.500       0.05471
    2    999      12       4    0.01524    1/256        1.000       0.06097
    3   1025      12       4    0.01564    6/256        1.833       0.04888
    4   1057      12       4    0.01613    6/256        1.833       0.05041
    5   1031      12       4    0.01573    8/256        1.625       0.05191
    6    958      12       4    0.01462    7/256        2.286       0.04104
```

Result: output-derived nonces are stateless but do not multiply arbitrary
target coverage. They select roughly one self-consistent output per seed, with
a small ambiguity tail.

### Family 2: Target-refresh without salt-refresh

The fixed-universe composition codec has exact encode/decode and needs no pass
salt, birth tag, or final-position note. Records recursively open in place.
On 200 unshaped random 96-block trials:

```text
pass  avg windows  avg matches  hit/window   avg gain
   1        95.00        2.720     0.02863      8.160
   2        92.06        0.065     0.00070      0.324
   3        89.25        0.000     0.00000      0.000
mean final wrapped-bit gain=8.460 bits
mean final original-payload gain=-87.540 bits
```

Result: target churn alone did not maintain match supply. It also showed an
important accounting trap: gaining against literal-wrapped working state is
still bloat against original payload.

The arity-flex mutation allowed fixed unsalted records of arity 2-5, so later
targets could include record/literal and record/record spans:

```text
valid fixed-universe spans by arity: a2=136, a3=114, a4=92, a5=65
pass  avg windows  avg matches  hit/window   avg gain       a2/a3/a4/a5
   1       374.00        1.010     0.00270      3.105 0.00/0.99/0.01/0.00
   2       361.48        0.000     0.00000      0.000 0.00/0.00/0.00/0.00
mean final wrapped-bit gain=3.105 bits
mean final original-payload gain=-92.895 bits
```

Result: effective-length migration did not stabilize match supply in this
unshaped toy.

The full-cover bundle-lattice mutation takes the "replace every block" idea
literally. Every output unit is a seed record, so the decoder never needs a
birth pass, open/carry bitmap, or final-position note. The encoder searches
every interval up to a maximum arity and runs an optimal shortest-path cover
over exact seed hits. This is stronger than the greedy "try arity 1, then 2,
..." algorithm because it gives the bundle lattice its best possible tiling.

Exact scaled toy, with real seed books and decode by stored arity+seed only:

```text
exact toy: block=3 bits blocks=72 max_arity=6 arity_bits=3
net/record is after paying the arity header. Negative rows are
intentional bloat rows: they ask how much overpayment is needed to
make a full all-record cover appear.
net/rec gross d   cover%   records   charged  net bits    E covers
     -2       1    0.880    15.074   246.148   -30.148   1.299e+11
     -1       2    0.085    17.647   233.647   -17.647   2.078e+03
      0       3    0.000     0.000       nan       nan   8.716e-04
      1       4    0.000     0.000       nan       nan   2.732e-09
      2       5    0.000     0.000       nan       nan   3.025e-14
      3       6    0.000     0.000       nan       nan   7.610e-19
```

Closed-form seed-depth tradeoff for 3-byte base blocks with one 3-byte seed
table reused across longer bundles:

```text
 arity target bits    hit/window gross before hdr
     1          24     1.000e+00                0
     2          48     5.960e-08               24
     3          72     3.553e-15               48
     4          96     2.118e-22               72
     5         120     1.262e-29               96
     8         192     2.673e-51              168
    16         384    4.258e-109              360
```

Result: full replacement really solves the birth-pass/open-carry ordering
problem, but it replaces that problem with a full-cover tiling requirement. To
save `s` bits after the arity header, each candidate interval hits with
probability about `2^-(header+s)`. In the exact toy, rows that cover require
bloating records; the first non-bloating row already has less than `0.001`
expected complete covers. Longer bundles amortize headers, but exact-match
probability falls by the same missing payload bits unless the stored seed grows
toward the full target length.

The adaptive smallest-replacement cover is the stronger version of the user's
overlap idea. Every interval may use the smallest seed width found up to a
bounded over-search limit; bloating records are allowed as bridge pieces; then
a shortest-path cover chooses the cheapest all-record tiling. This lets a later
bundle beat a set of bloating singles.

```text
exact toy: block=3 bits blocks=48 max_arity=5 arity_bits=3 max_extra_seed=2
       ledger   cover%   records      seed    arity    width   charged       net
   free-width    1.000    15.280    85.205   45.840    0.000   131.045    12.955
   width-paid    1.000    11.230   104.800   33.690   56.150   194.640   -50.640
```

Closed-form smallest-seed CDF for one target:

```text
 L bits seed bits   Pr[min<=b]  free rec  paid rec
     24        16      0.00778        19        24
     24        20      0.11750        23        28
     24        22      0.39347        25        30
     24        23      0.63212        26        31
     24        24      0.86466        27        32
     48        40      0.00778        43        48
    120       111      0.00390       114       119
```

Result: the overlap/order-statistic effect is real. The invalid free-width
oracle compresses the tiny exact toy. But stateless decode needs to know each
variable seed width or seed-rank boundary; once that class is stored, the same
cover becomes strongly negative.

The recursive adaptive-cover churn mutation turns that one-pass cover into an
actual stateless recursive codec. Every pass covers the entire current bitstream
with records from the same fixed seed universe. There is no literal/open bitmap
and no birth-pass salt. The only end-header side channel is the charged
alignment pad count for each layer:

```text
toy grammar: block=3 maxA=5 width_bits=5 passes=6 n_bits=144
round_trips=80/80 completed_all_passes=80/80
pass   avg in avg pad   avg out    ratio  records     cmp%     a1/a2/a3/a4/a5
   1   144.00   0.000    195.20    1.356    11.20    2.532 0.1/0.5/1.8/2.8/6.1
   2   195.20   1.075    265.61    1.361    15.12    2.186 0.0/0.7/2.2/3.8/8.4
   3   265.61   1.050    359.60    1.354    20.43    4.017 0.1/0.8/2.5/5.5/11.5
   4   359.60   0.887    485.82    1.351    27.52    2.841 0.1/1.0/3.1/7.5/15.7
   5   485.82   1.113    654.14    1.346    37.40    3.598 0.1/1.6/4.8/9.9/21.0
   6   654.14   1.062    881.66    1.348    50.20    2.981 0.2/1.8/6.5/13.5/28.2
mean final payload bits=881.663
mean charged end-header bits=15.000
mean total net vs original=-752.663 bits
```

Result: this is the clean all-block-replaced target-refresh version. It
decodes statelessly and makes birth pass irrelevant, but the fixed record
language is not a compression attractor under the uniform hash law. The target
population keeps changing; the match economics do not improve, and each layer
amplifies the width/address overhead by about `1.35x`.

The overlapping-option seed-rank crossover model calculates the user's
`1+2+3+4+5 = 15` choices per interior block directly at 3-byte block scale.
For an `L`-bit interval, unlimited search gives first matching seed rank about
`Exp(1) * 2^L`; the DP then chooses the best overlapping tiling.

```text
asymptotic simulation: block=24 bits, blocks=600, trials=80
     rank coding  maxA opts/block   gain@h0   gain@h3  h crossover
 oracle-log-rank     1          1     0.823    -2.172        0.833
 oracle-log-rank     2          3     1.467    -0.535        2.142
 oracle-log-rank     3          6     1.615    -0.048        2.909
 oracle-log-rank     5         15     1.680     0.279        3.876
 oracle-log-rank     8         36     1.695     0.421        4.739
 ideal-geometric     1          1    -1.445    -4.449         none
 ideal-geometric     2          3    -0.389    -2.047         none
 ideal-geometric     3          6    -0.172    -1.310         none
 ideal-geometric     5         15    -0.061    -0.751         none
 ideal-geometric     8         36    -0.023    -0.451         none
      delta-rank     1          1    -7.665   -10.653         none
      delta-rank     2          3    -4.533    -6.130         none
      delta-rank     3          6    -3.497    -4.622         none
      delta-rank     5         15    -2.078    -2.737         none
      delta-rank     8         36    -1.471    -1.900         none
```

Result: with the forbidden `log2(first_rank)` oracle, max arity 5 crosses over
near `3.876` overhead bits per record, so a 3-bit header appears positive.
That is the calculation the previous fixed-seed-table model missed. With a
self-delimiting rank code, however, the same 15-option row is negative even at
zero record overhead. Even the ideal arithmetic code for the geometric
first-hit rank distribution stays negative (`-0.061` bits/block at zero
overhead for max arity 5). The hidden channel is not the 5-block target length;
it is the seed-rank witness length/terminator needed for stateless parsing.

The finite-depth mutation asks the same question as "do we actually need to
search 15 bytes?" For a global search cap of `N` seed bits, every interval may
use its first match only if `rank <= 2^N`; the DP then chooses the cheapest
full cover. This separates three ledgers: a free log-rank oracle, a paid
selected-rank lower bound, and a parseable fixed-width `N`-bit seed field.

```text
finite search simulation: block=24 bits, maxA=5, opts/block=15, blocks=600, trials=80, h=3
 search    p(a4)    p(a5)   cover%    oracle    sel LB     sel+h    fixedW   rec/bl  bits/rec
     72  0.00000  0.00000  100.000    -0.059    -0.596    -2.043    -4.517    0.482    51.005
     80  0.00002  0.00000  100.000    -0.057    -0.611    -2.026    -3.667    0.472    52.181
     88  0.00390  0.00000  100.000    -0.028    -0.599    -2.004    -6.322    0.469    52.505
     92  0.06059  0.00000  100.000     0.072    -0.561    -1.899    -7.099    0.446    55.080
     96  0.63212  0.00000  100.000     0.172    -0.491    -1.699    -3.349    0.403    60.790
    104  1.00000  0.00002  100.000     0.172    -0.485    -1.680    -2.750    0.398    61.466
    112  1.00000  0.00390  100.000     0.190    -0.490    -1.680    -4.750    0.397    61.752
    116  1.00000  0.06059  100.000     0.241    -0.466    -1.605    -5.388    0.379    64.492
    120  1.00000  0.63212  100.000     0.279    -0.423    -1.477    -2.604    0.351    69.549
    122  1.00000  0.98168  100.000     0.288    -0.428    -1.487    -1.182    0.353    69.206
    128  1.00000  1.00000  100.000     0.285    -0.425    -1.478    -2.200    0.351    69.591
```

Result: under the free witness oracle, the crossover starts before 15 bytes:
around 92-96 search bits in this model, because 3-block intervals are
saturated and 4-block intervals begin to supply enough overlap. At 120 bits
the oracle is near its asymptote. But the parseable fixed-width row is
negative, and the selected-rank lower bound remains negative even after the
oracle DP biases the chosen witnesses toward small ranks. The approach is
understood: the overlap/order-statistic effect is real, but the stateless
decoder still needs the exact rank witness.

The block-local coupling mutation restates the same calculation in the user's
terms: for each interior block, there are `1+2+3+4+5 = 15` containing
intervals. The `local UB` column lets every block independently choose its
best containing interval; this is optimistic because neighboring choices can
conflict. The `legal` column is the actual non-overlapping shortest-path cover.

```text
finite search simulation: block=24 bits, maxA=5, opts/block=15, blocks=600, trials=80, h=3
 search  hit opt  pos opt  local UB     legal    sel LB     sel+h   rec/bl   cover%
     72    4.889    0.701     0.255    -0.063    -0.598    -2.044    0.482  100.000
     80    5.987    0.700     0.260    -0.050    -0.601    -2.016    0.472  100.000
     88    6.002    0.713     0.274    -0.032    -0.601    -2.006    0.468  100.000
     92    6.230    0.943     0.386     0.061    -0.569    -1.906    0.446  100.000
     96    8.497    1.172     0.492     0.166    -0.489    -1.691    0.401  100.000
    104    9.967    1.171     0.489     0.169    -0.494    -1.688    0.398  100.000
    112    9.985    1.184     0.514     0.187    -0.493    -1.683    0.397  100.000
    116   10.263    1.471     0.581     0.248    -0.462    -1.603    0.381  100.000
    120   13.106    1.754     0.613     0.283    -0.430    -1.496    0.355  100.000
    122   14.842    1.767     0.616     0.285    -0.426    -1.485    0.353  100.000
    128   14.933    1.752     0.610     0.280    -0.427    -1.483    0.352  100.000
```

Result: this validates the intended crossover statement more directly. At 120
search bits, an average block is touched by `13.106` finite matching intervals
and `1.754` individually compressive intervals; the legal non-overlapping cover
is still positive (`+0.283` bits/block) under the free witness oracle. So the
right statement is not "a 120-bit 5-block bundle cannot help." It is: overlap
and best-of-many selection can cross over well before the naive fixed-bundle
framing, but the crossing currently lives in the hidden seed-rank boundary
channel. The paid selected-witness lower bound is still negative (`-0.430`, or
`-1.496` with a 3-bit marker).

The collective selected-rank entropy mutation tests whether that conclusion is
too pessimistic because selected ranks are biased low. The oracle DP first
chooses the best tiling by log-rank cost. Then a public arithmetic model codes
the selected `(arity, floor(log2 rank))` symbols at empirical selected entropy,
and only raw lower rank bits are emitted inside each bin:

```text
asymptotic simulation: block=24 bits, blocks=600, trials=80
 maxA opts/block    oracle  entropy LB   +marker rec/block  bits/rec
    2          3    -0.544      -0.815    -2.652     0.612    40.534
    3          6    -0.040      -0.591    -2.005     0.471    52.167
    5         15     0.297      -0.423    -1.489     0.355    68.782
    8         36     0.432      -0.331    -1.199     0.289    84.055
```

Result: collective coding helps compared with a universal integer code, but it
still stays negative. The arity/log-rank selected distribution is cheap enough;
the exact lower rank bits inside the selected bucket still consume the gain.

The recursive full-cover overlap dynamics mutation then asks whether repeated
all-block replacement changes the answer. Every pass is a complete interval
cover, so there is no open/carry bitmap and no birth-pass tag. Under the
uniform hash law, the reserialized target stream is random again, so target
churn repeats the same one-pass gain distribution unless some new visible state
variable is introduced:

```text
projection: start=14400 bits block=24 maxA=5 overhead=3 passes=64
               model   status  gain/block    factor   P half      len@1      len@8     len@32     len@64
     oracle-log-rank  invalid       0.277   0.98845     59.7    14233.7    13121.9     9928.8     6845.9
     ideal-geometric     paid      -0.750   1.03126    never    14850.1    18420.2    38555.5   103230.8
          delta-rank     paid      -2.741   1.11421    never    16044.6    34204.6   458408.6 14592945.0
 selected-entropy-LB  paid-lb      -0.426   1.01773    never    14655.4    16574.4    25273.7    44358.3
     selected+marker  paid-lb      -1.494   1.06227    never    15296.7    23347.2    99507.0   687614.0
```

Result: the recursive attractor exists only in the same invalid free-witness
ledger. Once the selected seed-rank witness is parseable, the first pass grows
and target churn compounds that growth. Full replacement genuinely removes the
birth/open-carry problem, but it does not create arbitrary-content compression
without a cheaper witness language.

The whole-cover ordinal language mutation removes local terminators completely:
encode the entire selected cover as one ordinal in a public arity/rank cover
language. The decoder maps that ordinal to a full cover and expands it. This is
stateless, but now the code is simply a generated codebook whose coverage is the
number of distinct outputs in the language:

```text
exact toy: block=3 bits blocks=6 raw_bits=18
 maxA  rank  log desc   unique    cover%  save/hit    E save
    1     0     0.000        1   0.00000    18.000   0.00007
    1     1     6.000       64   0.00024    12.000   0.00293
    1     2    12.000      729   0.00278     6.000   0.01669
    1     3    18.000    46656   0.17798     0.000   0.00000
    2     0     3.700       13   0.00005    14.300   0.00071
    2     1     8.358      328   0.00125     9.642   0.01206
    2     2    13.401     2457   0.00937     4.599   0.04311
    2     3    18.783    53353   0.20353    -0.783  -0.15936
    3     0     4.585       24   0.00009    13.415   0.00123
    3     1     8.794      444   0.00169     9.206   0.01559
    3     2    13.579     2785   0.01062     4.421   0.04697
    3     3    18.844    57866   0.22074    -0.844  -0.18633
```

Result: a whole-cover ordinal removes local parsing overhead, but short
ordinals cover only a tiny fraction of arbitrary outputs. Broad languages raise
`log desc` toward or above raw payload length. This does not rescue
arbitrary/random average compression.

The whole-cover referee-as-codeword mutation stores a checksum/referee of the
generated cover output instead of storing the cover ordinal. The decoder
enumerates the public cover language and keeps outputs with matching referee
bits:

```text
exact toy: block=3 bits blocks=6 maxA=3 rank=2 unique_outputs=2785 coverage=0.01062
  ref  survivors    uniq%  save/hit    E save  E save+tag
    0   2785.000    0.000    18.000   0.19123    -0.80877
    4    174.990    0.000    14.000   0.14874    -0.85126
    8     12.055    0.000    10.000   0.10624    -0.89376
   10      3.800    0.085     8.000   0.08499    -0.91501
   12      1.610    0.555     6.000   0.06374    -0.93626
   14      1.145    0.855     4.000   0.04250    -0.95750
   16      1.040    0.965     2.000   0.02125    -0.97875
   18      1.010    0.990     0.000   0.00000    -1.00000
```

Result: a referee can replace the ordinal only by becoming the codeword for
the generated output. Short referees leave multiple valid generated outputs;
long referees approach raw length. Reachable hits can show a small expected
save before fallback, but arbitrary data needs a raw/mode channel and the
coverage is too small.

The global-referee interval-cover mutation scales this to the user's overlap
language. It stores no local seed ranks at all; the decoder enumerates a public
interval-cover language and uses one end referee/checksum to choose the output:

```text
exact toy: block=3 bits blocks=6 maxA=3 rank=2 raw=18 unique_outputs=2785
half-size referee bits=9 mean survivors among reachable targets=6.403 unique cost~=log2(unique)=11.443

asymptotic counter: block=24 bits blocks=600 raw=14400 half_ref=7200
  arity   seed   logD/bl     coverage  unique bits  hit save   surv@half
    1-5     24    24.000      0.63213      14399.3       0.7 2^7199.3
    2-5     48    24.000      0.63212      14399.3       0.7 2^7199.3
    3-5     72    24.000      0.63212      14399.3       0.7 2^7199.3
      5     48     9.600    2^-8640.0       5760.0    8640.0 2^-1440.0
      5     72    14.400    2^-5760.0       8640.0    5760.0 2^1440.0
      5     96    19.200    2^-2880.0      11520.0    2880.0 2^4320.0
      5    112    22.400     2^-960.0      13440.0     960.0 2^6240.0
      5    120    24.000      0.63212      14399.3       0.7 2^7199.3
```

Result: moving the witness to one end note does not remove its entropy. When
the language is broad enough to cover a useful fraction of random inputs, a
half-size referee leaves exponentially many generated outputs alive. When the
language is narrow enough for half-size uniqueness, coverage is exponentially
tiny. The end-state referee is the same hidden witness channel in global form.

The canonical-minimum cover mutation asks whether a public tie-breaker can make
the decoder derive the same witness without storing a local rank or global
referee. For every generated output, the canonical witness is the minimum cover
description. This removes duplicate descriptions, but not the need to identify
the output:

```text
exact toy: block=3 bits blocks=6 raw=18 half_code=9 bits
 maxA  rank  log desc  log uniq    dedup    cover% best half%  bits all
    1     2    12.000     9.510    2.490   0.00278    0.00195     9.510
    2     2    13.401    11.263    2.138   0.00937    0.00195    11.263
    3     2    13.579    11.443    2.136   0.01062    0.00195    11.443
    3     3    18.844    15.820    3.024   0.22074    0.00195    15.820

asymptotic canonical bound: block=24 bits blocks=600 raw=14400 half_code=7200 bits
  arity   seed   logD/bl  uniq bits     full cov  best half cov  bits all
    1-5     24    24.000    14399.3      0.63213      2^-7200.0   14399.3
    2-5     48    24.000    14399.3      0.63212      2^-7200.0   14399.3
    3-5     72    24.000    14399.3      0.63212      2^-7200.0   14399.3
      5     48     9.600     5760.0    2^-8640.0      2^-8640.0    5760.0
      5    120    24.000    14399.3      0.63212      2^-7200.0   14399.3
```

Result: canonicalization helps only by collapsing duplicate descriptions of
the same output. A half-size stateless code can still name at most `2^(raw/2)`
outputs. Broad overlap languages cover many random inputs but need almost raw
identity bits; narrow languages can be named cheaply but cover an exponentially
tiny fraction of arbitrary inputs.

The global fixed-depth rank-cover mutation makes that terminator decoder-known
once in a root/header schedule. Every record rank is fixed-width, so no
per-record seed-width class is needed. Raw fallback is treated optimistically
as zero gain when a full all-record cover is missing:

```text
asymptotic simulation: block=24 bits max_arity=5 blocks=480 trials=120 overhead=3
rank bits   cover%  gain/covered  E gain/block
       24    0.000         0.000         0.000
       28    1.000        -7.000        -7.000
       32    1.000       -11.000       -11.000
       40    1.000       -18.840       -18.840
       48    1.000        -7.229        -7.229
       52    1.000        -3.500        -3.500
       56    1.000        -5.500        -5.500
       72    1.000        -4.497        -4.497
       96    1.000        -3.277        -3.277
      100    1.000        -1.750        -1.750
      120    1.000        -2.627        -2.627
```

Result: a global fixed rank width is stateless and parseable, but it removes
the order-statistic benefit of lucky early ranks. Low widths cover with
bloating short records; high widths make long bundles available but charge that
same width to every selected record. No tested global depth crosses positive.

The homophonic literal-recoding mutation gives each payload block multiple
reversible surface encodings. The encoder may choose synonym bits that make a
seed expansion match the surface, while the decoder strips synonyms back to the
same payload:

```text
exact toy: value_bits=4 blocks=128 pair_seed=6
 syn     hits  hit/pair   literal    seed   bitmap   charged       net  p formula
   0   14.275   0.22305   397.800  85.650   51.208   534.658   -22.658    0.22158
   1   14.060   0.21969   499.400  84.360   50.784   634.544  -122.544    0.22158
   2   13.995   0.21867   600.060  83.970   50.720   734.750  -222.750    0.22158
   3   13.425   0.20977   708.050  80.550   49.654   838.254  -326.254    0.22158
   4   13.760   0.21500   803.840  82.560   50.410   936.810  -424.810    0.22158
```

Result: the synonym choices are decoder-visible and genuinely give the encoder
many possible surfaces, but under the uniform hash law they cancel against the
extra surface bits. The probability that a seed projects to a payload pair is
independent of synonym width, while missed literals get longer. Homophonic
freedom is stored surface entropy, not free target refresh.

The global public transform mutation tries a more generous target-refresh
model. It chooses one reversible public transform for the whole layer, stores
that transform index once, then encodes scheduled slots under a fixed seed
universe. This avoids per-window transform coordinates:

```text
toy grammar: span=12 seed=8 gross/hit=4 unique seed images=246
    K     hits   hit/slot     bitmap   K bits    charged        net
    1   15.955    0.06232     90.265    0.000   3098.445    -26.445
    2   15.595    0.06092     88.311    1.000   3098.931    -26.931
    4   16.445    0.06424     90.996    2.000   3099.216    -27.216
   16   18.365    0.07174     97.249    4.000   3099.789    -27.789
   64   19.825    0.07744    101.351    6.000   3100.051    -28.051
  256   22.400    0.08750    109.713    8.000   3100.113    -28.113
```

Idealized large-deviation ledger for one layer:

```text
 q hit     D(q||p)    q*d-H(q)  net incl K
0.06006     0.00000    -0.08744    -0.08744
0.08000     0.00463    -0.08218    -0.08681
0.10000     0.01717    -0.06900    -0.08617
0.12500     0.04181    -0.04356    -0.08537
0.16000     0.08995     0.00569    -0.08426
0.20000     0.16105     0.07807    -0.08298
0.25000     0.27011     0.18872    -0.08139
```

Result: a global transform can raise hit density while amortizing its index,
but under the uniform hash law the transform index is the large-deviation price
of finding that unusually good layer. After the open/carry bitmap is also
priced, the net remains negative. Per-window transform selection would only add
a larger coordinate channel.

The whole-layer rechunk/superposition mutation gives target-refresh a clean
stateless layer codec. Each pass encodes the entire current bitstream with a
fixed unsalted seed universe, literal tokens, and records. The decoder needs
only the fixed format and layer count, then decodes layers in reverse. Greedy
matching checks every bit position, so selected boundaries are visible in the
token stream rather than stored in a sidecar.

```text
toy grammar: literal=2 bits record=11 bits span=14 bits
fixed universe: unique outputs=991 hit_p/window=0.06049 gross per record=3 bits
round_trips=200/200
pass  avg in bits  avg out bits  avg windows  avg matches  hit/window  delta vs in delta vs orig
   1       192.00        280.21       179.00        6.105     0.03411      -88.215       -88.215
   2       280.21        423.41       267.21        8.060     0.03016     -143.195      -231.410
   3       423.41        720.68       410.41        7.420     0.01808     -297.270      -528.680
   4       720.68       1298.05       707.68        8.430     0.01191     -577.370     -1106.050
   5      1298.05       2451.26      1285.05        8.520     0.00663    -1153.210     -2259.260
   6      2451.26       4756.83      2438.26        8.570     0.00351    -2305.570     -4564.830
mean final delta vs original=-4564.830 bits
mean best intermediate delta vs original=-88.215 bits
```

Result: all-position rechunking solves the selected-window side channel by
making boundaries part of the prefix token stream, but then literal tokens carry
the non-hit regions. The first layer found matches, yet it bloated random
inputs; recursive target-refresh amplified the bloat rather than maintaining
net compression.

The adaptive-length target-refresh mutation lets each layer choose the best
public chunk length from a small set and stores only that length index once.
This tests effective-length migration without changing the hash universe:

```text
toy grammar: spans=(10, 12, 14) seed=8 choice_bits=2
pass    avg in  span mode   hits/ch visible net  tight net
   1    512.00         14   0.02225     -34.600     -6.792
   2    544.60         14   0.01962     -36.737     -6.691
   3    579.34         14   0.02314     -37.837     -6.670
   4    615.17         14   0.02114     -40.775     -6.858
   5    653.95         14   0.01861     -43.175     -6.799
```

Closed-form per-slot tight ledger:

```text
 span         p   gross      H(p)   net/slot
   10   0.25000       2   0.81128   -0.31128
   12   0.06250       4   0.33729   -0.08729
   14   0.01562       6   0.11612   -0.02237
```

Result: length choice refreshes boundaries and is cheap as a layer header, but
every fixed-length option still obeys `p*d-H(p)<0` under the uniform hash law.
The adaptive layer just chooses the least-bad negative option; recursion
amplifies the bloat rather than creating a target-refresh attractor.

The public-shuffle scheduled target-refresh mutation tests adjacency refresh
without salt refresh. Before each pass, a decoder-known bit permutation changes
which bits become neighbors, then fixed scheduled chunks are encoded. Decode
parses chunk tokens, expands records, and applies the public inverse
permutation. No pass-varying salt or birth tag is used.

```text
toy grammar: span=14 seed=10 literal-token=15 record=11
fixed universe: unique outputs=991 hit_p/chunk=0.06049 gross seed saving=4 bits
round_trips=200/200
pass  avg in bits  avg out bits    chunks      hits  hit/chunk  vis delta  sparse net
   1       512.00        538.94     36.00     2.265    0.06292    -26.940      -5.820
   2       538.94        567.35     38.01     2.400    0.06315    -28.405      -5.997
   3       567.35        597.57     40.10     2.470    0.06160    -30.220      -6.224
   4       597.57        629.68     42.23     2.530    0.05990    -32.115      -6.567
   5       629.68        663.66     44.48     2.625    0.05901    -33.985      -6.773
   6       663.66        698.54     46.94     3.015    0.06423    -34.880      -6.929
   7       698.54        736.71     49.42     2.815    0.05695    -38.165      -7.347
   8       736.71        777.50     52.16     2.845    0.05454    -40.785      -7.540
mean final visible delta vs original=-265.495 bits
mean best visible intermediate delta vs original=-26.940 bits
mean last-layer sparse scheduled delta vs that layer input=-7.540 bits
```

Result: public shuffling does maintain fresh adjacency samples: hit/chunk stays
near the fixed-universe rate instead of collapsing. But visible chunk tokens
bloat every pass, and the tighter scheduled-bitmap ledger is still negative
once the open/carry bitmap is priced. This is real target churn, not a hidden
birth channel, but it is not net compression for random input.

The decoded-left-context nonce mutation uses stable neighbor identity instead
of token prefix state. Each scheduled chunk is salted by the previous decoded
chunk in public-shuffled chunk order. The encoder knows that left neighbor
while matching, and the decoder knows it before opening the current chunk. This
avoids the instability of future/right-neighbor salts:

```text
toy grammar: span=14 left_seed=9 literal-token=15 record=10 hit_p/context=0.03125
round_trips=60/60
pass  avg in bits  avg out bits    chunks      hits  hit/chunk  contexts   vis net  tight net
   1       512.00        542.67     36.00     1.067    0.02963     35.95   -30.667     -4.914
   2       542.67        573.37     38.28     1.517    0.03962     38.25   -30.700     -4.608
   3       573.37        607.13     40.43     1.333    0.03298     40.38   -33.767     -4.903
   4       607.13        643.82     42.85     1.233    0.02878     42.75   -36.683     -5.278
mean final visible delta vs original=-131.817 bits
mean best visible intermediate delta vs original=-30.667 bits
```

Result: the previous decoded chunk is a genuine decoder-known nonce and
public shuffling keeps contexts fresh across passes. But only one context is
active at each chunk, so arbitrary hit supply is not multiplied. The open/carry
bitmap still dominates the tight ledger and visible tokens bloat the stream.

The context-lane validity mutation adds a structural lane rule to that same
causal neighbor. The lane bits are derived from the previous decoded chunk,
pass, and slot before opening; the record stores only local seed bits inside
that lane:

```text
toy grammar: span=14 total_seed=10 passes=3 n_bits=256
lane local     hit p   round    hit/ch  contexts  vis final tight last  closed net
   0    10   0.06250  12/12    0.06356     19.67    -40.417     -3.520    -0.08729
   2     8   0.01562  12/12    0.00417     20.00    -51.833     -4.252    -0.02237
   4     6   0.00391  12/12    0.00417     20.00    -55.667     -4.086    -0.00562
   6     4   0.00098  12/12    0.00000     20.00    -57.000     -4.392    -0.00141
   8     2   0.00024  12/12    0.00000     20.00    -57.000     -4.392    -0.00035
  10     0   0.00006  12/12    0.00417     19.92    -55.833     -3.586    -0.00009
```

Result: the lane is genuinely decoder-known before expansion, and wrong lanes
are structurally excluded. But only one lane is active for each chunk. Every
derived lane bit shortens the stored seed by one bit and halves eligible seed
supply, so the closed uniform ledger remains `p*d-H(p)<0`; exact round trips
still bloat under visible and tight bitmap accounting.

The checkerboard two-neighbor context mutation reopens the final/right-neighbor
idea in a stable form. A public checkerboard schedule carries one parity of
chunks as literal guards and attempts records only in the opposite parity. Each
active slot is salted by both adjacent guard chunks, so the decoder can parse
the layer, recover guard chunks, and then expand active records with both
neighbors known. The active parity alternates by public pass index:

```text
toy grammar: span=14 seed=9 passes=4 n_bits=256
active hit_p/context=0.03125 active closed net=-0.04437 all-slot closed net=-0.02219
round_trips=20/20
pass   avg in   avg out   active   guards     hits   hit/act  contexts   vis net  tight net
   1   256.00    262.75     9.00     9.00    0.450   0.05000      9.00    -6.750     -2.440
   2   262.75    270.50     9.00     9.00    0.250   0.02778      9.00    -7.750     -2.864
   3   270.50    277.00     9.00     9.85    0.500   0.05556      9.00    -6.500     -2.231
   4   277.00    284.75    10.00     9.25    0.450   0.04500     10.00    -7.750     -2.704
mean final visible delta vs original=-28.750 bits

seed-width closed surface, active slots only:
 seed      hit_p   gap  active net   all-slot
    6    0.00391     8    -0.00562   -0.00281
    7    0.00781     7    -0.01123   -0.00561
    8    0.01562     6    -0.02237   -0.01118
    9    0.03125     5    -0.04437   -0.02219
   10    0.06250     4    -0.08729   -0.04365
   11    0.12500     3    -0.16856   -0.08428
```

Result: this fixes the old right-neighbor instability without a birth tag:
both neighbors are decoder-known before expansion, and the nonce changes under
public shuffle plus alternating parity. But that stability is bought by forcing
about half the chunks to remain raw guards. Among the active half, there is
still exactly one hash context per slot, so the arbitrary-content hit supply is
not multiplied. The open/carry choice over active slots remains a bitmap/count
or visible tag, and the closed uniform ledger stays negative for all tested
seed widths.

The selected public-shuffle hitmap-shaping mutation then asks whether trying
many public shuffles can make the open/carry map itself cheaper. For each
layer, the encoder tries `K` public permutations, chooses the one with the best
charged lower-bound ledger, and stores the shuffle index. The bitmap is priced
favorably as the cheaper of count+enumerative coding or count+one-run coding:

```text
toy grammar: span=14 seed=10 gross seed saving=4 bits input=512 passes=4 trials=120
   K pass      hits  hit/chunk     runs    bitmap  K bits  tight net visible net
   1    1     2.208    0.06134    2.092    14.729   0.000     -5.896     -27.167
   1    2     2.367    0.06229    2.250    15.485   0.000     -6.018     -28.525
   1    3     2.400    0.05978    2.283    15.879   0.000     -6.279     -30.550
   1    4     2.467    0.05831    2.300    16.289   0.000     -6.422     -32.433
   4    1     3.475    0.09653    3.108    18.443   2.000     -6.543     -22.100
   4    2     2.592    0.06861    2.267    15.352   2.000     -6.985     -27.408
   4    3     3.192    0.08043    2.758    17.818   2.000     -7.052     -26.917
   4    4     3.358    0.08086    2.875    18.386   2.000     -6.953     -28.100
  16    1     4.808    0.13356    4.125    22.353   4.000     -7.120     -16.767
  16    2     4.242    0.11357    3.458    20.206   4.000     -7.239     -20.383
  16    3     4.042    0.10444    3.375    19.886   4.000     -7.719     -22.533
  16    4     4.350    0.10783    3.608    21.154   4.000     -7.754     -22.942
  64    1     5.992    0.16644    4.800    25.300   6.000     -7.333     -12.033
  64    2     5.983    0.16146    4.800    25.369   6.000     -7.435     -13.125
  64    3     5.817    0.15314    4.700    25.082   6.000     -7.815     -14.717
  64    4     6.083    0.15618    4.825    25.936   6.000     -7.603     -14.617
```

Result: public shuffle choice increases hits and improves the visible-token
net, but the priced lower-bound ledger gets worse as `K` grows. The shuffle
index and remaining bitmap entropy are the open/carry channel. This buys nicer
coordinates; it does not make the chosen hit map decoder-derivable for free.

The prefix-parse-state nonce mutation salts each record expansion with the
decoder's current prefix token state. The encoder knows this state while it
constructs the token stream, and the decoder knows it before opening the record.
No nonce field or birth tag is stored. This is a genuine decoder-known nonce
channel combined with whole-layer target-refresh:

```text
toy grammar: state_bits=4 literal=2 bits record=11 bits span=14 bits
mean unique outputs/state=992.3 hit_p/state-window=0.06057
round_trips=200/200
pass  avg in bits  avg out bits  avg windows  avg matches  hit/window   states delta vs orig
   1       192.00        279.19       179.00        6.165     0.03444    15.91       -87.195
   2       279.19        398.50       266.19        9.405     0.03533    15.99      -206.505
   3       398.50        569.21       385.50       13.400     0.03476    16.00      -377.210
   4       569.21        802.41       556.21       19.765     0.03554    16.00      -610.415
   5       802.41       1148.81       789.41       26.825     0.03398    16.00      -956.805
   6      1148.81       1661.38      1135.81       37.425     0.03295    16.00     -1469.385
mean final delta vs original=-1469.385 bits
mean best intermediate delta vs original=-87.195 bits
```

Result: prefix state did maintain a stable match rate over many passes in this
toy, while decoding statelessly. It still failed the goal because the visible
token stream carries the non-hit regions. The mechanism solves freshness more
honestly than fixed rechunking, but not compression.

The sparse-map prefix-state accounting mutation removes the visible-token
literal overhead. It stores only the miss bits, record seeds, and an optimistic
enumerative map of selected non-overlapping spans, plus the match-count class:

```text
toy grammar: span=14 seed=10 gross/match=4 state_bits=4
round_trips=200/200
n bits   matches  hit/window   literals  seed bits   map bits    count    charged        net
   512    16.950     0.03397    274.700    169.500     89.312    5.209    538.721    -26.721
mean gross seed-span saving before map=67.800 bits
mean optimistic map+count cost=94.521 bits
```

Result: removing token syntax gets much closer, but the selected-span map costs
more than the gross seed-span savings. This is the window-coordinate bill in
its tight sparse form: the decoder can reconstruct exactly, but it must know
which sparse random windows were replaced.

The scheduled-slot bitmap mutation removes the sparse selected-position map by
using public non-overlapping slots. The remaining open/carry channel is the hit
bitmap, priced optimistically as `log2 C(slots,hits) + log2(slots+1)`:

```text
toy grammar: slot_span=14 seed=10 gross/hit=4 state_bits=4
round_trips=200/200
n bits   slots     hits   hit/slot   literals  seed bits     bitmap    count    charged        net
   512   36.00    2.240    0.06222    480.640     22.400      9.579    5.209    517.828     -5.828
```

Closed-form scheduled-slot expectation under the uniform hash law:

```text
gap d=L-r      p=2^-d    save p*d        H(p)    net/slot
        1     0.50000     0.50000     1.00000    -0.50000
        2     0.25000     0.50000     0.81128    -0.31128
        3     0.12500     0.37500     0.54356    -0.16856
        4     0.06250     0.25000     0.33729    -0.08729
        6     0.01562     0.09375     0.11612    -0.02237
        8     0.00391     0.03125     0.03687    -0.00562
       12     0.00024     0.00293     0.00328    -0.00035
       16     0.00002     0.00024     0.00027    -0.00002
```

Result: public scheduling removes the selected-position map, but the hit bitmap
becomes the open/carry channel. The stricter finite toy no longer appears
almost break-even, and the entropy model remains negative for independent
uniform hits at every tested savings gap.

The parent-summary nonce mutation asks whether a parent state can be stored
once per group and then used as a fresh child salt. The decoder reads the
summary before child slots, opens children using `(summary, local_slot, seed)`,
then verifies the summary after reconstructing the group:

```text
toy grammar: span=14 seed=10 n_bits=1024
summary g slots  groups     hits   hit/slot   parent     bitmap    charged        net
      0      16     4.0    4.013    0.06270      0.0     24.756   1032.706     -8.706
      2      16     4.0    3.562    0.05566      8.0     22.880   1040.630    -16.630
      4      16     4.0    3.513    0.05488     16.0     22.886   1048.836    -24.836
      6      16     4.0    3.862    0.06035     24.0     24.126   1056.676    -32.676
```

Closed form for 14-bit spans and 10-bit seeds has `p=0.06250`, gross
`0.25000` saved bits/slot, and bitmap entropy `H(p)=0.33729` before parent
metadata. Summary bits add `summary_bits / group_size` per slot, so every
positive summary width worsens the ledger.

Result: parent state is a legitimate decoder-known salt, and the toy
round-trips. But there is only one active parent value for each child; storing
that value does not multiply arbitrary target coverage. It is metadata, not a
compression subsidy.

The scheduled-edge exclusion mutation uses a public `(pass, slot)` class as a
decoder-known salt. The stored seed omits those class bits, so the schedule can
refresh dice across passes without a per-record class field. The exact codec
round-trips each accepted slot from `(pass, slot, edge_class, local_seed)`:

```text
toy grammar: span=14 total_seed=10 slots=73
 edge local pass     hits   hit/slot     bitmap    count    charged        net
    0    10    1    4.638    0.06353     21.930    6.209   1033.590     -9.590
    0    10    2    4.138    0.05668     19.962    6.209   1033.622     -9.622
    0    10    3    4.525    0.06199     21.493    6.209   1033.603     -9.603

    1     9    1    2.550    0.03493     13.321    6.209   1030.781     -6.781
    1     9    2    2.225    0.03048     11.819    6.209   1030.903     -6.903
    1     9    3    2.650    0.03630     13.668    6.209   1030.627     -6.627

    2     8    1    1.288    0.01764      7.083    6.209   1029.568     -5.568
    2     8    2    1.113    0.01524      6.369    6.209   1029.904     -5.904
    2     8    3    1.075    0.01473      6.106    6.209   1029.866     -5.866

    3     7    1    0.637    0.00873      3.719    6.209   1029.466     -5.466
    3     7    2    0.550    0.00753      3.236    6.209   1029.596     -5.596
    3     7    3    0.625    0.00856      3.680    6.209   1029.515     -5.515

    4     6    1    0.325    0.00445      1.973    6.209   1029.583     -5.583
    4     6    2    0.188    0.00257      1.135    6.209   1029.845     -5.845
    4     6    3    0.287    0.00394      1.767    6.209   1029.676     -5.676
```

Closed-form scheduled-edge expectation:

```text
 edge local           p   gross        H(p)    net/slot
    0    10 6.25000e-02       4 3.37290e-01 -8.72901e-02
    1     9 3.12500e-02       5 2.00622e-01 -4.43723e-02
    2     8 1.56250e-02       6 1.16115e-01 -2.23651e-02
    3     7 7.81250e-03       7 6.59144e-02 -1.12269e-02
    4     6 3.90625e-03       8 3.68745e-02 -5.62451e-03
    6     4 9.76562e-04      10 1.11738e-02 -1.40819e-03
    8     2 2.44141e-04      12 3.28186e-03 -3.52177e-04
```

Result: the public edge schedule is a valid decoder-known salt and it refreshes
outputs across passes. But every omitted class bit removes half the eligible
seed supply. With the hit bitmap priced, the uniform ledger remains negative.

The seed-length class mutation uses the record class as a decoder-known nonce.
The decoder sees the class before expansion, and the class selects both the
seed length and the hash salt. Hits store a fixed-width class id plus the seed:

```text
toy grammar: span=14 slots=73
      classes cbits pass     hits   hit/slot     record     bitmap    charged        net
           10     0    1    4.638    0.06353     46.375     28.158   1033.608     -9.608
           10     0    2    4.650    0.06370     46.500     28.227   1033.627     -9.627
           10     0    3    4.425    0.06062     44.250     27.319   1033.619     -9.619

         9/10     1    1    6.412    0.08784     68.300     34.358   1036.883    -12.883
         9/10     1    2    6.713    0.09195     71.600     35.300   1036.925    -12.925
         9/10     1    3    6.638    0.09092     70.638     35.035   1036.748    -12.748

       8/9/10     2    1    7.100    0.09726     80.875     36.524   1041.999    -17.999
       8/9/10     2    2    7.213    0.09880     82.225     36.783   1042.033    -18.033
       8/9/10     2    3    7.438    0.10188     84.862     37.489   1042.227    -18.227

       6/8/10     2    1    5.562    0.07620     63.350     31.258   1040.733    -16.733
       6/8/10     2    2    5.950    0.08151     67.825     32.668   1041.193    -17.193
       6/8/10     2    3    5.425    0.07432     62.175     30.896   1041.121    -17.121

     4/6/8/10     2    1    5.875    0.08048     66.900     32.578   1041.228    -17.228
     4/6/8/10     2    2    6.213    0.08510     70.200     33.550   1040.775    -16.775
     4/6/8/10     2    3    5.825    0.07979     66.100     32.372   1040.922    -16.922
```

Closed form under independent hash outputs:

```text
      classes       p any     E gross        H(p)    net/slot
           10 6.25000e-02 2.50000e-01 3.37290e-01 -8.72901e-02
         9/10 9.17969e-02 3.06641e-01 4.42439e-01 -1.35799e-01
       8/9/10 1.05988e-01 2.73987e-01 4.87693e-01 -2.13706e-01
       6/8/10 8.07533e-02 2.08260e-01 4.04828e-01 -1.96568e-01
     4/6/8/10 8.16510e-02 2.15869e-01 4.07970e-01 -1.92101e-01
```

Result: seed length is a real parser-known salt, and extra classes increase hit
rate. But the class id, longer seed address, and open/carry bitmap cost more
than the added arbitrary match supply.

The arity-header-known nonce mutation uses the record arity itself as the
decoder-visible salt. The decoder reads the arity header before seed expansion,
so no birth tag is needed. The exact toy greedily accepts compressive arity-3
and arity-4 records, carries misses as literal base blocks, and reserializes
the token stream into the next fixed-universe pass:

```text
toy grammar: base=4 seed=7 arity_bits=2 arities=(1, 2, 3, 4) passes=4 n_bits=256
round_trips=120/120
pass   avg in   avg out      a3      a4   vis net  tight net
   1   256.00    308.79   2.092   0.075   -52.792    -15.144
   2   308.79    371.71   2.458   0.158   -62.917    -16.302
   3   371.71    449.37   2.600   0.192   -77.658    -17.963
   4   449.37    546.33   2.767   0.117   -96.967    -20.058
mean final visible delta vs original=-290.333 bits
```

Closed scheduled-window surface:

```text
arity  target          p  visible gap   mapless E       H(p)   net/slot
    1       4    1.00000           -6     0.00000    0.00000    0.00000
    2       8    0.50000           -2     0.00000    1.00000   -1.00000
    3      12    0.03125            2     0.06250    0.20062   -0.13812
    4      16    0.00195            6     0.01172    0.02039   -0.00867
```

Result: arity is a legitimate parser-known nonce, and target reserialization
keeps producing fresh arity-3/4 opportunities. But the arity header is a paid
record field in the visible codec, and in the tighter ledger the
non-overlapping parse/arity map replaces those header/tag bits. The extra dice
do not beat the class plus open/carry description under the uniform law.

The seed value/count separation mutation asks whether rare high-value classes
can avoid per-hit class IDs by storing only class counts. The exact counter
enumerates class histograms over 32 scheduled slots and prices the missing
assignment of classes to ordered slots:

```text
exact count/assignment entropy: slots=32
            case feasible  gross/sl  Hcount/sl  assign/sl  fullH/sl  count net   full net
     d4 feasible     True   0.25000    0.07583    0.26146   0.33729    0.17417   -0.08729
     d8 feasible     True   0.03125    0.01759    0.01929   0.03687    0.01366   -0.00562
       d4+d8+d12     True   0.28418    0.09548    0.28158   0.37706    0.18870   -0.09288
  jackpot d16/p8    False   0.06250    0.01759    0.01929   0.03687    0.04491    0.02563
 jackpot d24/p12    False   0.00586    0.00206    0.00122   0.00328    0.00380    0.00258
```

Result: count-only ledgers look positive because histogram entropy is
sublinear, but the decoder still has to know the assignment of value classes to
slots. Histogram plus assignment equals the full category map entropy. The
only positive full-net rows require impossible jackpot density: a class saving
`d` bits cannot cover more than about `2^-d` of arbitrary chunks without extra
codewords or side information.

The grouped scheduled-bundle mutation tries to amortize the bitmap by accepting
only complete public groups of scheduled slots. A group is a record only when
every slot in that group has a prefix-state seed; otherwise the whole group is
carried literally. The group bitmap is charged with its count class:

```text
g slots  groups     hits  hit/group     bitmap    count    charged        net
      1   292.0   18.065    0.06187     93.686    8.195   4125.620    -29.620
      2   146.0    0.570    0.00390      3.919    7.200   4102.558     -6.558
      3    97.0    0.040    0.00041      0.264    6.615   4102.399     -6.399
      4    73.0    0.005    0.00007      0.031    6.209   4102.160     -6.160
```

Closed form for all-hit groups, with `p = 2^-d`, group size `g`, and gross
gap `d = L-r`:

```text
g slots       q=p^g   save/group        H(q)   net/group
      1 6.25000e-02  2.50000e-01 3.37290e-01 -8.72901e-02
      2 3.90625e-03  3.12500e-02 3.68745e-02 -5.62451e-03
      3 2.44141e-04  2.92969e-03 3.28186e-03 -3.52177e-04
      4 1.52588e-05  2.44141e-04 2.66154e-04 -2.20136e-05
      8 2.32831e-10  7.45058e-09 7.78648e-09 -3.35904e-10
```

Result: grouping suppresses bitmap frequency by requiring rarer events. Under
the uniform hash law, `p^g*g*d - H(p^g)` remains negative; any finite row that
looks positive without the count class is using an unpaid cardinality channel.

The bundle-geometry partition selector mutation lets the group shape itself be
the decoder-known nonce. A 4-block group can be raw, one 4-block record, one
3-block record plus a literal, two 2-block records, or one 2-block record plus
literals. The decoder reads the shape before expanding child records, so shape
and segment index may salt each child seed:

```text
toy grammar: base=4 group=4 seed=4 modes=8 passes=4 n_bits=512
round_trips=160/160
pass   avg in   avg out   groups      rec   mode0%   vis net  tight net
   1   512.00    583.08    32.00    5.969   81.641   -71.075    -23.505
   2   583.08    664.00    36.08    6.519   82.129   -80.925    -25.298
   3   664.00    755.40    41.08    7.475   81.973   -91.400    -26.572
   4   755.40    858.62    46.75    8.838   81.143  -103.225    -28.687
mean final visible delta vs original=-346.625 bits
```

Closed shape surface, ignoring overlap between shapes:

```text
mode        shape           q    gap       q*gap       H(q)        net
   1           R4 2.44141e-04      9 2.19727e-03 3.28186e-03 -1.08460e-03
   2         R3L1 3.90625e-03      5 1.95312e-02 3.68745e-02 -1.73433e-02
   3         L1R3 3.90625e-03      5 1.95312e-02 3.68745e-02 -1.73433e-02
   4         R2R2 3.90625e-03      5 1.95312e-02 3.68745e-02 -1.73433e-02
   5       R2L1L1 6.25000e-02      1 6.25000e-02 3.37290e-01 -2.74790e-01
   6       L1R2L1 6.25000e-02      1 6.25000e-02 3.37290e-01 -2.74790e-01
   7       L1L1R2 6.25000e-02      1 6.25000e-02 3.37290e-01 -2.74790e-01
 all   optimistic 1.99463e-01        2.48291e-01 7.20853e-01 -4.72562e-01
```

Result: bundle geometry is a valid decoder-known salt only after the mode is
known. Trying several shapes raises match opportunities, but the selected
geometry is the open/carry map at group scale. Visible mode bits lose badly;
the optimistic enumerative mode-map ledger also remains negative.

The bucket-directory one-hit mutation stores a coarser public bucket directory
instead of a per-slot bitmap. Each non-empty bucket records at most one matching
slot with a local index and seed; all other slots are literals. This tests the
middle ground between per-slot bitmaps and all-hit groups.

```text
toy grammar: span=14 seed=10 gross/hit=4
g slots  groups  buckets   hit/bkt    index    dir+cnt    charged        net
      2   146.0   17.660   0.12096   17.660     81.002   4124.022    -28.022
      4    73.0   16.150   0.22123   32.300     57.941   4121.641    -25.641
      8    36.0   13.915   0.38653   41.745     36.357   4118.442    -22.442
     16    18.0   11.245   0.62472   44.980     18.260   4114.260    -18.260
```

Closed-form one-hit bucket expectation under uniform independent hits:

```text
g slots   q bucket     E save       H(q)  idx bits   net/group
      2    0.12109    0.36328    0.53250         1    -0.16922
      4    0.22752    0.45505    0.77367         2    -0.31862
      8    0.40328    0.40328    0.97284         3    -0.56956
     16    0.64393    0.00000    0.93938         4    -0.93938
     32    0.87321    0.00000    0.54857         5    -0.54857
```

Result: bucket directories lower bitmap resolution, but every non-empty bucket
needs a local coordinate and gives up additional hits inside the bucket. The
directory entropy plus local index cost stays larger than expected one-hit
savings under the uniform law.

The bitmap-free all-or-raw block mutation removes mixed open/carry positions
inside a block. A public block is either fully compressed, when every scheduled
slot in that block has a seed, or carried raw. The only local side channel is
one raw/compressed mode bit per block:

```text
toy grammar: span=14 seed=10 gross/hit=4
g slots  groups  cmp grp  hit/group     mode    charged        net
      1   292.0   17.605    0.06029    292.0   4317.580   -221.580
      2   146.0    0.445    0.00305    146.0   4238.440   -142.440
      3    97.0    0.010    0.00010     97.0   4192.880    -96.880
      4    73.0    0.000    0.00000     73.0   4169.000    -73.000
      8    36.0    0.000    0.00000     36.0   4132.000    -36.000
     16    18.0    0.000    0.00000     18.0   4114.000    -18.000
```

Closed-form all-or-raw expectation under uniform independent hits:

```text
g slots       q=p^g   save/group   net/group whole-layer net @292
      1 6.25000e-02  2.50000e-01 -7.50000e-01
      2 3.90625e-03  3.12500e-02 -9.68750e-01
      3 2.44141e-04  2.92969e-03 -9.97070e-01
      4 1.52588e-05  2.44141e-04 -9.99756e-01
      8 2.32831e-10  7.45058e-09 -1.00000e+00
     16 5.42101e-20  3.46945e-18 -1.00000e+00
    292 0.00000e+00  0.00000e+00 -1.00000e+00         -1.00000e+00
```

Result: replacing a bitmap with raw/compressed block modes is worse for
uniform chunks. The mode bit is still an open/carry channel, and making blocks
larger only makes all-hit compression events exponentially rarer. Whole-layer
all-hit mode has essentially zero random hit probability.

The hole-run bundle occupancy mutation gives the egg-carton idea its clean
mechanical toy. A 4-chunk bundle occupies the first public cell and leaves
three holes. If the holes remain visible, the decoder knows open vs carry; if
the stream is packed, the omitted hole pattern is exactly the hidden mode map:

```text
toy grammar: base=4 group=4 seed=10 n_bits=4096
round_trips=120/120
groups=256.0 hits=3.967 hit/group=0.01549
            ledger       bits        net                     note
        free holes   4072.200     23.800    invalid packed oracle
      1 mode/group   4328.200   -232.200      exact visible codec
    cell occupancy   5096.200  -1000.200      explicit hole cells
      tight bitmap   4107.712    -11.712  enumerative lower bound
```

Closed-form group expectation under uniform independent hits:

```text
p=0.015625 gap=6 p*gap=0.093750 H(p)=0.116115
free oracle net/group=0.093750
mode net/group=-0.906250
cell-occupancy net/group=-3.906250
tight bitmap net/group=-0.022365
```

Result: holes can be a valid open/carry signal, but not a free one. The
positive `free holes` row is the reward-hack ledger where the board remembers
holes after packing has erased them. The cheapest honest packed note is the
enumerative mode map, and it is still negative in this random/content-blind
setting.

The greedy score-order count-only mutation tries to remove the bitmap without
a checksum. A public slot order says every matchable chunk must be opened as a
record. The file stores only the seed and literal streams; the decoder
enumerates count-matched maps and rejects any map where a carried literal would
have been matchable in its assigned slot.

```text
toy grammar: slots=12 span=8 seed=4 raw=96 trials=400
round_trips=400/400
avg hits=0.775 avg survivors=17.302 unique%=0.443
avg bitmap bits avoided=2.504 avg ambiguity bits=2.175
charged=98.776 net=-2.776
```

Result: local greedy validity prunes some maps, but not enough. The decoder
still sees multiple valid seed/literal interleavings on average. The omitted
bitmap reappears as survivor ambiguity or a referee checksum; count-only score
order is not a free open/carry channel.

The prefix-stop count-free mutation removes both the bitmap and per-block hit
count in a favorable fixed-block setting. In a public slot order, the encoder
opens consecutive matchable slots until the first miss, then carries the rest
raw. The compressed block length would reveal the stop count only if block
boundaries were free; concatenated stateless blocks require the decoder to
infer all stop counts from the final bitstream.

```text
toy grammar: blocks=8 slots/block=6 span=8 seed=4 raw=384
true_path_round_trips=120/120
avg opened prefix slots=0.550 avg free saving=2.200 bits
avg survivors=6.367 avg ambiguity=1.333 bits
net after ambiguity=0.867 bits
length/count class=5.615 bits charged net=-4.748 bits
```

Result: the prefix-stop rule does remove an explicit local count inside an
isolated block, but the total compressed length becomes the stop-count/savings
class. Once that recursive-layer length/count channel is charged, the finite
positive row flips negative. This is a useful reward-hack catch, not a
compression mechanism.

The checksum-pruned hit-map mutation omits the hit bitmap. The decoder
receives ordered seed and literal streams, so the hit count is known from
stream lengths, then enumerates all `C(slots,hits)` assignments and keeps only
those whose block checksum agrees:

```text
toy grammar: slots=12 span=8 seed=4
 chk     hits    assign  survivors    uniq%    bitmap   charged       net
   0    0.825    26.390     26.390    0.410     2.651    96.400    -0.400
   2    0.765    21.975      6.170    0.455     2.503    98.640    -2.640
   4    0.670    17.105      1.950    0.635     2.221   101.020    -5.020
   6    0.860    27.280      1.470    0.735     2.745   102.260    -6.260
   8    0.760    26.000      1.150    0.890     2.406   104.660    -8.660
  10    0.790    22.755      1.015    0.985     2.560   106.540   -10.540
  12    0.735    19.070      1.000    1.000     2.434   108.760   -12.760
```

Closed-form checksum pruning for a fixed hit count:

```text
 hits     maps  log2 maps  chk for ~1
    0        1      0.000           0
    1       12      3.585           4
    2       66      6.044           7
    3      220      7.781           8
    4      495      8.951           9
    5      792      9.629          10
    6      924      9.852          10
    7      792      9.629          10
    8      495      8.951           9
    9      220      7.781           8
   10       66      6.044           7
   11       12      3.585           4
   12        1      0.000           0
```

Result: checksum search is a real nonlocal coupling, but a checksum wide
enough to leave about one map survivor has the same width as the enumerative
hit map it replaces. Shorter checksums leave multiple valid decodes, so round
trip with the encoder's chosen map is not deterministic stateless decode.

The tagless value-code mutation removes the hit bitmap entirely. For each
decoder-known state, seed-image chunks get short prefix codewords and non-image
chunks get long complement codewords. Open vs carry is derived from the parsed
value class itself. This is an exact stateless grammar, not a side bitmap:

```text
exact toy: span=8 seed=4 state_bits=3
 short pass    avg in   avg out  hit/chunk    long  delta orig
     5    1    512.00    561.56    0.05641    9.00     -49.560
     5    2    561.56    615.22    0.05830    9.00    -103.220
     5    3    615.22    674.37    0.05657    9.00    -162.370
     5    4    674.37    738.14    0.05991    9.00    -226.140
       final              738.14                       -226.140
     6    1    512.00    564.30    0.06094    9.00     -52.300
     6    2    564.30    622.02    0.05873    9.00    -110.025
     6    3    622.02    686.17    0.05673    9.00    -174.170
     6    4    686.17    756.05    0.06035    9.00    -244.055
       final              756.05                       -244.055
     8    1    512.00    512.00    0.05461    8.00       0.000
     8    2    512.00    512.00    0.05461    8.00       0.000
     8    3    512.00    512.00    0.05461    8.00       0.000
     8    4    512.00    512.00    0.05461    8.00       0.000
       final              512.00                          0.000
```

Ideal one-chunk Kraft ledger, ignoring integer code rounding and hash
collisions:

```text
   L    r  short      hit p  ideal long    E bits    E save
   8    4      5    0.06250     8.90689   8.66271  -0.66271
   8    4      6    0.06250     8.32193   8.17681  -0.17681
   8    4      8    0.06250     8.00000   8.00000   0.00000
  14   10     11    0.06250    14.90689  14.66271  -0.66271
  14   10     12    0.06250    14.32193  14.17681  -0.17681
  14   10     14    0.06250    14.00000  14.00000   0.00000
  32   16     17    0.00002    32.99998  32.99973  -0.99973
  32   16     18    0.00002    32.41502  32.41480  -0.41480
  32   16     32    0.00002    32.00000  32.00000   0.00000
```

Result: this candidate really makes open/carry derivable and keeps fresh
state-dependent seed-image opportunities. It still cannot compress uniform
chunks: if `S=2^r` image values use length `c`, the complement needs remaining
Kraft mass `K = 1 - S*2^-c`, so its ideal length is
`log2((2^L-S)/K)`. The expected uniform length is minimized at the
no-compression point `c=L`.

The finite-class local grammar bound generalizes the same conservation law to
local parser-known nonce tricks: decoder-known classes, seed lengths, lanes, or
salts produce seed-image codewords, and all non-image chunks use an ideal
fallback language. Under the optimistic model, hash images are disjoint and
fallback coding uses all remaining Kraft mass:

```text
                design   img frac      Kraft   fallback     E bits       save
       tagless r10 c11    0.06250    0.50000   14.90689   14.66271   -0.66271
       tagless r10 c12    0.06250    0.25000   14.32193   14.17681   -0.17681
     raw point r10 c14    0.06250    0.06250   14.00000   14.00000    0.00000
      seed length 9/10    0.09375    1.00000        inf        inf       -inf
    seed length 8/9/10    0.10938    0.75000   15.83289   15.35117   -1.35117
    mixed lanes 6/8/10    0.08203    0.75000   15.87652   15.51165   -1.51165
      visible nonce k2    0.06250    0.25000   16.32193   16.17681   -0.17681
      visible nonce k4    0.25000    0.25000   16.00000   16.00000    0.00000
```

Best brute-force local designs with at least one short seed-image class:

```text
        classes image/code   img frac      Kraft     E bits       save
            2/13+2/14+2/14    0.00073    0.00098   14.00011   -0.00011
            2/13+2/14+3/14    0.00098    0.00122   14.00011   -0.00011
            2/13+3/14+3/14    0.00122    0.00146   14.00011   -0.00011
            2/13+2/14+4/14    0.00146    0.00171   14.00011   -0.00011
            2/13+3/14+4/14    0.00171    0.00195   14.00011   -0.00011
            2/13+4/14+4/14    0.00220    0.00244   14.00011   -0.00011
            2/13+2/14+5/14    0.00244    0.00269   14.00011   -0.00011
            2/13+3/14+5/14    0.00269    0.00293   14.00011   -0.00011
```

Result: this is not a global impossibility for Telomere. It does rule out a
large local family: if open/carry is decided by a per-slot prefix grammar and
the source chunks are uniform, the seed-image plus fallback code cannot have
expected length below raw. Any apparent win in this family needs a bitmap,
arrangement channel, distributional restriction, or nonlocal coupling.

### Family 3: Self-dating grammar / wrong-pass explosion

The BBL random-density surface separates the finite wrong-pass ambiguity ledge
from the arbitrary/random open-carry bill. High-arity length-pinned bundles do
make `c_a(P)` small, but random scheduled windows also need a hit map:

```text
sparse uniform windows: block=24 bits header=3 bits
 a          P   c_a(P)  best d       hit p   no-map E  map net/hit       map E
 2         64    0.132       2   3.125e-02  5.837e-02       -4.552  -1.422e-01
 3         64    0.015       2   3.125e-02  6.204e-02       -4.435  -1.386e-01
 4    1000000    5.007       7   9.766e-04  1.946e-03       -9.449  -9.228e-03
 5    1000000    2.111       4   7.812e-03  1.476e-02       -6.548  -5.116e-02
 5 1000000000   11.698      13   1.526e-05  1.987e-05      -16.140  -2.463e-04
```

The dense half-layer requirement, if every public group could somehow be
selected, shows the missing density:

```text
dense half-layer requirement if every public group could be selected:
 a          P   c_a(P)  gap for 50%  uniform hit p
 2         64    0.132           25      3.725e-09
 3         64    0.015           37      9.095e-13
 4         64    0.003           49      2.220e-16
 5         64    0.000           61      5.421e-20
 5    1000000    2.111           63      1.355e-20
```

Result: BBL's wrong-pass pruning is real and improves with arity, but this is
a dense selected-bundle mechanism. On arbitrary/random scheduled windows,
`H(p)` for the hit map exceeds the rare selected savings; a one-layer 50%
random reduction would need exponentially unlikely large-gap bundle density.

Residue-valid grammar bits make wrong openings fail structurally, but true
targets must carry those bits too. At `P = 1,000,000`, the best toy row was:

```text
arity=2 residue=6 span=30 gross=15 hit_p=7.629e-06 ambiguity=7.112
expected_net_per_arbitrary_window=6.018e-05 bits
```

Result: this is a real finite ambiguity lever, but not yet an
arbitrary-content density solution. The current mutation target is to make the
self-dating validity check derive from already-present item bits instead of
carrying extra residue bits.

The residue validity / syndrome trilemma mutation separates three ways to use
the same residue bits:

- `raw-filter`: raw hash expansion is accepted only if it happens to parse as
  residue-valid. Wrong-pass openings are pruned, but arbitrary targets must
  already carry the residue too.
- `constrained`: every seed expansion is forced into the residue-valid
  language. This improves valid-target reachability, but wrong-pass openings
  are also valid.
- `syndrome`: the record stores the residue syndrome needed to repair
  arbitrary targets. This restores arbitrary reachability, but the syndrome is
  paid record data and structural wrong-pass failure disappears.

```text
toy codec: data=8 seed=6 chunks=64 trials=80 pass_window=1000000
res         mode   valid%   hit/ch   wrong q    ambig   vis net     tight    closed
  0   raw-filter  100.000   0.2246   1.00000   19.932   -35.250   -22.640    -5.294
  0  constrained  100.000   0.2188   1.00000   19.932   -36.000   -23.020    -5.294
  0     syndrome  100.000   0.2199   1.00000   19.932   -35.850   -22.718    -5.294

  2   raw-filter   25.098   0.0150   0.25664   17.969   -60.150    -7.442    -0.334
  2  constrained   24.121   0.0498   1.00000   19.932   -51.250    -8.682    -1.333
  2     syndrome   24.219   0.2256   1.00000   19.932   -35.125   -22.661    -5.294

  4   raw-filter    6.621   0.0008   0.06250   15.932   -63.700    -6.022    -0.021
  4  constrained    6.445   0.0137   1.00000   19.932   -58.750    -5.674    -0.334
  4     syndrome    6.484   0.2342   1.00000   19.932   -34.025   -22.617    -5.294

  6   raw-filter    2.109   0.0000   0.01621   13.985   -64.000    -6.022    -0.001
  6  constrained    1.445   0.0031   1.00000   19.932   -62.400    -5.610    -0.083
  6     syndrome    1.543   0.2277   1.00000   19.932   -34.850   -22.594    -5.294
```

Result: residue bits cannot simultaneously prune wrong passes, preserve
arbitrary target coverage, and remain unpaid. If they are used as structural
validity, arbitrary true targets are thinned. If the expander is constrained or
a syndrome repairs the target, wrong-pass survival is `1` or the syndrome bits
are in the record. This closes the local residue-valid bundle grammar in the
uniform scheduled-window model.

Derived validity from visible seed classes avoids adding residue bits to the
record, but restricts the eligible seed class by the same amount:

```text
best toy expected net/window=5.137e-05 at arity=3 class=6
```

Result: seed-class, checksum-residue, lane-constrained codeword, and
neighbor-state validity checks must be priced as match-supply loss unless they
reject wrong lanes more often than they reject true arbitrary targets.

The nested referee mutation generalizes residue checks into recursive internal
checks over a bundle. The exact wrapper round-trips arbitrary payload bits and
rejects random wrong streams at the expected internal-check rate:

```text
exact wrapper: arity=3 depth=2 leaves=9 payload=36 check_total=8 stream=44
round_trips=5000/5000
wrong_survivors=21/5000 expected~19.53
```

The anti-reward-hack ledger splits three interpretations:

```text
Top rows if referee validity were free for true targets:
 a  d chk payload nodes    ambig     fantasy      stored     derived
 2  2   8      32     3    0.084   7.273e-04   4.335e-11   4.335e-11
 2  2   6      32     3    2.267   5.940e-04   2.266e-09   2.266e-09
 2  2   4      32     3    7.937   2.480e-04   6.054e-08   6.054e-08
 4  1   8      32     1   11.932   4.154e-06   1.623e-08   1.623e-08
 5  1   8      40     1   11.932   1.924e-06   7.514e-09   7.514e-09
 5  1   6      40     1   13.932   1.447e-06   2.261e-08   2.261e-08
 5  1   4      40     1   15.932   9.700e-07   6.062e-08   6.062e-08
 5  1   2      40     1   17.932   4.932e-07   1.233e-07   1.233e-07

Best charged rows after storing checks or deriving them from seed class:
 a  d chk payload nodes    ambig     charged
 5  1   1      40     1   18.932   1.274e-07
 5  1   2      40     1   17.932   1.233e-07
 5  1   4      40     1   15.932   6.062e-08
 2  2   4      32     3    7.937   6.054e-08
 5  1   6      40     1   13.932   2.261e-08
 5  1   0      40     1   19.932   1.632e-08
 4  1   8      32     1   11.932   1.623e-08
 5  1   8      40     1   11.932   7.514e-09
```

Result: recursive structure really does reduce wrong-pass ambiguity, but only
when the true target is already in the referee-valid language. If the referee
bits are stored in the target/wrapper or derived from seed classes, the same
information cost returns as hit-probability loss. The best charged rows are
shallow; deeper nesting mainly creates a larger validity channel to pay.

## 50% Random Compression Gate

The updated finish condition allows completion only if a configuration can
maintain compression over many passes and theoretically reach about 50%
compression on arbitrary/random data. The lossless counting gate is severe:

```text
n raw    <=n/2 outputs     all inputs   cover fraction  missing bits/input
   16        5.110e+02      6.554e+04        7.797e-03               7.003
   32        1.311e+05      4.295e+09        3.052e-05              15.000
   64        8.590e+09      1.845e+19        4.657e-10              31.000
  128        3.689e+19      3.403e+38        1.084e-19              63.000
  256        6.806e+38      1.158e+77        5.877e-39             127.000
```

Result: unlimited compute can search more addresses, but it cannot make an
injective lossless map from all `n`-bit strings into `<= n/2` bits. Any future
candidate claiming 50% on arbitrary/random data must explicitly pay the missing
bits as side information, exceptions, a distributional restriction, or accept
non-injective loss.

The exception-burden mutation asks whether misses can simply fall back to raw
exceptions while hits use short records. This is the optimistic whole-block
ledger: missed inputs use `n` raw bits with no per-block tag.

```text
n     c   q max short   q for 1b avg   q for half avg  best avg len   best save  raw+tag avg
16    8     7.797e-03      1.113e-01        8.906e-01     15.929962   7.004e-02    16.922165
32   16     3.052e-05      5.882e-02        9.412e-01     31.999481   5.188e-04    32.999451
64   32     4.657e-10      3.030e-02        9.697e-01     64.000000   1.537e-08    65.000000
128  64     1.084e-19      1.538e-02        9.846e-01    128.000000   7.047e-18   129.000000
256 128     5.877e-39      7.752e-03        9.922e-01    256.000000   7.582e-37   257.000000
```

Result: exception fallback is not a loophole for arbitrary/random 50%. At
`n=128`, the short-code population is about `1.084e-19` of inputs, but even one
bit of average saving would require about `1.538e-02` of inputs to be short.
The gap is exponential. Per-record raw/carry tags make the average bloat.

The window/placement mutation asks whether many final board slots, lane slots,
or candidate windows can create enough chances. It can raise hit probability,
but the selected coordinate must be visible, stored, or paid as ambiguity:

```text
L   r  W trials   hit/chunk  coord bits     free E   priced E
16 12         1     0.06250       0.000      0.250      0.250
16 12         2     0.12109       1.000      0.484      0.363
16 12         4     0.22752       2.000      0.910      0.455
16 12         8     0.40328       3.000      1.613      0.403
16 12        16     0.64393       4.000      2.576      0.000
16 12        32     0.87321       5.000      3.493      0.000
16 12        64     0.98392       6.000      3.936      0.000

32 16         1     0.00002       0.000      0.000      0.000
32 16       256     0.00390       8.000      0.062      0.031
32 16      4096     0.06059      12.000      0.969      0.242
32 16     16384     0.22120      14.000      3.539      0.442
32 16     45426     0.50000      15.471      8.000      0.264
32 16     65536     0.63212      16.000     10.114      0.000
```

Result: multiplicity is useful only when the coordinate is already truly
decoder-visible. Otherwise the board slot, lane id, instruction slot, selected
window, hole pattern, or final arrangement is the hidden channel and costs
`log2(W)` or the equivalent survivor entropy.

The repeated-compute mutation asks whether enough public fresh trials can make
random half-size records hit. It can, but the selected trial index becomes an
implicit address:

```text
L   r            p      T for 50%   salt bits  eff record   save/hit  E save/span
16  8    3.906e-03      1.780e+02       7.476      15.476      0.524        0.262
24 12    2.441e-04      2.839e+03      11.471      23.471      0.529        0.264
32 16    1.526e-05      4.543e+04      15.471      31.471      0.529        0.264
48 24    5.960e-08      1.163e+07      23.471      47.471      0.529        0.264
64 32    2.328e-10      2.977e+09      31.471      63.471      0.529        0.264
```

Result: with the trial coordinate priced, the apparent half-size win collapses
to about `0.529` bits per hit and `0.264` expected bits per span at 50%
coverage. A future candidate must make that coordinate decoder-derivable
without becoming ambiguity, stored metadata, or target-language thinning.

The related salt trilemma showed the same conservation:

```text
K salts  stored net/window   try-all net/window  self-selected net  free-reject fantasy
      1            0.06250              0.06250            0.06250              0.06250
      2            0.09375              0.09375            0.06250              0.12500
      4            0.12500              0.12500            0.06250              0.25000
      8            0.12500              0.12500            0.06250              0.50000
     16            0.00000              0.00000            0.06250              1.00000
     32            0.00000              0.00000            0.06250              2.00000
     64            0.00000              0.00000            0.06250              4.00000
```

Result: the attractive column is the impossible one unless wrong salts reject
for free while true arbitrary targets are not thinned and no salt is stored.

## Prior Positive Controls

The strongest prior control stack is **TST + STF + BBL**, specified in
`BEST_SPEC.md` and exercised by:

```text
model_analysis/birth_channel_research/typed_scheduled_tree_codec.py
model_analysis/birth_channel_research/scheduled_tree_codec.py
model_analysis/birth_channel_research/bounded_bundle_codec.py
```

TST removes internal marker entropy by making child type public from the
schedule. Verified generated forests:

```text
depth=4, roots=4, leaves=64
raw_bits=512
charged_bits=503
net_bits=+9

depth=6, roots=2, leaves=128
raw_bits=1024
charged_bits=917
net_bits=+107
```

This is not arbitrary-content match maintenance. At depth 6, each root stores
415 seed bits plus a 2-bit marker to regenerate 512 raw bits. Under a uniform
output law, full seed-space coverage for one 512-bit root slab is:

```text
2^415 / 2^512 = 2^-97
```

That is the bill: reachable-set sparsity, not hidden metadata.

STF is the first fully charged-positive scheduled-tree toy. BBL remains the
bounded trial-decode extension path:

- It uses fresh SHA-256 dice keyed by `(pass, packed_position, seed)`.
- It avoids arity-1 singles as the deep engine.
- It opens/carries by reverse trial decode and a fixed root checksum/referee.
- It prices that referee as `R * c_a(P)` ambiguity bits, not as free metadata.

## Conservation Boundary

No unbounded, content-blind, stateless birth/open/carry channel survived. The
sharp obstruction is per-record birth pass information. Under the uniform hash
law, the pass on which a match first appears is a content outcome, independent
of any public position orbit. If a decoder must distinguish `P` possible birth
passes for `R` surviving records, the missing coordinate has entropy
approximately:

```text
birth_bill = R * log2(P) bits
```

That is above the available average match win once `P >= 4`, because the
format's honest conditional gain remains about 2 bits per accepted match.

There are useful finite channels:

- Arity-1 singles have no free structural subsidy. Their ambiguity is exactly
  `S = P^R`, so cost is `log2(P)` bits per record.
- Length-pinned bundles get a real finite parse/explosion subsidy. For arity
  `a`, wrong-salt survivors cost
  `c_a(P) = log2(1 + (P - 1) * 2^-E_a)` bits per bundle. This can stay below
  2 bits over a finite pass range, but it grows like `log2(P) - E_a` and is not
  unbounded.
- Final-position/egg-carton boards round-trip mechanically, but the final
  arrangement note is the birth channel. If positions are stored, its optimal
  cost is an enumerative code over valid final arrangements. If positions are
  not stored and are only public-shuffle-derived, they convey zero birth bits.

BBL deliberately stays inside the finite bundle window where this cost is below
the selected-record savings.

The affine-orbit phase mutation turns that conservation rule into an exact
codec. A fixed public orbit makes each slot's final coordinate known to the
decoder. If the salt uses that final coordinate, decode is stateless and no
birth field is needed, but each slot gets only one independent dice roll. If
the salt uses the coordinate at the record's birth phase, the encoder gets
`P` rolls, but the selected phase must be stored or paid as trial-decode
ambiguity:

```text
toy codec: span=14 seed=9 chunks=64 trials=120
   P              mode   hit/ch   vis net     tight   birth/R   ambig/R    closed
   1  final-coordinate   0.0309   -54.125    -6.350     0.000     0.000    -0.044
   1  birth-coordinate   0.0306   -54.208    -6.386     0.000     0.000    -0.044

   2  final-coordinate   0.0303   -54.292    -6.396     0.000     0.000    -0.044
   2  birth-coordinate   0.0613   -48.300    -8.689     0.696     1.000    -0.087

   4  final-coordinate   0.0324   -53.625    -6.390     0.000     0.000    -0.044
   4  birth-coordinate   0.1158   -41.775   -13.418     1.624     2.000    -0.169

   8  final-coordinate   0.0342   -53.042    -6.388     0.000     0.000    -0.044
   8  birth-coordinate   0.2172   -36.200   -22.832     2.531     3.000    -0.319

  16  final-coordinate   0.0311   -54.042    -6.286     0.000     0.000    -0.044
  16  birth-coordinate   0.3884   -39.142   -38.799     3.470     4.000    -0.572

  32  final-coordinate   0.0312   -54.000    -6.415     0.000     0.000    -0.044
  32  birth-coordinate   0.6411   -64.000   -62.220     4.283     5.000    -0.944
```

Result: final-coordinate salts are a genuine decoder-known nonce channel but
do not refresh dice across possible birth phases. Birth-coordinate salts do
refresh match supply, but the phase label has about `log2(P)` ambiguity per
record. The public orbit reads total motion, not when a surviving record was
opened.

## Final-Board Model

Let:

- `R` = final survivors whose birth/open time must be known.
- `Q` = final coordinate space or board cells.
- `P` = possible birth passes.
- `V(R, Q, P)` = valid final arrangements under the board rules.
- Payloads are serialized in coordinate order, which is the cheapest ordering
  convention. If payload order is stored separately, add `log2(R!)`.

The cheapest final-board note is:

```text
arrangement_cost = log2(V(R, Q, P))
```

For a plain unordered occupied-cell board:

```text
V = C(Q, R)
arrangement_cost = log2 C(Q, R)
```

For a pass-lane board with `P` lanes of size `Q/P` and a known histogram
`r_t`, the placement component is:

```text
V_lane = product_t C(Q/P, r_t)
arrangement_cost = log2(V_lane)
```

But the lane assignment itself is the birth-pass map. The active kernel now
prices three versions: the most optimistic pass-label lower bound, a universal
lane board with enough cells for adversarial birth histograms, and a
value/count split that separates a cheap histogram from the expensive
assignment of labels to ordered survivors.

Most optimistic lower bound, assuming each survivor somehow gets a pass label
with no slot or ordering overhead:

```text
P passes  birth bits/R   net after 2b/R
       2         1.000            1.000
       3         1.585            0.415
       4         2.000            0.000
       8         3.000           -1.000
      16         4.000           -2.000
      64         6.000           -4.000
```

Universal lane board, unordered occupied cells, `S=R` cells per pass lane:

```text
R     P      Q=P*R  cell bits/R   net after 2b/R
1    64         64        6.000           -4.000
10   64        640        7.133           -5.133
100  64       6400        7.385           -5.385
1000 64      64000        7.425           -5.425
100   2        200        1.959            0.041
100   3        300        2.711           -0.711
100   4        400        3.201           -1.201
```

Value/count separation for pass lanes:

```text
R     P    H(hist)    E(assign)    total/R    RlogP/R
8     4      6.483        9.517      2.000      2.000
16    4      8.082       23.918      2.000      2.000
32    4      9.616       54.384      2.000      2.000
16    8     15.837       32.163      3.000      3.000
```

For uniform independent births, histogram plus assignment carries exactly
`R * log2(P)` bits. Shrinking `R` lowers the total note and the total 2-bit
wins together. It does not lower the per-survivor price:

```text
birth_cost_per_survivor = log2(P)
win_per_survivor ~= 2 bits
net condition: log2(P) < 2
```

So final positions beat the note only for very small finite pass counts under
the impossibly favorable lower bound (`P <= 3`; `P = 4` is already break-even
before other costs). If a board is made huge enough that `log2 C(Q, R) >=
R log2(P)`, then the coordinate note has enough capacity only by becoming at
least as expensive as the birth map. If a board is kept tight so the note is
cheaper, it stores only counts or a restricted set of lane histograms; the
missing assignment entropy must be stored elsewhere or paid as match-supply
loss.

## Verdict Table

| Idea | Mechanism | Open vs carry | Birth pass / salt | Fresh outputs? | Stored, derived, or hidden info | Entropy cost | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Position salts, current spec rule | Salt by match position and reverse shuffle to the pass state | Trial decode chooses which records open | Correct only when the decoder opens at the birth-state position | Yes, if birth pass is known | Birth pass is hidden in trial-decode/checksum | Singles: `log2(P)` per record; bundles: `c_a(P)` | Finite, not unbounded |
| Final-position board / egg carton | Store final occupied coordinates once | Coordinate can mark a lane or pass | Decoder reads lane from coordinate if stored | Yes if lanes are pass-specific | Final positions are the channel | `log2 V`; at least `R log2(P)` for arbitrary births | Not net-positive for `P >= 4`; shrinking `R` does not fix per-match cost |
| Fixed board + modular wrap | Public permutation of a fixed coordinate board | No extra signal | Final coordinate is a function of original slot and total passes | Yes only if salt varies, but birth still unknown | No stored positions, only public orbit | 0 stored bits, 0 birth bits conveyed | Refuted |
| Global public transform layer | Choose one reversible public transform for the whole layer, then scheduled-slot encode | Bitmap tells open/carry slots | Transform index is stored once for the layer | Yes through target refresh across public transforms | Transform index plus hit bitmap are stored and priced | K=256 raises hit/slot to 0.08750 but net worsens to -28.113 bits on 3072-bit random layers; large-deviation ledger remains negative | Amortized target-refresh coordinate still loses |
| Full-cover bundle lattice | Search every interval up to max arity and choose an all-seed tiling | No carry: every parser unit is a seed record | No birth tag; the arity sequence is decoded forward | Fresh targets can be reserialized, but coverage must exist first | Arity headers and seed addresses are stored; cover existence is the hidden scarcity | Exact toy: bloat rows cover (`-30.148`, `-17.647` bits), first non-bloat row has expected complete covers `8.716e-04`; 3-byte seed over 5x3-byte bundle hits `1.262e-29` per window | Solves ordering, not arbitrary compression |
| Adaptive smallest-replacement cover | Give each interval its smallest found seed width, then DP-pick the cheapest all-record cover | No carry: every parser unit is a seed record | No birth tag; arity and seed width are parsed forward | Yes through deeper seed-rank search and overlapping intervals | Variable seed width/rank boundary is hidden unless stored | Exact toy: free-width oracle `+12.955` bits, width-paid ledger `-50.640` bits on 144 raw bits | Confirms overlap effect, but paid seed-width channel kills it |
| Overlapping-option seed-rank crossover | Model 1+2+3+4+5 interval choices per block with first-hit rank order statistics and finite search caps | No carry in full-cover tiling | No birth tag; rank identifies deterministic seed witness | Yes with enough search; finite-depth oracle crosses before 15 bytes in the tested scale | Seed-rank length/terminator is hidden in oracle mode | Max arity 5: oracle-log rank has `+0.279` bits/block at 3 overhead and crossover `3.876`; block-local 120-bit row has `13.106` finite options/block, `1.754` positive options/block, and legal oracle `+0.283`, but selected-rank lower bound is `-0.430` (`-1.496` with marker) | The intended overlap crossover is real; the unpaid witness boundary is the unsolved channel |
| Collective selected-rank entropy | Entropy-code selected `(arity, floor(log2 rank))` symbols after oracle DP, plus exact lower rank bits | No carry in full-cover tiling | No birth tag; arity/log-rank symbols parse the cover | Yes with unlimited compute | Public selected-distribution model plus raw lower rank bits | Max arity 5: oracle `+0.297` bits/block, selected entropy lower bound `-0.423`, or `-1.489` with 3-bit marker | Selection bias helps, exact rank value still consumes gain |
| Recursive adaptive-cover churn | Repeatedly serialize an all-record minimum cover under one fixed seed universe | No carry: every layer is all records | No birth tag; each layer expands the current record stream | Yes as target population churn, without salt refresh | Arity, seed-width class, seed bits, and per-layer pad counts are stored | Exact recursive toy round-trips 80/80; 144 bits grow to `881.663` payload bits plus `15` header bits after six passes, about `1.35x` per layer | Birth is irrelevant, but target churn amplifies negative address economics |
| Recursive full-cover overlap dynamics | Re-run the full interval-cover replacement over many random-looking serialized passes | No carry: every parser unit is a seed record | No birth tag; each layer is a complete stateless cover | Yes in the unlimited-search model | The selected seed-rank witness language must still be parseable each pass | From 14,400 bits, invalid oracle reaches 6,845.9 bits after 64 passes and half-size around 59.7 passes; paid selected-entropy lower bound grows to 44,358.3 bits and selected+marker to 687,614.0 bits | Recursion amplifies the honest one-pass margin; it only compresses with free witnesses |
| Whole-cover ordinal language | Encode the entire arity/rank cover as one ordinal in a public cover language | No carry; ordinal decodes to a complete cover | No birth tag; ordinal determines the full cover | Yes within the generated cover language | Ordinal/codebook size is stored once | Exact 18-bit toy: `maxA=3, rank=2` covers `1.062%` with `log desc=13.579`; `maxA=3, rank=3` covers `22.074%` but `log desc=18.844` exceeds raw | Local terminators removed, but coverage/codebook counting returns |
| Whole-cover referee-as-codeword | Store checksum/referee bits and enumerate cover-language outputs | No carry; referee selects generated output only if unique | No birth tag; referee identifies output among generated covers | Yes within the generated cover language | Referee bits are the codeword; raw fallback mode is still needed | Exact toy: `ref=8` leaves `12.055` survivors; `ref=16` is `96.5%` unique but saves only `2` bits/hit and `-0.97875` with a raw tag | Checksum replaces ordinal only at codeword scale |
| Global-referee interval-cover language | Omit local seed ranks; enumerate all public interval-cover outputs and store one end referee | No carry if the referee leaves exactly one generated output | No birth tag; referee identifies the whole generated output | Yes within the public cover language | End referee/checksum and uniqueness burden are stored globally | 600 3-byte blocks: arity-5 120-bit language covers `0.63212` but half referee leaves `2^7199.3` survivors; arity-5 48-bit is half-unique but coverage is `2^-8640` | Moving witness bits to the end does not make them cheaper |
| Canonical-minimum cover derivation | Publicly choose the minimum cover description for each reachable output | No carry only after the output identity is known | No birth tag; canonical rule chooses a witness for an already identified output | Yes within the public cover language | Output identity/ordinal remains; duplicate descriptions are the only free reduction | Exact toy `maxA=3,rank=2`: `13.579` description bits collapse to `11.443` unique bits, but half-size code covers `0.00195`; broad 600-block rows have best half coverage `2^-7200` | Derivation removes duplicates, not the witness/output channel |
| Global fixed-depth rank cover | Store one rank width globally and use fixed-width seed ranks for every record | No carry in full-cover tiling; fixed rank width parses records | No birth tag; global width is root/header metadata | Yes through deeper fixed search | Global width is stored once; early-rank luck is discarded | Tested widths 24-120 with 3-byte blocks, max arity 5, 3 overhead bits: best shown rows `rank_bits=100` at `-1.750` bits/block and `120` at `-2.627` | Stateless parseability works, but fixed width removes order-statistic gain |
| Homophonic literal recoding | Give payload blocks multiple reversible surface encodings and let seeds supply synonym bits | Bitmap tells which scheduled pairs are seed records | No birth tag; decoder strips synonyms after expansion | Surface choices refresh targets only by storing synonym entropy | Synonym bits are visible surface entropy; bitmap/count are stored | Exact toy hit/pair stays near formula `0.22158` for synonym widths 0-4; net worsens from `-22.658` to `-424.810` bits | Surface multiplicity cancels against literal bloat |
| Whole-layer rechunk / superposition | Encode each layer as prefix tokens and scan every bit position against a fixed seed universe | Token tag tells literal vs record | Whole layer is born at the known layer pass; no per-record birth tag | Target windows refresh through reserialized token bits | Boundaries are visible as literal/record tokenization | Literal carriage; measured random bloat from 192 bits to 280.21 bits after pass 1 and 4756.83 bits after pass 6 | Exact stateless codec, but not net-positive |
| Adaptive-length target refresh | Choose one public chunk length per layer from `(10,12,14)` under a fixed seed universe | Chunk token or bitmap tells open/carry | No birth tag; length index is stored once per layer | Yes; boundaries and target population change | Length index plus hit bitmap/count are stored | Exact toy round-trips; chose 14-bit mode, final visible delta `-183.125` over five passes, tight nets about `-6.7` bits/layer; closed forms all negative | Effective-length migration selects least-bad bloat |
| Public-shuffle scheduled target refresh | Apply a public bit permutation each pass, then encode fixed scheduled chunks | Chunk token or scheduled bitmap tells open/carry | No birth tag; layer count and inverse permutation are decoder-known | Yes; hit/chunk stays near fixed-universe rate across eight passes | Visible chunk tokens, or bitmap+count in tighter ledger | Exact toy round-trips 200/200; hit/chunk remains `0.06292` to `0.05454`, but visible 512-bit random inputs grow to `777.50` bits and sparse scheduled ledger remains negative (`-7.540` on last layer) | Adjacency refresh works, open/carry cost still dominates |
| Decoded-left-context nonce refresh | Salt each public-shuffled chunk by the previous decoded chunk | Chunk token or bitmap tells open/carry | No birth tag; previous decoded chunk is known before opening current chunk | Yes; contexts change with decoded content and public shuffle | Neighbor state is derived; bitmap/count still stored | Exact toy round-trips 60/60; hit/chunk stays `0.02963` to `0.03962`, visible 512-bit inputs grow to `643.82` bits after four passes, tight ledger stays about `-4.6` to `-5.3` bits/layer | Stable neighbor nonce works, one active context does not multiply supply |
| Context-lane validity grammar | Derive lane bits from previous decoded chunk/pass/slot and store only local seed bits | Token or bitmap tells open/carry; lane excludes wrong seed classes | No birth tag; lane is known before expansion | Yes; causal contexts change across passes | Lane bits are derived, but eligible seed supply is thinned; bitmap/count still stored | Exact toy round-trips all lanes; lane 4 closed net `-0.00562`, lane 10 `-0.00009`; visible/tight ledgers remain negative | Wrong-lane failure is real, but true-hit supply is thinned equally |
| Checkerboard two-neighbor context | Carry one parity as raw guard chunks; salt active parity by left and right guards | Active token or bitmap tells open/carry; guard parity is scheduled carry | No birth tag; both neighbors are known after parsing guard slots | Yes; public shuffle and alternating parity change guard contexts | Guard parity is raw payload; active bitmap/count still stored | Exact toy round-trips 20/20; 9-bit seeds have active closed net `-0.04437`, all-slot net `-0.02219`, visible final `-28.750`, tight layers about `-2.2` to `-2.9` | Fixes right-neighbor instability, but guard carriage and active bitmap keep it negative |
| Selected public-shuffle hitmap shaping | Try K public permutations and choose the one with best lower-bound bitmap ledger | Bitmap tells open/carry; shuffle index selects coordinates | No birth tag; chosen public permutation is stored once per layer | Yes; hit/chunk rises with K | Shuffle index plus residual bitmap entropy are stored | Pass 1 hit/chunk rises from `0.06134` at K=1 to `0.16644` at K=64, but tight net worsens from `-5.896` to `-7.333`; visible net remains negative | Choosing nicer coordinates is still a paid channel |
| Prefix-parse-state nonce layer | Salt each record expansion by decoder-visible prefix token state | Token tag tells literal vs record | State is known before opening; no birth tag | Yes; hit/window stayed near 0.033-0.036 over six passes | Prefix token stream supplies state; non-hit regions are carried as literals | Literal carriage; measured random bloat from 192 bits to 1661.38 bits after six passes | Maintains match rate but not compression |
| Sparse-map prefix-state layer | Store miss bits, seeds, an enumerative map, and count class for prefix-state matches | Map tells open/carry positions | State is reconstructed from output prefix before each record opens | Yes for the selected layer | Selected-span map and count class are stored and priced | Map+count cost 94.521 bits vs 67.800 gross savings on 512-bit random inputs | Removes token overhead, still negative |
| Scheduled-slot prefix-state layer | Use public non-overlapping slots and store a hit bitmap plus seeds/literals | Bitmap tells open/carry slots | State is reconstructed from decoded scheduled chunks | Yes on scheduled slots | Hit bitmap and hit-count class are stored and priced | Toy `-5.828` bits at 512 bits; closed-form `p*d-H(p)<0` for tested gaps | Count-priced finite lane, still negative under uniform hits |
| Parent-summary nonce slots | Store one parent summary per group, then salt each child slot by summary and local slot | Bitmap tells open/carry slots; summary is verified after child decode | Parent summary is known before child expansion | Yes, but only for the one active parent value | Parent summary bits plus hit bitmap/count are stored | At 1024 bits, best shown summary-0 row loses `-8.706`; summary 2/group 16 worsens to `-16.630`; closed form subtracts `summary_bits/group_size` per slot | Valid decoder-known salt, no extra arbitrary coverage |
| Grouped scheduled bundles | Accept only all-hit public slot groups to amortize bitmap frequency | Group bitmap tells open/carry groups | State is reconstructed through decoded group chunks | Yes within scheduled hit groups | Group bitmap and group-count class are stored and priced | 4096-bit random trials lose `-29.620`, `-6.558`, `-6.399`, `-6.160` bits for group sizes 1-4; `p^g*g*d-H(p^g)<0` | Count-free apparent wins are hidden cardinality channels |
| Bundle-geometry partition selector | Store/select one public group shape; shape salts child bundle records | Mode/shape tells which subsegments are records vs literals | No birth tag; shape is known before child expansion | Yes across shape-specific child universes and reserialized passes | Shape/mode assignment is stored visibly or as an enumerative mode map | Exact toy round-trips 160/160; final visible delta `-346.625`; tight layers `-23.505` to `-28.687`; optimistic all-shape net `-0.47256` | Geometry is a real nonce, but the shape selector is the open/carry map |
| Bucket-directory one-hit map | Store which public buckets are non-empty and one local hit index per non-empty bucket | Bucket directory plus local index tells open/carry for chosen hit | No birth tag; scheduled buckets are public | Yes for scheduled slots | Directory, count class, and local index are stored; extra hits are discarded | 4096-bit random trials lose `-28.022`, `-25.641`, `-22.442`, `-18.260` bits for bucket sizes 2-16; closed-form rows stay negative | Coarser map trades bitmap bits for local coordinate and lost hits |
| All-or-raw block mode | Compress a block only if every scheduled slot hits; otherwise carry the whole block raw | One mode bit tells compressed vs raw block | State is reconstructed through decoded block chunks | Yes inside compressed blocks | Mode bit is stored per block; raw fallback carries misses | 4096-bit random layers lose from `-221.580` bits at group 1 to `-18.000` at group 16; `p^g*g*d-1<0` | Removing bitmap by all-hit blocks collapses hit supply |
| Greedy score-order count-only map | Public order says every matchable slot must open; store only seed/literal streams | Derived only if map is unique after greedy validity pruning | No birth tag; slot order is public | Yes for scheduled slots | Hit count plus survivor ambiguity; checksum needed when non-unique | Exact 12-slot toy round-trips 400/400 but averages `17.302` survivors; avoids `2.504` bitmap bits but leaves `2.175` ambiguity bits and `-2.776` net | Structural pruning helps, does not remove map channel |
| Prefix-stop count-free map | Open consecutive matchable slots in public order until first miss; omit bitmap and per-block count | Stop count is inferred from block length only if boundaries are free | No birth tag; stop rule is public | Yes for prefix scheduled slots | Total compressed length/stop-count class plus survivor ambiguity | Exact toy round-trips 120/120; `+0.867` bits after ambiguity only, but length/count class costs `5.615`, giving `-4.748` | Positive finite row was hidden length-channel use |
| Seed-length class nonce | Store a class id that selects seed length and salts expansion | Bitmap tells open/carry; class id is read before seed expansion | Class is stored per hit, pass is public for the layer | Yes across classes and public passes | Class id and seed address are stored; bitmap/count are stored | `9/10` classes raise hit/slot to about 0.092 but worsen net to about -12.9 bits on 1024-bit random layers; closed-form all tested class sets negative | Parser-known salt works, address/class cost dominates |
| Arity-header-known nonce | Store arity header before seed; arity salts expansion and selects span length | Visible token or parse map tells literal vs record and arity | No birth tag; arity is read before expansion | Yes; reserialized targets keep finding arity-3/4 records over passes | Arity header/tag or lower-bound parse/arity map is stored | Exact toy round-trips 120/120; final visible delta `-290.333`; tight net per layer `-15.144` to `-20.058`; arity-3 closed net `-0.13812`, arity-4 `-0.00867` | Parser-known arity is valid salt, but the arity/open map consumes the gain |
| Tagless value-code grammar | Give seed-image chunks short prefix words and complement chunks long prefix words | Codeword class tells open/carry with no bitmap | State is known before each prefix parse | Yes; seed-image sets vary by prefix state | Kraft space is the paid channel; long complement words carry misses | 512-bit random inputs bloat to 738.14 or 756.05 bits after four passes for short lengths 5/6; no-bloat point uses raw-length short words | Open/carry solved, compression conserved away |
| Finite-class local grammar bound | Generalize local parser-known classes, lanes, seed lengths, and fallback words as a prefix code | Local codeword class tells open/carry | Class/salt known before local expansion | Yes locally, depending on class | Kraft mass and fallback language are priced optimistically | Disjoint-image/ideal-fallback designs all have expected length >= raw; brute-force best short-code rows reach only `14.00011` bits for 14-bit chunks | Scoped impossibility for local per-slot parser-known nonce tricks |
| Growing PCTB board | Encode carry/open as board instruction slots, store final positions | Instruction lane is decodable | Pass/code salt is recoverable | Yes | Final occupied set | Carry-only exact note `log2 C(Q_P, R)`; measured 21.9x raw at 64 passes for `M=1000` | Mechanics work, ledger fails raw+epsilon |
| Placement lanes / encrypted instruction slots | Hide open/carry in lane choice or PRP slot | Lane tells instruction if stored | Lane or PRP code tells salt | Yes | Lane occupancy / instruction placement | Same as final positions; if encrypted, ciphertext still has same entropy | Paid channel, not under 2 bits past tiny P |
| Pass count scratchpad | Store total pass count in header | Does not identify individual records | Gives `P`, not per-record birth | Helps schedule, not birth | Header total only | `log2(P)` total, but need `R log2(P)` | Insufficient except tiny `R` |
| CRT / modular clocks | Read residue clock from final coordinate | No open/carry distinction | Final residue is fixed by final slot, not birth | Public orbit refreshes positions but not birth info | Public coordinate | Exact orbit toy: final-coordinate hit/ch stays near `0.031` for P=1..32 with closed `-0.044`; birth-coordinate P=32 reaches `0.6411` hit/ch but owes `5` bits/hit ambiguity | Public final clocks do not convey birth phase |
| Affine / Feistel orbit fingerprints | Use orbit phase or stride as epoch | Singles have no stride; bundles get only candidates | Orbit phase reads total count, not birth for singles | Yes if birth coordinate is known | Public orbit, or stored birth phase | Exact toy: final-coordinate salt is stateless but not fresh across births; birth-coordinate salt refreshes but tight net worsens to `-62.220` at P=32 | Finite bundle subsidy only; singles still owe phase |
| Parity / sign lanes | One-bit lane from position parity or involution | Can filter candidates if acceptance is gated | Informative only if coupled to birth | Freshness reduced by gating | Either decoupled public parity or gated supply | Decoupled: 0; gated: 1 supply bit per bit | No net gain |
| Fibonacci / Zeckendorf registers | Number-system phase or bounded register | Same as public orbit | Birth absorbed by inverse starting slot | No extra channel | Public phase | 0, or stored phase reference / supply loss | Refuted |
| Occupancy / holes | Bundle removes slots; hole-run board marks opened bundles | Visible holes or mode bits tell open vs carry | Hole set can identify bundle geometry only if retained | Yes | Hole positions, mode bits, or enumerative hole map | Exact 4-chunk toy round-trips 120/120; free packed-hole oracle is `+23.800` bits, but visible mode codec is `-232.200`, cell occupancy is `-1000.200`, tight bitmap is `-11.712` | Holes are a valid signal only when paid |
| Scheduled edges / exclusion rules | Use public `(pass, slot)` edge class as salt and omit class bits from stored local seed | Bitmap tells open/carry slots | Pass/slot class is public before expansion | Yes across public passes and slots | Class bits are derived from schedule; missing class bits are paid as seed-supply loss | Exact toy round-trips across 3 passes; edge bits 0-4 all lose, best sampled row about `-5.466` bits on 1024-bit random layers; closed-form `p*gross-H(p)<0` | Fresh salt works, supply thinning and bitmap conserve it away |
| Trial decode / checksum pruning | Omit hit map, enumerate ordered seed/literal assignments, and keep checksum matches | Checksum selects one map only if wide enough | Birth/salt candidates are trialed; checksum/referee selects survivors | Yes for candidates tested | Checksum/referee plus hit count or stream lengths | Exact toy: checksum 0 leaves 26.390 survivors avg; checksum 12 is unique but loses -12.760 bits on a 96-bit block; fixed hit count needs about `log2 C(slots,hits)` checksum bits | Checksum replaces the bitmap only at the same entropy scale |
| Explosion checks | Wrong-salt digest often fails self-delimiting parse | Prunes wrong bundle opens | Only length-pinned records benefit | Yes for candidates not pruned | Structural grammar | Singles `E=0`; bundles finite `E_a` | Useful finite intercept |
| Residue-valid bundle trilemma | Use local residue bits to make wrong-pass openings invalid | Validity check can reject openings only when target language is restricted | Salt/pass is implicit in residue check, but wrong pass survives if expansion/repair is constrained | Yes if pass is in hash/check | Residue validity is either target restriction, seed-class restriction, or stored syndrome | Exact toy: raw-filter 6-bit residue has wrong `q=0.01621` but hit/chunk `0.0000`; constrained and syndrome modes have wrong `q=1.00000`; syndrome hit/chunk about `0.23` but closed ledger `-5.294` | Residue bits can prune, repair arbitrary targets, or stay unpaid, but not all three |
| Nested referee grammar | Recursive checks make wrong-pass expansions fail internally | Valid parse distinguishes surviving openings | Structural survival can select a true pass only when validity is paid | Yes for false-open pruning | Referee bits are stored in wrapper/target, derived from seed class, or hidden | Exact wrapper round-trips; `21/5000` wrong streams survived vs `19.53` expected; best fantasy row `7.273e-04` falls to `4.335e-11` when charged | Structural pruning works, but nested validity is not free |
| Biased seed grammars | Make seed class imply birth pass | Decoder reads class from seed | Birth bits carried by seed class | Fewer eligible seeds per pass | Match supply | `I` conveyed bits cost at least `I` supply bits; residual stored | No sub-1x channel |
| Value/count separation | Store only high-value seed-class counts/histogram, not per-slot class assignments | Counts do not tell open/class positions | Same as biased grammar if used for birth labels | Yes only for classes with enough supply | Count histogram is cheap; assignment map is hidden unless charged | Exact 32-slot counter: `d4` count net `+0.17417` but full net `-0.08729`; positive full-net jackpot rows are infeasible (`d16/p8`) | Histogram alone is not decode information |
| Recursion / layer stacking | Re-run output as a new file, resetting epoch | Layer boundary is known | Birth free only within short layer | Yes per layer | Layer carriage | Base-rate net/bit `-0.35` to `-0.37`; flip requires about 48x density | Not content-blind net-positive |
| BBL random-density surface | Length-pinned bundles with arity 2-5 and explicit ambiguity cost `c_a(P)` | Dense selected mode parses records; random mode still needs hit positions | Wrong-pass ambiguity is priced by structural parse survival | Yes over finite pass windows | Dense selected bundles need no hit map; arbitrary random windows need open/carry map entropy | Arity 5 at `P=1e6` has `c=2.111`, but best sparse random row has map net/hit `-6.548`; 50% dense layer requires gap 63 with uniform hit `1.355e-20` | Valid finite ledge, not arbitrary/random density solution |
| Bounded Bundle Layer | Use only arity>=2 length-pinned bundle records inside a capped pass window | Reverse DFS opens/carries records; structural parse prunes wrong opens; checksum/root picks survivor | Salt is `(pass, packed position, seed)` and is tested during reverse pass | Yes across the bounded pass window | No birth tags; ambiguity is charged as checksum/referee bits | `R*c_a(P)` plus fixed/root fields; selected-record net positive while `gross_win > c_a(P)` | Finite residual/extension path; useful while bundle ambiguity stays below selected-record savings |
| Scheduled Forest | Accept only complete public binary bundle trees; every node opens at its public depth | No carry ambiguity inside tree mode; raw fallback otherwise | Salt is `(depth, tree position, seed)` | Yes across tree depths | Root seeds plus mode/depth/count/checksum; no birth tags | Verified toy: depth-2 forest +41 bits, depth-3 forest +1 bit | **Fully charged-positive positive-control**; depth/search reach is bottleneck |
| Typed Scheduled Tree | Public tree depth gives child type; internal expansions emit child seeds directly | No carry ambiguity; every node opens at public depth | Salt is `(node kind, seed, depth, tree position)` | Yes across depths and positions | Root seeds plus mode/depth/count/checksum; schedule supplies type | Verified toy: depth-4 +9 bits, depth-6 +107 bits fully charged | Reachable-set control only; not arbitrary-content supply maintenance |

## Bundle Entropy Ledger

For length-pinned arity `a` bundles, let `E_a = -log2(q_a)`, where `q_a` is the
wrong-salt parse survival probability. The tested/derived values are:

| arity | `E_a` bits | near-free knee `2^E_a` | pass cap for birth cost `< 2 bits` | `c_a(64)` |
| --- | ---: | ---: | ---: | ---: |
| 2 | 9.36 | 657 | 1972 | 0.132 |
| 3 | 12.59 | 6165 | 18497 | 0.015 |
| 4 | 14.97 | 32094 | 96282 | 0.003 |
| 5 | 18.20 | 301124 | 903374 | 0.000 |

This is the best surviving finite open/carry-ambiguity mechanism for BBL. It
should be read carefully:
higher arity moves the intercept by making wrong parses rarer, but it does not
remove the asymptotic slope. At large `P`, the residual grows as:

```text
c_a(P) = log2(1 + (P - 1) * 2^-E_a) ~= log2(P) - E_a
```

The pass caps above price only the birth/open channel, not whole-file
compression. Content-blind hit density and literal carriage still decide
whether a layer should be kept.

## Prior Control And Residual Ledgers

TST is charged-positive in a generated reachable scheduled-tree regime, not on
random data. The honest whole-slab toy ledger is:

```text
charged_bits = mode + depth + root_count + fixed_width_root_seeds + checksum
net_bits = raw_bits - charged_bits
```

The verified charged-positive cases are:

```text
depth=4 roots=4 leaves=64  raw_bits=512  charged_bits=503  net_bits=+9
depth=6 roots=2 leaves=128 raw_bits=1024 charged_bits=917  net_bits=+107
```

The price is reachability density and encoder search. If the input group is not
in the recursive image of any searched root seed, typed-tree mode falls back to
raw. The current positive fixture is generated from reachable roots and stores
those roots at full fixed width; it is a codec/accounting proof for the
mechanism, not a natural-corpus prevalence claim.

This means TST did not move bloat into unpriced metadata. It moved the bill into
match supply. That may still be useful for a shaped, public-preset, or generated
subspace, but it is not a solved content-blind arbitrary-input match-rate
maintenance theorem.

BBL remains the best residual finite-pass mechanism for dense selected bundles.
The honest selected-record ledger is:

```text
net_per_bundle = replaced_bits - record_bits - c_a(P)
c_a(P) = log2(1 + (P - 1) * 2^-E_a)
```

For arity 2 at `P = 64`, `c_a(P) = 0.132` bits. With the Golden-style gross
selected-record win of about `2.17` bits, the charged birth/open net is about
`2.038` bits per accepted bundle before fixed header amortization. With `R`
accepted bundles and few leftovers:

```text
net ~= R * 2.038 - fixed_header - literal_carriage
```

So BBL is net-positive for large dense generated/reachable inputs where
accepted bundle density is high. The remaining work is to supply or discover
that dense class without violating the content-blind premise, or to explicitly
classify the mode as a dense-class/hybrid mode.

Concrete toy evidence now exists for the generated dense class:

```text
bounded_bundle_codec.py generated dense fixture
blocks=24, passes=2, matches=13
payload_delta=+19.000 bits
asymptotic_delta=+11.918 bits after ambiguity pricing
charged_delta=-54.082 bits after the 66-bit toy header
```

So the fixture is positive before fixed-header amortization and negative after
the tiny-instance fixed root cost. BBL is therefore not the top winner; it is the
bounded residual lane that can be combined with TST/STF when dense bundle
matches remain after scheduled-tree extraction.

Scheduled Forest supplies that mutation for a stricter generated class:

```text
scheduled_tree_codec.py forest fixture
depth=2, roots=8, leaves=32
charged_delta=+41 bits after mode/depth/root-count/checksum
depth=3, roots=2, leaves=16
charged_delta=+1 bit after mode/depth/root-count/checksum
```

The fixed-width version failed at depth 3. The tiered-width mutation uses a
larger internal-node seed budget and reaches a charged-positive depth-3 forest,
but only barely.

Typed Scheduled Tree supersedes that bottleneck by removing internal marker
entropy. Its public type schedule makes every seed decodable at every internal
node, so reachability no longer collapses with depth in the toy generated
regime. The new bottleneck is witness search on non-generated inputs.

## Impossibility Statement

Under the uniform hash law, for content-blind salted Telomere:

1. Birth pass is the time index of a uniform match event.
2. Public shuffles, CRT clocks, Feistel orbits, Fibonacci phases, and parity
   labels are deterministic functions independent of that match event unless
   the encoder gates acceptance or stores placement.
3. A decoder that must recover `R` independent birth passes over `P` candidate
   passes needs a discriminator for about `P^R` readings.
4. Any discriminator has cost `log2(P^R) = R log2(P)` bits, except for finite
   structural parse subsidies on length-pinned records.
5. Those subsidies are constants. They shift a finite intercept, but cannot
   sustain unbounded pass freshness.

Therefore a free, content-blind, unbounded birth channel would make arbitrary
random data net-compress with bounded worst-case loss, violating the counting
gate. The bill must appear as stored bits, match-supply loss, wrap/carriage, or
compute/checksum search.

## Runnable Kernels

Fast consolidation:

```powershell
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
python model_analysis\birth_channel_research\quick_birth_channel_kernels.py
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
python model_analysis\birth_channel_research\bounded_bundle_codec.py
python model_analysis\birth_channel_research\scheduled_tree_codec.py
python -c "import sys; sys.path.insert(0, r'model_analysis\birth_channel_research'); import scheduled_tree_codec as s; s.forest_demo(depth=3, roots=2)"
```

Representative audited lane kernels:

```powershell
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
python model_analysis\birth_channel_research\A-modular-orbit_invariance.py
python model_analysis\birth_channel_research\C-crt-clock_odometer.py
python model_analysis\birth_channel_research\C-crt-clock_frozen_coord.py
python model_analysis\birth_channel_research\P2-recursion-ledger.py
python model_analysis\proof_kernel\pctb_ledger.py
python model_analysis\birth_channel_research\P2-biased-hash_coupling_ledger.py
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
python model_analysis\birth_channel_research\bounded_bundle_codec.py
python model_analysis\birth_channel_research\scheduled_tree_codec.py
```

The default `B-ambiguity-bound_survivor_count.py` and `P2-bundle_survivor.py`
are valid but heavier in their high-`T` demonstration modes. Use their formulas
or reduce their demo parameters when quick reproduction is the goal.

## Verification Performed

Most recent local verification in this checkout:

```text
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
  ok: visible nonces paid as address bits; public unstored lanes hit the
  200000-candidate cap at K=8 and remain negative after lower-bound ambiguity;
  left-context/position nonce round-trips 20/20 but stalls by pass 2 and loses
  -19.300 charged bits vs payload; fixed-universe target-churn round-trips but
  decays by pass 3 and loses -87.540 bits vs original payload; arity-flex
  target-churn stalls by pass 2 and loses -92.895 bits vs payload; full-cover
  bundle lattice round-trips successful covers with no birth/open channel, but
  only bloat rows cover materially (-30.148 and -17.647 bits on successful
  covers), while the first non-bloating row has only 8.716e-04 expected covers
  and no observed covers; adaptive smallest-replacement cover confirms the
  overlap-order-statistic effect with a +12.955-bit free-width oracle row, but
  flips to -50.640 bits once variable seed widths are stored; recursive
  adaptive-cover churn round-trips 80/80 with no birth/open channel, but grows
  144 bits to 881.663 payload bits plus 15 end-header bits after six passes,
  about 1.35x per layer; overlapping
  seed-rank crossover at 3-byte block scale shows max arity 5 has 15
  options/block, +0.279 bits/block at 3 overhead bits, and crossover 3.876
  under the invalid log-rank oracle, while ideal geometric rank coding is
  -0.061 bits/block at zero overhead and -0.751 at 3 bits, and
  self-delimiting delta rank is -2.078 bits/block even at zero overhead; the
  finite-depth overlap sweep crosses under the invalid oracle around 92-96
  search bits, reaches +0.279 at 120 bits, but has -2.604 fixed-width and
  -0.423 selected-rank-lower-bound ledgers at 120 bits; the block-local
  15-option restatement shows 13.106 finite hit options/block and 1.754
  positive options/block at 120 search bits, with a legal oracle cover at
  +0.283 bits/block but a paid selected-witness lower bound at -0.430;
  collective selected-rank entropy coding narrows the gap but remains negative
  at max arity 5 (-0.423 lower-bound bits/block, or -1.489 with marker);
  recursive full-cover overlap dynamics projects the same all-block replacement
  across 64 passes: invalid log-rank oracle shrinks 14,400 bits to 6,845.9 and
  reaches half around 59.7 passes, but paid ideal-geometric rank grows to
  103,230.8 bits, selected-rank entropy lower bound grows to 44,358.3 bits,
  and selected+marker grows to 687,614.0 bits;
  whole-cover ordinal language removes local terminators but in an exact
  18-bit toy `maxA=3, rank=2` covers only 1.062% of outputs at `log desc`
  13.579, while `rank=3` covers 22.074% but exceeds raw at `log desc` 18.844;
  whole-cover referee-as-codeword shows short referees remain ambiguous
  (`ref=8` leaves 12.055 survivors), while near-unique referees approach raw
  and still lose with fallback (`ref=16` gives -0.97875 expected bits with tag);
  global-referee interval-cover language moves local witnesses to one end note,
  but arity-5 120-bit search on 600 3-byte blocks has 0.63212 coverage while a
  half-size referee leaves 2^7199.3 survivors, and the half-unique 48-bit row
  has only 2^-8640 coverage; canonical-minimum cover derivation removes
  duplicate descriptions (`13.579` to `11.443` bits in the maxA=3/rank=2 toy)
  but half-size canonical coverage is only 0.00195 in the toy and 2^-7200 in
  broad 600-block rows;
  global fixed-depth rank cover is stateless/parseable but all tested widths
  24-120 stay non-positive, with rank_bits 100 at -1.750 bits/block;
  homophonic literal recoding round-trips and offers decoder-visible synonym
  surfaces, but hit/pair stays near 0.22158 for synonym widths 0-4 while net
  worsens from -22.658 to -424.810 bits as literal surfaces grow;
  global public transform selection round-trips and raises hit/slot from 0.06232 to
  0.08750 at K=256, but charged net worsens from -26.445 to -28.113 bits and
  the ideal large-deviation ledger stays negative; whole-layer
  rechunk/superposition round-trips 200/200 but pass 1 bloats 192-bit random
  inputs to 280.21 bits on average and six passes bloat to 4756.83 bits;
  adaptive-length target refresh round-trips and can store length choice once,
  but it chose the least-bad 14-bit mode and bloated by -183.125 visible bits
  after five passes while closed-form options stayed negative;
  public-shuffle scheduled target refresh round-trips 200/200 and maintains
  hit/chunk near the fixed-universe rate over eight passes (0.06292 down to
  0.05454), but visible tokens grow 512-bit random inputs to 777.50 bits and
  the tighter scheduled-bitmap ledger remains negative, ending at -7.540 bits
  versus that layer input;
  decoded-left-context nonce refresh round-trips 60/60 and uses the previous
  decoded chunk as a stable neighbor salt before opening the current chunk,
  but hit/chunk only stays near the one-context rate (0.02963 to 0.03962),
  visible tokens grow 512-bit random inputs to 643.82 bits after four passes,
  and the tight bitmap ledger stays negative around -4.6 to -5.3 bits/layer;
  context-lane validity round-trips all tested causal lane widths, but lane
  bits thin true-hit supply equally and the closed net stays negative
  (`lane 4=-0.00562`, `lane 10=-0.00009`);
  checkerboard two-neighbor context round-trips 20/20 and makes both adjacent
  guards decoder-known before active expansion, but 9-bit seeds have active
  closed net -0.04437, all-slot net -0.02219, visible final -28.750, and tight
  layers about -2.2 to -2.9 bits;
  selected public-shuffle hitmap shaping round-trips and raises pass-1
  hit/chunk from 0.06134 at K=1 to 0.16644 at K=64, but the favorable
  bitmap lower-bound ledger worsens from -5.896 to -7.333 bits after paying
  the shuffle index and residual bitmap entropy;
  prefix-parse-state nonce layer round-trips 200/200 and keeps hit/window near
  0.033-0.036 through six passes, but still bloats to 1661.38 bits;
  sparse-map prefix-state accounting round-trips 200/200 on 512-bit random
  inputs and improves to -26.721 net bits, but its 94.521-bit map+count cost
  exceeds 67.800 gross seed-span savings;
  scheduled-slot prefix-state accounting round-trips 200/200 and improves to
  -5.828 net bits with count-priced bitmap accounting, while closed-form
  p*d-H(p) stays negative for tested uniform-hit gaps; parent-summary nonce
  slots round-trip and provide a legitimate decoder-known child salt, but the
  best sampled 1024-bit row still loses -8.706 bits and positive summary widths
  only add metadata;
  scheduled-edge exclusion rules round-trip across 3 public passes and provide
  decoder-known salt freshness, but edge bits 0-4 all lose on 1024-bit random
  layers and closed-form p*gross-H(p) stays negative;
  seed-length class nonce round-trips across 3 public passes and raises hit
  rate for class sets such as 9/10, but charged net worsens to about -12.9
  bits and all closed-form class-set ledgers stay negative; arity-header nonce
  round-trips 120/120 and keeps finding arity-3/4 records over four passes,
  but visible final delta is -290.333 and tight layers lose -15.144 to
  -20.058 bits; value/count separation makes feasible rows look positive with counts only (`d4`
  `+0.17417`) but full assignment entropy flips them negative (`d4`
  `-0.08729`, `d8` `-0.00562`);
  grouped scheduled bundles round-trip and avoid the count-free apparent win:
  group sizes 1-4 lose -29.620, -6.558, -6.399, and -6.160 bits on 4096-bit
  random inputs once the group-count class is charged; bundle-geometry
  partition selector round-trips 160/160 and finds shape-specific records, but
  final visible delta is -346.625 and tight layers lose -23.505 to -28.687 bits;
  bucket-directory one-hit maps round-trip but lose -28.022, -25.641, -22.442,
  and -18.260 bits for bucket sizes 2, 4, 8, and 16 because directory entropy
  plus local indices exceed one-hit savings;
  bitmap-free all-or-raw block modes round-trip but lose from -221.580 bits at
  group size 1 to -18.000 bits at group size 16 on 4096-bit random layers, and
  whole-layer all-hit mode has essentially zero random hit probability;
  hole-run bundle occupancy round-trips 120/120 and shows the free packed-hole
  oracle at +23.800 bits, but exact visible mode bits lose -232.200, explicit
  cell occupancy loses -1000.200, and the tight enumerative hole map loses
  -11.712 bits;
  greedy score-order count-only hit map round-trips 400/400 and avoids 2.504
  bitmap bits on average, but leaves 17.302 surviving maps, 2.175 ambiguity
  bits, and -2.776 net bits on a 96-bit block;
  prefix-stop count-free hit map round-trips 120/120 and appears positive
  after ambiguity only (+0.867 bits), but the hidden total length/count class
  costs 5.615 bits and flips the charged net to -4.748 bits;
  checksum-pruned hit-map search round-trips but checksum 0 leaves 26.390
  map survivors on average and checksum 12 is unique only after losing -12.760
  bits on a 96-bit toy block;
  tagless value-code grammar round-trips with no open/carry bitmap and keeps
  fresh state-dependent hit rates near 0.056-0.061, but Kraft pricing bloats
  512-bit random inputs to 738.14 or 756.05 bits after four passes for short
  lengths 5/6 and reaches only the raw no-compression point at short length 8;
  finite-class local grammar bound shows disjoint-image/ideal-fallback local
  designs all have expected length >= raw, with brute-force best short-code
  rows reaching only 14.00011 bits for 14-bit chunks; BBL random-density
  surface confirms high-arity ambiguity is cheap in dense selected mode
  (`a=5,P=1e6,c=2.111`) but arbitrary sparse windows lose after map entropy
  (`map E=-5.116e-02`) and a 50% dense layer needs uniform hit probability
  only `1.355e-20`;
  self-dating residue best toy row is arity 2 residue 6 at 6.018e-05 expected
  net bits/window; residue/syndrome trilemma round-trips exact codecs and
  shows 6-bit raw-filter residue lowers wrong q to 0.01621 but collapses
  hit/chunk to 0.0000 in the sample, while syndrome restores hit/chunk to
  about 0.23 with wrong q=1 and closed ledger -5.294; derived seed-class
  validity best row is arity 3 class 6 at 5.137e-05 expected net bits/window;
  nested referee grammar round-trips
  5000/5000 and wrong-stream survival matches expectation (21/5000 vs 19.53),
  but its best fantasy row falls from 7.273e-04 to 4.335e-11 once referee
  validity is charged; self-consistent output nonce stays near one output per
  seed rather than multiplying supply; affine-orbit final-coordinate salt
  round-trips and stays near 0.031 hit/chunk with closed -0.044 for P=1..32,
  while birth-coordinate salt reaches 0.6411 hit/chunk at P=32 but owes
  5 bits/hit ambiguity and has tight net -62.220; final-position board gate
  shows P=64 needs at least 6.000 birth-label bits/survivor and a universal
  R=100, Q=6400 cell board costs 7.385 bits/survivor; 50% random compression
  counting gate shows n=128 leaves about 63 missing bits/input; exception
  burden gate shows max short coverage at n=128 yields only 7.047e-18
  optimistic average bits saved/input; window/placement multiplicity gate shows
  L=32, r=16 half coverage leaves 0.264 priced expected bits/chunk; repeated
  compute gate shows half-coverage random spans need an implicit trial
  coordinate of about L-r bits, leaving about 0.529 bits saved per hit
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
  ok: depth-4 net_bits=+9; depth-6 net_bits=+107; raw fallback sanity ok
python model_analysis\birth_channel_research\scheduled_tree_codec.py
  ok: depth-2 forest net_bits=+41; raw fallback sanity ok
python model_analysis\birth_channel_research\bounded_bundle_codec.py
  ok: random and generated-dense fixtures round trip; dense asymptotic delta +11.918 bits
python model_analysis\birth_channel_research\quick_birth_channel_kernels.py
  ok: final-board, PCTB, singles, bundle, biased-seed, and recursion ledgers
python -m py_compile model_analysis\birth_channel_research\arbitrary_freshness_kernels.py model_analysis\birth_channel_research\typed_scheduled_tree_codec.py model_analysis\birth_channel_research\scheduled_tree_codec.py model_analysis\birth_channel_research\bounded_bundle_codec.py model_analysis\birth_channel_research\quick_birth_channel_kernels.py
  ok
cargo clippy --all-targets -- -D warnings
  ok
cargo check --features gpu --all-targets
  ok
```

Known verification blockers not introduced by this report:

```text
cargo fmt --all -- --check
  fails on pre-existing formatting in src/bin/v2_cost_probe.rs
python scripts\doc_lint.py
  fails: missing required file docs/ARCHITECTURE.md
cargo test --all-targets
  Rust/unit/integration tests pass until tests\doc_lint.rs, which fails on the
  same docs/ARCHITECTURE.md requirement
```

Executed successfully in this checkout:

```text
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
python model_analysis\birth_channel_research\A-modular-orbit_invariance.py
python model_analysis\birth_channel_research\C-crt-clock_odometer.py
python model_analysis\birth_channel_research\C-crt-clock_frozen_coord.py
python model_analysis\birth_channel_research\P2-recursion-ledger.py
python model_analysis\proof_kernel\pctb_ledger.py
python model_analysis\birth_channel_research\P2-biased-hash_coupling_ledger.py
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
python model_analysis\birth_channel_research\bounded_bundle_codec.py
python model_analysis\birth_channel_research\scheduled_tree_codec.py
python -c "from model_analysis.birth_channel_research.arbitrary_freshness_kernels import hole_run_bundle_demo; hole_run_bundle_demo()"
python -c "from model_analysis.birth_channel_research.arbitrary_freshness_kernels import adaptive_recursive_cover_churn_demo; adaptive_recursive_cover_churn_demo()"
python -m py_compile model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
```

Two heavier default demonstrations were started and then stopped because they
exceeded the intended "small kernel" runtime:

```text
python model_analysis\birth_channel_research\B-ambiguity-bound_survivor_count.py
python model_analysis\birth_channel_research\P2-bundle_survivor.py
```

They were stopped by exact command-line process targeting, not by broad process
cleanup.
