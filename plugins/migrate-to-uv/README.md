# migrate-to-uv

A skill for migrating Python projects from Poetry, pipx, or pip/requirements.txt to uv.

## Features

- Converts Poetry `pyproject.toml` to PEP 621 standard format
- Handles dependency groups, scripts, extras, and build backends
- Provides command equivalents for Poetry → uv and pipx → uv
- Includes CI/CD migration examples (GitHub Actions, Docker)
- Covers manual migration steps for complex projects

## Usage

The skill is automatically loaded when Claude detects migration-related requests like:
- "migrate from Poetry to uv"
- "convert requirements.txt to uv"
- "replace pipx with uv"
- "modernize Python project packaging"

## Installation

```bash
claude plugin install migrate-to-uv@fprochazka-claude-code-plugins
```
