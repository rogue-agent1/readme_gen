#!/usr/bin/env python3
"""readme_gen - Generate README.md from project structure and docstrings.

One file. Zero deps. Instant docs.

Usage:
  readme_gen.py .                      → generate README for current dir
  readme_gen.py . --style minimal      → short README
  readme_gen.py . --style full         → detailed README
  readme_gen.py . -o README.md         → write to file
  readme_gen.py . --license MIT        → include license badge
"""

import argparse
import ast
import glob
import json
import os
import re
import sys


LICENSES = {
    "MIT": "[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)",
    "Apache-2.0": "[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)",
    "GPL-3.0": "[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)",
}

LANG_INSTALL = {
    "python": "```bash\npython {main_file}\n```",
    "node": "```bash\nnpm install\nnode {main_file}\n```",
    "rust": "```bash\ncargo build --release\n```",
    "go": "```bash\ngo build\n```",
}


def detect_language(path: str) -> tuple[str, str]:
    if os.path.exists(os.path.join(path, "Cargo.toml")):
        return "rust", "Rust"
    if os.path.exists(os.path.join(path, "go.mod")):
        return "go", "Go"
    if os.path.exists(os.path.join(path, "package.json")):
        return "node", "Node.js"
    py_files = glob.glob(os.path.join(path, "*.py"))
    if py_files:
        return "python", "Python"
    return "unknown", "Unknown"


def get_python_info(path: str) -> dict:
    info = {"docstring": "", "functions": [], "classes": [], "main_file": ""}
    for py in sorted(glob.glob(os.path.join(path, "*.py"))):
        try:
            with open(py) as f:
                tree = ast.parse(f.read())
            ds = ast.get_docstring(tree)
            if ds and not info["docstring"]:
                info["docstring"] = ds
                info["main_file"] = os.path.basename(py)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    doc = ast.get_docstring(node) or ""
                    info["functions"].append({"name": node.name, "doc": doc.split("\n")[0]})
                elif isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node) or ""
                    info["classes"].append({"name": node.name, "doc": doc.split("\n")[0]})
        except (SyntaxError, ValueError):
            continue
    return info


def get_project_name(path: str) -> str:
    abs_path = os.path.abspath(path)
    # Check package.json
    pkg = os.path.join(abs_path, "package.json")
    if os.path.exists(pkg):
        try:
            with open(pkg) as f:
                return json.load(f).get("name", "")
        except Exception:
            pass
    return os.path.basename(abs_path)


def count_files(path: str) -> dict:
    counts = {}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext:
                counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1])[:10])


def generate(path: str, style: str = "standard", license_type: str = None) -> str:
    name = get_project_name(path)
    lang_key, lang_name = detect_language(path)
    lines = []

    # Title
    lines.append(f"# {name}\n")

    # License badge
    if license_type and license_type in LICENSES:
        lines.append(LICENSES[license_type] + "\n")

    # Description from docstring
    py_info = get_python_info(path) if lang_key == "python" else {}
    docstring = py_info.get("docstring", "")
    if docstring:
        # First line is usually "tool - description"
        first_line = docstring.split("\n")[0]
        if " - " in first_line:
            desc = first_line.split(" - ", 1)[1]
        else:
            desc = first_line
        lines.append(f"{desc}\n")

    # Usage from docstring
    if docstring and "Usage:" in docstring:
        usage_section = docstring[docstring.index("Usage:"):]
        lines.append("## Usage\n")
        lines.append(f"```\n{usage_section.strip()}\n```\n")
    elif lang_key in LANG_INSTALL:
        main = py_info.get("main_file", "") or f"{name}.py"
        lines.append("## Usage\n")
        lines.append(LANG_INSTALL[lang_key].format(main_file=main) + "\n")

    if style == "full":
        # File structure
        files = count_files(path)
        if files:
            lines.append("## Structure\n")
            for ext, count in files.items():
                lines.append(f"- `{ext}`: {count} file{'s' if count > 1 else ''}")
            lines.append("")

        # API (functions/classes)
        if py_info.get("functions") or py_info.get("classes"):
            lines.append("## API\n")
            for cls in py_info.get("classes", []):
                doc = f" — {cls['doc']}" if cls['doc'] else ""
                lines.append(f"### `{cls['name']}`{doc}\n")
            for fn in py_info.get("functions", [])[:20]:
                doc = f" — {fn['doc']}" if fn['doc'] else ""
                lines.append(f"- `{fn['name']}()`{doc}")
            lines.append("")

    # Requirements
    req = os.path.join(path, "requirements.txt")
    if os.path.exists(req):
        with open(req) as f:
            deps = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if deps:
            lines.append("## Requirements\n")
            for d in deps:
                lines.append(f"- `{d}`")
            lines.append("")
    elif lang_key == "python" and not any("requirements" in f for f in os.listdir(path)):
        lines.append("## Requirements\n")
        lines.append("Python 3.8+ (no external dependencies)\n")

    # License
    if license_type:
        lines.append(f"## License\n")
        lines.append(f"{license_type}\n")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Generate README.md from project structure")
    p.add_argument("path", default=".", nargs="?")
    p.add_argument("--style", choices=["minimal", "standard", "full"], default="standard")
    p.add_argument("--license", dest="license_type")
    p.add_argument("-o", "--output")
    args = p.parse_args()

    readme = generate(args.path, args.style, args.license_type)
    if args.output:
        with open(args.output, "w") as f:
            f.write(readme)
        print(f"Wrote {args.output}")
    else:
        print(readme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
