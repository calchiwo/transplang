import ast
from pathlib import Path


def parse_file(path: Path) -> ast.Module:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SyntaxError(f"Syntax error in {path}: {exc}") from exc
    return tree