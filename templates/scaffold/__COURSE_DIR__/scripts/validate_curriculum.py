#!/usr/bin/env python3
"""Validate <course_dir>/curriculum.yaml against the paideia chunk-graph schema.

This script is course-dir-agnostic: it derives its course directory from its
own location (it lives at ``<course_dir>/scripts/validate_curriculum.py``), so
the course dir may be named anything. Nothing here hardcodes a course-dir name.

Rules enforced per chunk:
  * all required fields present, no unknown fields;
  * id format "<module_num>.<seq>" and consistent with `module`;
  * enums: medium in {marimo, html, terminal}; status in {planned, built,
    reviewed, shipped}; module in M1..M12;
  * beats: non-empty, no duplicates, subset of [HOOK, RAMP, DO, LOCK_IN];
  * est_minutes: integer in the 25-45 band;
  * depends_on / unlocks reference real ids, are cross-consistent
    (b in a.unlocks  <=>  a in b.depends_on), and the DAG is acyclic;
  * gate: null is allowed ONLY for medium: html chunks (briefings + reveal);
    every other chunk needs a non-empty command string that names its own
    chunk id;
  * status >= built: for two-sided-gated chunks, <course>/exercises/<id>/ and
    <course>/solutions/<id>/ must exist; operate-gated chunks need only
    <course>/exercises/<id>/; html chunks need <course>/lessons/<id>.html;
    marimo chunks need <course>/lessons/<id>.py;
  * status == shipped: codex_review non-null and the referenced file exists.

Exits 0 when valid, 1 with readable errors otherwise, 2 on usage/env problems.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Course dir is derived from this file's own location, not hardcoded:
#   <course_dir>/scripts/validate_curriculum.py  ->  parents[1] == <course_dir>
COURSE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
CURRICULUM = COURSE_DIR / "curriculum.yaml"

REQUIRED_FIELDS = {
    "id", "module", "title", "medium", "beats", "gate",
    "depends_on", "unlocks", "est_minutes", "status", "codex_review",
}
MEDIA = {"marimo", "html", "terminal"}
STATUSES = ["planned", "built", "reviewed", "shipped"]
MODULES = {f"M{i}" for i in range(1, 13)}
BEATS = ["HOOK", "RAMP", "DO", "LOCK_IN"]


def load_yaml(path: Path):
    try:
        import yaml  # pyyaml
    except ImportError:
        print(
            "ERROR: pyyaml is not importable. Install it first, e.g.\n"
            "  uv pip install pyyaml   (or: python3 -m pip install pyyaml)",
            file=sys.stderr,
        )
        sys.exit(2)
    with path.open() as fh:
        return yaml.safe_load(fh)


def main() -> int:
    if not CURRICULUM.is_file():
        print(f"ERROR: {CURRICULUM} not found", file=sys.stderr)
        return 2

    doc = load_yaml(CURRICULUM)
    errors: list[str] = []

    if not isinstance(doc, dict) or "chunks" not in doc:
        print("ERROR: curriculum.yaml must be a mapping with a 'chunks' list",
              file=sys.stderr)
        return 1
    chunks = doc["chunks"]
    if not isinstance(chunks, list) or not chunks:
        print("ERROR: 'chunks' must be a non-empty list", file=sys.stderr)
        return 1

    # ---- pass 1: per-chunk field validation -------------------------------
    by_id: dict[str, dict] = {}
    for i, ch in enumerate(chunks):
        where = f"chunks[{i}]"
        if not isinstance(ch, dict):
            errors.append(f"{where}: chunk must be a mapping")
            continue
        cid = ch.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{where}: missing/invalid 'id'")
            continue
        where = f"chunk {cid}"

        missing = REQUIRED_FIELDS - set(ch)
        if missing:
            errors.append(f"{where}: missing fields: {sorted(missing)}")
        unknown = set(ch) - REQUIRED_FIELDS
        if unknown:
            errors.append(f"{where}: unknown fields: {sorted(unknown)}")

        if cid in by_id:
            errors.append(f"{where}: duplicate id")
            continue
        by_id[cid] = ch

        # id format + module consistency
        parts = cid.split(".")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            errors.append(f"{where}: id must look like '<module_num>.<seq>'")
        module = ch.get("module")
        if module not in MODULES:
            errors.append(f"{where}: module {module!r} not in M1..M12")
        elif len(parts) == 2 and parts[0].isdigit() and module != f"M{int(parts[0])}":
            errors.append(f"{where}: id prefix does not match module {module}")

        if not isinstance(ch.get("title"), str) or not ch.get("title", "").strip():
            errors.append(f"{where}: title must be a non-empty string")

        medium = ch.get("medium")
        if medium not in MEDIA:
            errors.append(f"{where}: medium {medium!r} not in {sorted(MEDIA)}")

        status = ch.get("status")
        if status not in STATUSES:
            errors.append(f"{where}: status {status!r} not in {STATUSES}")

        beats = ch.get("beats")
        if (not isinstance(beats, list) or not beats
                or len(set(beats)) != len(beats)
                or any(b not in BEATS for b in beats)):
            errors.append(f"{where}: beats must be a non-empty, duplicate-free "
                          f"subset of {BEATS} (got {beats!r})")

        est = ch.get("est_minutes")
        if not isinstance(est, int) or isinstance(est, bool) or not 25 <= est <= 45:
            errors.append(f"{where}: est_minutes must be an int in 25-45 (got {est!r})")

        for key in ("depends_on", "unlocks"):
            val = ch.get(key)
            if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
                errors.append(f"{where}: {key} must be a list of chunk-id strings")

        # gate-null policy: null only for html (briefings + read-only reveals)
        gate = ch.get("gate")
        if gate is None:
            if medium != "html":
                errors.append(f"{where}: gate: null is allowed only for "
                              f"medium: html chunks (medium is {medium!r})")
        else:
            if not isinstance(gate, str) or not gate.strip():
                errors.append(f"{where}: gate must be null or a non-empty command string")
            elif f"--chunk {cid}" not in gate:
                errors.append(f"{where}: gate command must target its own chunk "
                              f"('--chunk {cid}' not found in {gate!r})")

        cr = ch.get("codex_review")
        if cr is not None and (not isinstance(cr, str) or not cr.strip()):
            errors.append(f"{where}: codex_review must be null or a path string")

    # ---- pass 2: graph checks ---------------------------------------------
    ids = set(by_id)
    for cid, ch in by_id.items():
        for key in ("depends_on", "unlocks"):
            for ref in ch.get(key) or []:
                if ref not in ids:
                    errors.append(f"chunk {cid}: {key} references unknown id {ref!r}")
                if ref == cid:
                    errors.append(f"chunk {cid}: {key} references itself")
        for dep in ch.get("depends_on") or []:
            if dep in ids and cid not in (by_id[dep].get("unlocks") or []):
                errors.append(f"chunk {cid}: depends_on {dep} but {dep}.unlocks "
                              f"does not list {cid} (cross-consistency)")
        for unl in ch.get("unlocks") or []:
            if unl in ids and cid not in (by_id[unl].get("depends_on") or []):
                errors.append(f"chunk {cid}: unlocks {unl} but {unl}.depends_on "
                              f"does not list {cid} (cross-consistency)")

    # acyclicity (iterative DFS over depends_on edges)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in ids}
    for root in sorted(ids):
        if color[root] != WHITE:
            continue
        stack = [(root, iter(sorted(set(by_id[root].get("depends_on") or []) & ids)))]
        color[root] = GRAY
        while stack:
            node, it = stack[-1]
            for nxt in it:
                if color[nxt] == GRAY:
                    errors.append(f"dependency cycle detected through {nxt!r}")
                    color[nxt] = BLACK
                elif color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(sorted(set(by_id[nxt].get("depends_on") or []) & ids))))
                    break
            else:
                color[node] = BLACK
                stack.pop()

    # ---- pass 3: build-state checks ---------------------------------------
    for cid, ch in by_id.items():
        status = ch.get("status")
        if status not in STATUSES:
            continue
        rank = STATUSES.index(status)
        medium, gate = ch.get("medium"), ch.get("gate")
        if rank >= STATUSES.index("built"):
            if isinstance(gate, str):
                ex_dir = COURSE_DIR / "exercises" / cid
                if not ex_dir.is_dir():
                    errors.append(f"chunk {cid}: status {status} but {ex_dir.relative_to(REPO_ROOT)}/ missing")
                if "--operate" not in gate:
                    sol_dir = COURSE_DIR / "solutions" / cid
                    if not sol_dir.is_dir():
                        errors.append(f"chunk {cid}: status {status} but {sol_dir.relative_to(REPO_ROOT)}/ missing")
            lesson = COURSE_DIR / "lessons" / (f"{cid}.html" if medium == "html" else f"{cid}.py")
            if medium in ("html", "marimo") and not lesson.is_file():
                errors.append(f"chunk {cid}: status {status} but lesson {lesson.relative_to(REPO_ROOT)} missing")
        if status == "shipped":
            cr = ch.get("codex_review")
            if not cr:
                errors.append(f"chunk {cid}: status shipped requires non-null codex_review")
            elif not (COURSE_DIR / cr).is_file() and not (REPO_ROOT / cr).is_file():
                errors.append(f"chunk {cid}: codex_review file {cr!r} not found "
                              f"(looked under the course dir and repo root)")

    if errors:
        print(f"curriculum.yaml INVALID — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    n = len(by_id)
    per_module: dict[str, int] = {}
    for ch in by_id.values():
        per_module[ch["module"]] = per_module.get(ch["module"], 0) + 1
    summary = ", ".join(f"{m}:{per_module[m]}" for m in sorted(per_module, key=lambda s: int(s[1:])))
    print(f"curriculum.yaml OK — {n} chunks ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
