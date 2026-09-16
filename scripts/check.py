"""Run the local Phase 1 quality gate with cross-platform commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NPM = "npm.cmd" if sys.platform == "win32" else "npm"

COMMANDS = [
    ["uv", "run", "--directory", "apps/api", "ruff", "format", "--check", "."],
    ["uv", "run", "--directory", "apps/api", "ruff", "check", "."],
    ["uv", "run", "--directory", "apps/api", "mypy", "src", "tests"],
    ["uv", "run", "--directory", "apps/api", "pytest", "--cov", "--cov-report=term-missing"],
    [NPM, "run", "web:format:check"],
    [NPM, "run", "web:lint"],
    [NPM, "run", "web:test"],
    [NPM, "run", "web:build"],
]


def main() -> None:
    for command in COMMANDS:
        print(f"\n$ {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
