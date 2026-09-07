from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _validate_inputs(
    yaml_path: Path,
    archipelago_path: Path,
    apworld_path: Path | None,
) -> tuple[Path, Path, Path | None]:
    yaml_path = yaml_path.expanduser().resolve()
    archipelago_path = archipelago_path.expanduser().resolve()
    apworld_path = apworld_path.expanduser().resolve() if apworld_path else None

    if not yaml_path.is_file():
        raise FileNotFoundError(f"YAML not found: {yaml_path}")
    if yaml_path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"Expected .yaml or .yml: {yaml_path}")

    if not archipelago_path.is_dir():
        raise FileNotFoundError(f"Archipelago directory not found: {archipelago_path}")

    required = ["Generate.py", "Main.py", "BaseClasses.py", "worlds"]
    missing = [name for name in required if not (archipelago_path / name).exists()]
    if missing:
        raise ValueError(
            "The supplied Archipelago path does not look like an Archipelago "
            f"source/install tree. Missing: {', '.join(missing)}"
        )

    if apworld_path:
        if not apworld_path.is_file():
            raise FileNotFoundError(f"APWorld not found: {apworld_path}")
        if apworld_path.suffix.lower() != ".apworld":
            raise ValueError(f"Expected .apworld: {apworld_path}")

    return yaml_path, archipelago_path, apworld_path


def inspect_yaml(
    yaml_path: Path,
    archipelago_path: Path,
    apworld_path: Path | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    yaml_path, archipelago_path, apworld_path = _validate_inputs(
        yaml_path, archipelago_path, apworld_path
    )

    package_root = Path(__file__).resolve().parent
    worker_path = package_root / "_ap_worker.py"

    with tempfile.TemporaryDirectory(prefix="apbalance-") as temp:
        temp_path = Path(temp)
        players_path = temp_path / "Players"
        players_path.mkdir()
        staged_yaml = players_path / yaml_path.name
        shutil.copy2(yaml_path, staged_yaml)

        staged_apworld: Path | None = None
        custom_worlds = archipelago_path / "custom_worlds"

        if apworld_path:
            custom_worlds.mkdir(parents=True, exist_ok=True)
            staged_apworld = custom_worlds / apworld_path.name

            if staged_apworld.exists():
                raise FileExistsError(
                    f"Refusing to overwrite existing custom world: {staged_apworld}. "
                    "Remove --apworld if that world is already installed, or use a "
                    "separate Archipelago analysis tree."
                )

            shutil.copy2(apworld_path, staged_apworld)

        cmd = [
            sys.executable,
            str(worker_path),
            "--archipelago", str(archipelago_path),
            "--players", str(players_path),
        ]
        if seed is not None:
            cmd.extend(["--seed", str(seed)])

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            proc = subprocess.run(
                cmd,
                cwd=archipelago_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            if staged_apworld and staged_apworld.exists():
                staged_apworld.unlink()

        if proc.returncode != 0:
            details = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(
                "Archipelago generation/inspection failed."
                + (f"\n{details}" if details else "")
            )

        # The worker emits exactly one JSON document to stdout. AP logging is
        # directed to stderr in the worker.
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Worker returned invalid JSON.\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            ) from exc
