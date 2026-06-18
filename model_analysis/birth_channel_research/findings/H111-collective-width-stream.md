# H111 - Collective Payload-Width Stream

Date: 2026-06-18

## Question

H110 found that partial refresh crosses with a local payload-width oracle but
misses when every record pays J3D1 to delimit its seed. Can the missing payload
widths be transmitted collectively?

Runnable artifact:

```text
model_analysis/birth_channel_research/H111-collective_width_stream.py
```

## Parseable Layout Tested

The tested layout is:

```text
arity stream first
width/delta stream second
payload stream third
```

The decoder can read the fixed arity stream until the arities sum to the layer
length. It then knows the target size of each record, reads the paid
width/delta stream, and uses those widths to split the payload stream.

All rows include the optimistic H2 ready/carry lower bound for the rewritten
fraction. Full cover-shape placement is still not charged, so positive rows
would be targets rather than finished codecs.

## Modes

```text
local:
  arity + payload bits only; no width stream; hidden channel

fixed_delta:
  each record pays fixed bits for delta in the legal slack range

fixed_width:
  each record pays fixed bits for payload width in 1..D

j3d1:
  current self-delimiting payload-width cost

enum counts-free:
  group deltas by arity and pay sequence order only; per-file counts are free

enum count-paid:
  group deltas by arity and pay both count composition and sequence order
```

## Result

Best rows:

```text
mode              config          slack  qmin  delta bits/atom
local oracle      B4_K16_D64      4      .10   -0.118750
fixed delta       B4_K128_D512    8      .10   +0.127344
enum counts-free  B4_K16_D64      4      .10   -0.073289
enum count-paid   B4_K128_D512    8      .10   +0.147041
J3D1              B4_K128_D512    8      .10   +0.168652
```

Representative rows:

```text
config          s  qmin     q    local     fixD    enum0    enum+     J3D1
B4_K16_D64      4  0.10 1.000  -0.1187   0.4531  -0.0733   0.5755   0.5543
B4_K32_D128     8  0.10 1.000  -0.0484   0.3328  -0.0406   0.4271   0.4163
B4_K128_D512    8  0.10 1.000   0.0219   0.1273   0.0219   0.1470   0.1687
B8_K32_D256     8  0.10 0.998  -0.0672   0.3757  -0.0491   0.5366   0.4522
B8_K64_D512     8  0.10 1.000  -0.0177   0.2354  -0.0115   0.4184   0.2771
```

## Reading

H111 narrows the H110 target:

```text
local width oracle crosses
counts-free enumerative width stream still crosses
count-paid enumerative width stream does not cross
fixed delta and J3D1 do not cross
```

So collective width coding improves the parseable bill, but the per-file width
histogram/count vector is not free. The hidden channel has become more exact:

```text
not "payload bits"
not "arity"
not "ready/carry H2"
but the selected width/delta law for this file/layer
```

## Verdict

No paid partial-refresh configuration crosses in this tested frontier.

The live next target is a frozen public width/delta model:

```text
train or derive P(delta | public context)
freeze it before evaluation
decode widths from that public law
show held-out paid delta < 0 after H2 ready/carry
```

If that public law crosses, H111's count-paid miss would be an artifact of
universal per-file counts. If it does not, the partial-refresh width-boundary
escape is closed at this level.
