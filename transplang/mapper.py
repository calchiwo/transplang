from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from transplang.analyzer import (
    SemanticModel, SemFunction, SemAssign, SemFor, SemReturn,
    SemPrint, SemCall, SemBinOp, SemName, SemLiteral, SemList,
)


@dataclass
class RustLiteral:
    value: Any
    typ: str


@dataclass
class RustName:
    name: str
    typ: str


@dataclass
class RustBinOp:
    op: str
    left: Any
    right: Any


@dataclass
class RustVecLiteral:
    elements: list


@dataclass
class RustCall:
    func: str
    args: list


@dataclass
class RustLet:
    name: str
    typ: str
    value: Any
    mutable: bool = False


@dataclass
class RustAssign:
    name: str
    value: Any


@dataclass
class RustFor:
    target: str
    iterable: Any
    body: list


@dataclass
class RustReturn:
    value: Any


@dataclass
class RustPrintln:
    args: list


@dataclass
class RustFunction:
    name: str
    params: list[tuple[str, str]]
    return_type: str
    body: list


@dataclass
class RustProgram:
    functions: list[RustFunction]
    main_body: list | None = None


def map_to_rust_ir(model: SemanticModel) -> RustProgram:
    functions = [_map_function(f) for f in model.functions]

    main_body: list | None = None
    if model.top_level:
        mutables = _collect_mutables(model.top_level)
        main_body = _map_stmts(model.top_level, declared=set(), mutables=mutables)

    return RustProgram(functions=functions, main_body=main_body)


def _map_function(fn: SemFunction) -> RustFunction:
    declared: set[str] = {p for p, _ in fn.params}
    mutables = _collect_mutables(fn.body)
    body = _map_stmts(fn.body, declared, mutables)
    return RustFunction(
        name=fn.name,
        params=fn.params,
        return_type=fn.return_type,
        body=body,
    )


def _collect_mutables(stmts: list) -> set[str]:
    seen: set[str] = set()
    mutables: set[str] = set()

    def _scan(stmts_inner: list) -> None:
        for stmt in stmts_inner:
            if isinstance(stmt, SemAssign):
                if stmt.target in seen:
                    mutables.add(stmt.target)
                seen.add(stmt.target)
                if _is_accumulated(stmt):
                    mutables.add(stmt.target)
            elif isinstance(stmt, SemFor):
                _scan(stmt.body)

    _scan(stmts)
    return mutables


def _map_stmts(stmts: list, declared: set[str], mutables: set[str]) -> list:
    result = []
    for s in stmts:
        result.extend(_map_stmt(s, declared, mutables))
    return result


def _map_stmt(stmt, declared: set[str], mutables: set[str]) -> list:
    if isinstance(stmt, SemAssign):
        val = _map_expr(stmt.value)
        typ = _rust_type_of(stmt.value)
        mutable = stmt.target in mutables
        if stmt.target not in declared:
            declared.add(stmt.target)
            return [RustLet(name=stmt.target, typ=typ, value=val, mutable=mutable)]
        else:
            return [RustAssign(name=stmt.target, value=val)]

    if isinstance(stmt, SemFor):
        declared.add(stmt.target)
        iterable = _map_expr(stmt.iterable)
        body = _map_stmts(stmt.body, declared, mutables)
        return [RustFor(target=stmt.target, iterable=iterable, body=body)]

    if isinstance(stmt, SemReturn):
        val = _map_expr(stmt.value) if stmt.value is not None else None
        return [RustReturn(value=val)]

    if isinstance(stmt, SemPrint):
        args = [_map_expr(a) for a in stmt.args]
        return [RustPrintln(args=args)]

    if isinstance(stmt, SemCall):
        args = [_map_expr(a) for a in stmt.args]
        return [RustCall(func=stmt.func, args=args)]

    raise ValueError(f"Unexpected semantic node in mapper: {type(stmt).__name__}")


def _map_expr(expr) -> Any:
    if isinstance(expr, SemLiteral):
        return RustLiteral(value=expr.value, typ=expr.typ)
    if isinstance(expr, SemName):
        return RustName(name=expr.name, typ=expr.typ)
    if isinstance(expr, SemBinOp):
        return RustBinOp(
            op=expr.op,
            left=_map_expr(expr.left),
            right=_map_expr(expr.right),
        )
    if isinstance(expr, SemList):
        return RustVecLiteral(elements=[_map_expr(e) for e in expr.elements])
    if isinstance(expr, SemCall):
        return RustCall(func=expr.func, args=[_map_expr(a) for a in expr.args])
    raise ValueError(f"Unexpected semantic expression in mapper: {type(expr).__name__}")


def _rust_type_of(expr) -> str:
    if isinstance(expr, SemLiteral):
        return expr.typ
    if isinstance(expr, SemName):
        return expr.typ
    if isinstance(expr, SemBinOp):
        return "i32"
    if isinstance(expr, SemList):
        return "Vec<i32>"
    if isinstance(expr, SemCall):
        return "i32"
    return "i32"


def _is_accumulated(stmt: SemAssign) -> bool:
    val = stmt.value
    if isinstance(val, SemBinOp):
        left = val.left
        if isinstance(left, SemName) and left.name == stmt.target:
            return True
    return False