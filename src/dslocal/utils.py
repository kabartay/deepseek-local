from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class Colors:
    BLUE = "\033[1;34m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[1;31m"
    RESET = "\033[0m"


def log(msg: str) -> None:
    print(f"{Colors.BLUE}==>{Colors.RESET} {msg}")


def ok(msg: str) -> None:
    print(f"{Colors.GREEN} ok{Colors.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{Colors.YELLOW} !!{Colors.RESET} {msg}")


def die(msg: str, code: int = 1) -> None:
    print(f"{Colors.RED} xx{Colors.RESET} {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def which(binary: str) -> str | None:
    return shutil.which(binary)


def expand(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def write_file(path: Path, content: str, mode: int | None = None) -> None:
    path = expand(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if mode is not None:
        path.chmod(mode)
