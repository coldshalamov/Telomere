# H201 - Multi-Root Generated Superposition

## Conjecture

```text
If a plain residual is too expensive, make the residual itself generated:
encode a target as the XOR/sum of several H198 generated phenotypes, or as a
subset of a public generated codebook.
```

This tests sparse multi-root superposition and full linear-span / bitmask
variants of the H198 generated tree.

## Kernel

`H201-multiroot_superposition.py`

Exact rows enumerate H198 generated codewords for tiny byte-aligned parameters
and form unordered XOR combinations:

```text
target = phenotype(root_1) XOR ... XOR phenotype(root_k)
```

The kernel reports:

```text
xor_support       = distinct XOR outputs from k-combinations
selection_log2    = log2 C(unique_codewords,k)
native_bits       = k * paid_H198_root_record
paid_index_net    = log2(xor_support) - selection_log2
native_net        = log2(xor_support) - native_bits
```

It also computes the GF(2) rank of the generated codebook. A full linear-span
diagnostic stores a bitmask over public codewords:

```text
span_support = 2^rank
bitmask_net = rank - codebook_size
```

## Result

Exact one-pass row:

```text
G=4,C=8,B=8,A=2,P=1,N=16,unique=16,rank=15

k=1:
  xor_support=16
  xor_log2=4.000000
  selection_log2=4.000000
  paid_index_net=0
  native_net=-13.000000

k=4:
  xor_support=1820
  xor_log2=10.829723
  selection_log2=10.829723
  paid_index_net=0
  native_net=-57.170277

k=8:
  xor_support=10350
  xor_log2=13.337343
  selection_log2=13.651724
  paid_index_net=-0.314381
  native_net=-122.662657

full span:
  rank=15
  span_support=2^15
  bitmask_net=-1.000000
  native_allroot_net=-257.000000
```

Exact two-pass row:

```text
G=4,C=8,B=8,A=2,P=2,N=32,unique=15,rank=15,fixed_pass_count

k=1:
  paid_index_net=0
  native_net=-8.093109

k=8:
  paid_index_net=0
  native_net=-83.348276

full span:
  span_support=2^15
  bitmask_net=0
```

The two-pass bitmask tie is not all-data compression: the span covers only
`2^15` of `2^32` targets, leaving a 17-bit source membership gap.

Large H198 bound:

```text
N=500000,m=16,native_root_bits=27

k=1:   native_tuple_net=-11
k=8:   native_tuple_net=-88
k=128: native_tuple_net=-1408

full span rank bound = 65536
span support gap = 434464 bits
bitmask_net <= 0
```

## Bill

Sparse superposition:

```text
support <= number_of_selected_root_descriptions
paid_index_net <= 0
native_net <= -k * root_record_overhead
```

Full linear span:

```text
span_support <= 2^rank
bitmask_bits = codebook_size
bitmask_net = rank - codebook_size <= 0
```

If `rank < N`, the missing `N-rank` bits are a source/reachable membership tax.
If `rank >= N`, then the codebook has at least `N` independent public vectors
and the bitmask costs at least `N` bits before Telomere overhead.

## Mutation

Multi-root superposition is a clean generated residual law, but not a
roughly-all-data breakthrough. It either pays selected-root entropy, pays one
bit per public codeword, or leaves a support gap. Future generated-residual
ideas must create support faster than their selector rank, which would require
a non-injective or ambiguous decoder and therefore reopens the H197 referee
bill.

