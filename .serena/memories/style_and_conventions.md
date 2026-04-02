# Code Style and Conventions

## Python
- **Line length**: 100 characters (ruff, flake8)
- **Formatting**: ruff format
- **Linting**: ruff (selected rules: N, YTT, S, B, FBT, EM, ISC, EXE, G, Q, SIM, PD, PL, TRY, NPY, RUF; ignores PLR, T20, ISC001, FBT001, FBT003)
- **Type hints**: Used throughout (pyright basic mode). Uses `float | np.floating`, `str | None`, etc.
- **Docstrings**: Short, lowercase docstrings on functions (e.g., `"""return a rounded value down"""`)
- **Imports**: Standard library first, then third-party, then local. Uses `from spinorama import logger` pattern.
- **File header**: GPLv3 license block at top of every file, preceded by `# -*- coding: utf-8 -*-`
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Testing**: pytest with class-based test organization (e.g., `class TestBrands:`)
- **Python version**: 3.12

## JavaScript
- **Formatting**: Prettier (single quotes, 4-space indent, 128 print width, trailing commas es5, semicolons)
- **Linting**: oxlint (primary), eslint
- **Module system**: ES modules (export/import)
- **File header**: GPLv3 license block in `// ` comments
- **Testing**: Vitest with jsdom environment
- **Naming**: camelCase for functions/variables, PascalCase for classes, UPPER_CASE for constants

## HTML Templates
- Handlebars for client-side templating
- Mako for server-side Python-generated HTML
- Bulma CSS framework

## Pre-commit Hooks
Configured via `.pre-commit-config.yaml`:
- trailing-whitespace, end-of-file-fixer, check-json, check-merge-conflict, detect-private-key
- csslint
- eslint + prettier (JS)
- ruff + ruff-format (Python)

## General
- GPLv3 license on all source files
- No default/fallback cases — crash hard on unknown values
