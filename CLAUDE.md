# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Semantix is a Python package for building searchable data for AI deep research. It's a PDM-managed project with a minimal structure in early development (Alpha stage).

## Development Commands

This project uses PDM (Python Dependency Manager) for package management:

- **Install dependencies**: `pdm install`
- **Run tests**: `pdm test` or `pytest tests/`
- **Lint code**: `pdm lint` (runs pre-commit hooks on all files)
- **Build package**: `pdm build`
- **Run documentation server**: `pdm doc`
- **Release**: `pdm release`

For multi-version testing, use Nox:
- **Test across Python versions**: `nox` (tests on Python 3.7-3.10)

## Project Structure

- **Source code**: `src/semantix/` - Main package code
- **Tests**: `tests/` - Pytest-based test suite
- **Documentation**: `docs/` - MkDocs documentation with Material theme
- **Release management**: `tasks/release.py` - Custom release automation
- **News fragments**: `news/` - Towncrier changelog fragments

## Code Quality & Tooling

The project enforces strict code quality standards:

- **Formatter**: Black (100 character line length)
- **Linter**: Ruff with comprehensive rule set (bugbear, comprehensions, pycodestyle, etc.)
- **Type checking**: MyPy with strict settings (disallow_untyped_defs, etc.)
- **Import sorting**: isort with Black profile
- **Pre-commit hooks**: Configured with ruff, black, mypy, and standard hooks

## Testing

- Uses pytest with filterwarnings for deprecation warnings
- Single test file currently: `tests/test_core.py`
- Test configuration in `pyproject.toml` under `[tool.pytest.ini_options]`

## Release Process

- Uses towncrier for changelog management
- Fragment types: feature, bugfix, doc, dep, removal, misc
- Changelog fragments go in `news/` directory
- Custom release script at `tasks/release.py`