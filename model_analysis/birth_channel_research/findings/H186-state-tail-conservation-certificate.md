# H186 - State-Tail Conservation Certificate

## Conjecture

```text
Decoder-derived digest-tail state, bits-back state, syndromes, or checksum
reuse might carry salt/fertility across passes without explicit metadata.
```

This kernel asks whether state itself changes the paid recurrent row mass.

## Kernel

`H186-state_tail_conservation_certificate.py`

Modes:

- `observe`: tail state is emitted by the chosen witness and observed for free;
- `condition_value`: a particular next state is required;
- `condition_subset`: a public subset of states is allowed;
- `selected_tail`: encoder chooses among state tails and pays selector bits;
- bits-back tape settlement with parameter `gamma`.

The base row mass is:

```text
base_mass = arity_kraft * 2^-saving
```

## Result

Representative V1 rows:

```text
s=0 observe:           rowMass=0.875000, log2rho=-0.192645
s=0 condition r=8:     rowMass=0.003418, log2rho=-8.192645
s=0 subset f=0.5:      rowMass=0.437500, log2rho=-1.192645
s=0 selected d=16:     rowMass=1.000000, log2rho=0, gain=-4
s=1 observe:           rowMass=0.437500, log2rho=-1.192645
s=-1 observe:          rowMass=1.750000, log2rho=0.807355, gain=-1
```

Observed state is free, but it does not lift mass. Conditioning state thins
supply. Selecting among tails can repair support only by paying selector bits.

Bits-back examples with one-state settlement:

```text
gap=0.1,r=4,P=16,gamma=1.0:  net=-5.6, conserved or negative
gap=0.1,r=4,P=16,gamma=1.1:  net=0.8, positive only with gamma>1 fertility
gap=1.0,r=8,P=64,gamma=1.1:  net=-20.8, settlement/gap still dominates
```

## Bill

```text
observe q_next: free coordinate, no controllable value
force q_next: costs r bits of hit supply
choose q_next: costs selector/referee entropy
bits-back tape: conserved at gamma=1; positive requires gamma>1
```

The `gamma>1` case is a separate fertility/source law and is priced by H182/H183.

## Mutation

Keep digest-tail state as decode geometry and salting scaffold only. It can help
organize a future real fertility mechanism, but it is not itself maintained
compression fuel.
