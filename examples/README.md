# Examples

## Reference tutor: physician-in-the-loop medical AI

The method and machinery in this repo came out of a full tutor built end-to-end with the
`/paideia` process: **44 chunks across 12 modules**. Every chunk was adversarially reviewed by an
independent tool and gated two-sided, culminating in a capstone (a verifier-gated world-model
rollout). The final audit passed with the oracle property holding for every shipped chunk.

That repo is the worked example of everything in `references/`:

- `curriculum.yaml` with the full chunk graph, media mix (marimo / html / terminal), and the
  `depends_on` DAG across 12 modules.
- The batch-build history in git: one commit per module (author) + one per module (apply review
  fixes + ship), with the adversarial reviews archived under `notes/codex/`.
- The recurring-defect fixes the reviewer caught, visible in the "apply review fixes" commits: the
  "beats-the-baseline is really a mean trick" ablation fixes, spoiler-leakage moves to `*_reveals/`
  files, and curve-provenance gate hardening.
- A per-course runtime skill (`/tutor`) generalized here into `templates/scaffold/runtime-skill/`.

If you have access to that repo, read its `TUTOR-PLAN.md` (the grilled decision record) alongside
`references/methodology.md`. It shows the grill → plan → wave-delivery flow on a real, large
course. The `docs/goals/*/state.yaml` board shows the batch loop and the module-boundary judge /
final-audit gates in practice.

## A minimal stamped tutor

`scripts/scaffold_tutor.py --dest <path> --course-name demo --course-dir course` produces a fresh
tutor with an example 3-chunk curriculum (one marimo gated, one terminal gated, one html briefing)
that passes `validate_curriculum.py` out of the box. It's the smallest complete instance to read
before authoring your own.
