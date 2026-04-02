# Suggested Commands

## Environment Setup
```bash
export PYTHONPATH=src:src/website:src/spinorama:.
source .venv/bin/activate
```

## Python

### Type checking
```bash
pyright
```

### Linting & Formatting
```bash
ruff check .                # lint
ruff format .               # format
```

### Testing
```bash
PYTHONPATH=.:./src:./src/spinorama:./src/website pytest tests
pytest tests/test_api.py    # API tests only
pytest tests -k "test_name" # specific test
```

## JavaScript

### Testing
```bash
npm test                    # runs vitest
npx vitest                  # alternative
```

### Linting
```bash
npx oxlint                  # primary JS linter
```

### Formatting
```bash
npx prettier --write "src/website/*.js"
```

## Website Generation
```bash
./generate_html.py --dev --sitedev=http://localhost:8888 --skip-speakers  # local dev
./generate_html.py --dev --optim --sitedev=https://dev.spinorama.org     # dev deploy
./generate_html.py --optim                                                # production
```

## Data Generation
```bash
python3.12 ./generate_meta.py           # speaker metadata
python3.12 ./generate_headphone_meta.py  # headphone metadata
python3.12 ./generate_graphs.py --update-cache  # graphs
```

## Deployment
```bash
./scripts/update_api_ovh.sh     # deploy API to OVH VPS
./scripts/update_prod_ovh.sh    # deploy website to OVH VPS
./scripts/update_dev.sh         # deploy to dev environment
```

## Pre-commit
```bash
pre-commit run --all-files
```

## Full Website Update Pipeline
```bash
./update_website.sh
```

## Git
- Main branch: `master`
- Development branch: `develop`
- CI triggers on push/PR to `develop`
