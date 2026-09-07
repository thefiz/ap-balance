from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import yaml


IGNORED_TOP_LEVEL_KEYS = {
    "name",
    "description",
    "game",
}


def load_yaml_configuration(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Player YAML must contain a top-level mapping.")

    config = {
        key: value
        for key, value in data.items()
        if key not in IGNORED_TOP_LEVEL_KEYS
    }

    return normalize_configuration(config)


def normalize_configuration(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): normalize_configuration(value[key])
            for key in sorted(value, key=lambda k: str(k))
        }

    if isinstance(value, list):
        return [normalize_configuration(item) for item in value]

    if isinstance(value, tuple):
        return [normalize_configuration(item) for item in value]

    return value


def configuration_fingerprint(config: dict[str, Any]) -> str:
    rendered = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def describe_configuration(path: Path) -> dict[str, Any]:
    normalized = load_yaml_configuration(path)
    return {
        "normalized": normalized,
        "fingerprint": configuration_fingerprint(normalized),
    }
