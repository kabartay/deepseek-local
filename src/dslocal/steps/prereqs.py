from __future__ import annotations

import platform

from ..config import Config
from ..utils import die, log, ok, which


def run_step(cfg: Config) -> None:
    log("checking prerequisites")

    if platform.system().lower() != cfg.platform.os:
        die(f"this config targets {cfg.platform.os}, got {platform.system()}")

    if platform.machine() != cfg.platform.arch:
        die(f"this config targets {cfg.platform.arch}, got {platform.machine()}")

    for binary in ("brew", "git", "curl"):
        if not which(binary):
            die(f"required binary not found: {binary}")

    ok("prerequisites pass")
