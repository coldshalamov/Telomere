# H55/H56 - self-synchronizing slack syntax

Date: 2026-06-17

## Question

Can the decoder infer a global slack/profile from the record syntax itself,
without an explicit selector or checksum referee?

This directly tests the tempting headerless rule:

```text
try every slack/profile
only one parses as a full-cover stream
therefore the selector is derived
```

## H55 exact language audit

Runnable artifact:

```text
model_analysis/birth_channel_research/H55-unique_slack_survivor_audit.py
```

H55 enumerates tiny exact bitstream languages. For each slack `s`, records use:

```text
[arity syntax][payload of width min(D, aB-s)]
```

The stream is valid if it parses to a full cover of `N` atoms. H55 then counts
how many slacks accept the same emitted stream.

Default/smoke findings:

```text
B=2,K=3,D=6,N=4,S={0,1,2}
  prefix:    ambiguous=0
  fixed:     ambiguous=8
  gamma:     ambiguous=8
  fibonacci: ambiguous=0

B=2,K=4,D=8,N=5,S={0,1,2}
  prefix:    ambiguous=0
  fixed:     ambiguous=192
  gamma:     ambiguous=48
  fibonacci: ambiguous=0

B=3,K=4,D=12,N=4,S={0,1,2}
  prefix:    ambiguous=0
  fixed:     ambiguous=520
  gamma:     ambiguous=192
  fibonacci: ambiguous=0
```

So the user-suggested Fibonacci/Zeckendorf lane is not nonsense. In these tiny
grammars, Fibonacci-style syntax makes the slack language self-identifying.
Fixed-width arity does not; Elias gamma reduces but does not remove overlap.

## Why this is not automatically free compression

Disjoint syntax can make the selector derivable, but the delimiter bits are
part of the record. The cost must be charged as syntax length or lost code
space. H55 only proves a possible decoder observation:

```text
decoder observation = unique slack parse
```

It does not prove a negative repeated-pass reproduction number.

## H56 repeated-pass scout

Runnable artifact:

```text
model_analysis/birth_channel_research/H56-self_sync_slack_ladder_rg.py
```

H56 charges the actual arity syntax bits and tests the repeated-pass target:

```text
record cost = arity_syntax_bits(a) + min(D, aB-s)
need mean log2 rho < 0
```

Run:

```text
python model_analysis\birth_channel_research\H56-self_sync_slack_ladder_rg.py \
  --config 4,128,512,128 --config 4,192,768,192 \
  --passes 2 --trials 3 --codes gamma fibonacci \
  --modes headerless_best paid_best
```

Results:

```text
B=4,K=128,D=512
  gamma headerless:     +0.033486 mean log2 rho
  fibonacci headerless: +0.029812 mean log2 rho

B=4,K=192,D=768
  gamma headerless:     +0.026707 mean log2 rho
  fibonacci headerless: +0.023081 mean log2 rho
```

Paid selector rows are slightly worse. The selector itself is not the main
problem in H56; the arity delimiter cost is.

## Accounting

Derived:

- global slack/profile, in tiny Fibonacci/prefix exact languages;
- record boundaries under the chosen self-synchronizing syntax.

Paid:

- arity syntax bits per record;
- payload width under the chosen slack;
- selector bits if the syntax is not proven disjoint at the target scale.

Hidden if omitted:

- overlap ambiguity for non-disjoint grammars (`fixed`, `gamma` in H55);
- syntax/Kraft cost for grammars that do create disjoint languages;
- high-K delimiter overhead when Fibonacci/gamma arity codes replace a learned
  public arity model.

## Verdict

Self-synchronizing arity syntax is a real stateless decoder trick. It can make
the global slack/profile derivable in exact toy grammars, and the Fibonacci
variant is worth remembering as a building block.

It does not solve the current repeated-pass compression gap. Once delimiter
bits are charged, H56 expands much more than H52/H53:

```text
H52 fixed slack best:          about +0.0037 mean log2 rho
H53 paid global slack ladder:       +0.004480
H56 fibonacci headerless K192:      +0.023081
```

The next use of this idea should be narrow: use self-synchronizing syntax only
as a decoder-proof tool around some other near-crossing witness, not as the
main arity code for high-K Total-Cover.
