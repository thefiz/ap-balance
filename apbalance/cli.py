from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import inspect_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apbalance",
        description="Analyze Archipelago YAML progression structure."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser(
        "inspect",
        help="Generate and inspect one YAML/seed."
    )
    inspect.add_argument("yaml", type=Path, help="Player YAML file.")
    inspect.add_argument(
        "--archipelago",
        type=Path,
        required=True,
        help="Path to a local Archipelago source/install directory."
    )
    inspect.add_argument(
        "--apworld",
        type=Path,
        default=None,
        help="Optional custom .apworld to stage for generation."
    )
    inspect.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional deterministic generation seed."
    )
    inspect.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file. Defaults to stdout."
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "inspect":
        try:
            result = inspect_yaml(
                yaml_path=args.yaml,
                archipelago_path=args.archipelago,
                apworld_path=args.apworld,
                seed=args.seed,
            )
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        rendered = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(args.output)
        else:
            print(rendered)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
