# Test data

## Help Centre demo data (2026-09-17)

Created by `help_centre/screenshots/seed_demo.py` on a throwaway local database. Dates are relative to the day it runs.

| Login | Role | Notes |
|---|---|---|
| `office` | Administrator | Adds Olivia Brown during the capture run |
| `emma.wilson` | Teacher | Three past shifts; clocked in one hour ago; class today |
| `liam.chen` | Teacher | Three past shifts including a morning shift yesterday (09:24-12:41); class today |
| `sophie.nguyen` | Teacher | One manual entry; missed clock-out yesterday at 07:02 |
| `olivia.brown` | Teacher | Created by `capture.py` to prove a new teacher can clock in |

All passwords: `DemoPass-2026!`. All emails end in `@example.com`.

Campus: Claremont Studio at -31.9816097, 115.7883782, radius 100 m.
`capture.py` uses a phone location about 10 m away (verified) and one in Perth CBD about 7.6 km away (too far).
