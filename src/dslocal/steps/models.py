from __future__ import annotations

import tempfile
from pathlib import Path

from ..config import Config
from ..utils import log, ok, run


MODELFILE_TEMPLATE = """\
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
