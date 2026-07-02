# curriculum.yaml: the chunk-graph schema

`curriculum.yaml` is the single source of truth for the course: every chunk, its medium, its
gate, and the dependency graph. Author the **whole graph up front** (all chunks `status: planned`)
before writing any lesson. That forces the budget and dependencies to be coherent.
`validate_curriculum.py` enforces this schema.

## Schema

```yaml
chunks:
  - id: "1.1"                    # "<module_num>.<seq>" — unique, ordered within a module
    module: M1                   # M1..Mn — groups chunks; used for --module gate sweeps
    title: "Error analysis before you trust any judge"
    medium: marimo               # marimo | html | terminal
    beats: [HOOK, RAMP, DO, LOCK_IN]   # briefings use [HOOK, RAMP]
    gate: "python3 <coursedir>/scripts/check_gates.py --chunk 1.1"   # or "... --chunk 3.1 --operate"; null for briefings/reveals
    depends_on: []               # chunk ids that must be `done` first
    unlocks: ["1.2"]             # inverse edges (validator cross-checks against depends_on)
    est_minutes: 35              # 25-45 band
    status: planned              # planned | built | reviewed | shipped
    codex_review: null           # null | "notes/codex/M1-review.md" (required non-null when shipped)
```

Keep it flat: no free-form prose beyond `title`. Learner run-state (gate runs, skip debt,
per-chunk status) lives in `progress.json`, **not** here.

## Field notes

- **id / module**: `id` is `"<module_num>.<seq>"`; `module` is the `M<n>` the chunk belongs to.
  The gate runner selects by `--chunk <id>` or `--module M<n>`.
- **medium**: picks the lesson file extension and how the runtime skill opens it (`marimo edit`,
  `open`, or a terminal walkthrough). See `chunk-anatomy.md` §media.
- **gate**: the exact command the learner runs. `null` only for `html` briefings and reveal
  chunks. Append `--operate` for run-and-inspect chunks (single-pass, not two-sided).
- **depends_on / unlocks**: the DAG. The validator checks that both reference real ids, are
  mutually consistent, and form an acyclic graph. `1.1` (or your entry chunk) has `depends_on: []`.
- **status**: `planned` → `built` (files exist) → `reviewed` → `shipped`. Once `status >= built`,
  the validator requires `exercises/<id>/` and `solutions/<id>/` to exist; once `shipped`, a
  resolving `codex_review`.
- **codex_review**: path to the archived adversarial review that cleared this chunk. A non-null
  value is the ship gate. It's how the final audit proves every chunk was reviewed.

## What the validator enforces (`validate_curriculum.py`)

- Required fields present; `medium`, `status`, `module` in their allowed sets.
- `depends_on` / `unlocks` reference real chunk ids, are cross-consistent, and acyclic.
- `gate: null` allowed **only** for `html` briefings and the reveal chunk(s).
- For `status >= built`: `exercises/<id>/` and `solutions/<id>/` paths exist.
- For `status == shipped`: `codex_review` is non-null and the file exists.

Run it after every edit to the graph and after each batch. A green validator is a precondition
for every gate sweep.
