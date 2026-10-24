.PHONY: verify

verify:
	uv run --frozen python scripts/validate_catalog.py
	uv run --frozen python -m unittest discover -s evals/tests -v
