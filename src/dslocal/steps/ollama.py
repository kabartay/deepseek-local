from __future__ import annotations

import time
from pathlib import Path

import httpx

from ..config import Config
from ..utils import log, ok, run, warn, which


OFFICIAL_BIN_PATH = Path("/Applications/Ollama.app/Contents/Resources/ollama")
USER_BIN_DIR = Path.home() / ".local" / "bin"


def _install_official() -> None:
    """Install Ollama via the official installer.

    The Homebrew formula has shipped without the llama-server runtime
    binary in some versions, leading to 'llama-server binary not found'
    errors at inference time. The official installer always bundles it.
    """
    log("downloading Ollama via official installer")
    run(["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"])
    # the installer's sudo step may fail silently; symlink ourselves.
    if OFFICIAL_BIN_PATH.exists() and not which("ollama"):
        USER_BIN_DIR.mkdir(parents=True, exist_ok=True)
        target = USER_BIN_DIR / "ollama"
        target.unlink(missing_ok=True)
        target.symlink_to(OFFICIAL_BIN_PATH)
        warn(f"symlinked {target} -> {OFFICIAL_BIN_PATH}")
        warn(f"make sure {USER_BIN_DIR} is on your PATH")


def _install_brew() -> None:
    log("installing Ollama via Homebrew")
    run(["brew", "install", "ollama"])
    run(["brew", "services", "start", "ollama"], check=False)


def _wait_for_daemon(host: str, attempts: int = 20) -> None:
    for _ in range(attempts):
        try:
            r = httpx.get(f"{host}/api/tags", timeout=1.0)
            if r.status_code == 200:
                ok(f"Ollama responding at {host}")
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError(
        f"Ollama did not come up at {host}. "
        "If you installed via the official .pkg, launch it once with: "
        "open -a Ollama"
    )


def run_step(cfg: Config) -> None:
    log("installing Ollama")
    if which("ollama"):
        ok("ollama already installed")
    elif cfg.ollama.install_method == "official":
        _install_official()
    else:
        _install_brew()

    # for the official installer, the daemon starts via the app bundle.
    # the user may need to launch it once if it's not auto-started.
    if cfg.ollama.install_method == "official":
        run(["open", "-a", "Ollama"], check=False)

    _wait_for_daemon(cfg.ollama.host)
