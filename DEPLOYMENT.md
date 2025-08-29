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
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
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
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database (if using PostgreSQL/MySQL)
DATABASE_URL=postgresql://user:password@host:port/database

# Email Configuration (AWS SES)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_SES_FROM_EMAIL=noreply@your-domain.com

# SMS Configuration (Optional - Twilio)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=your-twilio-number

# WooCommerce Integration (Future)
WOOCOMMERCE_URL=https://your-wordpress-site.com
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

## Production Deployment

### Web Server Configuration
Configure your web server (Apache/Nginx) to:
- Serve static files from `/static/` directory
- Serve media files from `/media/` directory
- Proxy Django application
- Handle HTTPS certificates

### Example Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /path/to/edupulse/static/;
    }
    
    location /media/ {
        alias /path/to/edupulse/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Security Considerations

### File Upload Security
The system implements several security measures for file uploads:
- File type validation (only JPG, PNG, GIF, WebP for images)
- File size limits (5MB for images)
- Unique filename generation using UUID
- Directory traversal protection
- Organized storage by date (YYYY/MM structure)

### Recommended Production Settings
- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure `ALLOWED_HOSTS` properly
- Use HTTPS in production
- Regular database backups
- Monitor file upload directories for disk space

## Feature Components

### Core Features Implemented
- **Staff Management**: User authentication and role management
- **Student Management**: Student profiles and information
- **Course Management**: Course creation with rich text descriptions (TinyMCE)
- **Facility Management**: Location and facility tracking
- **Classroom Management**: Room assignments linked to facilities
- **Class Scheduling**: Course scheduling and management
- **Rich Text Editing**: TinyMCE integration with image upload support

### File Upload Functionality
- **TinyMCE Image Upload**: Secure image upload for course descriptions
- **Automatic Directory Creation**: Upload directories created as needed
- **File Organization**: Date-based directory structure (YYYY/MM)
- **Security Validation**: File type and size restrictions

## WordPress Integration (Planned)
The system is designed to integrate with WordPress/WooCommerce:
- Course synchronization from EduPulse to WooCommerce
- Enrollment redirection from WordPress to EduPulse
- Rich text content compatibility between systems

## Troubleshooting

### Common Issues
1. **Media files not accessible**: Check file permissions and web server configuration
2. **TinyMCE not loading**: Verify static files are properly served
3. **Upload errors**: Check media directory permissions and disk space
4. **Database errors**: Ensure proper database configuration and migrations

### Log Files
Monitor Django logs for errors:
```bash
# If using logging configuration
tail -f logs/django.log
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

## Support
For technical support or questions about deployment, refer to the project documentation or contact the development team.