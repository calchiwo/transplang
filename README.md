# Transplang

**Translate software across programming languages.**

Transplang is an experimental developer tool that explores whether programs can be structurally analyzed and reconstructed in another programming language.

The current prototype focuses on a very small subset of Python and Rust to demonstrate the core idea.

---

## Installation

```bash
pip install transplang
```

Or install locally for development:

```bash
git clone https://github.com/calchiwo/transplang
cd transplang
pip install -e .
```

---

## Usage

```bash
transplang translate script.py --to rust
```

This will generate:

```
script.rs
```

The resulting Rust file can then be compiled normally.

Example:

```bash
rustc script.rs
./script
```

Write output to a file:

```bash
transplang translate script.py --to rust --output out.rs
rustc out.rs && ./out
```

---

## Example

Python input:

```python
def total(nums):
    s = 0
    for n in nums:
        s += n
    return s

print(total([1, 2, 3, 4]))
```

Generated Rust output

```rust
fn total(nums: Vec<i32>) -> i32 {
    let mut s: i32 = 0;
    for n in nums {
        s = s + n;
    }
    s
}

fn main() {
    println!("{}", total(vec![1, 2, 3, 4]));
}
```

---

## Supported Python constructs

| Construct | Notes |
|---|---|
| `def` functions | scalar and Vec parameters |
| Integer literals | mapped to `i32` |
| String literals | mapped to `&str` |
| List literals | mapped to `vec![…]` |
| Variable assignment | `let` / `let mut` |
| Augmented assignment | `+=`, `-=`, `*=`, `/=` |
| Arithmetic | `+`, `-`, `*`, `/` |
| `for x in y` loops | iterating over lists or Vec params |
| `return` | last return rendered as tail expression |
| `print()` | mapped to `println!` |

---

## Unsupported (rejected with a clear error)

- `import` statements
- `class` definitions
- `if` / `while` / `with` / `try`
- `async` / `await`
- Decorators
- Comprehensions
- Dicts, sets
- Attribute access (`obj.attr`)
- Subscript access (`x[i]`)

---

## Architecture

```
Python file
    ↓
ast.parse()          [parser.py]
    ↓
SemanticModel        [analyzer.py]
    ↓
RustIR               [mapper.py]
    ↓
Rust source          [rust_generator.py]
```

No runtime dependencies; stdlib only (`ast`, `argparse`, `pathlib`).

---

## Scope

Transplang currently focuses on a very small subset of Python and Rust.

The goal of this version is simple: demonstrate that structured translation between programming languages can work in practice when the surface area is tightly controlled.

Only a limited set of constructs are supported:

* functions
* integers
* lists
* loops
* basic arithmetic
* `print`

Anything outside this scope is intentionally rejected.

This constraint keeps the system deterministic and makes it easier to reason about translation correctness.

## Why start small

Real software systems are complex. Languages differ in runtime models, type systems, and ecosystem conventions.

Attempting to translate entire applications immediately would produce unreliable results.

Instead, Transplang begins with a narrow slice of functionality to test the core idea: that a program can be analyzed structurally and rebuilt in another language.

If this approach proves reliable on small programs, the surface area can expand over time.

## Long-term direction

Programs written in different languages ultimately describe the same underlying elements:

* state
* transformations
* control flow
* side effects

Transplang explores whether those elements can be extracted and reconstructed in another language environment.

The current prototype should be viewed as a minimal experiment around that idea.

---

## Limitations

This is an early prototype.

Current limitations include:

* Only Python → Rust translation
* Limited language constructs
* No support for external libraries
* No support for classes or modules

Complex programs will likely fail.

---

## Development

Run tests:

```bash
pip install pytest
pytest
```

Or without pytest:

```bash
python -m unittest discover -s tests
```

Project structure:

```
transplang/
├── cli.py            # Command-line interface; handles user commands and orchestrates the translation pipeline
├── parser.py         # Parses Python source code into an abstract syntax tree (AST)
├── analyzer.py       # Performs semantic analysis and extracts a structured representation of the program
├── mapper.py         # Maps analyzed program structures to equivalent constructs in the target language
└── rust_generator.py # Generates Rust source code from the mapped representation
```

Pipeline:

```
Python source
↓
AST
↓
semantic model
↓
Rust code generation
```

---

## Contributing

Contributions are welcome. Improvements in parsing, type inference, and Rust code generation are especially valuable.

---

## License

MIT

## Author

[Caleb Wodi](https://github.com/calchiwo)