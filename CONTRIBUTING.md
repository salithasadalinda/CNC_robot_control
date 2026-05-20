# Contributing

Thanks for helping improve CNC Robot Control.

## Development Setup

Install Python 3.14 or later, then from the repository root:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
uv sync --extra dev
```

On macOS or Linux:

```bash
source .venv/bin/activate
uv sync --extra dev
```

## Run The App

```bash
uv run python -m tk_app.main
```

If needed, set `PYTHONPATH=src` before running.

## Checks

Run tests:

```bash
uv run pytest
```

Run lint:

```bash
uv run ruff check .
```

Both checks should pass before opening a pull request.

## Pull Requests

- Keep changes focused on one issue or feature.
- Include tests when changing behavior.
- Update `README.md` or docs when user-facing behavior changes.
- Do not commit local caches, virtual environments, or build artifacts.

## Releases

Release builds are created by the GitHub Actions `Release` workflow. Push a version tag to publish release assets:

```bash
git tag v0.1.0
git push origin v0.1.0
```
