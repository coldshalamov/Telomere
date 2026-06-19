# H189 - Non-Prefix Uniquely-Decodable Kraft Check

## Conjecture

```text
A non-prefix or self-synchronizing record grammar might have more usable row
mass than a prefix grammar while still decoding statelessly.
```

## Kernel

`H189-nonprefix_ud_kraft.py`

The kernel exhaustively scans binary codebooks with word length `<=4` and code
sizes `2..5`, using Sardinas-Patterson to test unique decodability.

## Result

```text
L=4,size=2: UD=421, nonprefixUD=54, maxUD=1.000000, maxNonprefix=0.750000
L=4,size=3: UD=3448, nonprefixUD=986, maxUD=1.000000, maxNonprefix=1.000000
L=4,size=4: UD=17457, nonprefixUD=7022, maxUD=1.000000, maxNonprefix=1.000000
L=4,size=5: UD=56638, nonprefixUD=26564, maxUD=1.000000, maxNonprefix=1.000000
```

Examples:

```text
prefix critical: 0,10,110,111        Kraft=1, prefix=True, UD=True
nonprefix UD:    01,10,011           Kraft=0.625, prefix=False, UD=True
non-UD overfull: 0,1,00              Kraft=1.25, prefix=False, UD=False
```

## Bill

Non-prefix uniquely-decodable grammars can be useful parser designs, but they
do not exceed Kraft mass `1`. Overfull grammars need a referee, length channel,
or source restriction.

## Mutation

Close non-prefix/self-synchronizing grammar as a row-mass escape. Keep it only
as a parseability tool if a separate paid positive mechanism appears.
