# Help Centre screenshots

The screenshots in `static/help_centre/img/` are generated, not taken by hand.
Regenerate them whenever the staff, facility, clock or timesheet screens change.

`capture.py` also works as an end-to-end test of teacher clock-in: it prints PASS or FAIL for
location checks, missed clock-outs, Perth times, exports and permissions.

## Steps

Use a throwaway database. Never point these scripts at production data.

```bash
# 1. Fresh local database with fake staff and clock records (dates are relative to today)
mv db.sqlite3 db.sqlite3.bak   # if you have a local database you want to keep
DEBUG=True WOOCOMMERCE_SYNC_ENABLED=False python manage.py migrate
DEBUG=True WOOCOMMERCE_SYNC_ENABLED=False python manage.py shell < help_centre/screenshots/seed_demo.py

# 2. Local server on the port the script expects
DEBUG=True WOOCOMMERCE_SYNC_ENABLED=False python manage.py runserver 127.0.0.1:8765

# 3. In another terminal: walk through the flows and capture screenshots
uv run --no-project --with playwright --with openpyxl python help_centre/screenshots/capture.py /tmp/help-shots

# 4. Resize and compress into the static folder (macOS sips + pngquant)
for f in /tmp/help-shots/shots/*.png; do
  name=$(basename "$f"); cp "$f" "static/help_centre/img/$name"
  case $name in clock-*|export-my-*) width=720 ;; *) width=1600 ;; esac
  sips --resampleWidth $width "static/help_centre/img/$name" >/dev/null
  pngquant --force --skip-if-larger --quality 70-90 --output "static/help_centre/img/$name" "static/help_centre/img/$name"
done
```

The seed script refuses to run unless `DEBUG=True` and the database has no students and no
staff outside `@example.com`. Demo logins use the password `DemoPass-2026!`.

If Playwright cannot find a browser, run `playwright install chromium` or set
`CHROMIUM_EXECUTABLE` to an existing Chromium binary.

The capture run adds records (a new teacher, clock-ins, manual entries), so reseed before
running it again.
