from pathlib import Path

from apbalance.configuration import (
    load_yaml_configuration,
    configuration_fingerprint,
)


def test_configuration_ignores_identity_fields(tmp_path: Path):
    path = tmp_path / "player.yaml"
    path.write_text(
        """
name: Alice
game: Test Game
description: Example
goal: ganon
key_shuffle: true
""".strip(),
        encoding="utf-8",
    )

    config = load_yaml_configuration(path)
    assert "name" not in config
    assert "game" not in config
    assert "description" not in config
    assert config["goal"] == "ganon"
    assert config["key_shuffle"] is True


def test_configuration_fingerprint_stable():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert configuration_fingerprint(a) == configuration_fingerprint(b)
