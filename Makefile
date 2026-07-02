# AI Smile Simulator — dev entrypoints. `make check` must stay green (CLAUDE.md).
.PHONY: check backend-check app-check backend-install run-backend spike

# One-shot gate: lint + tests for backend, plus flutter analyze if flutter exists.
check: backend-check app-check

backend-check:
	cd backend && python -m ruff check . ../scripts && python -m ruff format --check . ../scripts && python -m pytest -q

# Flutter analyze is skipped gracefully when the toolchain isn't installed locally
# (CI always runs it — see .github/workflows/ci.yml).
app-check:
	@if command -v flutter >/dev/null 2>&1; then \
		cd app && flutter analyze ; \
	else \
		echo "flutter not found — skipping analyze (CI covers it)"; \
	fi

backend-install:
	cd backend && pip install -e ".[dev]"

run-backend:
	cd backend && uvicorn app.main:app --reload

# Phase 0 spike (needs FAL_API_KEY + the ml extra + model bundle; see scripts/phase0).
spike:
	cd scripts/phase0 && python run_spike.py --input ./selfies --output ./out --styles all
