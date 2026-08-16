#!/usr/bin/env python3
"""Remind the agent to add tests when a new src/*.py file is created."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SKIP_NAMES = {"__init__.py"}


def read_input() -> Dict[str, Any]:
    raw = sys.stdin.read().strip()
    return json.loads(raw) if raw else {}


def file_path_from(payload: Dict[str, Any]) -> Optional[Path]:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("path") or tool_input.get("file_path")
    return Path(raw).resolve() if raw else None


def is_untracked(path: Path, cwd: Path) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", str(path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def expected_test_path(src_file: Path, root: Path) -> Path:
    # src/evaluation/decision_router.py -> tests/test_decision_router.py
    return root / "tests" / f"test_{src_file.stem}.py"


def tests_mention_module(src_file: Path, root: Path) -> bool:
    rel = src_file.relative_to(root / "src").with_suffix("")
    module = "src." + ".".join(rel.parts)
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return False
    for test_file in tests_dir.rglob("test_*.py"):
        if module in test_file.read_text(encoding="utf-8", errors="ignore"):
            return True
    return False


def main() -> None:
    payload = read_input()
    path = file_path_from(payload)
    if path is None:
        print("{}")
        return

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    try:
        rel = path.relative_to(cwd)
    except ValueError:
        print("{}")
        return

    if rel.parts[:1] != ("src",) or path.suffix != ".py":
        print("{}")
        return
    if path.name in SKIP_NAMES or "tests" in rel.parts:
        print("{}")
        return
    if not is_untracked(path, cwd):
        print("{}")
        return

    expected = expected_test_path(path, cwd)
    if expected.exists() or tests_mention_module(path, cwd):
        print("{}")
        return

    module = "src." + ".".join(path.relative_to(cwd / "src").with_suffix("").parts)
    context = (
        f"New source file `{rel}` has no test coverage. "
        f"Add `{expected.relative_to(cwd)}` covering `{module}` before finishing. "
        "Do not call external services from evaluation code."
    )
    print(json.dumps({"additional_context": context}))


if __name__ == "__main__":
    main()
