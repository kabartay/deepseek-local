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
