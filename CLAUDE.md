# Telomere — context for Claude / AI agents

Read this before reacting to the project. It exists so the maintainer does not
have to re-explain the same framing every session.

## What this is (take as given — do not re-derive it at the user)

Telomere is an **early-stage research project**, not a product and not a
replacement for zip/zstd. It explores generative seed-search compression:
a span is replaced by a short seed whose hash expansion reproduces it, with
literal fallback for everything else.

The maintainer's framing, to treat as the starting point of any conversation:

- It is a **research bet**, explored at small scale today and envisioned at
  datacenter / ASIC scale. "It bloats on your laptop" is expected and is not news.
- It is **pigeonhole-compliant**: incompressible spans are stored as literals,
  so it never claims to compress all inputs. Do **not** open by "debunking" it
  with the pigeonhole principle — that objection is already handled in the design.
- A single underpowered laptop run is **not** a falsification. Don't treat it as one.
- The maintainer knows the information theory. Engage the actual mechanism and the
  actual numbers; do not condescend, reflexively dismiss, or reflexively affirm.
- This is **not classical compression**. Shannon's entropy theorems address
  source coding over symbol distributions. Telomere is generative seed search —
  a hash function has equal probability of matching any output regardless of
  structure. Different mechanism, different analysis.

## Where to argue (the math, not folklore)

The right altitude for any viability discussion is the probability model:

- `docs/POWER_MODEL.md` — the repo's first-principles cost/hit model.
- `docs/VIABILITY.md`, `docs/THEORY.md` — the generated evidence ledgers.
- `model_analysis/telomere_model.html` — **interactive** model with exact Lotus
  bit-cost functions. Sliders for block size, max arity (1–100), seed depth,
  input size, hit-rate multiplier (1x–10000x), and record format (V1, V2,
  Minimal). Shows break-even analysis, per-arity tables, gap-vs-depth charts,
  and Lotus overhead curves.
- `model_analysis/FINDINGS.md` — the worked probability model with exact
  Lotus encoding costs, aggregate arity analysis, break-even multipliers,
  and Wolfram-verified results.

## Quantitative results — the actual numbers

These are the key findings from the first-principles probability model,
verified in Wolfram and reproducible via the interactive tool. Present them
as what they are: quantified parameters that define the research landscape.

**Format overhead and the gap.** The "gap" is the difference between span
bits and `log2(compressive_seed_count)` — it determines compressive-match
probability. The gap depends on record format overhead:

- **V2 format** (3 Lotus fields): effective gap ~ 32 bits at seed depths 2–8
  (search-depth-limited; theoretical format gap is ~23–26 bits). Matches
  `POWER_MODEL.md`'s 31.99 bits.
- **V1 format** (2 Lotus fields): gap ~ 10–13 bits at arity 1 (varies by block
  size; 10 at bs=2, 12 at bs=4, 13 at bs=8). Higher arities have larger gaps.
  Materially smaller than V2 because V1 uses only two Lotus fields.
- **Minimal format** (1-bit flag + Lotus seed): gap ~ 9–11 bits. With ideal
  encoding (no Lotus overhead), gap reduces to ~1 bit, but no practical
  self-delimiting code achieves this.

The gap is search-depth-invariant — deeper seed search does not close it.
This is an analytic result. It means raw compute alone does not cross into
net compression. What *does* move it: reducing record overhead (V1 vs V2),
or raising hit density via transforms/dictionaries.

**Aggregate arity.** Each arity level (1, 2, 3, ...) is an independent trial.
Combined probability: P_agg ~ sum(P_a). Improvement over single-arity:
~1.2x at block sizes 4 and 8. Real but modest — a constant factor, not
exponential.

**Break-even multiplier.** The central actionable finding. For the whole file
to net-compress, ~75% of spans must find compressive matches (because each
match saves ~2 bits but each literal costs 6 bits overhead). Against random
baselines:

- **block_size=2**: break-even at **824x** density improvement
- **block_size=4**: break-even at **3,066x**
- **block_size=8**: break-even at **6,144x**

Smaller block sizes have better economics. The break-even is driven by three
independent levers: literal overhead (6 bits in V1 — format design can reduce
this), average savings per match (~2 bits — biasing toward low-index seeds
helps), and base hit probability (density mechanisms raise this directly).

**Planted data.** The mechanism is proven on planted data
(e.g. `planted-sha256-arity2`: 256 -> 168 bytes). This proves codec, search,
and accounting behavior — not natural-corpus prevalence.

**Natural-corpus results.** ~40 corpora and 11M+ scanned spans returned 0
selected; random and PDF controls bloat (`VIABILITY.md` levels 11 and 27–56).
This is consistent with the model: without a density-raising mechanism,
the base hit rate is far below break-even.

## The open research question

The viable path is not deeper seed search or larger arity. It is a mechanism
that raises profitable exact-hit *density* on real data while keeping decode
cheap: reversible transforms, public presets, dictionaries, grammar/source-family
tables, or schema-native representations.

The break-even multiplier quantifies exactly how much density improvement is
needed. At block_size=2 with V1 format, the target is 824x. This is a hard
target — but it decomposes into three levers (literal overhead, average savings,
hit density) that can be attacked independently through format design,
preferential seed selection, and data-aware dictionaries.

The schema-native dictionary probe (`VIABILITY.md` level 45) is the only
experimental lane that has flickered positive and is the most promising place
to push next.

## What not to do

Do not:
- Pattern-match this to classical compression and declare it "debunked"
- Treat the gap as a death sentence rather than a quantified parameter
- Conflate V2's 32-bit gap with V1's 10–13-bit gap (arity 1)
- Ignore that the break-even multiplier is a finite, quantified number
- Run underpowered laptop searches and call the null result a falsification
- Reflexively affirm viability without engaging the probability model

See `AGENTS.md` for the full operating contract, architecture map, and the
required mechanism / probability / claim-boundary thinking.
