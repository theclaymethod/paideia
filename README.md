# paideia

**Forge interactive, gated tutors from course materials, a meta-skill for coding agents.**

`paideia` (Greek: the formation of a learner) turns a syllabus or a pile of docs into a hands-on
course a coding agent can drive. Bite-size chunks. Hard pytest gates that fail on the learner's
starter and pass only on a real implementation. Visual lessons: marimo notebooks, static HTML, or
terminal walkthroughs. An adversarial review of every chunk. It exists to kill the failure mode of
every well-meaning curriculum: **a reading path that feels like progress but ships no skill.**

This repo is itself a Claude Code skill. The root `SKILL.md` is the entry point, `references/`
holds the method, and `templates/` + `scripts/` hold the proven, generalized machinery.

## Install

Symlink the repo as a skill (or add it as a plugin):

```bash
ln -s ~/dev/paideia ~/.claude/skills/paideia
```

Then invoke it in any repo with `/paideia`, or just ask to "turn these materials into a tutor".

## What you get

- **A scaffolder**: `scripts/scaffold_tutor.py` stamps a fresh tutor repo with a working
  two-sided gate runner, curriculum validator, the `conftest` gate mechanism, an example
  curriculum, and a per-course runtime skill the *learner* invokes. All of it generalized from a
  tutor that shipped 44 chunks, then verified to work in a stamped repo.
- **The method.** `references/` encodes the whole playbook: how to grill the scope, split the
  work across model tiers (cheap reader → strong author → independent adversarial reviewer →
  skeptical judge), deliver in waves, and gate every chunk two ways.
- **Templates**: per-medium lesson skeletons (marimo/html/terminal) and exercise/gate/solution
  skeletons with the anti-gaming patterns baked in as comments.

## Quickstart

```bash
# 1. Stamp a new tutor
python3 ~/dev/paideia/scripts/scaffold_tutor.py \
    --dest ~/dev/my-course --course-name mycourse --course-dir tutor
cd ~/dev/my-course && git init

# 2. Validate the example graph
python3 tutor/scripts/validate_curriculum.py

# 3. From here, drive the build with /paideia:
#    grill scope → author curriculum.yaml → build modules in batches
#    (brief → author → adversarial review → fix) → gate each chunk two-sided → audit.
```

The learner later runs the course with the generated `/mycourse` skill. It opens each lesson,
runs the four beats (HOOK → RAMP → DO → LOCK_IN), and gates completion. The gate fails on their
starter until they've genuinely implemented the concept. A hint ladder helps; it never hands over
the answer.

## Layout

```
paideia/
  SKILL.md                 # /paideia — the meta-skill entry (workflow + invariants)
  references/
    methodology.md         # grill, agent-role split, wave delivery, batch loop, judge/audit
    chunk-anatomy.md       # the 4 beats, media selection, chunk sizing
    gate-discipline.md     # two-sided gates, hint ladder, novel-probe & provenance anti-gaming
    curriculum-schema.md   # the curriculum.yaml chunk schema + validator rules
  templates/
    scaffold/              # the fresh-tutor skeleton (gate runner, validator, runtime skill, example)
    lesson/                # marimo / html / terminal lesson templates
    exercise/              # starter-with-holes / two-sided gate / reference-solution templates
  scripts/
    scaffold_tutor.py      # stamp a new tutor repo from templates/scaffold/
  examples/                # a full reference tutor built with this method
```

## The invariants it enforces

- **Two-sided gates**: every exercise gate fails on the starter AND passes on the reference,
  proven by the runner, or it doesn't ship.
- **No answer reveals**: `solutions/` is agent-only until the gate passes; a 3-rung hint ladder,
  never the answer.
- **Offline & deterministic**: gates are stdlib/numpy, seeded, no network; live/cloud steps live
  outside gates.
- **Adversarially reviewed**: every chunk clears an independent skeptical pass before it ships.
