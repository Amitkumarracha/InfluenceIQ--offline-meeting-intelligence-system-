"""Load and provide access to config.yaml and environment variables."""

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
_DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
_config: dict[str, Any] | None = None


def load_env(env_path: Path | None = None) -> None:
    """Load environment variables from a .env file if it exists."""
    path = env_path or _DEFAULT_ENV_PATH
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            # Set in os.environ if not already defined
            if key and key not in os.environ:
                os.environ[key] = val


# Load .env variables on module import
load_env()


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load config from disk (cached after first load)."""
    global _config
    if _config is None:
        config_path = path or _DEFAULT_CONFIG_PATH
        with open(config_path, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    return _config


def get(key_path: str, default: Any = None) -> Any:
    """Retrieve a nested config value using dot notation e.g. 'audio.sample_rate'."""
    cfg = load_config()
    keys = key_path.split(".")
    val: Any = cfg
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return val

