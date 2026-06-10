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
