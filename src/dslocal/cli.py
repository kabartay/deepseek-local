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
