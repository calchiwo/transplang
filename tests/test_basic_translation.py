from __future__ import annotations

import ast
import contextlib
import textwrap
import unittest

try:
    import pytest
    _has_pytest = True
except ImportError:
    _has_pytest = False

from transplang.analyzer import analyze
from transplang.mapper import map_to_rust_ir
from transplang.rust_generator import generate_rust


def translate(python_source: str) -> str:
    source = textwrap.dedent(python_source).strip()
    tree = ast.parse(source)
    model = analyze(tree)
    ir = map_to_rust_ir(model)
    return generate_rust(ir)


@contextlib.contextmanager
def assert_raises(exc_type):
    if _has_pytest:
        with pytest.raises(exc_type) as info:
            yield info
    else:
        try:
            yield None
            raise AssertionError(
                f"Expected {exc_type.__name__} but no exception was raised"
            )
        except exc_type:
            pass


class TestFunctionTranslation(unittest.TestCase):
    def test_total_function(self):
        rust = translate("""
            def total(nums):
                s = 0
                for n in nums:
                    s += n
                return s

            print(total([1, 2, 3, 4]))
        """)
        self.assertIn("fn total(", rust)
        self.assertIn("Vec<i32>", rust)
        self.assertIn("-> i32", rust)
        self.assertIn("let mut s: i32 = 0;", rust)
        self.assertIn("for n in nums", rust)
        self.assertIn("fn main()", rust)
        self.assertIn("println!", rust)

    def test_simple_return(self):
        rust = translate("""
            def double(x):
                return x * 2
        """)
        self.assertIn("fn double(x: i32) -> i32", rust)
        self.assertIn("x * 2", rust)

    def test_no_main_without_top_level(self):
        rust = translate("""
            def add(a, b):
                return a + b
        """)
        self.assertNotIn("fn main()", rust)

    def test_main_generated_for_top_level_print(self):
        rust = translate("print(42)")
        self.assertIn("fn main()", rust)
        self.assertIn("println!", rust)


class TestArithmetic(unittest.TestCase):
    def test_addition(self):
        self.assertIn("a + b", translate("def f(a, b):\n    return a + b"))

    def test_subtraction(self):
        self.assertIn("a - b", translate("def f(a, b):\n    return a - b"))

    def test_multiplication(self):
        self.assertIn("a * b", translate("def f(a, b):\n    return a * b"))

    def test_division(self):
        self.assertIn("a / b", translate("def f(a, b):\n    return a / b"))


class TestLiterals(unittest.TestCase):
    def test_integer_literal(self):
        self.assertIn("99", translate("def f():\n    return 99"))

    def test_string_print(self):
        self.assertIn('println!("hello")', translate('print("hello")'))

    def test_vec_literal(self):
        self.assertIn("vec![1, 2, 3]", translate("print([1, 2, 3])"))


class TestVariables(unittest.TestCase):
    def test_let_declaration(self):
        rust = translate("""
            def f():
                x = 5
                return x
        """)
        self.assertIn("let x: i32 = 5;", rust)

    def test_mut_on_accumulator(self):
        rust = translate("""
            def f(nums):
                s = 0
                for n in nums:
                    s += n
                return s
        """)
        self.assertIn("let mut s", rust)


class TestRejection(unittest.TestCase):
    def test_class_rejected(self):
        with assert_raises(ValueError):
            translate("class Foo:\n    pass")

    def test_import_rejected(self):
        with assert_raises(ValueError):
            translate("import os")

    def test_while_rejected(self):
        with assert_raises(ValueError):
            translate("while True:\n    pass")

    def test_if_rejected(self):
        with assert_raises(ValueError):
            translate("if True:\n    pass")

    def test_decorator_rejected(self):
        with assert_raises(ValueError):
            translate("""
                @staticmethod
                def f():
                    pass
            """)


class TestTailExpression(unittest.TestCase):
    def test_no_return_keyword_for_tail(self):
        rust = translate("""
            def add(a, b):
                return a + b
        """)
        lines = [l.strip() for l in rust.splitlines()]
        expr_lines = [l for l in lines if "a + b" in l]
        self.assertTrue(expr_lines, "Expected 'a + b' in output")
        self.assertFalse(expr_lines[0].startswith("return"))

    def test_single_return_functions_are_all_tails(self):
        rust = translate("""
            def always_zero():
                return 0

            def also_zero():
                return 0
        """)
        self.assertNotIn("return", rust)


class TestSnapshot(unittest.TestCase):
    def test_canonical_example(self):
        rust = translate("""
            def total(nums):
                s = 0
                for n in nums:
                    s += n
                return s

            print(total([1, 2, 3, 4]))
        """)
        for fragment in [
            "fn total(",
            "Vec<i32>",
            "-> i32",
            "let mut s",
            "for n in nums",
            "s = s + n",
            "fn main()",
            "println!",
            "vec![1, 2, 3, 4]",
        ]:
            self.assertIn(fragment, rust, msg=f"Missing: {fragment!r}\n{rust}")


if __name__ == "__main__":
    unittest.main()