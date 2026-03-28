# readme_gen

Generate README.md files from project analysis. Detects languages, deps, CI, Docker, tests.

## Usage

```bash
# Generate README from project directory
python3 readme_gen.py generate .
python3 readme_gen.py generate . --style detailed
python3 readme_gen.py generate . --style minimal -o README.md

# Generate badge markdown
python3 readme_gen.py badge .
python3 readme_gen.py badge . --badges ci,license,stars
```

## Detects
- Languages: Python, Node.js, Go, Rust
- Features: tests, CI, Docker, Makefile, license
- package.json scripts and description
- GitHub remote for badge URLs

## Zero dependencies. Single file. Python 3.8+.
