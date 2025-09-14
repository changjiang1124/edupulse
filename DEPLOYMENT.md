# EduPulse Deployment Guide

## Overview
This document outlines the steps required to deploy EduPulse in a new environment.

## Prerequisites
- Python 3.8+
- pip package manager
- Git
- Web server (Apache/Nginx) for production
- Database (SQLite for development, PostgreSQL/MySQL recommended for production)

## Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd edupulse
```

### 2. Create Virtual Environment
```bash
python -m venv .venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the project root with the following variables:

```env
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=edupulse.perthartschool.com.au,www.perthartschool.com.au,localhost,127.0.0.1

# Database (if using PostgreSQL/MySQL)
# DATABASE_URL=postgresql://user:password@host:port/database

# SMTP Email (AWS SES or other SMTP)
SMTP_SERVER=email-smtp.ap-southeast-2.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password

# SMS Configuration (Optional - Twilio)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=your-twilio-number

# WooCommerce Integration (Future)
WOOCOMMERCE_URL=https://perthartschool.com.au
WOOCOMMERCE_CONSUMER_KEY=your-consumer-key
WOOCOMMERCE_CONSUMER_SECRET=your-consumer-secret
```

### 5. Directory Structure Setup

**Important**: The following directories will be created automatically by Django when needed, but you should ensure proper permissions:

#### Media Directories (Auto-created)
Django will automatically create these directories when files are uploaded:
- `media/` (root media directory)
- `media/uploads/` (general uploads)
- `media/uploads/courses/descriptions/YYYY/MM/` (course description images, organized by date)
- `media/uploads/courses/thumbnails/` (course thumbnail images - future feature)

#### Static Files Directory
```bash
# Create static files directory for production
mkdir -p static
```

#### Logs Directory (Optional)
```bash
mkdir -p logs
```

### 6. File Permissions
Ensure the web server has write permissions to:
```bash
# Media directory (for file uploads)
chmod 755 media/
# Database file (if using SQLite)
chmod 644 db.sqlite3
# Parent directory for database writes
chmod 755 .
```

### 7. Database Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### 8. Create Superuser
```bash
python manage.py createsuperuser
```

### 9. Collect Static Files (Production)
```bash
python manage.py collectstatic --noinput
```

### 10. Test Installation
```bash
python manage.py runserver
```
Visit `http://localhost:8000` to verify the installation.

## Production Deployment on Ubuntu 22.04 (Nginx + Gunicorn + SSL)

### 1) Install system packages
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx
```

### 2) Create directories and clone to /var/www/edupulse
```bash
sudo mkdir -p /var/www/edupulse
sudo chown -R $USER:www-data /var/www/edupulse
cd /var/www/edupulse
# Copy or git clone project here
```

### 3) Setup virtualenv and install deps
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Django initialisation
```bash
# Ensure .env is created with proper values (see above)
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

### 5) Systemd service for Gunicorn
Copy the service file we provide and enable it:
```bash
sudo mkdir -p /etc/systemd/system
sudo cp deploy/edupulse.service /etc/systemd/system/edupulse.service
sudo systemctl daemon-reload
sudo systemctl enable edupulse.service
sudo systemctl start edupulse.service
sudo systemctl status edupulse.service --no-pager -n 0
```

### 6) Nginx configuration
```bash
sudo cp deploy/nginx-edupulse.conf /etc/nginx/sites-available/edupulse.conf
sudo ln -s /etc/nginx/sites-available/edupulse.conf /etc/nginx/sites-enabled/edupulse.conf || true
sudo nginx -t
sudo systemctl reload nginx
```

### 7) Issue Let's Encrypt SSL (after DNS points to server)
```bash
sudo certbot --nginx -d edupulse.perthartschool.com.au --redirect --agree-tos -m admin@perthartschool.com.au -n
```

### 8) Post-SSL hardening (optional)
- Verify HSTS, TLS versions, and security headers in Nginx as per organisation policy

### 9) Deploy updates in the future
Use the helper script:
```bash
sudo bash deploy/deploy.sh PROJECT_DIR=/var/www/edupulse VENV_DIR=/var/www/edupulse/venv SERVICE_NAME=edupulse
```

### 10) Log locations
- Gunicorn (stderr/stdout): `journalctl -u edupulse -n 200 -f`
- Nginx access/error: `/var/log/nginx/`

## Nginx config (reference)
A copy is available at `deploy/nginx-edupulse.conf`. Ensure the paths:
- Static: `/var/www/edupulse/staticfiles/` (matches Django STATIC_ROOT)
- Media: `/var/www/edupulse/media/`
- Upstream socket: `/run/edupulse/gunicorn.sock`

## Gunicorn service (reference)
A copy is available at `deploy/edupulse.service`. Ensure:
- WorkingDirectory: `/var/www/edupulse`
- ExecStart: `/var/www/edupulse/venv/bin/gunicorn ... edupulse.wsgi:application`
- RuntimeDirectory: `edupulse` so `/run/edupulse/` exists for socket

## Security Considerations

### Production Environment Variables
For any production deployment, it is **critical** to configure the following environment variables in your `.env` file or server environment. These settings directly address Django's deployment security warnings.

-   **`DEBUG=False`**
    -   **Why:** This is the most important setting. Setting it to `False` prevents sensitive application details (like configuration and code paths) from being displayed on error pages.
    -   **Value:** `False`

-   **`SECRET_KEY`**
    -   **Why:** This key is used for cryptographic signing (e.g., sessions, password resets). A weak or exposed key compromises the entire application's security. It **must not** be the default `django-insecure-...` key.
    -   **Value:** A long, random, and unique string. You can generate one with the following command:
        ```bash
        python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
        ```

-   **`ALLOWED_HOSTS`**
    -   **Why:** This is a list of domain names that your Django site can serve. It prevents HTTP Host header attacks.
    -   **Value:** A comma-separated list of your domains, e.g., `edupulse.perthartschool.com.au`

### HTTPS and Secure Cookies
When `DEBUG=False`, the `settings.py` file is now configured to automatically enable the following for enhanced security:
-   `SESSION_COOKIE_SECURE = True`: Ensures session cookies are only sent over HTTPS.
-   `CSRF_COOKIE_SECURE = True`: Ensures CSRF cookies are only sent over HTTPS.
-   `SECURE_SSL_REDIRECT = True`: Redirects all non-HTTPS requests to HTTPS at the application level.
-   `SECURE_HSTS_SECONDS`: Enables HTTP Strict Transport Security (HSTS), which instructs browsers to only communicate with your site via HTTPS. This is enabled with a 30-day duration.

**To make these settings work, your site must be correctly configured with an SSL certificate (e.g., via Let's Encrypt as described above) and served over HTTPS.**

### File Upload Security
The system also implements several security measures for file uploads:
- File type validation (only JPG, PNG, GIF, WebP for images)
- File size limits (5MB for images)
- Unique filename generation using UUID
- Directory traversal protection
- Organized storage by date (YYYY/MM structure)

### Recommended Production Settings
- Use a non-SQLite database like PostgreSQL for production.
- Regular database backups.
- Monitor file upload directories for disk space.

## Troubleshooting

### Common Issues
1. Media files not accessible: Check file permissions and Nginx alias paths
2. TinyMCE not loading: Verify static files are properly collected and served
3. Upload errors: Check media directory permissions and disk space
4. Database errors: Ensure proper database configuration and migrations

### Log Files
Monitor logs for errors:
```bash
journalctl -u edupulse -n 200 -f
sudo tail -f /var/log/nginx/error.log
```

## Maintenance

### Regular Tasks
- Monitor disk space for media uploads
- Regular database backups
- Update dependencies periodically
- Review uploaded files for content policy compliance

### Backup Strategy
Ensure regular backups of:
- Database
- Media files (`media/` directory)
- Environment configuration
- Custom static files

## Recent Changes

### GST Settings Simplification (2025-09-08)
**Impact**: Code-level changes only, no database migration required

**Changes Made**:
- Simplified organisation settings GST configuration interface
- Fixed Australian GST rate at 10% and label as "GST" in code
- Removed complex GST calculator and preview components
- Only "Prices Include GST" toggle remains user-configurable

**Deployment Notes**:
- ✅ **No migration required**: Existing database fields preserved
- ✅ **Backward compatible**: All existing price calculation logic maintained
- ✅ **No configuration changes**: Environment variables unchanged
- ✅ **Static files**: No new static assets added

**Verification Steps**:
1. Access `/core/settings/organisation/` after deployment
2. Confirm GST Configuration card shows only "Prices Include GST" toggle
3. Test price display functionality on course pages
4. Verify GST calculations use fixed 10% rate

**Rollback**: If needed, revert commits related to GST simplification - no data loss risk

## Support
For technical support or questions about deployment, refer to the project documentation or contact the development team.


## Pre-deployment Checklist: Organisation Contact & Email

Before deploying to a new environment, verify the following to ensure email contact information is consistent and reply-to works as expected:

1) Organisation Settings
- In Admin > Organisation Settings, set:
  - Contact Email (used in templates and as email Reply-To)
  - Contact Phone (displayed on success page and email bodies)

2) Django Email Settings
- DEFAULT_FROM_EMAIL is set appropriately in settings or environment
- SMTP credentials are valid and tested (see .env variables in this doc)

3) Notification Service
- Outbound emails include reply_to using OrganisationSettings.contact_email
- Test a sample enrollment flow to confirm Reply-To header is present

4) Frontend Validation
- Visit an enrollment success page: /enrollment/success/<id>/
- Confirm the "Contact Us" section shows the Organisation Settings contact email/phone

Notes
- Migration defaults and test fixtures may still contain placeholder emails like info@perthartschool.com.au; these are intentional and do not affect runtime configuration.

## Scheduled Tasks Configuration

EduPulse uses django-crontab for automatic course status management. After deployment, ensure scheduled tasks are configured:

### Setup Scheduled Tasks

1) **Install django-crontab** (included in requirements.txt):
```bash
pip install django-crontab
```

2) **Add crontab tasks to system**:
```bash
python manage.py crontab add
```

3) **Verify tasks are installed**:
```bash
python manage.py crontab show
crontab -l  # Check system crontab
```

### Configured Tasks

The system automatically configures these scheduled tasks:

- **Daily Course Status Update** (2:00 AM): Updates expired courses based on end dates
- **Weekly Status Consistency Check** (3:00 AM Sunday): Verifies status consistency across the system

### Manual Management

You can also run these tasks manually:

```bash
# Update expired courses
python manage.py update_expired_courses

# Check status consistency
python manage.py update_expired_courses --check-consistency

# Preview changes without updating
python manage.py update_expired_courses --dry-run

# Show courses expiring in next N days
python manage.py update_expired_courses --upcoming 7
```

### Removing Tasks

To remove scheduled tasks (if needed):
```bash
python manage.py crontab remove
```