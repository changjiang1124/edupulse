# Repository Guidelines

## Project Structure & Module Organization
EduPulse is a modular Django project. Domain apps live in `core/`, `accounts/`, `students/`, `academics/`, `facilities/`, and `enrollment/`; extend the app that matches your feature. Shared templates stay under `templates/`, while static assets use `static/` (collected files in `staticfiles/`). Persist user uploads in `media/`, keep automation utilities such as `test_*.py` and `check_*` scripts at the repository root, and update `project_rules.md` or `DEPLOYMENT.md` when architectural decisions change.

## Build, Test, and Development Commands
Run work inside the project virtual environment (`source .venv/bin/activate`) and export settings via `.env`. Core routines:
```bash
python manage.py runserver          # local server on http://127.0.0.1:8000
python manage.py makemigrations     # generate model migrations
python manage.py migrate            # apply migrations to SQLite
python manage.py createsuperuser    # add staff admin accounts
python manage.py collectstatic      # stage assets before deployment
```
Use Node only for Playwright (`npm install` then `npx playwright test`) when e2e coverage is restored.

## Coding Style & Naming Conventions
Follow PEP 8: four-space indentation, snake_case modules, PascalCase models, and descriptive method names. Templates should lean on Bootstrap components with Australian English copy. Avoid inline CSS/JS; place overrides in `static/` and reuse shared includes from `templates/core/`. Document non-obvious business rules with concise comments.

## Testing Guidelines
Prefer `python manage.py test` for Django suites and keep test modules alongside the features they verify. Use the root-level diagnostic scripts (for example `python test_notifications.py`) to reproduce reported issues; refresh fixtures under the relevant app's `fixtures/` directory (create one if needed) when data assumptions change. Aim for meaningful coverage of enrollment flows, student lifecycle, and integrations before merging. Record new manual E2E steps in `tests/e2e/README.md` (create if needed) until automated Playwright specs return.

## Commit & Pull Request Guidelines
Match the existing Conventional Commit style: `<type>: <task>` in lowercase, e.g. `feat: add teacher attendance export`. Squash incidental WIP commits locally. Every PR should include a clear summary, linked issue or plan item, screenshots/GIFs for UI changes, and notes on data migrations. Update `plans.md` with progress and adjust `DEPLOYMENT.md` when operational steps change before requesting review.

## Environment & Security Notes
Secrets load from `.env`; never commit credentials or generated keys. Regenerate API tokens via the Perth Art School accounts and document handover steps privately. When integrating external APIs (WooCommerce, SES, Twilio), add configuration hints to `DEPLOYMENT.md` and sanity-check network calls in the restricted staging environment before enabling them in production.


## Response rule 
Respond me in Simplifed Chinese by default. 

Code, interface and comments in Australian English.

## Coding
遵循最小化修改代码的原则来修改代码。