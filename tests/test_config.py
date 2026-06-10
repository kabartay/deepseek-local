from pathlib import Path

from dslocal.config import Config


def test_config_loads(tmp_path: Path) -> None:
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    cfg = Config.load(cfg_path)
    assert "main" in cfg.models
    assert "fast" in cfg.models
    assert cfg.resolve_model("main").alias == "deepseek-coder-32k"
