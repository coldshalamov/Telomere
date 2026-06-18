# H72 - Public-Q / Visible-State Converse

Date: 2026-06-17

## Question

Can best-of public profiles, final-board states, cover-shape choices, or
checksum-refereed decodes multiply the number of winning short descriptions
without storing a selector?

H72 prices that family as exact short-output counts.

Runnable artifact:

```text
model_analysis/birth_channel_research/H72-public_q_visible_state_converse.py
```

## Core Count

For `n`-bit uniform inputs and final saving `S`, the short-output inventory is
finite. Splitting a compressed file into:

```text
[visible state][payload]
```

does not increase the number of short outputs. A multiplier from profiles,
checksums, board arrangements, or cover shapes helps only if its identity is
not counted in the file length.

## Exact Tiny Audit

For `n=16,S=4`:

```text
prefix base count = 4096/65536 = 0.062500
EOF base count    = 8191/65536 = 0.124985
```

With `16` best-of profiles:

```text
prefix, selector free: 65536/65536 = 1.000000
prefix, selector paid: 4096/65536  = 0.062500
EOF, selector free:    65536/65536 = 1.000000
EOF, selector paid:    8176/65536  = 0.124756
```

The EOF paid row has small finite-length edge effects, but the multiplier is
still effectively canceled once profile identity is inside the output.

With `4096` cover shapes:

```text
prefix, selector free: 65536/65536 = 1.000000
prefix, selector paid: 4096/65536  = 0.062500
EOF, selector paid:    4096/65536  = 0.062500
```

This is the hidden-selector trap in miniature.

## Checksum / Referee Budget

A finite checksum/referee can choose among finite profiles, but if its bits are
charged to the compressed file, the gain cancels:

```text
n=16,S=4,profiles=4096,C=8:
  base count          = 4096/65536 = 0.062500
  free referee count  = 65536/65536 = 1.000000
  charged count       = 4096/65536 = 0.062500
  profile bits owed   = 4.000
```

So a checksum can be a finite referee or integrity check, but it cannot be an
unbounded free profile selector.

## Public Q Reading

For a frozen public `Q`:

```text
E_U[-log2 Q(X)] = n + KL(U || Q) >= n
```

Current nearest rows:

```text
H58 frozen bucket Q:  excess +0.229195 bits
H59 raw/Q mixture T1: excess +0.053411 bits
```

They are close, but still positive under uniform held-out accounting. They can
become constructive only as source-shaped targets: the source must visit the
high-`Q` states more often than uniform does.

## Verdict

Final boards, cover shapes, checksums, and best-of public profiles are not
rejected by name. They are valid only when:

- their identity is visibly present in the compressed file and therefore
  counted;
- their valid-state count is priced as `log2(valid states)`;
- or they are public restrictions that pay in match supply.

If their identity multiplies the winning set while not appearing in the output
length, that is hidden metadata.
