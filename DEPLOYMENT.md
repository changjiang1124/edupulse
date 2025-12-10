# EduPulse Deployment Guide

## Overview
This document outlines the steps required to deploy EduPulse in a new environment.

## Quick Deploy (recommended)
1) 仅首次：系统准备  
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip redis-server git
   sudo systemctl enable --now redis-server
   ```
2) 仅首次：目录与虚拟环境  
   ```bash
   sudo mkdir -p /var/www/edupulse
   sudo chown -R $USER:www-data /var/www/edupulse
   cd /var/www/edupulse
   python3 -m venv .venv
   source .venv/bin/activate
   # 放置代码（git clone 或 scp）
   pip install -r requirements.txt
   ```
3) 准备 `.env`（SMTP、Redis、域名等必需变量）。  
4) 一键部署（自动安装/更新 systemd 服务，迁移、collectstatic、检查，重启 Gunicorn + RQ Worker，并尝试恢复 Redis）：  
   ```bash
   sudo bash deploy/deploy.sh
   ```

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

**Note**: The requirements.txt file has been organized and updated to include:
- Core Django framework and web server components
- Django extensions (TinyMCE, django-crontab)
- Communication services (Twilio for SMS)
- Image processing and file handling
- All necessary utilities and dependencies

Ensure all dependencies install successfully before proceeding.

### 4. Environment Variables
Create a `.env` file in the project root with the following variables:

```env
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=edupulse.perthartschool.com.au,www.perthartschool.com.au,localhost,127.0.0.1

# Site Domain Configuration (for URL generation)
# Development: SITE_DOMAIN=localhost:8000
# Production: SITE_DOMAIN=edupulse.perthartschool.com.au
SITE_DOMAIN=edupulse.perthartschool.com.au
SITE_PROTOCOL=https

# Database (if using PostgreSQL/MySQL)
# DATABASE_URL=postgresql://user:password@host:port/database

# SMTP Email (AWS SES or other SMTP)
SMTP_SERVER=email-smtp.ap-southeast-2.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password

# Email Performance Settings (New in v1.1)
EMAIL_TIMEOUT=60
BULK_EMAIL_BATCH_SIZE=20
BULK_EMAIL_BATCH_DELAY=0    # Set to 0 to avoid blocking (recommended)

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

### 9. Bootstrap and Frontend Assets

The project includes local copies of Bootstrap CSS/JS in the `static/` directory as fallbacks:
- `static/css/bootstrap.min.css` (227KB)
- `static/css/bootstrap.min.css.map` (source map for debugging)
- `static/js/bootstrap.bundle.min.js` (90KB)

These files ensure the frontend works even if CDN is blocked or offline.

**Important**: Ensure these files are present before deployment:
```bash
# Verify Bootstrap files exist
ls -lh static/css/bootstrap.min.css
ls -lh static/js/bootstrap.bundle.min.js

# If missing, download from CDN:
curl -o static/css/bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css
curl -o static/css/bootstrap.min.css.map https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css.map
curl -o static/js/bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js
```

### 10. Collect Static Files (Production)
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

### 5) Nginx configuration
```bash
sudo cp deploy/nginx-edupulse.conf /etc/nginx/sites-available/edupulse.conf
sudo ln -s /etc/nginx/sites-available/edupulse.conf /etc/nginx/sites-enabled/edupulse.conf || true
sudo nginx -t
sudo systemctl reload nginx
```

### 6) Issue Let's Encrypt SSL (after DNS points to server)
```bash
sudo certbot --nginx -d edupulse.perthartschool.com.au --redirect --agree-tos -m admin@perthartschool.com.au -n
```

### 7) Post-SSL hardening (optional)
- Verify HSTS, TLS versions, and security headers in Nginx as per organisation policy

### 8) Log locations
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

### Organisation Settings Enhancement (2025-01-XX)
**Impact**: Database migration required, new configurable fields added

**Changes Made**:
- Added configurable banking details fields (BSB, account number, account name)
- Added configurable website domain field
- Updated email templates to use configurable values instead of hardcoded ones
- Enhanced organisation settings admin interface and frontend form

**Database Changes**:
- New fields: `bank_account_name`, `bank_bsb`, `bank_account_number`, `site_domain`
- Migration: `core/migrations/0010_organisationsettings_bank_account_name_and_more.py`

**Deployment Notes**:
- ⚠️ **Migration required**: Run `python manage.py migrate` after deployment
- ✅ **Backward compatible**: Default values provided for all new fields
- ✅ **Email templates updated**: Now use configurable banking details
- ✅ **Admin interface enhanced**: New fields available in Django admin

**Verification Steps**:
1. Run database migration: `python manage.py migrate`
2. Access `/core/settings/organisation/` after deployment
3. Confirm new "Banking Details" and "Website Configuration" sections are visible
4. Test updating banking details and verify they appear in enrollment emails
5. Verify email templates use configurable values instead of hardcoded ones

**Files Modified**:
- `core/models.py`: Added new fields to OrganisationSettings model
- `core/views.py`: Updated organisation_settings_view to handle new fields
- `core/admin.py`: Enhanced admin interface with new fieldsets
- `core/services/notification_service.py`: Updated email context with new variables
- `templates/core/emails/enrollment_pending.html`: Use configurable banking details
- `templates/core/emails/enrollment_pending.txt`: Use configurable banking details
- `templates/core/settings/organisation.html`: Added form fields for new settings

**Rollback**: If needed, revert migration and related code changes - no data loss risk as defaults are provided

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

**Rollback**: Simply revert to previous code version - no data changes required

### Batch Email Performance Optimization (2025-09-18) - UPDATED
**Impact**: Performance improvement for bulk email operations with critical bug fixes

**Changes Made**:
- Enhanced email sending with batch processing (default 20 emails per batch)
- Added SMTP connection pooling and validation with retry logic (max 2 retries)
- Fixed N+1 database query issue in bulk course reminders
- Improved error handling with per-email error isolation
- Immediate quota consumption (per successful email)
- Created `BatchEmailService` class for reliable bulk email sending
- Updated `NotificationService.send_bulk_course_reminders()` with optimized queries
- Modified `students.views.bulk_notification()` to use batch service

**Critical Bug Fixes**:
- ✅ SMTP connection management and validation
- ✅ Database query optimization (N+1 problem)
- ✅ Quota consumption timing
- ✅ Individual email retry logic
- ⚠️ **Still synchronous**: User requests are blocked during email sending

**New Environment Variables Required**:
```env
EMAIL_TIMEOUT=60                # SMTP connection timeout in seconds
BULK_EMAIL_BATCH_SIZE=20       # Number of emails per batch
BULK_EMAIL_BATCH_DELAY=0       # Delay between batches (0=no delay, recommended)
```

**Files Modified**:
- `edupulse/settings.py`: Updated email performance configuration
- `core/services/batch_email_service.py`: Enhanced batch service with fixes
- `core/services/notification_service.py`: Fixed N+1 queries and caching
- `students/views.py`: Enhanced bulk notification with batch processing
- `templates/core/emails/bulk_notification.html`: New template (NEW FILE)
- `templates/core/emails/bulk_notification.txt`: New template (NEW FILE)
- `EMAIL_QUEUE_DEPLOYMENT.md`: Comprehensive deployment guide
- `EMAIL_SYSTEM_LIMITATIONS.md`: Current limitations and solutions (NEW FILE)

**Testing Steps**:
1. Configure new environment variables in .env file
2. Restart application server (gunicorn/runserver)
3. Test bulk email functionality with 10-20 recipients first
4. Monitor logs for batch processing and retry confirmation
5. Limit production usage to max 50 emails per batch

**Performance Benefits**:
- Reliable SMTP connection handling with auto-retry
- Optimized database queries (eliminated N+1 problem)
- Better error isolation (failed emails don't affect entire batch)
- Immediate quota tracking prevents double-billing
- Enhanced monitoring and logging capabilities

**⚠️ Known Limitations**:
- **Still synchronous**: Email sending blocks user interface
- **Recommended limit**: Max 30-50 emails per batch for good UX
- **Large batches**: 100+ emails may cause browser timeout

**Future Upgrade Path**:
- Phase 2: Django-RQ for async processing (50+ emails)
- Phase 3: Celery for enterprise-scale operations (200+ emails)
- See `EMAIL_QUEUE_DEPLOYMENT.md` for detailed upgrade instructions

**Rollback**: Revert code changes and remove new environment variables - no database changes required

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

## Domain Configuration

### Overview
EduPulse uses environment variables to configure the correct domain for URL generation across different environments. This is crucial for features like:
- Public enrollment URL copying in course details
- Email notifications with correct links
- WordPress/WooCommerce integration URLs

### Environment-Specific Configuration

#### Development Environment
```env
SITE_DOMAIN=localhost:8000
SITE_PROTOCOL=http
DEBUG=True
```

#### Production Environment
```env
SITE_DOMAIN=edupulse.perthartschool.com.au
SITE_PROTOCOL=https
DEBUG=False
```

### Template Usage
The system provides custom template tags for generating correct URLs:

```django
{% load custom_filters %}

<!-- Generate full site URL -->
{% site_url 'enrollment:public_enrollment' %}

<!-- Generate enrollment URL with course parameter -->
{% enrollment_url course.pk %}
```

### Important Notes
- **SITE_DOMAIN**: Should NOT include protocol (http/https)
- **SITE_PROTOCOL**: Automatically defaults to 'https' in production (DEBUG=False) and 'http' in development
- **Port Numbers**: Include port number in SITE_DOMAIN for development (e.g., localhost:8000)
- **SSL**: Ensure SITE_PROTOCOL matches your actual SSL configuration

### Troubleshooting
If enrollment URLs show incorrect domains:
1. Verify SITE_DOMAIN is set correctly in your .env file
2. Ensure SITE_PROTOCOL matches your server configuration
3. Restart the Django application after changing environment variables
4. Check that custom_filters template tags are loaded in templates

### Removing Tasks

To remove scheduled tasks (if needed):
```bash
python manage.py crontab remove
```
