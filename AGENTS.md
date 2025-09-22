# Repository Guidelines

## Project Structure & Module Organisation
- Keep domain logic inside modular Django apps: `core/`, `accounts/`, `students/`, `academics/`, `facilities/`, and `enrollment/`.
- Shared templates belong in `templates/`; static overrides live in `static/`, with collected assets in `staticfiles/`.
- Persist uploads under `media/` and place automation helpers (for example `test_notifications.py`, `check_*`) at the repository root.
- Record architectural or deployment decisions in `project_rules.md` or `DEPLOYMENT.md`; update `plans.md` as delivery milestones shift.

## Build, Test, and Development Commands
- `source .venv/bin/activate` loads the Python virtual environment; ensure `.env` is exported before running services.
- `python manage.py runserver` starts the local server at `http://127.0.0.1:8000` for manual checks.
- `python manage.py makemigrations` and `python manage.py migrate` keep the SQLite schema current; run both before committing model changes.
- `python manage.py test` executes the Django test suite; prefer targeted app labels (`python manage.py test students`) for quicker feedback.
- `npm install` followed by `npx playwright test` restores end-to-end coverage once Playwright specs return.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation, snake_case modules, and PascalCase models; favour descriptive method names.
- Templates lean on Bootstrap components with Australian English copy; avoid inline CSS or JavaScript and reuse includes from `templates/core/`.
- Document non-obvious business rules in concise comments; keep changes minimal and scoped.

## Testing Guidelines
- Store test modules alongside the features they exercise; refresh fixtures within each app’s `fixtures/` directory when data assumptions change.
- Aim for meaningful coverage around enrolment flows, student lifecycle events, and third-party integrations.
- Capture new manual end-to-end steps in `tests/e2e/README.md` until automated Playwright coverage resumes.

## Commit & Pull Request Guidelines
- Use Conventional Commit messages such as `feat: add teacher attendance export`; squash incidental work-in-progress commits locally.
- Every pull request needs a summary, linked issue or plan reference, screenshots or GIFs for UI updates, and notes on data migrations or configuration shifts.
- Highlight security-sensitive changes in `DEPLOYMENT.md` and coordinate token rotations through the Perth Art School accounts team.

## Security & Configuration Tips
- Load secrets from `.env` only; never commit credentials or generated keys.
- Sanity-check outbound integrations (WooCommerce, SES, Twilio) in the restricted staging environment before enabling them in production.
- Document operational handover steps privately and align with the repository’s access controls.
