## Overview

This is a django project named EduPulse for a client named PerthArtSchool. our agreed proposal included in `proposal.md` of the current folder. 

client's current website (perthartschool.com.au) is built with WordPress + Woocommerce on SiteGround for their display, courses, etc. after this project rolls out, the enrolment should be handled by EduPulse instead of the woocommerce. which means the course created (as well as other actions like edit, delete) on edupulse, should be synchronised with the woocommerce, so the customers always have the latest information thru the current woocommerce website. and when customers click the enrolment button, they should be redirected to the edupulse website to fill form, and receive payment instruction after submit the form. (the client asks for bank transfer or offline payment instead of online payment to avoid surcharge fee from the payment gateway)

the project could use url like https://edupulse.perthartschool.com.au/ for the new website.

client's priority is to use this to have enrolment feature. but to have enrolment feature, the system should have course plan, student CRUD management and any other necessary modules. because the form involves student information, course selection, enrolment info and status, etc. 

## Current Implementation Status

### 🏗️ Architecture
- **Modular Django Architecture**: Apps organized by functional domains
- **Custom User Model**: `accounts.Staff` extends AbstractUser with roles (admin/teacher)
- **Template Structure**: Centralized templates with app-specific organization needed
- **URL Routing**: Clean URL structure with app namespacing

### 📦 Applications Structure
1. **core**: Dashboard, clock system, email/SMS logging, shared utilities
2. **accounts**: Staff authentication and user management (custom user model)
3. **students**: Student records with guardian information and contact management
4. **academics**: Course and Class management with TinyMCE integration
5. **facilities**: Facility and classroom management for location tracking
6. **enrollment**: Enrollment process and attendance tracking

### 🎯 Key Models & Features Implemented
- **Course Management**: Enhanced with WordPress-compatible descriptions, repeat patterns, status management
- **Class System**: Individual class instances generated from courses with scheduling
- **Student Management**: Full student profiles with guardian information and reference tracking
- **Enrollment System**: Public enrollment form with JSON data storage and status tracking
- **Attendance Tracking**: Comprehensive attendance records linked to class instances
- **Staff System**: Role-based access with admin/teacher roles
- **Facilities**: Location and classroom capacity management
- **Communication Logs**: Email and SMS logging for audit trails

### 🛠️ Tech Stack
- **Backend**: Django 5.2.5 with SQLite database
- **Frontend**: Bootstrap framework with custom theme, jQuery
- **Editor**: TinyMCE for WordPress-compatible content
- **Location**: Perth timezone, Australian English
- **Communication**: AWS SES email, Twilio SMS integration setup

### 📋 Template Organization Issue
**Current**: Templates are mixed between `/templates/core/` and app-specific locations
**Needed**: Move templates to respective app directories following Django best practices

### 🔗 URL Namespacing
- Core: `/core/` - Dashboard and utilities
- Students: `/students/` - Student management
- Academics: `/academics/` - Courses and classes  
- Facilities: `/facilities/` - Location management
- Enrollment: `/enrollment/` - Enrollment management
- Public: `/enroll/` - Public enrollment form (no auth required)

## eng choice 

django
sqlite
bootstrap as framework, with customised theme colours 
jquery
TinyMCE (WordPress-compatible rich text editing)

try best to not include inline css and js in the html, to have a clean and maintainable code. 

## code 
comments and UI in Australian English. 

## iterative 
in `next-step.md` file, i will keep it updated as the project goes, indicating what should be implemented in the next step. 

## response rule 
respond me in simplified Chinese by default, while coding and comments in Australian English, including the user interface text.


包括生成 implementation plan 的时候，也用简体中文。

## Style 
make sure it's align with framework of bootstrap, even the colours and radius are not exactly the same, the layout should be consistent. and review if any other places have such issue.

## Deployment preparation
While implementing, update `DEPLOYMENT.md` file for any operations/steps before deploy to another new environment. 
- when model changed, check if the relevant frontend / form needed to be changed accordingly.


## Google API Enabled Service 
reference to the list below to check if sufficient:

```
Gemini for Google Cloud
Cloud Speech-to-Text API					
Cloud Text-to-Speech API					
Cloud Translation API					
Directions API					
Distance Matrix API					
Geocoding API					
Geolocation API					
Google Drive API					
Google Sheets API					
Maps Elevation API					
Maps JavaScript API					
Maps Static API					
Places API					
Places API (New)					
reCAPTCHA Enterprise API					
Roads API					
Street View Static API					
Time Zone API
```

## Product Environment 
Django
Ubuntu 22.04
Nginx
Gunicorn
SSL - Let's Encrypt
url: https://edupulse.perthartschool.com.au/

## Dev Environment 
macOS
with venv as environment in .venv folder. so activate it before make any changes.

the account for test: 
username: admin
password: Wasd!234

## Local Server URL
http://127.0.0.1:20003/