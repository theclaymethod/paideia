# Chunk anatomy: the 4 beats, media selection, and sizing

A **chunk** is one bite-size unit of the course: ~25-45 minutes, one concept, ending (usually) in
a gated exercise. Every chunk follows the same four-beat shape so the learner always knows where
they are.

## The 4 beats

1. **HOOK**: ELI5. A concrete analogy or visual, *zero math*, ~3 minutes. The job is to make the
   concept feel obvious before any notation appears. (e.g. "CRPS is darts on a dartboard: you're
   scored on the whole spread of where your darts land, not just the bullseye.")
2. **RAMP**: the real mechanism, notation introduced *on top of* the analogy, ~10 minutes. Where
   manipulation teaches, an interactive widget lives here (drag a parameter, watch the metric
   respond). Introduce only the math the exercise needs.
3. **DO**: the gated exercise, ~15-25 minutes. The learner fills holes in `exercises/<id>/impl.py`.
   This is the beat that produces the artifact; the other three exist to make this one succeed.
4. **LOCK_IN**: 2-3 Socratic questions the runtime agent asks, tying the concept back to the
   larger design/goal. Not recitation: the agent probes the answers.

Briefings (conceptual chunks with no exercise) run only HOOK + RAMP and end with the LOCK_IN
questions; they have no DO beat.

## Media selection (choose per chunk, by what the content needs)

| Medium | Use when | File |
|--------|----------|------|
| **marimo** (`.py` notebook) | manipulating live code teaches the concept: sliders driving a recomputed chart, a widget that morphs as a parameter changes, or the learner's own impl visualized against a reference as they fix it | `lessons/<id>.py` |
| **static HTML** | conceptual/architectural content, briefings, "read the production version" reveals: a diagram or table, no code to run | `lessons/<id>.html` |
| **terminal** (`.md` walkthrough) | the lesson *is* running something in the shell: a training job, a data pipeline, an operate-and-inspect step | `lessons/<id>.md` |

marimo is the workhorse for interactive chunks. The notebook is a plain `.py` file: git-diffable,
agent-authorable, reviewable. It can `import` the learner's exercise module with autoreload, so
the "your impl vs reference" visual goes green live as they fill the holes. Reserve custom
interactivity for the few concepts where prose genuinely can't substitute. Most chunks are a
couple of `mo.ui` sliders over a computed chart plus static diagrams.

Static HTML must be self-contained: inline CSS, no external assets, no JS required. A briefing is
one central visual + the explanation + the LOCK_IN questions.

## Sizing & budgeting

- **Per chunk**: 25-45 minutes. If a concept won't fit, split it; if two are trivial, merge.
- **Per module**: budget chunk counts up front so the total lands near your target. Deep
  critical-path modules earn more chunks; briefing-only modules get 1-2.
- **The whole course**: the full `curriculum.yaml` (every chunk mapped) exists before any lesson
  is authored. That's what forces the budget and the dependency graph to be coherent.
- **Long-running DO beats** (a training run, a slow computation): structure as
  *fire-and-check-back*: the learner kicks off the job, does the next chunk's HOOK/RAMP while it
  runs, and returns for the result. Say so in the lesson.

## What makes a good exercise (the DO beat)

- **A substantive problem, not a syntax drill.** This is the difference between a course that
  teaches and a leetcode set. The worst exercise is "implement `tpr(counts) = TP/(TP+FN)`": the
  docstring hands over the formula and the learner transcribes it. The best exercise poses a real
  problem the subject is actually about, a **decision, diagnosis, design, or red-team**, where a
  formula is a *tool the learner reaches for*, never the deliverable. "Three judges and a gold set;
  one is 92% accurate and useless; decide which is safe to ship and defend it" teaches judgment;
  "compute TP/(TP+FN)" teaches typing. Hand the formula tools already implemented (as given
  material); make the hole the judgment. The gate then judges the *outcome* (does the learner's
  decision hold up on fresh adversaries the gate generates at test time), so transcription and
  hardcoding both fail. Recurring problem shapes: *decide* (which of these is safe / which rung
  buys the most), *diagnose* (this looks fine but is broken, find how), *design* (build a check
  that resists this attack), *red-team* (build the thing that games the weak signal, then harden
  it against yourself).
- **Holes, not blanks.** The starter `impl.py` has full docstrings and signatures with
  `raise NotImplementedError("TODO: …")` where the learning is. The contract is clear; the
  algorithm is what they supply.
- **Contract-only docstrings.** State *what* the function must decide and its signature, not the
  decision logic. A docstring that spells out the algorithm turns the exercise into transcription.
- **The gate proves the concept, not output-matching.** See `gate-discipline.md`. The exercise is
  only as honest as its gate.
- **Given-material is separate.** Fixtures, corpora, and shared helpers live in `resources/` or as
  byte-identical helper files in the exercise/solution dirs, never mixed into the holes the
  learner fills.
