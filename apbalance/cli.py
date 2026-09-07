from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import inspect_yaml
from .simulation import analyze_yaml
from .configuration import describe_configuration
from .group import analyze_group


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


    analyze = subparsers.add_parser(
        "analyze",
        help="Run repeated generation and aggregate statistics."
    )
    analyze.add_argument("yaml", type=Path, help="Player YAML file.")
    analyze.add_argument(
        "--archipelago",
        type=Path,
        required=True,
        help="Path to a local Archipelago source/install directory."
    )
    analyze.add_argument(
        "--apworld",
        type=Path,
        default=None,
        help="Optional custom .apworld to stage for generation."
    )
    analyze.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of generated seeds. Default: 100."
    )
    analyze.add_argument(
        "--base-seed",
        type=int,
        default=None,
        help="Optional seed controlling the list of generation seeds."
    )
    analyze.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel simulation workers. Default: 1."
    )
    analyze.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file. Defaults to stdout."
    )



    group = subparsers.add_parser(
        "group",
        help="Analyze a folder of player YAMLs as repeated multiworlds."
    )
    group.add_argument("players", type=Path, help="Directory containing player YAML files.")
    group.add_argument(
        "--archipelago",
        type=Path,
        required=True,
        help="Path to a local Archipelago source/install directory."
    )
    group.add_argument(
        "--apworld",
        type=Path,
        action="append",
        default=[],
        help="Optional custom .apworld. Repeat for multiple custom worlds."
    )
    group.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of generated multiworld seeds. Default: 100."
    )
    group.add_argument(
        "--base-seed",
        type=int,
        default=None,
        help="Optional seed controlling the generated seed list."
    )
    group.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file. Defaults to stdout."
    )

    config = subparsers.add_parser(
        "config",
        help="Extract normalized YAML configuration and fingerprint."
    )
    config.add_argument("yaml", type=Path, help="Player YAML file.")
    config.add_argument(
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


    if args.command == "analyze":
        try:
            result = analyze_yaml(
                yaml_path=args.yaml,
                archipelago_path=args.archipelago,
                apworld_path=args.apworld,
                samples=args.samples,
                base_seed=args.base_seed,
                workers=args.workers,
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



    if args.command == "group":
        try:
            result = analyze_group(
                players_path=args.players,
                archipelago_path=args.archipelago,
                apworld_paths=args.apworld,
                samples=args.samples,
                base_seed=args.base_seed,
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

    if args.command == "config":
        try:
            result = {
                "schema_version": 1,
                "analyzer_version": "0.9.0",
                "mode": "configuration",
                "configuration": describe_configuration(args.yaml),
            }
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
