.PHONY: build lint proof security test

lint:
	uv run ruff check .

test:
	uv run coverage run -m unittest discover -s tests
	uv run coverage report -m

proof:
	uv run repo-loop proof . --json

build:
	uv build

security:
	uv export --locked --no-dev --no-emit-project --no-hashes | uvx pip-audit -r /dev/stdin
