# Spinorama Project Overview

## Purpose
Spinorama is an open-source (GPLv3) database and website for speaker and headphone frequency response measurements.
It helps users view, compare, and analyze audio equipment data (1000+ speakers, growing headphone database).

**Website**: https://www.spinorama.org
**API**: https://api.spinorama.org
**Author**: Pierre Aubert (pierre@spinorama.org)

## Tech Stack

### Python (backend / data processing)
- **Python 3.12** (required: >=3.12, <3.14)
- **Key libraries**: numpy, pandas, scipy, more-itertools
- **Web framework**: FastAPI + Gunicorn + Uvicorn (for the API)
- **Templating**: Mako (for HTML generation)
- **Build**: setuptools, wheel, Cython, maturin (Rust bindings)
- **Type checking**: pyright (basic mode)
- **Linting/formatting**: ruff
- **Testing**: pytest

### JavaScript (frontend)
- **Plotly.js** for charting
- **Bulma** CSS framework (compiled via sass)
- **Fuse.js** for search
- **Handlebars** for templating
- **Build**: Vite, Rollup, Terser
- **Testing**: Vitest (jsdom environment)
- **Linting**: oxlint, eslint
- **Formatting**: Prettier (single quotes, 4-space tabs, 128 print width, trailing commas es5)

### Infrastructure
- Hosted on OVH VPS (vps-c2ea73ea.vps.ovh.net)
- Nginx reverse proxy → Gunicorn/Uvicorn
- Supervisor for process management
- GitHub Actions CI (self-hosted runner)

## Codebase Structure

```
/                           # Root: entry point scripts (generate_*.py), config files
├── src/
│   ├── spinorama/          # Core library: scoring, filtering, loading, plotting (Python)
│   │   ├── compute_scores_rust/   # Rust bindings via maturin
│   │   └── compute_scores_cython/ # Cython optimized scoring
│   ├── website/            # Frontend: JS, CSS, HTML templates
│   ├── api/                # FastAPI REST API (main.py)
│   ├── importer/           # Data importers
│   ├── autoeq/             # Auto-EQ generation
│   ├── metahint/           # Metadata hinting
│   ├── metaedit/           # Metadata editing
│   ├── graphextract/       # Graph data extraction
│   └── dotli/              # dotli integration
├── datas/                  # Speaker & headphone metadata (Python dicts), measurement data
├── tests/                  # pytest test suite
├── scripts/                # Shell/Python utility scripts (deploy, compute, update)
├── dist/                   # Generated output (JSON, HTML)
├── conf/                   # Server configuration files
└── .github/workflows/      # CI: pythonapp.yml, webapp.yml
```

## Key Entry Points
- `generate_html.py` — Main website generator (uses Mako templates)
- `generate_graphs.py` — Graph generation
- `generate_meta.py` — Metadata generation
- `generate_stats.py` — Statistics generation
- `generate_headphone_meta.py` — Headphone metadata generation
- `generate_headphone_datas.py` — Headphone data generation
- `src/api/main.py` — FastAPI REST API (speaker + headphone endpoints)

## Environment
- `PYTHONPATH=src:src/website:src/spinorama:.`
- Virtual environment: `.venv/`
