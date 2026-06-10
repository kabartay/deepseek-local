# deepseek-local

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-Apple%20Silicon-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A one-command bootstrap for a fully local, Claude-Code-equivalent coding stack on Apple Silicon.

Everything runs on your Mac. No API keys, no cloud, no data leaving your machine.

## What you get

| Tool | Role | Cloud equivalent |
|------|------|------------------|
| Ollama | Model runtime | — |
| DeepSeek-Coder-V2 16B Lite (32k ctx) | Main coding model | mid-tier cloud models |
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
git clone https://github.com/kabartay/deepseek-local
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

## Author

Built by [Mukharbek Organokov](https://www.organokov.com) · [@kabartay](https://github.com/kabartay)

## License

MIT
