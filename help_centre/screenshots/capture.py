"""Walk through teacher clock-in end to end and capture the Help Centre screenshots.

Checks the real behaviour as it goes (location checks, missed clock-outs, Perth times,
exports, permissions) and prints PASS/FAIL for each step.

Usage (see README.md in this folder):
    uv run --no-project --with playwright --with openpyxl python help_centre/screenshots/capture.py <out_dir>
Expects a local server on 127.0.0.1:8765 using a database seeded by seed_demo.py.
Set CHROMIUM_EXECUTABLE to use a specific Chromium build.
"""
import os
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765'
PW = 'DemoPass-2026!'
OUT = Path(sys.argv[1])
SHOTS = OUT / 'shots'
DL = OUT / 'downloads'
SHOTS.mkdir(parents=True, exist_ok=True)
DL.mkdir(exist_ok=True)
EXE = os.environ.get('CHROMIUM_EXECUTABLE') or None
PERTH = ZoneInfo('Australia/Perth')
TODAY = datetime.now(PERTH).date()


def day(days_ago, fmt='%d/%m/%Y'):
    return (TODAY - timedelta(days=days_ago)).strftime(fmt)


def iso(days_offset):
    return (TODAY + timedelta(days=days_offset)).isoformat()


WEEK = f'start_date={iso(-3)}&end_date={iso(3)}'
MONTH = f'start_date={iso(-14)}&end_date={iso(0)}'
NEAR = {'latitude': -31.98166, 'longitude': 115.78846, 'accuracy': 12}
FAR = {'latitude': -31.9505, 'longitude': 115.8605, 'accuracy': 12}

results = []


def check(name, condition, detail=''):
    results.append({'check': name, 'pass': bool(condition), 'detail': str(detail)[:300]})
    print(('PASS ' if condition else 'FAIL ') + name + (f'  [{detail}]' if detail and not condition else ''))


def near_times(text, moment, tolerance_min=2):
    return any((moment + timedelta(minutes=d)).strftime('%H:%M') in text for d in range(-tolerance_min, tolerance_min + 1))


def highlight(page, selector):
    page.locator(selector).first.evaluate("el => { el.style.outline = '3px solid #e11d48'; el.style.outlineOffset = '3px'; }")


def clear_highlights(page):
    page.evaluate("document.querySelectorAll('[style*=outline]').forEach(el => { el.style.outline = ''; el.style.outlineOffset = ''; })")


def shot(page, name, selector=None, clip_height=None, full=False):
    path = SHOTS / f'{name}.png'
    if selector:
        page.locator(selector).first.screenshot(path=str(path))
    elif clip_height:
        page.screenshot(path=str(path), clip={'x': 0, 'y': 0, 'width': page.viewport_size['width'], 'height': clip_height}, full_page=True)
    else:
        page.screenshot(path=str(path), full_page=full)


def login(page, username):
    page.goto(BASE + '/auth/login/')
    page.fill('input[name=username]', username)
    page.fill('input[name=password]', PW)
    page.click('button[type=submit]')
    page.wait_for_load_state('networkidle')


def wait_location(page):
    page.wait_for_function(
        "() => { const t = document.getElementById('locationTitle'); return t && !['Locating...', 'Verifying Location'].includes(t.textContent.trim()); }",
        timeout=20000,
    )
    page.wait_for_timeout(300)


def phone(browser, playwright, geolocation=None, grant=True):
    device = dict(playwright.devices['iPhone 13'])
    device.pop('default_browser_type', None)
    kwargs = dict(device, accept_downloads=True)
    if geolocation:
        kwargs['geolocation'] = geolocation
    if grant:
        kwargs['permissions'] = ['geolocation']
    ctx = browser.new_context(**kwargs)
    page = ctx.new_page()
    page.on('dialog', lambda d: d.accept())
    return ctx, page


def staff_url(page, full_name):
    page.goto(BASE + '/accounts/staff/?status=all')
    return page.locator(f'tr:has-text("{full_name}") a:has-text("View")').first.get_attribute('href')


def xlsx_rows(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    return [(ws.title, row) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) if any(c not in (None, '') for c in row)]


def submit_json(page, payload):
    return page.evaluate(
        """async (payload) => {
            const token = document.cookie.split('; ').find(c => c.startsWith('csrftoken=')).split('=')[1];
            const r = await fetch('/attendance/teacher/submit/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token}, body: JSON.stringify(payload)});
            return {status: r.status, body: await r.json()};
        }""",
        payload,
    )


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=EXE)

    # ---------------------------------------------------------------- Add a teacher
    admin_ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=2, accept_downloads=True)
    admin = admin_ctx.new_page()
    admin.on('dialog', lambda d: d.accept())
    login(admin, 'office')

    admin.goto(BASE + '/accounts/staff/')
    highlight(admin, 'a[href="/accounts/staff/add/"]')
    shot(admin, 'add-teacher-staff-list', clip_height=620)
    clear_highlights(admin)

    admin.click('a[href="/accounts/staff/add/"]')
    admin.fill('input[name=username]', 'olivia.brown')
    admin.fill('input[name=password1]', PW)
    admin.fill('input[name=password2]', PW)
    admin.fill('input[name=first_name]', 'Olivia')
    admin.fill('input[name=last_name]', 'Brown')
    admin.fill('input[name=email]', 'olivia.brown@example.com')
    admin.fill('input[name=phone]', '0400 000 000')
    admin.select_option('select[name=role]', 'teacher')
    highlight(admin, 'select[name=role]')
    shot(admin, 'add-teacher-form', selector='.card:has(input[name=username])')
    clear_highlights(admin)
    admin.click('button[type=submit]:has-text("Add Staff")')
    admin.wait_for_load_state('networkidle')
    check('admin: new teacher saved and listed', 'Olivia Brown' in admin.content() and admin.url.endswith('/accounts/staff/'), admin.url)
    shot(admin, 'add-teacher-saved', clip_height=620)

    # ---------------------------------------------------------------- Campus location
    admin.goto(BASE + '/facilities/')
    facility_edit = admin.locator('a[href$="/edit/"]').first.get_attribute('href')
    highlight(admin, f'a[href="{facility_edit}"]')
    shot(admin, 'campus-facility-list', clip_height=520)
    clear_highlights(admin)
    admin.goto(BASE + facility_edit)
    for sel in ['input[name=latitude]', 'input[name=longitude]', 'input[name=attendance_radius]']:
        highlight(admin, sel)
    shot(admin, 'campus-facility-edit', selector='.card:has(input[name=latitude])')
    clear_highlights(admin)
    admin.goto(BASE + '/facilities/add/')
    check('admin: a new campus form suggests a 100 m radius', admin.input_value('input[name=attendance_radius]') == '100', admin.input_value('input[name=attendance_radius]'))

    # ---------------------------------------------------------------- Teacher clocks in (Liam)
    liam_ctx, liam = phone(browser, p, NEAR)
    liam.goto(BASE + '/auth/login/')
    liam.fill('input[name=username]', 'liam.chen')
    liam.fill('input[name=password]', PW)
    shot(liam, 'clock-login')
    liam.click('button[type=submit]')
    liam.wait_for_load_state('networkidle')

    icon = liam.eval_on_selector('.navbar-toggler-icon', 'el => getComputedStyle(el).backgroundImage')
    check('phone: menu button icon is dark on the white bar', '30, 41, 59' in icon, icon[:120])
    liam.click('.navbar-toggler')
    liam.wait_for_selector('#navbarNav.show', timeout=5000)
    liam.locator('.navbar .dropdown-toggle').last.click()
    liam.wait_for_selector('.dropdown-menu.show', timeout=5000)
    check('phone: account menu opens and shows Clock In/Out', liam.locator('.dropdown-menu.show a[href="/clock/"]').is_visible())
    highlight(liam, '.dropdown-menu.show a[href="/clock/"]')
    liam.locator('.dropdown-menu.show a[href="/clock/"]').scroll_into_view_if_needed()
    shot(liam, 'clock-menu')

    liam.goto(BASE + '/clock/')
    wait_location(liam)
    check('teacher: location verified at the studio', 'Claremont Studio' in liam.inner_text('#locationTitle'), liam.inner_text('#locationDesc'))
    check('teacher: Clock In enabled', liam.is_enabled('#clockInBtn'))
    liam.locator('#classesList .class-item').first.click()
    shot(liam, 'clock-ready', selector='.attendance-panel')

    clock_in_moment = datetime.now(PERTH)
    liam.dblclick('#clockInBtn')  # a double tap must only record one clock-in
    liam.wait_for_selector('#clockOutBtn', timeout=15000)
    wait_location(liam)
    check('teacher: after clock in the page offers Clock Out', liam.is_enabled('#clockOutBtn'))
    check('teacher: recent activity in Perth time', near_times(liam.inner_text('.recent-activity-feed'), clock_in_moment))
    shot(liam, 'clock-clocked-in', selector='.attendance-panel')
    facility_id = int(facility_edit.strip('/').split('/')[-2])
    dup = submit_json(liam, {'clock_type': 'clock_in', 'latitude': NEAR['latitude'], 'longitude': NEAR['longitude'], 'facility_id': facility_id})
    check('guard: second clock-in rejected', dup['status'] == 400, dup)

    # ---------------------------------------------------------------- Teacher clocks out (Emma)
    emma_ctx, emma = phone(browser, p, NEAR)
    login(emma, 'emma.wilson')
    emma.goto(BASE + '/clock/')
    wait_location(emma)
    check('teacher: clocked-in teacher sees Clock Out', emma.locator('#clockOutBtn').count() == 1 and emma.is_enabled('#clockOutBtn'))
    shot(emma, 'clock-clock-out', selector='.attendance-panel')
    emma.click('#clockOutBtn')
    emma.wait_for_selector('#clockInBtn', timeout=15000)
    check('teacher: after clock out the page offers Clock In again', emma.locator('#clockInBtn').count() == 1)

    # ---------------------------------------------------------------- Problems: too far, blocked, offline, missed clock-out
    far_ctx, far = phone(browser, p, FAR)
    login(far, 'olivia.brown')
    far.goto(BASE + '/clock/')
    wait_location(far)
    far_desc = far.inner_text('#locationDesc')
    check('guard: 7 km away is blocked', 'Too far' in far_desc and not far.is_enabled('#clockInBtn'), far_desc)
    check('guard: Try again button is labelled', 'Try again' in far.inner_text('#retryLocationBtn'))
    shot(far, 'clock-too-far', selector='.attendance-panel')

    blocked_ctx, blocked = phone(browser, p, None, grant=False)
    login(blocked, 'olivia.brown')
    blocked.goto(BASE + '/clock/')
    wait_location(blocked)
    blocked_desc = blocked.inner_text('#locationDesc')
    check('guard: denied location explains how to fix it', 'phone settings' in blocked_desc and not blocked.is_enabled('#clockInBtn'), blocked_desc)
    shot(blocked, 'clock-location-blocked', selector='.attendance-panel')

    olivia_ctx, olivia = phone(browser, p, NEAR)
    login(olivia, 'olivia.brown')
    olivia.goto(BASE + '/clock/')
    wait_location(olivia)
    olivia_ctx.set_offline(True)
    olivia.click('#clockInBtn')
    olivia.wait_for_function("() => !document.getElementById('feedbackAlert').classList.contains('d-none')", timeout=10000)
    offline_msg = olivia.inner_text('#feedbackAlert')
    check('offline: clear message and the button works again (no frozen overlay)', 'No internet' in offline_msg and olivia.is_enabled('#clockInBtn'), offline_msg)
    olivia_ctx.set_offline(False)
    olivia.click('#clockInBtn')
    olivia.wait_for_selector('#clockOutBtn', timeout=15000)
    check('new teacher: can clock in straight after the account is created', olivia.locator('#clockOutBtn').count() == 1)

    sophie_ctx, sophie = phone(browser, p, NEAR)
    login(sophie, 'sophie.nguyen')
    sophie.goto(BASE + '/clock/')
    wait_location(sophie)
    check('missed clock-out: warning shown and Clock In offered', sophie.locator('#missedClockOutAlert').is_visible() and sophie.locator('#clockInBtn').count() == 1)
    shot(sophie, 'clock-missed-clock-out', selector='.attendance-panel')
    sophie.click('#clockInBtn')
    sophie.wait_for_selector('#clockOutBtn', timeout=15000)
    check('missed clock-out: teacher can still clock in for today', sophie.locator('#clockOutBtn').count() == 1)

    # ---------------------------------------------------------------- Teacher views and exports own hours
    liam.goto(BASE + f'/timesheet/?start_date={iso(-7)}&end_date={iso(0)}')
    liam.wait_for_load_state('networkidle')
    ts_text = liam.inner_text('body')
    check('teacher timesheet: yesterday shows 09:24 (Perth)', '09:24' in ts_text, re.findall(r'\d{2}:\d{2}', ts_text)[:10])
    check('teacher timesheet: today shows clock-in in Perth time', near_times(ts_text, clock_in_moment), re.findall(r'\d{2}:\d{2}', ts_text)[:10])
    highlight(liam, 'a:has-text("Export Current Range")')
    shot(liam, 'export-my-timesheet', clip_height=760)
    clear_highlights(liam)

    liam.goto(BASE + f'/timesheet/export/?{MONTH}')
    liam.wait_for_load_state('networkidle')
    highlight(liam, 'button.export-btn')
    shot(liam, 'export-my-export', selector='.form-card')
    clear_highlights(liam)
    with liam.expect_download(timeout=20000) as dl_info:
        liam.locator('button[type=submit]').filter(has_text='Export').first.click()
    path = DL / 'teacher-liam.xlsx'
    dl_info.value.save_as(path)
    rows = xlsx_rows(path)
    session = [r for _, r in rows if r and r[0] == day(1)]
    check('teacher export: yesterday 09:24-12:41 with numeric hours', session and session[0][2] == '09:24' and isinstance(session[0][6], float), session[:1])
    check('permission: teacher export has no other teacher', not any(n in json.dumps([list(map(str, r)) for _, r in rows]) for n in ('Emma', 'Sophie', 'Olivia')))

    emma_url = staff_url(admin, 'Emma Wilson')
    sophie_url = staff_url(admin, 'Sophie Nguyen')
    for path_ in ['/accounts/staff/timesheet/', emma_url, f'{emma_url}timesheet/export/?{MONTH}&format=excel']:
        resp = liam.request.get(BASE + path_, max_redirects=0)
        check(f'permission: teacher blocked from {path_.split("?")[0]}', resp.status in (302, 403, 404), resp.status)

    # ---------------------------------------------------------------- Admin checks hours
    admin.goto(BASE + f'/accounts/staff/timesheet/?{WEEK}')
    admin.wait_for_load_state('networkidle')
    overview = admin.inner_text('main')
    check('admin overview: lists all teachers with activity this week', all(n in overview for n in ('Liam Chen', 'Emma Wilson', 'Sophie Nguyen', 'Olivia Brown')))
    shot(admin, 'hours-overview', selector='main')

    admin.goto(BASE + f'{emma_url}?timesheet_start={iso(-3)}&timesheet_end={iso(3)}')
    admin.wait_for_load_state('networkidle')
    detail = admin.inner_text('main')
    check('admin staff timesheet: 2 days ago shows 15:20-17:10 (Perth)', '15:20' in detail and '17:10' in detail, re.findall(r'\d{2}:\d{2}', detail)[:8])
    shot(admin, 'hours-staff-timesheet', selector='.card:has(input[name=timesheet_start])')

    admin.goto(BASE + f'{sophie_url}?timesheet_start={iso(-3)}&timesheet_end={iso(3)}')
    admin.wait_for_load_state('networkidle')
    sophie_detail = admin.inner_text('main')
    check('admin: Sophie\'s forgotten shift is labelled Missing clock-out, today\'s is In Progress', 'Missing clock-out' in sophie_detail and 'In Progress' in sophie_detail)
    highlight(admin, f'tr:has-text("{day(1)}") a:has-text("Edit")')
    shot(admin, 'hours-missing-clock-out', selector='.card:has(input[name=timesheet_start])')
    clear_highlights(admin)

    edit_href = admin.locator(f'tr:has-text("{day(1)}") a:has-text("Edit")').first.get_attribute('href')
    admin.goto(BASE + edit_href)
    admin.wait_for_load_state('networkidle')
    admin.select_option('select[name=entry_mode]', 'full_session')
    admin.wait_for_timeout(300)
    if not admin.input_value('input[name=work_date]'):
        admin.fill('input[name=work_date]', iso(-1))
    admin.fill('input[name=session_start_time]', '07:02')
    admin.fill('input[name=session_end_time]', '11:30')
    optional = admin.get_by_text('Optional Details')
    if optional.count():
        optional.first.click()
        admin.wait_for_timeout(300)
    if admin.locator('textarea[name=manual_reason]').is_visible():
        admin.fill('textarea[name=manual_reason]', 'Forgot to clock out. Finish time confirmed by Sophie.')
    shot(admin, 'hours-edit-entry', selector='.card:has(select[name=entry_mode])')
    admin.locator('button[type=submit]').filter(has_text='Save Changes').first.click()
    admin.wait_for_load_state('networkidle')
    fixed = admin.inner_text('main')
    check('admin edit: missed shift now 07:02-11:30', '07:02' in fixed and '11:30' in fixed and 'Missing clock-out' not in fixed, admin.url)

    admin.goto(BASE + f'{sophie_url}attendance/manual/')
    admin.wait_for_load_state('networkidle')
    admin.fill('input[name=work_date]', iso(-3))
    admin.fill('input[name=session_start_time]', '09:00')
    admin.fill('input[name=session_end_time]', '12:00')
    optional = admin.get_by_text('Optional Details')
    if optional.count():
        optional.first.click()
        admin.wait_for_timeout(300)
    if admin.locator('textarea[name=manual_reason]').is_visible():
        admin.fill('textarea[name=manual_reason]', 'Paper sign-in sheet. Hours confirmed with the office.')
    shot(admin, 'hours-add-entry', selector='.card:has(select[name=entry_mode])')
    admin.get_by_role('button', name=re.compile('Save Timesheet Entry')).click()
    admin.wait_for_load_state('networkidle')
    added = admin.inner_text('main')
    check('admin manual entry: 3 days ago shown as 09:00-12:00', day(3) in added and '09:00' in added and '12:00' in added)

    # ---------------------------------------------------------------- Admin exports
    admin.goto(BASE + f'/accounts/staff/timesheet/?{MONTH}')
    admin.wait_for_load_state('networkidle')
    highlight(admin, 'a:has-text("Export Summary")')
    shot(admin, 'export-summary-button', clip_height=790)
    clear_highlights(admin)
    with admin.expect_download(timeout=20000) as dl_info:
        admin.click('a:has-text("Export Summary")')
    path = DL / 'admin-summary.xlsx'
    dl_info.value.save_as(path)
    rows = [r for _, r in xlsx_rows(path)]
    emma_row = next((r for r in rows if r and r[0] == 'Emma Wilson'), None)
    check('admin summary export: Emma total hours is a number', emma_row is not None and isinstance(emma_row[1], (int, float)), emma_row)

    highlight(admin, 'tr:has-text("Emma Wilson") a[href*="/timesheet/export/"]')
    shot(admin, 'export-staff-row', selector='.card:has(th:has-text("Staff Member"))')
    clear_highlights(admin)

    admin.goto(BASE + f'{emma_url}?timesheet_start={iso(-14)}&timesheet_end={iso(0)}')
    admin.wait_for_load_state('networkidle')
    with admin.expect_download(timeout=20000) as dl_info:
        admin.locator('a[href*="/timesheet/export/"]').first.click()
    path = DL / 'admin-emma.xlsx'
    dl_info.value.save_as(path)
    rows = [r for _, r in xlsx_rows(path)]
    header = next(r for r in rows if r and r[0] == 'Date')
    s15 = next((r for r in rows if r and r[0] == day(2, '%Y-%m-%d')), None)
    check('admin per-teacher export: 2 days ago is 15:20-17:10 with numeric hours', s15 is not None and s15[1] == '15:20' and s15[2] == '17:10' and isinstance(s15[header.index('Hours')], float), s15)

    browser.close()

(OUT / 'results.json').write_text(json.dumps(results, indent=2))
print(f"\n{sum(r['pass'] for r in results)}/{len(results)} checks passed")
