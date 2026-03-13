from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SemLiteral:
    value: Any
    typ: str


@dataclass
class SemName:
    name: str
    typ: str = "i32"


@dataclass
class SemBinOp:
    op: str
    left: Any
    right: Any
    typ: str = "i32"


@dataclass
class SemCall:
    func: str
    args: list


@dataclass
class SemList:
    elements: list
    typ: str = "Vec<i32>"


@dataclass
class SemAssign:
    target: str
    value: Any


@dataclass
class SemReturn:
    value: Any


@dataclass
class SemFor:
    target: str
    iterable: Any
    body: list


@dataclass
class SemPrint:
    args: list


@dataclass
class SemFunction:
    name: str
    params: list[tuple[str, str]]
    return_type: str
    body: list


@dataclass
class SemanticModel:
    functions: list[SemFunction] = field(default_factory=list)
    top_level: list[Any] = field(default_factory=list)


_UNSUPPORTED_MSG = {
    ast.ClassDef:         "classes are not supported",
    ast.Import:           "import statements are not supported",
    ast.ImportFrom:       "import statements are not supported",
    ast.AsyncFunctionDef: "async functions are not supported",
    ast.While:            "while loops are not supported",
    ast.If:               "if statements are not supported",
    ast.With:             "with statements are not supported",
    ast.Try:              "try/except blocks are not supported",
    ast.Delete:           "del statements are not supported",
    ast.Global:           "global statements are not supported",
    ast.Nonlocal:         "nonlocal statements are not supported",
    ast.Lambda:           "lambda expressions are not supported",
    ast.DictComp:         "comprehensions are not supported",
    ast.ListComp:         "comprehensions are not supported",
    ast.SetComp:          "comprehensions are not supported",
    ast.GeneratorExp:     "generator expressions are not supported",
    ast.Dict:             "dicts are not supported",
    ast.Set:              "sets are not supported",
    ast.Attribute:        "attribute access is not supported",
    ast.Subscript:        "subscript access is not supported",
}


def _guard(node: ast.AST, label: str = "construct") -> None:
    msg = _UNSUPPORTED_MSG.get(type(node))
    if msg:
        raise ValueError(
            f"Unsupported {label} at line {getattr(node, 'lineno', '?')}: {msg}"
        )


def analyze(tree: ast.Module) -> SemanticModel:
    model = SemanticModel()
    analyzer = _Analyzer()

    for node in tree.body:
        _guard(node, "statement")
        if isinstance(node, ast.FunctionDef):
            model.functions.append(analyzer.visit_function(node))
        else:
            sem = analyzer.visit_stmt(node)
            if sem is not None:
                model.top_level.append(sem)

    return model


class _Analyzer:
    def __init__(self):
        self._vars: dict[str, str] = {}

    def visit_function(self, node: ast.FunctionDef) -> SemFunction:
        if node.decorator_list:
            raise ValueError(f"Decorators are not supported (line {node.lineno})")
        args = node.args
        if args.vararg or args.kwarg or args.defaults or args.kw_defaults:
            raise ValueError(
                f"Complex argument signatures are not supported (line {node.lineno})"
            )

        params_raw = [a.arg for a in args.args]
        vec_params = _detect_vec_params(node.body, set(params_raw))

        params = []
        self._vars = {}
        for p in params_raw:
            t = "Vec<i32>" if p in vec_params else "i32"
            params.append((p, t))
            self._vars[p] = t

        body = self._visit_body(node.body)
        ret_type = _infer_return_type(body)

        return SemFunction(name=node.name, params=params, return_type=ret_type, body=body)

    def _visit_body(self, stmts: list[ast.stmt]) -> list:
        result = []
        for s in stmts:
            _guard(s, "statement")
            sem = self.visit_stmt(s)
            if sem is not None:
                result.append(sem)
        return result

    def visit_stmt(self, node: ast.stmt):
        if isinstance(node, ast.Assign):
            return self._visit_assign(node)
        if isinstance(node, ast.AugAssign):
            return self._visit_aug_assign(node)
        if isinstance(node, ast.For):
            return self._visit_for(node)
        if isinstance(node, ast.Return):
            val = self.visit_expr(node.value) if node.value else None
            return SemReturn(value=val)
        if isinstance(node, ast.Expr):
            return self._visit_expr_stmt(node)
        _guard(node, "statement")
        return None

    def _visit_assign(self, node: ast.Assign) -> SemAssign:
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise ValueError(
                f"Only simple single-target assignments are supported (line {node.lineno})"
            )
        name = node.targets[0].id
        val = self.visit_expr(node.value)
        self._vars[name] = _type_of(val)
        return SemAssign(target=name, value=val)

    def _visit_aug_assign(self, node: ast.AugAssign) -> SemAssign:
        if not isinstance(node.target, ast.Name):
            raise ValueError(
                f"Only simple augmented assignments are supported (line {node.lineno})"
            )
        name = node.target.id
        op = _binop_symbol(node.op, node.lineno)
        left = SemName(name=name, typ=self._vars.get(name, "i32"))
        right = self.visit_expr(node.value)
        val = SemBinOp(op=op, left=left, right=right, typ="i32")
        self._vars[name] = "i32"
        return SemAssign(target=name, value=val)

    def _visit_for(self, node: ast.For) -> SemFor:
        if not isinstance(node.target, ast.Name):
            raise ValueError(
                f"Only simple for-loop targets are supported (line {node.lineno})"
            )
        if node.orelse:
            raise ValueError(f"for/else is not supported (line {node.lineno})")
        target = node.target.id
        self._vars[target] = "i32"
        iterable = self.visit_expr(node.iter)
        body = self._visit_body(node.body)
        return SemFor(target=target, iterable=iterable, body=body)

    def _visit_expr_stmt(self, node: ast.Expr):
        if not isinstance(node.value, ast.Call):
            raise ValueError(
                f"Bare expression statements other than function calls "
                f"are not supported (line {node.lineno})"
            )
        call = node.value
        func_name = _call_name(call)
        if func_name == "print":
            args = [self.visit_expr(a) for a in call.args]
            return SemPrint(args=args)
        args = [self.visit_expr(a) for a in call.args]
        return SemCall(func=func_name, args=args)

    def visit_expr(self, node: ast.expr) -> Any:
        _guard(node, "expression")
        if isinstance(node, ast.Constant):
            return _visit_constant(node)
        if isinstance(node, ast.Name):
            t = self._vars.get(node.id, "i32")
            return SemName(name=node.id, typ=t)
        if isinstance(node, ast.List):
            elems = [self.visit_expr(e) for e in node.elts]
            return SemList(elements=elems, typ="Vec<i32>")
        if isinstance(node, ast.BinOp):
            return self._visit_binop(node)
        if isinstance(node, ast.Call):
            return self._visit_call_expr(node)
        raise ValueError(
            f"Unsupported expression type {type(node).__name__} "
            f"at line {getattr(node, 'lineno', '?')}"
        )

    def _visit_binop(self, node: ast.BinOp) -> SemBinOp:
        op = _binop_symbol(node.op, node.lineno)
        left = self.visit_expr(node.left)
        right = self.visit_expr(node.right)
        return SemBinOp(op=op, left=left, right=right, typ="i32")

    def _visit_call_expr(self, node: ast.Call) -> SemCall:
        name = _call_name(node)
        args = [self.visit_expr(a) for a in node.args]
        return SemCall(func=name, args=args)


def _visit_constant(node: ast.Constant) -> SemLiteral:
    if isinstance(node.value, int):
        return SemLiteral(value=node.value, typ="i32")
    if isinstance(node.value, str):
        return SemLiteral(value=node.value, typ="&str")
    raise ValueError(
        f"Unsupported literal type {type(node.value).__name__} at line {node.lineno}"
    )


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    raise ValueError(
        f"Only simple function calls are supported (line {getattr(node, 'lineno', '?')})"
    )


def _binop_symbol(op: ast.operator, lineno: int) -> str:
    table = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
    sym = table.get(type(op))
    if sym is None:
        raise ValueError(f"Unsupported operator {type(op).__name__} at line {lineno}")
    return sym


def _type_of(sem) -> str:
    if isinstance(sem, SemLiteral):
        return sem.typ
    if isinstance(sem, SemName):
        return sem.typ
    if isinstance(sem, SemBinOp):
        return sem.typ
    if isinstance(sem, SemList):
        return sem.typ
    if isinstance(sem, SemCall):
        return "i32"
    return "i32"


def _detect_vec_params(body: list[ast.stmt], params: set[str]) -> set[str]:
    vec = set()
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
            if node.iter.id in params:
                vec.add(node.iter.id)
    return vec


def _infer_return_type(body: list) -> str:
    for stmt in body:
        if isinstance(stmt, SemReturn):
            if stmt.value is not None:
                return _type_of(stmt.value)
    return "i32"