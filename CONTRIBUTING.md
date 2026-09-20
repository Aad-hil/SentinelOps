# Contributing to SentinelOps

Thanks for contributing.

## Development setup

SentinelOps targets Python 3.13.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest pytest-cov ruff
```

For isolated tests, use the in-memory checkpoint backend:

```env
SENTINELOPS_CHECKPOINT_BACKEND=memory
```

## Before opening a pull request

Run:

```powershell
ruff check .
pytest
python -m evaluation.runner
```

Keep changes focused and update tests/documentation when behavior changes.

## Pull requests

Please describe:

- what changed;
- why it changed;
- how it was tested;
- whether benchmark results changed;
- whether configuration or security behavior changed.

Avoid committing credentials or local environment files.

## Architecture changes

For changes to agent responsibilities, graph routing, evaluation semantics, safety behavior, memory, or recovery planning, update the relevant documentation under `docs/`.
