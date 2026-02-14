---
name: migrate-to-uv
description: |
  Migrate Python projects from Poetry, pipx, or pip/requirements.txt to uv.
  Converts pyproject.toml from Poetry format to PEP 621 standard, handles dependency groups,
  scripts, extras, build backends, and generates uv.lock. Use when user asks to:
  (1) migrate/convert from Poetry to uv, (2) replace pipx with uv tool,
  (3) modernize Python project packaging, (4) convert requirements.txt to uv,
  (5) switch to uv, or mentions "poetry to uv" or "migrate to uv".
---

# Migrate to uv

Convert Python projects from Poetry/pipx/pip to uv.

## Pre-Migration Assessment

**IMPORTANT: Before starting any migration, assess the project for blockers.** Read `pyproject.toml`, `setup.py` (if present), and the build configuration to check for the following. Report findings to the user before proceeding.

### Check 1: C/C++/Rust Extensions

Look for signs of compiled extensions:
- `setup.py` with `ext_modules`, `cffi`, `cython`, or `Extension()` calls
- Build dependencies like `setuptools`, `cffi`, `cython`, `pybind11`, `maturin`, `scikit-build-core`
- `.c`, `.cpp`, `.pyx`, or `.rs` source files referenced in the build

**If found:** `uv_build` does NOT support compiling C/C++/Rust extensions. The project must use a compatible build backend (`setuptools`, `scikit-build-core`, `maturin`, or `hatchling` with extension plugins). This is a non-trivial change — warn the user that the build backend swap may require significant effort and testing, especially for projects with complex `setup.py` logic.

### Check 2: Private Package Indexes

Look for `[[tool.poetry.source]]` sections or references to private PyPI mirrors.

**If found:** uv handles authentication differently from Poetry. Poetry uses `poetry config http-basic.<name> <user> <pass>`, while uv uses environment variables:
- `UV_INDEX_<NAME>_USERNAME` / `UV_INDEX_<NAME>_PASSWORD`
- Or `UV_INDEX_URL` with credentials embedded
- Or keyring integration

The migration tool won't convert auth config. The user needs to set up credentials separately for CI and local dev. See the "Private indexes" section below for format conversion.

### Check 3: Monorepo / Multiple pyproject.toml Files

Look for multiple `pyproject.toml` files, path dependencies between packages, or Poetry monorepo plugins (`poetry-plugin-monorepo`, `monoranger`).

**If found:** This is actually a good candidate for migration — uv workspaces handle monorepos much better than Poetry. But the migration is more involved than a single-package project. See the "Monorepo / Workspace Migration" section below.

### Check 4: Tox Configuration

Look for `tox.ini` or `[tool.tox]` sections.

**If found:** `tox` creates its own virtualenvs using pip by default. While tox can be configured to use uv, consider whether `uv run --python 3.X pytest` can replace tox environments entirely. This is a separate concern from the Poetry migration — tox can coexist with uv.

## Quick Start: Automated Migration

For most Poetry projects, use the `migrate-to-uv` tool:

```bash
uvx migrate-to-uv
```

**What it does:**
- Parses `[tool.poetry]` sections and converts to PEP 621 `[project]` format
- Converts Poetry version specifiers (`^`, `~`) to PEP 440 format (`>=`, `<`)
- Moves `[tool.poetry.group.*.dependencies]` to `[dependency-groups]`
- Converts `[tool.poetry.scripts]` to `[project.scripts]`
- Converts `[tool.poetry.extras]` to `[project.optional-dependencies]`
- Handles git/path/url dependencies → `[tool.uv.sources]`
- Preserves exact versions from `poetry.lock` when generating `uv.lock`
- Deletes `poetry.lock` after successful conversion

**After running, verify and test:**

```bash
rm -rf .venv
uv sync
uv run pytest
```

**Note:** The tool does NOT change the build backend. You may need to manually update `[build-system]` from `poetry-core` to `hatchling` (see step 6 below).

## Manual Migration Steps

Use manual migration for complex projects or when automated tool fails.

### 1. Convert Metadata

**Poetry → PEP 621:**

```toml
# BEFORE: [tool.poetry]
[tool.poetry]
name = "myapp"
version = "1.0.0"
description = "My app"
authors = ["John Doe <john@example.com>"]
license = "MIT"
readme = "README.md"

# AFTER: [project]
[project]
name = "myapp"
version = "1.0.0"
description = "My app"
authors = [{name = "John Doe", email = "john@example.com"}]
license = {text = "MIT"}
readme = "README.md"
```

### 2. Convert Dependencies

**Version specifier conversions:**
- `^1.2.3` → `>=1.2.3,<2.0.0` (caret = compatible)
- `~1.2.3` → `>=1.2.3,<1.3.0` (tilde = patch only)
- `python = "^3.10"` → `requires-python = ">=3.10,<4.0"`

```toml
# BEFORE
[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.26.0"
pandas = {version = "^2.0", extras = ["excel"]}

# AFTER
[project]
requires-python = ">=3.10,<4.0"
dependencies = [
    "requests>=2.26.0,<3.0.0",
    "pandas[excel]>=2.0,<3.0",
]
```

### 3. Convert Dev Dependencies

Poetry groups → `[dependency-groups]` (PEP 735):

```toml
# BEFORE
[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
ruff = "^0.1.0"

[tool.poetry.group.docs.dependencies]
sphinx = "^7.0"

# AFTER
[dependency-groups]
dev = [
    "pytest>=7.0,<8.0",
    "ruff>=0.1.0,<1.0",
]
docs = ["sphinx>=7.0,<8.0"]
```

### 4. Convert Scripts

```toml
# BEFORE
[tool.poetry.scripts]
myapp = "myapp.cli:main"

# AFTER
[project.scripts]
myapp = "myapp.cli:main"
```

### 5. Convert Extras (Optional Dependencies)

```toml
# BEFORE
[tool.poetry.dependencies]
psycopg2 = {version = "^2.9", optional = true}

[tool.poetry.extras]
postgresql = ["psycopg2"]

# AFTER
[project.optional-dependencies]
postgresql = ["psycopg2>=2.9,<3.0"]
```

### 6. Set Build Backend

Choose based on project type:

```toml
# Option 1: hatchling (recommended for most projects)
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/myapp"]  # if using src layout

# Option 2: uv_build (fastest, pure Python only — NO C/C++/Rust extensions)
[build-system]
requires = ["uv_build>=0.6,<0.7"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "myapp"     # use a plain string, NOT a list — list syntax breaks on older uv
module-root = ""          # "" for flat layout, "src" for src layout

# Option 3: setuptools (required for C extensions with ext_modules)
[build-system]
requires = ["setuptools>=61", "cffi"]  # add extension build deps
build-backend = "setuptools.build_meta"

# Option 4: scikit-build-core (for CMake-based C++ extensions)
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

# Option 5: maturin (for Rust extensions via PyO3)
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"
```

**WARNING:** `uv_build` does NOT support compiling C/C++/Rust extensions. If the project has compiled extensions, you MUST use `setuptools`, `scikit-build-core`, or `maturin` as the build backend.

**Do NOT use setuptools** with `license = {text = "MIT"}` — it has a known bug. Use `license = "MIT"` string form instead when using setuptools.

### 7. Convert Special Dependencies

**Git dependencies:**
```toml
# BEFORE
[tool.poetry.dependencies]
httpx = {git = "https://github.com/encode/httpx.git", tag = "0.27.0"}

# AFTER
[project]
dependencies = ["httpx"]

[tool.uv.sources]
httpx = {git = "https://github.com/encode/httpx", tag = "0.27.0"}
```

**Path dependencies:**
```toml
# BEFORE
[tool.poetry.dependencies]
mylib = {path = "../mylib", develop = true}

# AFTER
[project]
dependencies = ["mylib"]

[tool.uv.sources]
mylib = {path = "../mylib", editable = true}
```

**Private indexes:**
```toml
# BEFORE
[[tool.poetry.source]]
name = "private"
url = "https://pypi.company.com/simple"

# AFTER
[[tool.uv.index]]
name = "private"
url = "https://pypi.company.com/simple"
```

**Private index authentication** (Poetry uses `poetry config http-basic`, uv uses env vars):
```bash
# Option 1: Environment variables (recommended for CI)
export UV_INDEX_PRIVATE_USERNAME="user"
export UV_INDEX_PRIVATE_PASSWORD="token"

# Option 2: Credentials in URL (use with caution)
# [[tool.uv.index]]
# url = "https://user:token@pypi.company.com/simple"

# Option 3: keyring integration
uv --keyring-provider subprocess ...
```

### 8. Add uv Configuration

```toml
[tool.uv]
package = true  # if this is an installable package
```

### 9. Generate Lock and Test

```bash
rm poetry.lock
rm -rf .venv
uv lock
uv sync --all-extras --dev
uv run pytest
```

## Monorepo / Workspace Migration

If the project has multiple packages with Poetry path dependencies, convert to a uv workspace.

### 1. Create workspace root

Add a `pyproject.toml` at the repository root (or use an existing one):

```toml
[project]
name = "my-monorepo"
version = "0.0.0"
requires-python = ">=3.10"

[tool.uv.workspace]
members = ["packages/*", "services/*"]

[tool.uv]
package = false  # the root is not an installable package
```

### 2. Convert each member package

Run the migration (automated or manual) for each `pyproject.toml` individually. Convert Poetry path dependencies to uv sources:

```toml
# BEFORE (in services/service-a/pyproject.toml)
[tool.poetry.dependencies]
lib-core = {path = "../../packages/lib-core", develop = true}

# AFTER
[project]
dependencies = ["lib-core"]

[tool.uv.sources]
lib-core = {workspace = true}
```

### 3. Generate unified lockfile

```bash
# Remove per-package Poetry lockfiles
find . -name "poetry.lock" -delete
rm -rf .venv

# Generate single workspace lockfile at the root
uv lock
uv sync --all-packages
```

**Key differences from Poetry monorepos:**
- Single `uv.lock` at workspace root instead of per-package lockfiles
- `uv sync` installs all workspace members in one environment
- Cross-package dependencies use `{workspace = true}` instead of relative paths
- No need for monorepo plugins (`poetry-plugin-monorepo`, `monoranger`)

## Converting pipx to uv tool

Replace pipx installations with uv:

```bash
# BEFORE
pipx install black
pipx install ruff

# AFTER
uv tool install black
uv tool install ruff

# For editable local installs (git pull updates automatically)
uv tool install -e .
```

## Converting requirements.txt

```bash
# Generate pyproject.toml from requirements.txt
uv init
uv add $(cat requirements.txt | grep -v '^#' | grep -v '^$' | tr '\n' ' ')

# Or keep requirements.txt and use uv pip
uv pip install -r requirements.txt
```

## Command Equivalents

| Poetry | uv |
|--------|-----|
| `poetry install` | `uv sync` |
| `poetry install --with dev` | `uv sync --dev` |
| `poetry add requests` | `uv add requests` |
| `poetry add pytest --group dev` | `uv add pytest --dev` |
| `poetry remove requests` | `uv remove requests` |
| `poetry run pytest` | `uv run pytest` |
| `poetry build` | `uv build` |
| `poetry publish` | `uv publish` |
| `poetry lock` | `uv lock` |
| `poetry update` | `uv lock --upgrade` |

| pipx | uv |
|------|-----|
| `pipx install pkg` | `uv tool install pkg` |
| `pipx run pkg` | `uvx pkg` |
| `pipx list` | `uv tool list` |
| `pipx upgrade pkg` | `uv tool upgrade pkg` |
| `pipx uninstall pkg` | `uv tool uninstall pkg` |

## CI/CD Updates

**GitHub Actions:**
```yaml
# BEFORE
- run: pip install poetry
- run: poetry install

# AFTER
- uses: astral-sh/setup-uv@v5
- run: uv sync --frozen
```

**Docker:**
```dockerfile
# BEFORE
RUN pip install poetry && poetry install --no-root

# AFTER
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen
```

## README Updates

Update installation instructions:

```markdown
## Installation

Clone the repository, then:

\`\`\`bash
uv tool install -e .
\`\`\`

Updates are automatic after `git pull`.
```

## Cleanup Checklist

After migration:
- [ ] Delete `poetry.lock`
- [ ] Delete old `.venv`
- [ ] Remove `[tool.poetry]` sections from pyproject.toml
- [ ] Remove `[build-system]` with `poetry-core`
- [ ] Update README installation instructions
- [ ] Update CI/CD pipelines
- [ ] Update Dockerfile if applicable
- [ ] Run full test suite
- [ ] Commit changes
