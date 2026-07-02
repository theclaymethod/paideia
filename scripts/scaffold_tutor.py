#!/usr/bin/env python3
"""paideia scaffolder — stamp a fresh gated-tutor repo from templates/scaffold/.

Usage:
    python3 scripts/scaffold_tutor.py --dest <path> --course-name <name> \
        [--course-dir tutor] [--learner-profile "..."] [--check] [--force]

What it does:
  * copies templates/scaffold/ into <dest>, renaming the `__COURSE_DIR__`
    placeholder dir to the chosen --course-dir (default: tutor);
  * stamps the runtime skill to <dest>/.claude/skills/<course-name>/SKILL.md;
  * writes gitignore.tmpl to <dest>/.gitignore;
  * substitutes {{COURSE_NAME}} / {{COURSE_DIR}} / {{LEARNER_PROFILE}} in every
    template file (a no-op in the machinery scripts, which derive the course dir
    from their own location);
  * writes the example curriculum.yaml + progress.json (already in the scaffold).

It does NOT author lessons/exercises — that is the build phase the runtime skill
drives. `--check` is a dry run (prints what it would create). It refuses to
write into a non-empty <dest> unless `--force` is given.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCAFFOLD_ROOT = Path(__file__).resolve().parents[1] / "templates" / "scaffold"
PLACEHOLDER_DIR = "__COURSE_DIR__"
DEFAULT_LEARNER_PROFILE = "a motivated learner new to this domain"


def is_text(path: Path) -> bool:
    try:
        path.read_text(encoding="utf-8")
        return True
    except (UnicodeDecodeError, ValueError):
        return False


def substitute(text: str, subs: dict[str, str]) -> str:
    for key, val in subs.items():
        text = text.replace(key, val)
    return text


def plan_targets(dest: Path, course_name: str, course_dir: str) -> list[tuple[Path, Path]]:
    """Return (source_file, target_file) pairs for every file in the scaffold."""
    pairs: list[tuple[Path, Path]] = []
    for src in sorted(SCAFFOLD_ROOT.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(SCAFFOLD_ROOT)
        parts = rel.parts
        if parts[0] == "runtime-skill" and rel.name == "SKILL.md":
            target = dest / ".claude" / "skills" / course_name / "SKILL.md"
        elif rel.name == "gitignore.tmpl" and len(parts) == 1:
            target = dest / ".gitignore"
        else:
            # rename the placeholder course dir to the chosen course dir
            mapped = [course_dir if p == PLACEHOLDER_DIR else p for p in parts]
            target = dest.joinpath(*mapped)
        pairs.append((src, target))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dest", required=True, help="path to the new tutor repo")
    ap.add_argument("--course-name", required=True,
                    help="skill/course name, e.g. 'ml-evals' (becomes /<name>)")
    ap.add_argument("--course-dir", default="tutor",
                    help="course directory name inside the repo (default: tutor)")
    ap.add_argument("--learner-profile", default=DEFAULT_LEARNER_PROFILE,
                    help="one-line description of the target learner")
    ap.add_argument("--check", action="store_true",
                    help="dry run: print what would be created, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="allow writing into a non-empty destination")
    args = ap.parse_args()

    if not SCAFFOLD_ROOT.is_dir():
        print(f"ERROR: scaffold templates not found at {SCAFFOLD_ROOT}", file=sys.stderr)
        return 2
    if not args.course_dir or "/" in args.course_dir or args.course_dir in (".", ".."):
        print(f"ERROR: --course-dir must be a simple directory name (got {args.course_dir!r})",
              file=sys.stderr)
        return 2

    dest = Path(args.dest).resolve()
    subs = {
        "{{COURSE_NAME}}": args.course_name,
        "{{COURSE_DIR}}": args.course_dir,
        "{{LEARNER_PROFILE}}": args.learner_profile,
    }

    if dest.exists() and any(dest.iterdir()) and not args.force and not args.check:
        print(f"ERROR: destination {dest} is not empty; pass --force to write into it",
              file=sys.stderr)
        return 2

    pairs = plan_targets(dest, args.course_name, args.course_dir)

    if args.check:
        print(f"[dry run] would stamp {len(pairs)} files into {dest}:")
        for _src, target in pairs:
            print(f"  + {target.relative_to(dest)}")
        print("\n(no files written)")
        return 0

    written = 0
    for src, target in pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        if is_text(src):
            target.write_text(substitute(src.read_text(encoding="utf-8"), subs),
                              encoding="utf-8")
        else:
            target.write_bytes(src.read_bytes())
        written += 1

    print(f"Stamped {written} files into {dest}")
    print("\nNext steps:")
    print(f"  1. cd {dest}")
    print(f"  2. python3 {args.course_dir}/scripts/validate_curriculum.py   # example curriculum passes")
    print(f"  3. Edit {args.course_dir}/curriculum.yaml — replace the example chunks with your course.")
    print(f"  4. For each chunk, author from templates/lesson/ + templates/exercise/, then run")
    print(f"     python3 {args.course_dir}/scripts/check_gates.py --chunk <id>   (two-sided build check)")
    print(f"  5. Drive the interactive build with the /{args.course_name} skill "
          f"(.claude/skills/{args.course_name}/SKILL.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
