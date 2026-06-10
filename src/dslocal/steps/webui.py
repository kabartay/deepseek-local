from __future__ import annotations

from ..config import Config
from ..utils import log, ok, run, warn, which


def run_step(cfg: Config) -> None:
    if not cfg.webui.enabled:
        log("Open WebUI disabled in config, skipping")
        return

    if not which("docker"):
        if cfg.webui.skip_if_no_docker:
            warn("Docker not installed, skipping Open WebUI")
            return
        raise RuntimeError("Docker required for Open WebUI")

    existing = run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture=True,
    ).stdout.split()

    if cfg.webui.container_name in existing:
        run(["docker", "start", cfg.webui.container_name], check=False)
        ok(f"Open WebUI restarted at http://localhost:{cfg.webui.port}")
        return

    host = cfg.ollama.host.replace("localhost", "host.docker.internal")
    run(
        [
            "docker", "run", "-d",
            "-p", f"{cfg.webui.port}:8080",
            "-v", "open-webui:/app/backend/data",
            "-e", f"OLLAMA_BASE_URL={host}",
            "--name", cfg.webui.container_name,
            "--restart", "always",
            cfg.webui.image,
        ]
    )
    ok(f"Open WebUI running at http://localhost:{cfg.webui.port}")
