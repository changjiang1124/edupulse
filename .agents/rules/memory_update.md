# Memory Maintenance Strategy

When completing a task, DO NOT just record "Done X".
Instead, record **Architectural Decisions** and **System Facts** in `.agents/memory.md`.

## When to Update Memory
1.  **New Patterns**: "We decided to place all PDF generation logic in `core/services/pdf.py`."
2.  **Schema Changes**: "Added `is_active` field to `Driver` model to support soft deletes."
3.  **Infrastructure**: "Switched to S3 for media storage; requires `AWS_ACCESS_KEY_ID` in env."
4.  **Workarounds**: "Temporarily disabling CSRF on `/api/webhooks/` until signature verification is fixed."

## Format
Appends entries to `.agents/memory.md` in this format:
- **[YYYY-MM-DD] Category**: The decision or fact. (Context if necessary).
