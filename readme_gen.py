#!/usr/bin/env python3
"""readme_gen — Generate README.md files from project analysis.

Detects language, dependencies, scripts, and generates structured README.

Usage:
    readme_gen.py generate .
    readme_gen.py generate . --style minimal
    readme_gen.py generate . --style detailed
    readme_gen.py badge . --badges ci,license,version
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path


def detect_project(directory):
    """Analyze project directory."""
    info = {
        'name': os.path.basename(os.path.abspath(directory)),
        'languages': [],
        'files': [],
        'has_tests': False,
        'has_ci': False,
        'has_docker': False,
        'has_license': False,
        'scripts': {},
        'description': '',
        'dependencies': 0,
    }
    
    files = os.listdir(directory)
    info['files'] = files
    
    # Detect language
    if 'package.json' in files:
        info['languages'].append('JavaScript/Node.js')
        try:
            with open(os.path.join(directory, 'package.json')) as f:
                pkg = json.load(f)
            info['name'] = pkg.get('name', info['name'])
            info['description'] = pkg.get('description', '')
            info['scripts'] = pkg.get('scripts', {})
            deps = len(pkg.get('dependencies', {})) + len(pkg.get('devDependencies', {}))
            info['dependencies'] = deps
        except (json.JSONDecodeError, KeyError):
            pass
    
    if 'pyproject.toml' in files or 'setup.py' in files or 'requirements.txt' in files:
        info['languages'].append('Python')
    
    if 'go.mod' in files:
        info['languages'].append('Go')
    
    if 'Cargo.toml' in files:
        info['languages'].append('Rust')
    
    if 'Makefile' in files:
        info['has_makefile'] = True
    
    # Detect features
    info['has_tests'] = any(f.startswith('test') or f == 'tests' for f in files)
    info['has_ci'] = '.github' in files or '.gitlab-ci.yml' in files
    info['has_docker'] = 'Dockerfile' in files or 'docker-compose.yml' in files
    info['has_license'] = 'LICENSE' in files or 'LICENSE.md' in files
    
    # Get git remote for badges
    try:
        remote = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, cwd=directory
        ).stdout.strip()
        if 'github.com' in remote:
            # Extract owner/repo
            m = __import__('re').search(r'github\.com[:/](.+?)(?:\.git)?$', remote)
            if m:
                info['github'] = m.group(1)
    except Exception:
        pass
    
    return info


def generate_readme(info, style='standard'):
    lines = []
    name = info['name']
    desc = info['description']
    
    lines.append(f'# {name}\n')
    
    if desc:
        lines.append(f'{desc}\n')
    else:
        lines.append('TODO: Add project description\n')
    
    # Badges
    if info.get('github'):
        gh = info['github']
        if info['has_ci']:
            lines.append(f'![CI](https://github.com/{gh}/actions/workflows/ci.yml/badge.svg)')
        lines.append(f'![License](https://img.shields.io/github/license/{gh})')
        lines.append('')
    
    # Languages
    if info['languages']:
        lines.append(f'**Built with:** {", ".join(info["languages"])}\n')
    
    if style != 'minimal':
        # Prerequisites
        lines.append('## Prerequisites\n')
        for lang in info['languages']:
            if 'Python' in lang:
                lines.append('- Python 3.8+')
            elif 'Node' in lang:
                lines.append('- Node.js 18+')
            elif 'Go' in lang:
                lines.append('- Go 1.21+')
            elif 'Rust' in lang:
                lines.append('- Rust (stable)')
        lines.append('')
    
    # Installation
    lines.append('## Installation\n')
    lines.append('```bash')
    if info.get('github'):
        lines.append(f'git clone https://github.com/{info["github"]}.git')
        lines.append(f'cd {name}')
    
    if 'Python' in ' '.join(info['languages']):
        lines.append('pip install -e .')
    elif 'JavaScript' in ' '.join(info['languages']):
        lines.append('npm install')
    elif 'Go' in ' '.join(info['languages']):
        lines.append(f'go build -o {name} .')
    elif 'Rust' in ' '.join(info['languages']):
        lines.append('cargo build --release')
    else:
        lines.append('# TODO: add install steps')
    lines.append('```\n')
    
    # Usage
    lines.append('## Usage\n')
    lines.append('```bash')
    if info['scripts']:
        for name_s, cmd in list(info['scripts'].items())[:5]:
            lines.append(f'npm run {name_s}  # {cmd}')
    else:
        lines.append('# TODO: add usage examples')
    lines.append('```\n')
    
    if style == 'detailed':
        # Project structure
        lines.append('## Project Structure\n')
        lines.append('```')
        for f in sorted(info['files'])[:15]:
            if not f.startswith('.'):
                lines.append(f'├── {f}')
        lines.append('```\n')
        
        if info['has_tests']:
            lines.append('## Testing\n')
            lines.append('```bash')
            if 'Python' in ' '.join(info['languages']):
                lines.append('pytest')
            elif 'JavaScript' in ' '.join(info['languages']):
                lines.append('npm test')
            elif 'Go' in ' '.join(info['languages']):
                lines.append('go test ./...')
            lines.append('```\n')
    
    # License
    if info['has_license']:
        lines.append('## License\n')
        lines.append('See [LICENSE](LICENSE) for details.\n')
    
    return '\n'.join(lines)


def cmd_generate(args):
    info = detect_project(args.directory)
    readme = generate_readme(info, style=args.style)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(readme)
        print(f'Written to {args.output}')
    else:
        print(readme)


def cmd_badge(args):
    info = detect_project(args.directory)
    gh = info.get('github', 'owner/repo')
    
    badges = {
        'ci': f'![CI](https://github.com/{gh}/actions/workflows/ci.yml/badge.svg)',
        'license': f'![License](https://img.shields.io/github/license/{gh})',
        'version': f'![Version](https://img.shields.io/github/v/release/{gh})',
        'issues': f'![Issues](https://img.shields.io/github/issues/{gh})',
        'stars': f'![Stars](https://img.shields.io/github/stars/{gh})',
        'forks': f'![Forks](https://img.shields.io/github/forks/{gh})',
    }
    
    requested = args.badges.split(',') if args.badges else list(badges.keys())
    for name in requested:
        if name in badges:
            print(badges[name])


def main():
    p = argparse.ArgumentParser(description='README.md generator')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('generate', help='Generate README')
    s.add_argument('directory', default='.')
    s.add_argument('--style', choices=['minimal', 'standard', 'detailed'], default='standard')
    s.add_argument('--output', '-o')
    s.set_defaults(func=cmd_generate)

    s = sub.add_parser('badge', help='Generate badge markdown')
    s.add_argument('directory', default='.')
    s.add_argument('--badges', help='Comma-separated badge names')
    s.set_defaults(func=cmd_badge)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
