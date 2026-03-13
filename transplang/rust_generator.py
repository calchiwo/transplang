from __future__ import annotations

from transplang.mapper import (
    RustProgram, RustFunction, RustLet, RustAssign,
    RustFor, RustReturn, RustPrintln, RustCall,
    RustLiteral, RustName, RustBinOp, RustVecLiteral,
)

_INDENT = "    "


def generate_rust(program: RustProgram) -> str:
    parts: list[str] = []

    for fn in program.functions:
        parts.append(_gen_function(fn))

    if program.main_body is not None:
        parts.append(_gen_main(program.main_body))

    return "\n".join(parts) + "\n"


def _gen_function(fn: RustFunction) -> str:
    params = ", ".join(f"{n}: {t}" for n, t in fn.params)
    lines = [f"fn {fn.name}({params}) -> {fn.return_type} {{"]
    lines.extend(_gen_body(fn.body, depth=1, is_fn_body=True))
    lines.append("}")
    return "\n".join(lines)


def _gen_main(body: list) -> str:
    lines = ["fn main() {"]
    lines.extend(_gen_body(body, depth=1, is_fn_body=False))
    lines.append("}")
    return "\n".join(lines)


def _gen_body(stmts: list, depth: int, is_fn_body: bool) -> list[str]:
    lines: list[str] = []
    pad = _INDENT * depth

    tail_idx = -1
    if is_fn_body:
        for i in range(len(stmts) - 1, -1, -1):
            if isinstance(stmts[i], RustReturn):
                tail_idx = i
                break

    for i, stmt in enumerate(stmts):
        is_tail = is_fn_body and i == tail_idx
        lines.extend(_gen_stmt(stmt, depth, pad, tail_return=is_tail))

    return lines


def _gen_stmt(stmt, depth: int, pad: str, tail_return: bool = False) -> list[str]:
    if isinstance(stmt, RustLet):
        mut = "mut " if stmt.mutable else ""
        return [f"{pad}let {mut}{stmt.name}: {stmt.typ} = {_gen_expr(stmt.value)};"]

    if isinstance(stmt, RustAssign):
        return [f"{pad}{stmt.name} = {_gen_expr(stmt.value)};"]

    if isinstance(stmt, RustFor):
        lines = [f"{pad}for {stmt.target} in {_gen_expr(stmt.iterable)} {{"]
        lines.extend(_gen_body(stmt.body, depth + 1, is_fn_body=False))
        lines.append(f"{pad}}}")
        return lines

    if isinstance(stmt, RustReturn):
        if stmt.value is None:
            return [f"{pad}return;"]
        val = _gen_expr(stmt.value)
        if tail_return:
            return [f"{pad}{val}"]
        return [f"{pad}return {val};"]

    if isinstance(stmt, RustPrintln):
        return [f"{pad}{_gen_println(stmt)}"]

    if isinstance(stmt, RustCall):
        args = ", ".join(_gen_expr(a) for a in stmt.args)
        return [f"{pad}{stmt.func}({args});"]

    raise ValueError(f"Unknown RustIR statement: {type(stmt).__name__}")


def _gen_expr(expr) -> str:
    if isinstance(expr, RustLiteral):
        if expr.typ == "&str":
            return f'"{str(expr.value).replace(chr(34), chr(92) + chr(34))}"'
        return str(expr.value)

    if isinstance(expr, RustName):
        return expr.name

    if isinstance(expr, RustBinOp):
        left = _gen_expr(expr.left)
        right = _gen_expr(expr.right)
        if isinstance(expr.left, RustBinOp):
            left = f"({left})"
        if isinstance(expr.right, RustBinOp):
            right = f"({right})"
        return f"{left} {expr.op} {right}"

    if isinstance(expr, RustVecLiteral):
        elems = ", ".join(_gen_expr(e) for e in expr.elements)
        return f"vec![{elems}]"

    if isinstance(expr, RustCall):
        args = ", ".join(_gen_expr(a) for a in expr.args)
        return f"{expr.func}({args})"

    raise ValueError(f"Unknown RustIR expression: {type(expr).__name__}")


def _gen_println(stmt: RustPrintln) -> str:
    args = stmt.args
    if not args:
        return "println!();"
    if len(args) == 1:
        a = args[0]
        if isinstance(a, RustLiteral) and a.typ == "&str":
            return f'println!("{str(a.value).replace(chr(34), chr(92) + chr(34))}");'
        return f"println!(\"{{}}\", {_gen_expr(a)});"
    fmt = " ".join("{}" for _ in args)
    exprs = ", ".join(_gen_expr(a) for a in args)
    return f'println!("{fmt}", {exprs});'