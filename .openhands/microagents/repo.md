---
name: repo
type: repo
agent: CodeActAgent
---

This repository contains the Agent-Computer Interface (ACI) for OpenHands, providing essential tools and interfaces for AI agents to interact with computer systems for software development tasks. The core functionality is implemented in Python and includes code editing, linting, and utility functions.

## General Setup:

Before pushing any changes, ensure all checks pass:
* Run pre-commit hooks: `pre-commit run --files openhands_aci/**/* tests/**/* --config ./dev_config/python/.pre-commit-config.yaml`
* Run tests: `poetry run pytest`

The pre-commit hooks include:
- Code formatting with Ruff
- Type checking with MyPy
- YAML validation
- Trailing whitespace and EOF fixes
- pyproject.toml validation and formatting

## Repository Structure
Core Code:
- Located in the `openhands_aci` directory
  - `editor/`: Code editing functionality
  - `linter/`: Code linting capabilities (tree-sitter based)
  - `utils/`: Utility functions (shell commands, diff generation, logging)

Testing:
- Located in the `tests` directory
  - `tests/unit/`: Unit tests
  - `tests/integration/`: Integration tests
  - Run tests with: `poetry run pytest`

Configuration:
- `dev_config/python/`: Development configuration files
  - `.pre-commit-config.yaml`: Pre-commit hook configuration
  - `ruff.toml`: Ruff linter configuration
  - `mypy.ini`: MyPy type checker configuration

CI/CD:
- GitHub Actions workflows in `.github/workflows/`
  - `lint.yml`: Code linting checks
  - `py-unit-tests.yml`: Unit tests
  - `py-intg-tests.yml`: Integration tests
  - `pypi-release.yml`: Package publishing to PyPI
