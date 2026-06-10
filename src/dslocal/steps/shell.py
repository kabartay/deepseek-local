from __future__ import annotations

from ..config import Config
from ..utils import expand, log, ok


HELPERS_HEADER = """\
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
    helpers_path.write_text("\n".join(lines) + "\n")
    ok(f"wrote {helpers_path}")

    source_line = f"source {helpers_path}"
    for rc in cfg.shell.rc_files:
        rc_path = expand(rc)
        if not rc_path.exists():
            continue
        content = rc_path.read_text()
        if source_line not in content:
            rc_path.write_text(content.rstrip() + f"\n{source_line}\n")
            ok(f"added source line to {rc_path}")
