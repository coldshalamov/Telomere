# H103 - Class-Local Kraft Check

Date: 2026-06-18

## Question

H102 claims a public lane can remove the visible seed-parity tax if the witness
is a local rank inside the lane's public seed class. Does that preserve honest
Kraft mass in an exact finite domain, or does it secretly add code space?

Runnable artifact:

```text
model_analysis/birth_channel_research/H103-class_local_kraft_check.py
```

## Families

```text
base_all:
  W-bit rank grammar over 2^W public seeds.

visible_global_class:
  same W-bit global grammar, but only one seed class is accepted.
  This is the H99/H101 supply-loss model.

local_class:
  lane supplies the class; W bits name 2^W local ranks inside that class.
```

## Result

Exact H74 domain, `B=1,N=12`:

```text
family                 K   D   collective log2Z   delta vs base
base_all               6   8        -1.781751       0.000000
visible_global_class   6   8        -5.464267      -3.682516
local_class            6   8        -1.781751       0.000000

base_all               8  10        -2.188694       0.000000
visible_global_class   8  10        -5.115053      -2.926359
local_class            8  10        -2.188694       0.000000

base_all              12  10        -2.314713       0.000000
visible_global_class  12  10        -4.061686      -1.746973
local_class           12  10        -2.314713       0.000000
```

## Verdict

The public-lane local-class grammar does not create hidden Kraft mass. It
preserves the base witness family exactly in this finite check. Visible global
seed parity loses mass because the seed witness is doing the readiness
signaling. Local class grammar avoids that loss only because the class is
already supplied by public position/lane geometry.

This strengthens H102's surviving spec:

```text
public lane supplies epoch/readiness
class-local seed rank supplies fresh salt
compression still requires a positive paid witness margin
```

The remaining gap is not birth/open entropy in this branch. It is the paid
forced-rewrite witness margin.
