# Common development commands for spinorama.

.DEFAULT_GOAL := help

PYTHON ?= $(CURDIR)/.venv/bin/python3
MATURIN ?= $(CURDIR)/.venv/bin/maturin
CARGO ?= cargo
NPM ?= npm
WASM_PACK ?= wasm-pack

ANNOTATIONS_MANIFEST := src/spinorama/annotations_rust/Cargo.toml
ANNOTATIONS_CRATE := src/spinorama/annotations_rust
WASM_BUILD_DIR := $(CURDIR)/build/website/annotations-rust
WASM_DIST_DIR := $(CURDIR)/dist/js/annotations-rust

DEV_HOST ?= 127.0.0.1
DEV_PORT ?= 8888
DEV_URL ?= http://localhost:$(DEV_PORT)
SPEAKER ?= RCF KX 32-A
PYTHONPATH := .:./src:./src/spinorama:./src/website:./scripts
PYTHON_LINT_PATHS ?= src scripts tests

.PHONY: help setup install-js rust rust-build rust-python rust-check rust-fmt \
	rust-clippy wasm build build-dev build-dev-full rebuild serve dev run \
	test test-rust test-python test-js test-annotations lint lint-python \
	lint-python-strict check annotations clean

help: ## Show available targets and configurable variables.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target> [VARIABLE=value]\n\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-18s %s\n", $$1, $$2} END {printf "\nExamples:\n  make dev\n  make annotations SPEAKER=\"RCF KX 32-A\"\n  make test-annotations\n"}' $(MAKEFILE_LIST)

setup: ## Install project dependencies and compile native extensions.
	./scripts/setup.sh

install-js: ## Install JavaScript dependencies from the lockfile.
	$(NPM) ci

rust: rust-python ## Rebuild Rust and install the Maturin Python extension.

rust-build: ## Build a release Python wheel with Maturin.
	$(MATURIN) build --release --manifest-path $(ANNOTATIONS_MANIFEST)

rust-python: ## Rebuild and install the annotation solver into the project venv.
	$(MATURIN) develop --release --manifest-path $(ANNOTATIONS_MANIFEST)

rust-check: ## Type-check the native Rust annotation solver.
	$(CARGO) check --manifest-path $(ANNOTATIONS_MANIFEST)

rust-fmt: ## Check Rust formatting without modifying files.
	$(CARGO) fmt --manifest-path $(ANNOTATIONS_MANIFEST) -- --check

rust-clippy: ## Lint the Rust annotation solver and deny warnings.
	$(CARGO) clippy --manifest-path $(ANNOTATIONS_MANIFEST) -- -D warnings

wasm: ## Force a release WASM rebuild and copy browser assets into dist.
	$(WASM_PACK) build $(ANNOTATIONS_CRATE) --target web --release --out-dir $(WASM_BUILD_DIR)
	mkdir -p $(WASM_DIST_DIR)
	cp $(WASM_BUILD_DIR)/annotations_rust.js $(WASM_DIST_DIR)/annotations_rust.js
	cp $(WASM_BUILD_DIR)/annotations_rust_bg.wasm $(WASM_DIST_DIR)/annotations_rust_bg.wasm

build: ## Build the complete optimized production website.
	$(PYTHON) scripts/generate_html.py --optim

build-dev: ## Build fast local assets and reuse existing speaker pages.
	$(PYTHON) scripts/generate_html.py --dev --sitedev=$(DEV_URL) --skip-speakers

build-dev-full: ## Build the complete local website, including speaker pages.
	$(PYTHON) scripts/generate_html.py --dev --sitedev=$(DEV_URL)

rebuild: rust wasm build-dev ## Rebuild native Rust, WASM, and local website assets.

serve: ## Serve dist with CORS and disabled caching on DEV_HOST:DEV_PORT.
	@test -d dist || { echo "dist is missing; run 'make build-dev' first"; exit 1; }
	@echo "Serving $(CURDIR)/dist at $(DEV_URL)"
	@cd dist && $(PYTHON) $(CURDIR)/scripts/debug_server.py --ip=$(DEV_HOST) --port=$(DEV_PORT)

dev: build-dev serve ## Build local assets and start the development server.

run: dev ## Alias for the local build-and-run workflow.

test: test-rust test-python test-js ## Run Rust, Python, and frontend test suites.

test-rust: ## Run Rust annotation solver unit tests.
	$(CARGO) test --manifest-path $(ANNOTATIONS_MANIFEST)

test-python: ## Run the complete Python test suite.
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests

test-js: ## Run the frontend Vitest suite once.
	$(NPM) test -- --run

test-annotations: test-rust ## Run focused native and Python annotation tests.
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest tests.test_spin_plot_annotations
	$(NPM) test -- --run src/website/annotation-layout.test.js

lint-python: ## Run CI-critical Ruff checks over Python source and tests.
	$(PYTHON) -m ruff check --select E9,F63,F7,F82 $(PYTHON_LINT_PATHS)

lint-python-strict: ## Run every Ruff rule configured in pyproject.toml.
	$(PYTHON) -m ruff check $(PYTHON_LINT_PATHS)

lint: rust-fmt rust-clippy lint-python ## Run Rust, Python, and JavaScript lint checks.
	$(NPM) run lint

check: lint test-annotations ## Run focused annotation QA.

annotations: rust-python ## Render one annotated CEA-2034 plot (set SPEAKER=...).
	$(PYTHON) scripts/plot_cea2034_annotations.py "$(SPEAKER)" --force

clean: ## Run the repository cleanup script.
	./scripts/cleanup.sh
