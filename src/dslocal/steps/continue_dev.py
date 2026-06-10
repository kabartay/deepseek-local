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
