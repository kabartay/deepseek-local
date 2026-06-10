from __future__ import annotations

import yaml

from ..config import Config
from ..utils import die, expand, log, ok, run, warn, which


def _pick_python(candidates: list[str]) -> str:
    """Pick the first available python that has a working pyexpat.

    Homebrew's Python 3.12 has shipped with a broken pyexpat linkage
    against the system libexpat on some macOS versions. We probe each
    candidate to find one that actually works before handing it to pipx.
    """
    for cmd in candidates:
        path = which(cmd)
        if not path:
            continue
        probe = run(
            [path, "-c", "import pyexpat; import xml.parsers.expat"],
            check=False,
            capture=True,
        )
        if probe.returncode == 0:
            return path
        warn(f"{path} found but pyexpat is broken — skipping")

    die(
        "no working python found from candidates: "
        + ", ".join(candidates)
        + ". Try: brew install python@3.11"
    )


def run_step(cfg: Config) -> None:
    log("installing aider")
    if not which("pipx"):
        run(["brew", "install", "pipx"])

    python_bin = _pick_python(cfg.aider.python_versions)
    log(f"using {python_bin} for aider")

    if which("aider"):
        run(["pipx", "upgrade", "aider-chat"], check=False)
    else:
        run(["pipx", "install", "aider-chat", "--python", python_bin])

    model = cfg.resolve_model(cfg.aider.model_ref)
    aider_conf = {
        "model": f"ollama/{model.alias}",
        "auto-commits": cfg.aider.auto_commits,
        "map-tokens": cfg.aider.map_tokens,
    }

    path = expand(cfg.aider.config_path)
    path.write_text(yaml.safe_dump(aider_conf, sort_keys=False))
    ok(f"wrote {path}")
