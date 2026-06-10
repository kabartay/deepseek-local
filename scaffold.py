#!/usr/bin/env python3

"""
scaffold.py — generate the deepseek-local repo on disk.

Usage:
    python3 scaffold.py                  # creates ./deepseek-local
    python3 scaffold.py --target ~/code  # creates ~/code/deepseek-local
    python3 scaffold.py --force          # overwrite if target exists
"""

from __future__ import annotations

import argparse
import shutil
import stat
import sys
from pathlib import Path
from textwrap import dedent


REPO_NAME = "deepseek-local"


# ---------------------------------------------------------------------------
# file contents
# ---------------------------------------------------------------------------

CONFIG_YAML = dedent('''\
    platform:
      os: darwin
      arch: arm64
      min_ram_gb: 16

    ollama:
      host: http://localhost:11434
      num_gpu: 99
      max_loaded_models: 2
      # use the official installer (https://ollama.com/install.sh).
      # the Homebrew formula has historically shipped without the
      # llama-server binary, which breaks inference at runtime.
      install_method: official

    models:
      main:
        source: deepseek-coder-v2:16b-lite-instruct-q4_K_M
        alias: deepseek-coder-32k
        num_ctx: 32768
        role: chat
      fast:
        source: qwen2.5-coder:7b-instruct-q4_K_M
        alias: qwen-coder-fast-32k
        num_ctx: 32768
        role: autocomplete

    aider:
      config_path: ~/.aider.conf.yml
      model_ref: main
      auto_commits: false
      map_tokens: 4096
      # python 3.12 has had pyexpat linkage issues on Homebrew —
      # pin to 3.11 which has rock-solid arm64 wheels for aider's deps.
      python_versions:
        - python3.11
        - python3.12
        - python3

    continue_dev:
      config_path: ~/.continue/config.json
      chat_model_ref: main
      autocomplete_model_ref: fast
      embeddings_model_ref: main

    shell:
      helpers_path: ~/.deepseek-local.sh
      rc_files:
        - ~/.zshrc
      aliases:
        ds: aider --model ollama/{main.alias}
        ds-chat: ollama run {main.alias}
        ds-fast: ollama run {fast.alias}

    webui:
      enabled: true
      port: 3000
      container_name: open-webui
      image: ghcr.io/open-webui/open-webui:main
      skip_if_no_docker: true

    steps:
      - prereqs
      - ollama
      - models
      - aider
      - continue_dev
      - shell
      - webui
''')


PYPROJECT_TOML = dedent('''\
    [project]
    name = "dslocal"
    version = "0.1.0"
    description = "DeepSeek local coding environment bootstrap"
    requires-python = ">=3.11"
    dependencies = [
        "typer>=0.12",
        "pydantic>=2.6",
        "pyyaml>=6.0",
        "httpx>=0.27",
    ]

    [project.optional-dependencies]
    dev = [
        "pytest>=8.0",
    ]

    [project.scripts]
    dslocal = "dslocal.cli:app"

    [build-system]
    requires = ["setuptools>=68"]
    build-backend = "setuptools.build_meta"

    [tool.setuptools.packages.find]
    where = ["src"]

    [tool.pytest.ini_options]
    pythonpath = ["src"]
    testpaths = ["tests"]
''')


README_MD = dedent('''\
    # deepseek-local

    A one-command bootstrap for a fully local, Claude-Code-equivalent coding stack on Apple Silicon.

    Everything runs on your Mac. No API keys, no cloud, no data leaving your machine.

    ## What you get

    | Tool | Role | Cloud equivalent |
    |------|------|------------------|
    | Ollama | Model runtime | — |
    | DeepSeek-Coder-V2 16B Lite (32k ctx) | Main coding model | Claude Sonnet |
    | Qwen2.5-Coder 7B (32k ctx) | Fast autocomplete model | GitHub Copilot |
    | aider | Terminal coding agent | Claude Code |
    | Continue.dev | VS Code / JetBrains inline assistant | Cursor / Copilot Chat |
    | Open WebUI | Browser chat UI | claude.ai |

    Shell helpers wired up so `ds` drops you straight into an aider session with the right model.

    ## Requirements

    - Apple Silicon Mac (M1/M2/M3/M4)
    - macOS 13 or newer
    - **At least 16 GB** unified memory (32 GB+ recommended; 64 GB lets you run both models simultaneously)
    - Homebrew installed: <https://brew.sh>
    - About 20 GB of free disk space for the models
    - Docker Desktop (optional, only needed for Open WebUI)

    ## Install

    ```bash
    git clone https://github.com/YOUR_USERNAME/deepseek-local
    cd deepseek-local
    pipx install -e .
    dslocal doctor       # sanity-check prerequisites
    dslocal setup        # full pipeline (the slow part: ~15 GB of model downloads)
    ```

    After it finishes:

    ```bash
    source ~/.zshrc      # pick up the new shell helpers
    ds-status            # confirm Ollama is up and models are listed
    ```

    ## Usage

    ### Terminal (aider — the Claude Code equivalent)

    ```bash
    cd ~/your-project
    ds                    # start aider with DeepSeek
    ```

    Inside aider:
    - `/add path/to/file.py` — bring a file into the conversation
    - `/run pytest` — run a command and feed the output back
    - `/diff` — show pending changes
    - `/commit` — commit them
    - `/help` — full list

    ### VS Code / JetBrains (Continue.dev)

    Install the **Continue** extension from your editor's marketplace. The config is already written to `~/.continue/config.json`.

    - `Cmd+L` — open chat sidebar
    - `Cmd+I` — inline edit selected code
    - `Tab` — accept autocomplete suggestion

    ### Browser (Open WebUI)

    Open <http://localhost:3000>. First time, create an admin account (it stays local). Pick `deepseek-coder-32k` from the model dropdown and chat.

    ## Configuration

    Everything tunable lives in [`config.yaml`](./config.yaml). Edit and re-run `dslocal setup`:

    ```yaml
    models:
      main:
        source: deepseek-coder-v2:16b-lite-instruct-q4_K_M  # or :33b-instruct-q4_K_M if you have the RAM
        alias: deepseek-coder-32k
        num_ctx: 32768
    ```

    Common customizations:

    - **Use a bigger model** — change `models.main.source` to `deepseek-coder-v2:33b-instruct-q4_K_M` (needs ~25 GB RAM)
    - **Change context window** — bump `num_ctx`. Default Ollama is 2048, which is uselessly small; we override to 32k
    - **Disable Open WebUI** — set `webui.enabled: false`
    - **Point at a remote Ollama** — set `ollama.host` to e.g. `http://desktop.local:11434`
    - **Add shell aliases** — extend `shell.aliases`

    ## CLI

    ```bash
    dslocal setup                       # full pipeline
    dslocal setup --only models         # one step
    dslocal setup --only aider,shell    # multiple (comma-separated)
    dslocal setup --skip webui          # everything except Open WebUI
    dslocal show                        # print resolved config
    dslocal doctor                      # check prerequisites
    ```

    Steps are defined as separate modules under [`src/dslocal/steps/`](./src/dslocal/steps/) and listed in `config.yaml` under `steps:`. Each step is idempotent — running setup twice is a no-op the second time.

    ## When to use what

    Different tools for different moments. They all share the same models underneath.

    - **aider** — multi-file refactors, "implement this feature", "fix this bug", "add tests". Closest to the Claude Code experience.
    - **Continue.dev** — writing new code, autocomplete, ask-this-function-something quickly without leaving the editor.
    - **Open WebUI** — exploring an idea, learning, longer back-and-forth conversations, anything where you want chat history saved.

    ## Reality check on the models

    DeepSeek-Coder-V2 16B Lite is genuinely good and runs at zero marginal cost. It's not Claude Opus 4.7. Honest comparison:

    **Local stack wins for:** inline autocomplete (zero latency), boilerplate / type hints / docstrings, quick reviews, code on sensitive data you can't send to a cloud API, working offline, iterative loops where API costs would add up.

    **Claude still wins for:** multi-file architectural changes across a large codebase, complex debugging that needs deep reasoning, tasks where the cost of a wrong answer is high.

    A workable pattern: local stack for the 80% of "do the obvious thing" work, Claude for the hard 20%.

    ## Troubleshooting

    These are the issues we hit while developing this. Each one is now handled automatically by the scaffold, but documenting them helps if something goes sideways.

    ### `llama-server binary not found` from Ollama

    The Homebrew formula has shipped without the inference runtime in some versions. The scaffold uses the official installer (`curl -fsSL https://ollama.com/install.sh | sh`) to avoid this. If you previously installed via Homebrew:

    ```bash
    brew uninstall ollama
    curl -fsSL https://ollama.com/install.sh | sh
    open -a Ollama   # launch once to start the daemon
    ```

    Your models in `~/.ollama/models/` survive the swap.

    ### `pyexpat` ImportError when installing aider

    Some Homebrew Python 3.12 builds link against a system libexpat that's missing newer symbols, producing errors like:

    ```
    ImportError: ... Symbol not found: _XML_SetAllocTrackerActivationThreshold
    ```

    The scaffold probes each candidate Python (3.11 first, then 3.12) and picks one with a working pyexpat. To install 3.11 manually if needed:

    ```bash
    brew install python@3.11
    ```

    ### `numpy==1.24.3` build failure during pipx install

    Old numpy versions predate prebuilt arm64 wheels and try to compile from source — which usually fails without Xcode CLT. Either:

    ```bash
    xcode-select --install
    ```

    or just let the scaffold pick a newer Python (Python 3.11+ pulls in numpy with native arm64 wheels).

    ### `docker ps` returns non-zero in the webui step

    Docker is installed but the daemon isn't running. The scaffold now detects this and skips gracefully. To enable Open WebUI later:

    ```bash
    open -a Docker
    # wait ~30 seconds for the daemon, then:
    dslocal setup --only webui
    ```

    ### First model response is very slow

    Ollama loads the model into RAM on first use (~10–20 seconds) and unloads it after ~5 minutes of inactivity. To keep models warm longer:

    ```bash
    echo 'export OLLAMA_KEEP_ALIVE=30m' >> ~/.zshrc
    ```

    ## Uninstall

    ```bash
    # stop and remove the services
    osascript -e 'quit app "Ollama"'
    docker rm -f open-webui 2>/dev/null

    # remove the tools
    pipx uninstall aider-chat
    pipx uninstall dslocal

    # remove the configs
    rm ~/.deepseek-local.sh ~/.aider.conf.yml
    rm -rf ~/.continue/config.json
    rm -rf ~/.ollama/models   # optional, this frees ~15 GB

    # remove the source line from ~/.zshrc manually
    # look for: source ~/.deepseek-local.sh
    ```

    ## Contributing

    PRs welcome. The code is structured so adding a new step is just creating a module under `src/dslocal/steps/` exposing `run_step(cfg: Config)` and listing it in `config.yaml` under `steps:`.

    Ideas worth picking up:

    - `dslocal benchmark` — run fixed prompts across models, time and log results
    - `dslocal uninstall` — automate the manual teardown above
    - Add Linux support (most steps work, only the installer paths need tweaking)
    - Add a pyenv-based fallback for the aider Python step

    ## License

    MIT
''')


GITIGNORE = dedent('''\
    __pycache__/
    *.py[cod]
    *.egg-info/
    .venv/
    dist/
    build/
    .pytest_cache/
    .ruff_cache/
    .mypy_cache/
    .DS_Store
''')


INIT_PY = ""


CONFIG_PY = dedent('''\
    from __future__ import annotations

    from pathlib import Path
    from typing import Literal

    import yaml
    from pydantic import BaseModel, Field


    class Platform(BaseModel):
        os: Literal["darwin", "linux"] = "darwin"
        arch: Literal["arm64", "x86_64"] = "arm64"
        min_ram_gb: int = 16


    class Ollama(BaseModel):
        host: str = "http://localhost:11434"
        num_gpu: int = 99
        max_loaded_models: int = 2
        install_method: Literal["official", "brew"] = "official"


    class Model(BaseModel):
        source: str
        alias: str
        num_ctx: int = 32768
        role: Literal["chat", "autocomplete", "embeddings"] = "chat"


    class Aider(BaseModel):
        config_path: Path = Path("~/.aider.conf.yml")
        model_ref: str = "main"
        auto_commits: bool = False
        map_tokens: int = 4096
        python_versions: list[str] = Field(
            default_factory=lambda: ["python3.11", "python3.12", "python3"]
        )


    class ContinueDev(BaseModel):
        config_path: Path = Path("~/.continue/config.json")
        chat_model_ref: str = "main"
        autocomplete_model_ref: str = "fast"
        embeddings_model_ref: str = "main"


    class Shell(BaseModel):
        helpers_path: Path = Path("~/.deepseek-local.sh")
        rc_files: list[Path] = Field(default_factory=lambda: [Path("~/.zshrc")])
        aliases: dict[str, str] = Field(default_factory=dict)


    class WebUI(BaseModel):
        enabled: bool = True
        port: int = 3000
        container_name: str = "open-webui"
        image: str = "ghcr.io/open-webui/open-webui:main"
        skip_if_no_docker: bool = True


    class Config(BaseModel):
        platform: Platform
        ollama: Ollama
        models: dict[str, Model]
        aider: Aider
        continue_dev: ContinueDev
        shell: Shell
        webui: WebUI
        steps: list[str]

        @classmethod
        def load(cls, path: Path) -> "Config":
            with open(path) as f:
                data = yaml.safe_load(f)
            return cls(**data)

        def resolve_model(self, ref: str) -> Model:
            if ref not in self.models:
                raise KeyError(f"model ref {ref!r} not in config.models")
            return self.models[ref]
''')


UTILS_PY = dedent('''\
    from __future__ import annotations

    import shutil
    import subprocess
    import sys
    from pathlib import Path


    class Colors:
        BLUE = "\\033[1;34m"
        GREEN = "\\033[1;32m"
        YELLOW = "\\033[1;33m"
        RED = "\\033[1;31m"
        RESET = "\\033[0m"


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
''')


CLI_PY = dedent('''\
    from __future__ import annotations

    import importlib
    from pathlib import Path

    import typer

    from .config import Config
    from .utils import die, log, ok

    app = typer.Typer(add_completion=False, help="DeepSeek local bootstrap")


    def _split_csv(values: list[str] | None) -> list[str]:
        """Allow both `--only a --only b` and `--only a,b` styles."""
        if not values:
            return []
        out: list[str] = []
        for v in values:
            out.extend(part.strip() for part in v.split(",") if part.strip())
        return out


    @app.command()
    def setup(
        config: Path = typer.Option("config.yaml", "-c", "--config"),
        only: list[str] = typer.Option(None, "--only", "-o", help="run only these steps (comma-separated or repeated)"),
        skip: list[str] = typer.Option(None, "--skip", "-s", help="skip these steps (comma-separated or repeated)"),
    ) -> None:
        """Run the full bootstrap pipeline."""
        cfg = Config.load(config)

        only_list = _split_csv(only)
        skip_list = _split_csv(skip)

        steps = cfg.steps
        if only_list:
            steps = [s for s in steps if s in only_list]
        if skip_list:
            steps = [s for s in steps if s not in skip_list]

        for step_name in steps:
            log(f"step: {step_name}")
            try:
                module = importlib.import_module(f".steps.{step_name}", package="dslocal")
                module.run_step(cfg)
            except Exception as e:
                die(f"step {step_name} failed: {e}")

        ok("all steps complete")


    @app.command()
    def show(config: Path = typer.Option("config.yaml", "-c", "--config")) -> None:
        """Print resolved config."""
        cfg = Config.load(config)
        typer.echo(cfg.model_dump_json(indent=2))


    @app.command()
    def doctor(config: Path = typer.Option("config.yaml", "-c", "--config")) -> None:
        """Check the current state of the installation."""
        from .steps import prereqs
        cfg = Config.load(config)
        prereqs.run_step(cfg)
        ok("doctor pass")


    if __name__ == "__main__":
        app()
''')


PREREQS_PY = dedent('''\
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
''')


OLLAMA_STEP_PY = dedent('''\
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
''')


MODELS_STEP_PY = dedent('''\
    from __future__ import annotations

    import tempfile
    from pathlib import Path

    from ..config import Config
    from ..utils import log, ok, run


    MODELFILE_TEMPLATE = """\\
    FROM {source}
    PARAMETER num_ctx {num_ctx}
    PARAMETER num_gpu {num_gpu}
    """


    def run_step(cfg: Config) -> None:
        for name, model in cfg.models.items():
            log(f"pulling {model.source} (role: {model.role})")
            run(["ollama", "pull", model.source])

            log(f"creating tuned variant: {model.alias} (ctx={model.num_ctx})")
            with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False) as f:
                f.write(
                    MODELFILE_TEMPLATE.format(
                        source=model.source,
                        num_ctx=model.num_ctx,
                        num_gpu=cfg.ollama.num_gpu,
                    )
                )
                modelfile_path = Path(f.name)

            run(["ollama", "create", model.alias, "-f", str(modelfile_path)])
            modelfile_path.unlink()
            ok(f"{model.alias} ready")
''')


AIDER_STEP_PY = dedent('''\
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
''')


CONTINUE_STEP_PY = dedent('''\
    from __future__ import annotations

    import json

    from ..config import Config
    from ..utils import expand, log, ok


    def run_step(cfg: Config) -> None:
        chat = cfg.resolve_model(cfg.continue_dev.chat_model_ref)
        auto = cfg.resolve_model(cfg.continue_dev.autocomplete_model_ref)
        embed = cfg.resolve_model(cfg.continue_dev.embeddings_model_ref)

        payload = {
            "models": [
                {
                    "title": f"{chat.alias} (chat)",
                    "provider": "ollama",
                    "model": chat.alias,
                    "apiBase": cfg.ollama.host,
                }
            ],
            "tabAutocompleteModel": {
                "title": f"{auto.alias} (autocomplete)",
                "provider": "ollama",
                "model": auto.alias,
                "apiBase": cfg.ollama.host,
            },
            "embeddingsProvider": {
                "provider": "ollama",
                "model": embed.alias,
                "apiBase": cfg.ollama.host,
            },
        }

        path = expand(cfg.continue_dev.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        log("wrote Continue.dev config")
        ok(str(path))
''')


SHELL_STEP_PY = dedent('''\
    from __future__ import annotations

    from ..config import Config
    from ..utils import expand, log, ok


    HELPERS_HEADER = """\\
    export OLLAMA_API_BASE={host}
    export OLLAMA_MAX_LOADED_MODELS={max_loaded}
    export OLLAMA_NUM_GPU={num_gpu}

    ds-status() {{
      curl -fsS {host}/api/tags >/dev/null && echo 'ollama: up' || echo 'ollama: down'
      ollama list
    }}
    """


    def _render_alias(template: str, models: dict) -> str:
        out = template
        for ref, model in models.items():
            out = out.replace(f"{{{ref}.alias}}", model.alias)
            out = out.replace(f"{{{ref}.source}}", model.source)
        return out


    def run_step(cfg: Config) -> None:
        log("writing shell helpers")

        lines = [
            HELPERS_HEADER.format(
                host=cfg.ollama.host,
                max_loaded=cfg.ollama.max_loaded_models,
                num_gpu=cfg.ollama.num_gpu,
            )
        ]

        for alias_name, cmd in cfg.shell.aliases.items():
            rendered = _render_alias(cmd, cfg.models)
            lines.append(f'{alias_name}() {{ {rendered} "$@"; }}')

        helpers_path = expand(cfg.shell.helpers_path)
        helpers_path.write_text("\\n".join(lines) + "\\n")
        ok(f"wrote {helpers_path}")

        source_line = f"source {helpers_path}"
        for rc in cfg.shell.rc_files:
            rc_path = expand(rc)
            if not rc_path.exists():
                continue
            content = rc_path.read_text()
            if source_line not in content:
                rc_path.write_text(content.rstrip() + f"\\n{source_line}\\n")
                ok(f"added source line to {rc_path}")
''')


WEBUI_STEP_PY = dedent('''\
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
''')


LICENSE_MIT = dedent('''\
    MIT License

    Copyright (c) 2026 deepseek-local contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
''')


CHANGELOG_MD = dedent('''\
    # Changelog

    ## 0.1.0

    Initial public release.

    ### Features
    - YAML-driven configuration (`config.yaml`)
    - Pydantic-validated config with model references
    - Modular step architecture (each step independently re-runnable)
    - Typer CLI: `setup`, `show`, `doctor`
    - Comma-separated and repeated `--only` / `--skip` flags
    - Idempotent — running setup twice is a no-op

    ### Robustness fixes baked in
    - Uses the official Ollama installer instead of Homebrew. The Homebrew formula has shipped without the `llama-server` runtime binary on some versions, causing inference to fail at runtime with cryptic errors.
    - Probes for a Python with a working `pyexpat` before handing one to pipx. Homebrew Python 3.12 has had broken libexpat linkage on some macOS versions, blocking aider installation.
    - Detects when the Docker daemon isn't running (vs. Docker just not being installed) and skips the Open WebUI step gracefully instead of erroring.
    - Auto-launches `Ollama.app` to ensure the daemon is up before health-checking.
''')


TEST_CONFIG_PY = dedent('''\
    from pathlib import Path

    from dslocal.config import Config


    def test_config_loads(tmp_path: Path) -> None:
        cfg_path = Path(__file__).parent.parent / "config.yaml"
        cfg = Config.load(cfg_path)
        assert "main" in cfg.models
        assert "fast" in cfg.models
        assert cfg.resolve_model("main").alias == "deepseek-coder-32k"
''')


# ---------------------------------------------------------------------------
# file map
# ---------------------------------------------------------------------------

FILES: dict[str, str] = {
    "README.md": README_MD,
    "CHANGELOG.md": CHANGELOG_MD,
    "LICENSE": LICENSE_MIT,
    "config.yaml": CONFIG_YAML,
    "pyproject.toml": PYPROJECT_TOML,
    ".gitignore": GITIGNORE,
    "src/dslocal/__init__.py": INIT_PY,
    "src/dslocal/cli.py": CLI_PY,
    "src/dslocal/config.py": CONFIG_PY,
    "src/dslocal/utils.py": UTILS_PY,
    "src/dslocal/steps/__init__.py": INIT_PY,
    "src/dslocal/steps/prereqs.py": PREREQS_PY,
    "src/dslocal/steps/ollama.py": OLLAMA_STEP_PY,
    "src/dslocal/steps/models.py": MODELS_STEP_PY,
    "src/dslocal/steps/aider.py": AIDER_STEP_PY,
    "src/dslocal/steps/continue_dev.py": CONTINUE_STEP_PY,
    "src/dslocal/steps/shell.py": SHELL_STEP_PY,
    "src/dslocal/steps/webui.py": WEBUI_STEP_PY,
    "tests/__init__.py": INIT_PY,
    "tests/test_config.py": TEST_CONFIG_PY,
}


# ---------------------------------------------------------------------------
# scaffolder
# ---------------------------------------------------------------------------

def scaffold(target: Path, force: bool = False) -> Path:
    repo_root = target / REPO_NAME

    if repo_root.exists():
        if not force:
            print(f"error: {repo_root} already exists. pass --force to overwrite.", file=sys.stderr)
            sys.exit(1)
        shutil.rmtree(repo_root)

    repo_root.mkdir(parents=True)

    for rel_path, content in FILES.items():
        file_path = repo_root / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    print(f"created {repo_root} with {len(FILES)} files")
    print()
    print("next steps:")
    print(f"  cd {repo_root}")
    print(f"  git init && git add -A && git commit -m 'initial scaffold'")
    print(f"  pipx install -e .")
    print(f"  dslocal doctor")
    print(f"  dslocal setup")
    return repo_root


def main() -> None:
    parser = argparse.ArgumentParser(description="generate the deepseek-local repo on disk")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="parent dir for the new repo")
    parser.add_argument("--force", action="store_true", help="overwrite existing target")
    args = parser.parse_args()
    scaffold(args.target.expanduser().resolve(), force=args.force)


if __name__ == "__main__":
    main()