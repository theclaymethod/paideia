# Gate discipline: the property that makes the course honest

A gate is a pytest in `exercises/<id>/test_gate.py` that decides whether a chunk is done. The
entire value of the tutor rests on gates being **two-sided** and **ungameable**. Get this file
right; the rest is downstream of it.

## Two-sided: the core mechanism

`test_gate.py` does a bare `import impl` and asserts properties. Which `impl` it imports is
chosen by the runner via the `TUTOR_IMPL_DIR` env var (the `conftest_gate.py` mechanism loads
`impl.py` from that dir and registers it in `sys.modules` so pytest's path ordering can't shadow
it). This gives two runs of the same test file:

1. `TUTOR_IMPL_DIR=exercises/<id>` → the learner's starter (holes) → **must FAIL**.
2. `TUTOR_IMPL_DIR=solutions/<id>` → the reference → **must PASS**.

`check_gates.py` (default mode) runs both. If run 1 *passes*, the gate is gameable (it doesn't
actually exercise the holes) and the runner reports a **DEFECT** with non-zero exit. If run 2
fails, the reference is broken. A chunk ships only when it's "two-sided OK".

The learner's runtime uses `--learner` mode: a single run against `exercises/` only. `solutions/`
is placed on the path **exclusively** inside the runner's two-sided build check, never in the
learner flow. This is what lets the reference exist in the repo without being reachable during
learning.

## No answer reveals (the hint ladder)

When the learner's gate fails, the runtime skill climbs a **3-rung hint ladder** and never hands
over the answer:
1. a conceptual nudge,
2. point at the specific failing property/test,
3. pseudocode.

`solutions/` is opened only *after* the gate passes, as a diff-against-reference learning step.
Any post-pass "here's the production version" material lives in an agent-only `*_reveals/` file
that the lesson names. Keep spoilers out of every learner-facing file (lessons, exercises,
resources).

## Ungameable: anti-gaming patterns

A gate that only checks committed fixtures can be passed by a lookup table or a hardcoded
constant. Defend with:

- **Novel probes.** Generate fresh fixtures *at test time* (seeded for determinism) with known
  analytic answers, inputs the learner has never seen and can't hardcode. The learner's function
  must be correct on new inputs, not just the committed ones.
- **Provenance for curves/trajectories.** If the exercise produces a sequence (a training curve, a
  rollout), don't just assert it looks monotone; assert each step was actually produced by the
  gated step function: `metric[t]` recomputed from `state[t]`, and `state[t+1] ==
  gated_step(state[t], …)`. This blocks a fabricated "looks-right" curve. It's the highest-value
  fix in practice: a learner could otherwise hand-build a plausible monotone curve without running
  the true update.
- **Ablation assertions for "beats the baseline".** If a chunk claims a model learns from its
  input, assert *full model > input-blind baseline > floor*, and add an input-swap probe (permuting
  the input must change the output). This catches the "wins by predicting the mean/constant" trick
  the single most recurrent defect an adversarial reviewer finds.
- **Meaningful properties, not output equality.** Assert invariants (monotonicity, symmetry,
  known limits, analytic anchors) rather than exact expected outputs a learner could reverse-engineer.

## Two leak classes (what adversarial review keeps catching)

Building a real course, an independent adversarial review of every chunk caught the same two leaks
over and over. The gates themselves were sound; the leaks were in what surrounded them. Budget a
review pass specifically for these, and do not trust the runner to find them: it only checks
starter-fails and reference-passes, so a chunk can be "two-sided OK" while still being beatable by
a *third* implementation that transcribes a rule or table-matches an answer.

- **Hint leak.** The starter's `# HINT`, the lesson, or the resources README states the decision
  rule, the exact threshold, the formula, or the decision ladder. Then the "problem" is
  transcription: the learner copies the rule. Discipline: a hint gives the concept, which given
  tool to reach for, and the required output shape/vocabulary, never the rule. A named threshold
  may live in code as an *opaque grading tolerance* the gate uses, but the hint must not say "flag
  when x > THRESHOLD". The learner infers the rule; the gate grades the outcome. This is the single
  most common finding: authors reliably over-explain in the starter, so review every learner-facing
  file for it.
- **Oracle leak.** The adversary generator returns the expected answer alongside the inputs (an
  `expected_label` field); or a lesson cell imports the gate's generator and prints `(got, want)`;
  or a lesson tells the learner to put `solutions/<id>` on the path. Each hands over the answer.
  Discipline: **generators return inputs only**; the gate computes ground truth itself, in a
  private test helper or by running the reference, never read from the returned data. Lessons
  never display the expected answer and never reference a `solutions/` path (the post-pass reveal
  is the runtime skill's job, on the learner's own gate pass). Decouple lesson demos from the gate's
  adversary module by using a small lesson-local toy.

## Hermeticity

Gates run offline, deterministic, stdlib/numpy only:
- The runner strips `PYTHONPATH` and sets `PYTHONHASHSEED=0`; gate tests seed their own RNGs.
- No network in anything the gate executes.
- **Shared helpers are byte-identical** across `exercises/<id>/` and `solutions/<id>/` (verify with
  `cmp`). This lets a chunk reuse a given world/generator without a cross-exercise import that
  would break hermeticity. Don't rely on the learner having completed earlier chunks. Capstone
  gates take their upstream inputs from committed/solution-side fixtures, so they run in a fresh
  checkout.

## Gate kinds

| `gate:` value | kind | runner behavior |
|---------------|------|-----------------|
| `…check_gates.py --chunk <id>` | two-sided | fail-on-starter + pass-on-reference (the default) |
| `…check_gates.py --chunk <id> --operate` | operate | single passing run (run-and-inspect chunks); no two-sided requirement |
| `null` | none | briefings/reveals; skipped by the runner, walked by the runtime skill |

The validator enforces that `gate: null` is used only for `html` briefings and reveal chunks, and
that a `shipped` chunk has a non-null `codex_review` receipt.
