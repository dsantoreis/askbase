# Contributing to Askbase

Thanks for considering a contribution. Here's how to get started.

## Getting Started

1. Fork the repo and clone your fork
2. Create a branch from `main` (`git checkout -b fix/your-change`)
3. Install dependencies: `pip install -r requirements.txt` for the API, `npm install` in `frontend/`
4. Run locally with `docker compose up --build -d`

## Making Changes

- Keep PRs focused on a single concern
- Follow existing code style (black + ruff for Python, prettier for TypeScript)
- Add or update tests for behavioral changes
- Run the test suite before opening a PR

## PR Format

Structure your PR description:

```
**Problem:** What was broken or missing
**Root cause:** Why it was happening
**Fix:** What you changed
**Testing:** How you verified it works
```

## Development Setup

```bash
# Backend
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest

# Frontend
cd frontend
npm install
npm run dev

# Full stack
docker compose up --build -d
```

## Reporting Bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, browser)

## Code Review

All submissions go through review. We look for correctness, test coverage, clean code, and no unnecessary complexity.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
