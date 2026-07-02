#!/usr/bin/env python3
"""Two-sided gate runner for a paideia gated-tutor course.

This script is course-dir-agnostic: it derives its course directory from its
own location (it lives at ``<course_dir>/scripts/check_gates.py``), so the
course dir may be named anything (``tutor/``, ``course/``, ...). Nothing here
hardcodes a course-dir name.

Layout per gated chunk (``<course>`` = the derived course dir):
    <course>/exercises/<id>/impl.py       starter with holes (NotImplementedError/TODO)
    <course>/exercises/<id>/test_gate.py  bare `import impl`; asserts properties
    <course>/solutions/<id>/impl.py       reference; same module name + signatures

conftest mechanism
------------------
The shared template ``<course>/exercises/conftest_gate.py`` is copied by this
script into ``<course>/exercises/<id>/conftest.py`` (generated when missing; a
drifted copy is an error). That conftest reads $TUTOR_IMPL_DIR, loads
<dir>/impl.py, and registers it as sys.modules["impl"] before test collection
(also placing the dir at sys.path[0] for helper modules), so a bare
`import impl` in test_gate.py resolves to whichever implementation directory
this runner selects — pytest's own sys.path prepending cannot shadow it.
solutions/ is selected ONLY by this script's two-sided mode — never by the
learner flow.

Modes
-----
default (two-sided, the build/CI check): pytest runs TWICE per chunk on
    <course>/exercises/<id>/:
      1. TUTOR_IMPL_DIR=<course>/exercises/<id>  -> MUST FAIL (holes present;
         if it passes, the gate is gameable -> defect, exit != 0)
      2. TUTOR_IMPL_DIR=<course>/solutions/<id>  -> MUST PASS (else the
         reference is broken -> defect)
--learner: what the runtime tutor skill calls. ONE pytest run with
    TUTOR_IMPL_DIR=<course>/exercises/<id>. Exit 0 = gate passed. solutions/ is
    never placed on sys.path in this mode.
--operate: for operate-and-inspect chunks. ONE pytest run on
    <course>/exercises/<id>/ (a light ran-the-smoke check), must pass. No
    two-sided requirement and no solutions/ involvement.
--list: print every chunk with its gate kind and status; no tests run.

Selection: --chunk <id> (repeatable) and/or --module Mx (repeatable).
Chunks whose curriculum gate command contains --operate are always run in
operate mode. gate: null chunks (html briefings/reveal) are skipped.
Runs are seeded (PYTHONHASHSEED=0; gate tests seed their own RNGs).

Exit codes: 0 all selected gates satisfied; 1 defect/failure; 2 usage error.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Course dir is derived from this file's own location, not hardcoded:
#   <course_dir>/scripts/check_gates.py  ->  parents[1] == <course_dir>
COURSE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
CURRICULUM = COURSE_DIR / "curriculum.yaml"
CONFTEST_TEMPLATE = COURSE_DIR / "exercises" / "conftest_gate.py"


def load_chunks() -> dict[str, dict]:
    try:
        import yaml  # pyyaml
    except ImportError:
        print(
            "ERROR: pyyaml is not importable. Install it first, e.g.\n"
            "  uv pip install pyyaml   (or: python3 -m pip install pyyaml)",
            file=sys.stderr,
        )
        sys.exit(2)
    if not CURRICULUM.is_file():
        print(f"ERROR: {CURRICULUM} not found", file=sys.stderr)
        sys.exit(2)
    with CURRICULUM.open() as fh:
        doc = yaml.safe_load(fh)
    chunks = {c["id"]: c for c in (doc or {}).get("chunks", [])}
    if not chunks:
        print("ERROR: no chunks found in curriculum.yaml", file=sys.stderr)
        sys.exit(2)
    return chunks


def gate_kind(chunk: dict) -> str:
    gate = chunk.get("gate")
    if gate is None:
        return "none"
    if "--operate" in gate:
        return "operate"
    return "two-sided"


def ensure_conftest(ex_dir: Path) -> str | None:
    """Copy the shared conftest template into the chunk dir if missing.

    Returns an error string if an existing conftest.py drifted from the
    template (we refuse to silently overwrite learner-visible files).
    """
    if not CONFTEST_TEMPLATE.is_file():
        return f"missing template {CONFTEST_TEMPLATE.relative_to(REPO_ROOT)}"
    template = CONFTEST_TEMPLATE.read_text()
    target = ex_dir / "conftest.py"
    if not target.exists():
        target.write_text(template)
        return None
    if target.read_text() != template:
        return (f"{target.relative_to(REPO_ROOT)} differs from "
                f"{CONFTEST_TEMPLATE.relative_to(REPO_ROOT)}; regenerate it "
                f"(delete the copy and re-run)")
    return None


def run_pytest(ex_dir: Path, impl_dir: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["TUTOR_IMPL_DIR"] = str(impl_dir)
    env["PYTHONHASHSEED"] = "0"
    env.pop("PYTHONPATH", None)  # hermetic: nothing leaks onto sys.path
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", str(ex_dir)],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    out = (proc.stdout + proc.stderr).strip()
    tail = "\n".join(out.splitlines()[-15:])
    return proc.returncode, tail


def check_built(cid: str, need_solution: bool) -> tuple[Path, Path | None, str | None]:
    ex_dir = COURSE_DIR / "exercises" / cid
    sol_dir = COURSE_DIR / "solutions" / cid if need_solution else None
    if not (ex_dir / "test_gate.py").is_file():
        return ex_dir, sol_dir, f"not built yet: {ex_dir.relative_to(REPO_ROOT)}/test_gate.py missing"
    if need_solution and not (sol_dir / "impl.py").is_file():
        return ex_dir, sol_dir, f"not built yet: {sol_dir.relative_to(REPO_ROOT)}/impl.py missing"
    return ex_dir, sol_dir, None


def run_chunk(cid: str, chunk: dict, mode: str) -> tuple[bool, str]:
    """Returns (ok, message). mode: 'two-sided' | 'learner' | 'operate'."""
    ex_dir, sol_dir, err = check_built(cid, need_solution=(mode == "two-sided"))
    if err:
        return False, err
    err = ensure_conftest(ex_dir)
    if err:
        return False, err

    if mode == "learner":
        rc, tail = run_pytest(ex_dir, ex_dir)
        if rc == 0:
            return True, "learner gate PASSED (exercises/ implementation satisfies the gate)"
        return False, f"learner gate not passed yet (pytest exit {rc}):\n{tail}"

    if mode == "operate":
        rc, tail = run_pytest(ex_dir, ex_dir)
        if rc == 0:
            return True, "operate check PASSED"
        return False, f"operate check FAILED (pytest exit {rc}):\n{tail}"

    # two-sided
    rc_ex, tail_ex = run_pytest(ex_dir, ex_dir)
    if rc_ex == 0:
        return False, ("DEFECT: gate PASSES against the starter exercises/ "
                       "implementation — the gate is gameable (holes not exercised)")
    rc_sol, tail_sol = run_pytest(ex_dir, sol_dir)
    if rc_sol != 0:
        return False, (f"DEFECT: gate FAILS against solutions/ reference "
                       f"(pytest exit {rc_sol}):\n{tail_sol}")
    return True, "two-sided OK (exercises fail as required; solutions pass)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunk", action="append", default=[], metavar="ID",
                    help="chunk id, e.g. 2.2 (repeatable)")
    ap.add_argument("--module", action="append", default=[], metavar="Mx",
                    help="module, e.g. M2 (repeatable)")
    ap.add_argument("--list", action="store_true", help="list chunks and gate kinds")
    ap.add_argument("--operate", action="store_true",
                    help="run the light operate check (single run, must pass)")
    ap.add_argument("--learner", action="store_true",
                    help="single run against exercises/ only (the runtime gate run)")
    args = ap.parse_args()

    chunks = load_chunks()

    if args.list:
        print(f"{'id':<6} {'module':<7} {'medium':<9} {'gate':<10} {'status':<9} title")
        for cid, ch in chunks.items():
            print(f"{cid:<6} {ch['module']:<7} {ch['medium']:<9} "
                  f"{gate_kind(ch):<10} {ch['status']:<9} {ch['title']}")
        gated = sum(1 for c in chunks.values() if gate_kind(c) != "none")
        print(f"\n{len(chunks)} chunks; {gated} gated, {len(chunks) - gated} ungated (html)")
        return 0

    if args.learner and args.operate:
        print("ERROR: --learner and --operate are mutually exclusive", file=sys.stderr)
        return 2

    selected: list[str] = []
    for cid in args.chunk:
        if cid not in chunks:
            print(f"ERROR: unknown chunk id {cid!r}", file=sys.stderr)
            return 2
        selected.append(cid)
    for mod in args.module:
        members = [cid for cid, c in chunks.items() if c["module"] == mod]
        if not members:
            print(f"ERROR: no chunks in module {mod!r}", file=sys.stderr)
            return 2
        selected.extend(members)
    if not selected:
        print("ERROR: select chunks with --chunk/--module, or use --list",
              file=sys.stderr)
        return 2
    selected = list(dict.fromkeys(selected))  # dedupe, keep order

    failures = 0
    skipped = 0
    for cid in selected:
        ch = chunks[cid]
        kind = gate_kind(ch)
        if kind == "none":
            print(f"[skip] {cid}: ungated (gate: null, medium {ch['medium']})")
            skipped += 1
            continue
        if kind == "operate" or args.operate:
            if kind != "operate" and args.operate:
                print(f"ERROR: chunk {cid} is not an operate chunk", file=sys.stderr)
                return 2
            mode = "operate"
        elif args.learner:
            mode = "learner"
        else:
            mode = "two-sided"
        ok, msg = run_chunk(cid, ch, mode)
        print(f"[{'ok' if ok else 'FAIL'}] {cid} ({mode}): {msg}")
        if not ok:
            failures += 1

    ran = len(selected) - skipped
    print(f"\n{ran} gate(s) run, {failures} failure(s), {skipped} skipped")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
