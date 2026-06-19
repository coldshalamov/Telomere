# H209 - Developmental Macro Codec

## Conjecture

```text
The best visible-population generated branch should be made into an explicit
stateless codec: generated roots unfold by public developmental law, while
arbitrary non-reachable strings use a raw escape.
```

This tests whether the biology-inspired branch is a real parseable recursive
mechanism, not only a ledger.

## Kernel

`H209-developmental_macro_codec.py`

Finite exact mode:

```text
generated code = visible root population
raw code       = literal N-bit layer
decode         = public child law for P passes, then leaf expansion
```

The tiny default enumerates all `2^8` outputs and verifies round trips.

Symbolic mode reports the large H205/H208 rows without enumerating support.

## Result

Exact default:

```text
M=1,G=3,C=3,B=2,A=2,P=2,N=8
support=8/256
roundtrip=True
nativeGen=11
packedGen=4
rawPrefix=9
generatedGain(native)=-3
generatedGain(packed)=+4
uniformMean(native)=9.062500
uniformMean(packed)=8.843750
membershipTax=5
netAfterMembership(native)=-8
netAfterMembership(packed)=-1
```

Large symbolic rows:

```text
native_v1_roots M=32,G=16,A=5,P=6,N=16000000:
  genBits=833
  generated_gain=15999167
  uniform_after_membership=-321
  q=2.341e-97
  rawOH=3.377e-97
  alpha*=2.111e-104
  minStep=1888

packed_roots M=32,G=16,A=5,P=6,N=16000000:
  genBits=513
  generated_gain=15999487
  uniform_after_membership=-1
  rawOH=1
```

## Bill

Generated/reachable source:

```text
gain = N - generatedBits
```

Arbitrary uniform source:

```text
membership_tax >= N - log2(support)
net <= log2(support) - generatedBits
```

The packed generated branch can shrink recursively inside the generated class,
but raw escape or mode/Kraft cost keeps arbitrary-uniform use non-positive.

## Mutation

H209 is the cleanest constructive stateless recursive codec so far, but its
positive result is bounded/generated.  The next arbitrary-content attack must
either make source membership native without hidden entropy or find a real
overfull/referee surplus after ambiguity bits.
