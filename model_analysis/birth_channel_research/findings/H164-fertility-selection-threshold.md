# H164 - Fertility-Selected Superposition Threshold

Date: 2026-06-18

## Question

Can non-greedy witness choice still be the missing piece if H162/H163 already
give the cover DP the best local records and still expand?

Runnable artifact:

```text
model_analysis/birth_channel_research/H164-fertility_selection_threshold.py
```

## Model

If several witnesses match the same current interval, the encoder can choose the
one whose visible record string is more fertile for the next pass. The decoder
does not need a selector because it sees only the chosen `[arity][seed]`.

But the value is capped. The primary unit is bits per selected record. Under the
uniform law, choosing among `M` same-interval alternatives can buy at most
`log2(M)` bits/selected-record unless a public fertility feature genuinely
predicts future compression against same-budget random controls.

```text
missing bits/record = missing bits/item / selected records/item
equivalent best-of-M choices = 2^(missing bits/record)
```

## Results

```text
row                             strict  support  miss/item  rec/item  miss/rec   M_eq
H162 K5 D80 N32 exact           true    0.310    4.110081   0.491532  8.361777   328.962
H162 K5 D80 N32 mixed           false   0.384    3.472168   0.426758  8.136152   281.336
H163 K5 D256 N32 exact          true    0.603    3.524344   0.363778  9.688172   824.955
H163 K5 D512 N32 exact          true    0.817    3.476722   0.327168  10.626718  1581
H163 K16 D256 N32 escape5       true    0.663    3.546954   0.359454  9.867616   934.218
H163 K16 D512 N32 escape5       true    0.833    3.266563   0.293125  11.143925  2263
```

The smallest strict miss per item is `H163 K16 D512 escape5`, but because it
uses fewer selected records per item it needs more than `11` bits of future
value per selected record. The smallest strict miss per selected record is the
original H162 K5/D80 row: `8.361777` bits/record. In the idealized best-of-M
conversion, that is `M ~= 329` same-interval choices.

## Reading

This keeps fertility-selected superposition alive, but it makes the target much
sharper. The next recurrent-transfer kernel must show one of these:

```text
same-interval witness alternatives provide >8.36 bits/record future paid value
or a different item witness mode reduces the H162/H163 base miss first
```

Merely saying "there are many non-greedy alternatives" is not enough. The
alternatives must be visible as actual chosen witnesses, or their value is capped
by lost match supply / option entropy.

## Verdict

The best live non-greedy compression-value knob is still fertility-selected
superposition, but it is now a high bar rather than a vague hope. For current
V1/J3D1 item streams, it must deliver `8` to `11+` bits of future value per
selected record. Equivalently, a pure best-of-M mechanism would need hundreds to
thousands of same-interval choices, but that is only a conversion of the bit
gap, not a compression-rate multiplier.

The clean stateless scaffold to combine with it remains public lanes/class-local
seed enumeration; that solves salt/readiness geometry, not the value source.
