# H109 - Non-Prefix Referee Capacity

Date: 2026-06-18

## Question

Can a non-prefix record language, trial decode, or checksum/referee rule be the
missing stateless syntax that avoids paying local record boundaries, opening
state, or birth path?

Runnable artifact:

```text
model_analysis/birth_channel_research/H109-nonprefix_referee_capacity.py
```

## Model

For an ambiguous length language with codeword lengths `L`, the number of
candidate parses of an `m`-bit stream is:

```text
A_0 = 1
A_m = sum_{l in L, l<=m} A_{m-l}
```

The missing delimiter/selector information is:

```text
log2 max_{j<=m} A_j
```

The prefix maximum matters because exact-length ambiguity is not monotone:
some stream lengths can be uniquely parseable while nearby lengths have many
readings. A fixed `C`-bit checksum can referee only while this liability stays
below `C` after any safety margin.

For arbitrary file length, ambiguity grows exponentially at rate
`log2(lambda)`, where:

```text
sum_l lambda^-l = 1
```

## Result

```text
language       lengths                   rate bits/bit     m@64    m@64-32safe
fixed8         (8,)                           0.000000  unbounded      unbounded
fib_1_2        (1, 2)                         0.694242         92             46
byte_or_marker (8, 9)                         0.117788        569            296
record_7_16    (7, 16)                        0.092059        730            382
lotus_toy      (7..16)                        0.312208        215            113
```

Exact examples:

```text
language            m     log2 A_m   false@C64 log2
fib_1_2            64    43.964760       -20.035240
fib_1_2           256   177.259208       113.259208

byte_or_marker    256    27.193007       -36.806993
byte_or_marker   1024   117.531359        53.531359

record_7_16       256    20.962637       -43.037363
record_7_16      1024    90.946727        26.946727

lotus_toy         256    76.626449        12.626449
lotus_toy        1024   316.402361       252.402361
```

The carried-record connection is the same ledger:

```text
A = T^R
log2 A = R * log2(T)

T=64,  R=10   -> 60 bits, 64-bit referee can cover it
T=64,  R=100  -> 600 bits, 64-bit referee cannot cover it
T=256, R=8    -> 64 bits, exactly at the 64-bit line
T=256, R=100  -> 800 bits, 64-bit referee cannot cover it
```

## Verdict

Non-prefix syntax and keep-what-decodes are legitimate finite engineering
tools. They can replace local prefix decisions with a global referee when the
surviving reading count is bounded.

They do not provide an unbounded arbitrary-pass birth/open channel by
themselves. The omitted parser/opening/path information reappears as either:

```text
checksum/referee bits
exponential decode work
a public invariant bounding survivor readings
or a hidden selector/path channel
```

So H109 keeps trial-decode/checksum pruning alive only as a bounded-window or
near-total-exception tool. It does not close the H105 `0.468557` bits/record
forced-rewrite witness gap, and it does not rescue arbitrary sparse carried
records unless a separate invariant keeps `max A_j` bounded independently of
file size and pass count.
