.PHONY: verify

verify:
	uv run --frozen python scripts/validate_catalog.py
	uv run --frozen python skills/verify-work/scripts/boundary_checks.py ci --dialect github --file .github/workflows/ci.yml
	uv run --frozen python -m unittest discover -s evals/tests -v
