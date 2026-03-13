import argparse
import sys
from pathlib import Path

from transplang.parser import parse_file
from transplang.analyzer import analyze
from transplang.mapper import map_to_rust_ir
from transplang.rust_generator import generate_rust

SUPPORTED_TARGETS = {"rust"}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="transplang",
        description="Translate a Python script to another language.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    translate = sub.add_parser("translate", help="Translate a Python source file.")
    translate.add_argument("source", type=Path, help="Path to the Python source file.")
    translate.add_argument(
        "--to",
        dest="target",
        required=True,
        choices=sorted(SUPPORTED_TARGETS),
        help="Target language (currently only 'rust').",
    )
    translate.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Write output to this file instead of stdout.",
    )
    return ap


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()

    if args.command == "translate":
        _cmd_translate(args)


def _cmd_translate(args: argparse.Namespace) -> None:
    source: Path = args.source

    if not source.exists():
        _die(f"Source file not found: {source}")
    if source.suffix != ".py":
        _die(f"Expected a .py file, got: {source}")

    try:
        tree = parse_file(source)
        semantic_model = analyze(tree)
        rust_ir = map_to_rust_ir(semantic_model)
        rust_code = generate_rust(rust_ir)
    except (SyntaxError, ValueError) as exc:
        _die(str(exc))

    if args.output:
        args.output.write_text(rust_code, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(rust_code)


def _die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)