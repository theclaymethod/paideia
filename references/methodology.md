# Methodology: how to build a tutor without shipping a reading path

This is the playbook the `/paideia` skill drives, distilled from building a full 12-module tutor
end-to-end. The through-line: **subordinate readings to deliverables, and prove every deliverable
with a gate.**

## The agent-role split (who does what)

Building a tutor is a lot of authoring plus a lot of skeptical checking. Split it:

| Role | Model tier | Job |
|------|-----------|-----|
| **Orchestrator** | strong/planning | Owns the aggregate plan, the curriculum graph, cross-module coherence (shared schemas, the gate chain), and the board. Does not hand-author every chunk. |
| **Reader** | cheap/fast | Digests source material for one module into a structured authoring brief. Cheap because it's bulk reading. |
| **Author** | strong | Writes each chunk from the brief: lesson, exercise-with-holes, two-sided gate, reference solution. One subagent per module (or per few chunks). |
| **Reviewer** | adversarial, *independent* | A skeptical external pass on every chunk. Ideally a different model/tool (e.g. the `codex` CLI) so it doesn't share the author's blind spots. Hunts: wrong math, gameable gates, spoiler leakage, weak pedagogy. |
| **Judge** | strong, skeptical | Read-only gate at module/phase boundaries and the final audit. Runs verification, not vibes. |

Independence is the whole point: an author and reviewer sharing a model share failure modes. In
practice the independent adversarial reviewer caught the highest-value defects. A gate that
"passed" but was satisfiable by predicting a constant instead of learning the concept. A lesson
that leaked the answer it was supposed to make the learner derive. An author grading its own work
would have waved both through.

## Grill (before authoring anything)

Interview the user until the decision tree has no open branches. Resolve, at minimum:
- **Capstone**: what working artifact does the learner end with? Everything ramps toward it.
- **Coverage**: which topics get the full interactive treatment vs. lighter "operate/inspect"
  chunks vs. no-exercise briefings. Depth on the critical path beats breadth.
- **Chunk shape**: target minutes/chunk (25-45 is a good band), rough chunk count, the fixed
  beat anatomy (see `chunk-anatomy.md`).
- **Media mix**: which chunks are interactive notebooks, which are static briefings, which are
  terminal walkthroughs (see `chunk-anatomy.md` §media).
- **Learner profile**: expertise level sets the ELI5 floor and the ramp slope.
- **Compute/tooling**: does any chunk need real training/GPU/cloud? Those live outside gates.
- **Delivery**: build everything first, or ship in waves and learn while building? Waves win.
  Real usage corrects the format before you've authored 40 more chunks the wrong way.

Write the answers to `TUTOR-PLAN.md` in the new repo. It becomes the binding spec, and every
later subagent reads it. When a subagent's build diverges from the plan for a good reason, it
appends a dated "contract change" note rather than silently drifting.

## Wave delivery

Ship **one module per wave**, staying one module ahead of the learner:
- **Wave 0**: scaffold + the full `curriculum.yaml` (every chunk mapped, `status: planned`) +
  the first module fully built and reviewed. The learner starts immediately.
- **Wave N**: build the next module while the learner works the current one.

The full map existing from Wave 0 matters. It forces the dependency graph and chunk budget to
be coherent before mass production. The first module doubles as a **format checkpoint**: a judge
verifies it matches the plan's anatomy and gate discipline before you replicate the format 40
times.

## The batch loop (per module)

```
brief (reader)  →  author (strong, 1 subagent per module)  →  two-sided gate check
   →  adversarial review (independent, every chunk)  →  triage  →  fix pass  →  ship
```

Practical notes learned the hard way:
- **Author disjoint files in parallel** when a module splits cleanly (e.g. chunks 1-3 / 4-6), but
  pass the first author's fixture contract to the second so shared given-material stays consistent.
- **Pipeline the review**: kick off the adversarial review of module N in the background while
  authoring module N+1 (disjoint files). Don't serialize.
- **One fix pass per module**, applying the triaged findings together, then flip to `shipped`.
- **Recurring defect classes** to expect (the reviewer will find these):
  - *"Beats the baseline" that's actually a mean/constant trick.* A model/forecaster "wins" by
    predicting the marginal, not by using the input. Fix: make the target genuinely depend on the
    input, and add an ablation assertion (full model > mean-only baseline > floor) plus an
    input-swap probe (permuting the input must change the output).
  - *Spoiler leakage.* The lesson displays the ground truth the exercise is meant to derive, or a
    reference's docstring narrates the answer. Move reveals to an agent-only `*_reveals/` file the
    lesson names for *after* the gate.
  - *Gameable gate.* The gate only checks committed fixtures, so a lookup table passes. Fix with
    novel probes (see `gate-discipline.md`).
  - *Doc overclaim.* Lessons state causal/statistical claims too absolutely, or a driver's docs
    claim it "submits/trains" when it stops at a stub. Soften to what the code does.

## Judge & audit gates

- **Module-boundary judge** (after the format-checkpoint module, and any high-risk module): a
  read-only skeptical pass that RUNS the gates and the runtime flow, not just reads. Approves mass
  production or orders fixes.
- **Final audit**: the completion gate. It must verify, with evidence:
  1. `validate_curriculum.py` passes; every chunk `shipped` with a `codex_review` that resolves.
  2. The full gate sweep is green (two-sided for exercises, operate for inspect-chunks, skip for
     briefings).
  3. The **oracle demo**: a fresh run of the runtime skill opens chunk 1, and its `--learner` gate
     FAILS on the untouched starter (proving the holes are real and unfilled).
  4. Solutions discipline holds: sampled exercises still have holes; no learner-facing file imports
     from `solutions/`; byte-identical helper pairs match.
  Declare done only when the oracle property holds for *every* shipped chunk, not because the work
  looks substantial.

## A note on "operate" chunks and briefings

Not every chunk is a two-sided coding exercise:
- **Operate/inspect** chunks (run existing code, read outputs, light property check) use the gate
  runner's `--operate` mode: a single passing run, no two-sided requirement.
- **Briefings** (conceptual, no exercise) are `medium: html`, `gate: null`. The runtime skill
  walks them and asks the LOCK_IN questions; nothing to gate.
Use these deliberately to keep the critical path deep without padding every topic into a full
exercise.
