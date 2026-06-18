# H130 - Near-Total Witness Margin

## Question

If a public-coordinate board is near-total rather than all-open, does the
exception ledger make the witness target easier or harder?

Model:

```text
net = (1-eps) * records_per_atom * (base_margin + boost)
      - exception_ledger(eps, P)
      - eps * fallback_overhead
```

The kernel solves the extra paid witness `boost` per selected record required to
break even.

## Result

Near-total exceptions always increase the required witness boost over the
all-open case.

Examples:

```text
H7 raw first-hit delta:
  eps=0,     boost = 1.357000 bits/record
  eps=0.001, P=4096, F=0:
             boost = 4.022927 bits/record

H12 perfect-credit upper bound:
  eps=0,     boost = 0.746000 bits/record
  eps=0.001, P=4096, F=0:
             boost = 2.878596 bits/record

H105 custom_record:
  eps=0,     boost = 0.468557 bits/record
  eps=0.001, P=4096, F=0:
             boost = 0.542498 bits/record
  eps=0.001, P=4096, F=3:
             boost = 0.551974 bits/record
```

## Interpretation

Public near-total boards remain useful only when exact all-open cover is not
available. They do not relax the witness problem. The cleanest target remains:

```text
all-open public board
+ positive paid forced-rewrite witness margin
```

Near-total exceptions are a fallback geometry, not a compression source.

## Artifact

`model_analysis/birth_channel_research/H130-near_total_witness_margin.py`
