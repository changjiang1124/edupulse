# Coding Standards & Architecture

## Toolchain
1.  **Package Manager**: Always use `uv`.
    *   Run commands: `uv run python manage.py ...`
    *   Install/Update: `uv add ...` or `uv sync`
2.  **Environment**: Assume `.venv` is managed by `uv`.

## Architectural Patterns
1.  **Service Layer**: Put complex business logic in `services.py` (or a `services/` package) inside the app.
    *   ❌ Avoid fat Models (keep them for data definitions).
    *   ❌ Avoid fat Views (keep them for request/response handling).
2.  **Multi-Tenancy**:
    *   The system is Organization-based.
    *   Always verify if queries need to be filtered by `organization=request.user.organization`.
3.  **App Boundaries**:
    *   `vehicles`: Core vehicle data.
    *   `contractor_vehicle_checks`: Inspection logic.
    *   `core`: Shared utilities.

## Testing
- Use `django.test.TestCase`.
- Leverage helpers in `core/tests.py`.
- New features *must* include unit tests.
