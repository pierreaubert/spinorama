# Task Completion Checklist

When a task is completed, run the following checks as appropriate:

## Python changes
1. `ruff check .` — lint
2. `ruff format .` — format
3. `pyright` — type check
4. `PYTHONPATH=.:./src:./src/spinorama:./src/website pytest tests` — run tests

## JavaScript changes
1. `npx oxlint` — lint
2. `npx prettier --write "src/website/*.js"` — format
3. `npm test` — run vitest tests

## API changes
1. Run `pytest tests/test_api.py` specifically
2. Verify OpenAPI schema is correct

## Pre-commit (before committing)
1. `pre-commit run --all-files`

## Notes
- CI runs on self-hosted runner, triggered on push/PR to `develop` branch
- Python CI: installs deps, checks metadata, builds cython/rust, runs pytest
- JS CI: npm install, npm ci, npm test
