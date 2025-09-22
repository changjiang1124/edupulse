# Term 4 2025 Enrollment Preparation Guide

## Overview
This guide provides a step-by-step process for preparing Term 4 2025 enrollment, from course creation to enrollment management.

## Prerequisites
- TSV files for course data and student data ready
- Django environment set up and database accessible
- Admin access to Django backend
- WooCommerce sync configured

---

## Step 1: Create Courses

### 1.1 Generate Draft Courses
Create all Term 4 2025 courses in draft status for review:

```bash
# Generate courses from TSV file (creates as draft)
python manage.py generate_term_courses

# Preview before creating (recommended first)
python manage.py generate_term_courses --dry-run

# Custom parameters if needed
python manage.py generate_term_courses \
  --start-date 2025-10-14 \
  --end-date 2025-12-21 \
  --term-name "Term 4 2025" \
  --early-bird-days 14

# If you need to regenerate courses
python manage.py generate_term_courses --clear-existing
```

**Expected Result**: 25 courses created in draft status

### 1.2 Review and Publish Courses
1. **Django Admin Review**:
   - Go to `/admin/academics/course/`
   - Filter by "Term 4 2025" courses
   - Review course details:
     - Pricing (original price, early bird price, registration fee)
     - Schedule (dates, times, weekdays)
     - Course descriptions
     - Capacity settings

2. **Publish Courses**:
   - Change status from `draft` to `published`
   - Verify `is_online_bookable` is set to `True`
   - Change `bookable_state` from `closed` to `bookable`
   - Save each course

3. **Verify WooCommerce Sync**:
   - Check that courses sync to WooCommerce
   - Verify pricing and descriptions match
   - Test enrollment redirect links

---

## Step 2: Import Students

### 2.1 Prepare Student Data
Ensure your student TSV file has the correct format:
```
Student Name    DOB    Guardian Name    Phone    Address    Email
```

### 2.2 Import Students
```bash
# Preview student import (recommended first)
python manage.py import_students --file students.tsv --dry-run

# Import students
python manage.py import_students --file students.tsv

# Custom file path if needed
python manage.py import_students --file /path/to/your/students.tsv
```

**Expected Result**: All students imported with contact details and guardian information

### 2.3 Verify Student Data
1. **Django Admin Check**:
   - Go to `/admin/students/student/`
   - Verify student names, contact details
   - Check guardian information
   - Ensure no duplicate entries

2. **Student Management**:
   - Review and clean up any data issues
   - Update missing information
   - Verify contact details for notifications

---

## Step 3: Create Enrollments

> **Note**: No automated command available yet. Manual process required.

### 3.1 Manual Enrollment Creation
1. **Via Django Admin**:
   - Go to `/admin/enrollment/enrollment/`
   - Click "Add enrollment"
   - Select student and course
   - Set enrollment status (pending, confirmed, etc.)
   - Add payment and pricing information

2. **Via Public Enrollment Form**:
   - Use the public enrollment form at `/enroll/`
   - Test the enrollment process
   - Verify form validation and data capture

### 3.2 Bulk Enrollment (if needed)
For staff-assisted bulk enrollments:
1. Create enrollment records through admin
2. Set appropriate status for each enrollment
3. Verify pricing calculations
4. Generate payment instructions

**Expected Result**: All enrollments created with correct student-course mappings and pricing

---

## Step 4: Manage Notifications and Enrollment Status

### 4.1 Review Enrollment Status
1. **Enrollment Dashboard**:
   - Access enrollment management views
   - Check enrollment status distribution
   - Verify payment status tracking

2. **Status Categories**:
   - `pending`: Awaiting confirmation/payment
   - `confirmed`: Enrollment confirmed and paid
   - `waitlisted`: Course full, student on waitlist
   - `cancelled`: Enrollment cancelled

### 4.2 Send Notifications

#### Email Notifications
```bash
# Send course reminders (if command exists)
python manage.py send_course_reminders

# Check email logs
# Go to /admin/core/emaillog/ to verify sent emails
```

#### SMS Notifications
- Use SMS logging in Django admin
- Send manual notifications through admin interface
- Verify contact numbers are current

### 4.3 Payment Management
1. **Payment Instructions**:
   - Generate payment instructions for confirmed enrollments
   - Include bank transfer details
   - Set payment deadlines

2. **Payment Tracking**:
   - Update enrollment status when payments received
   - Send confirmation emails
   - Update course capacity tracking

### 4.4 Waitlist Management
1. **Monitor Course Capacity**:
   - Track enrollment numbers vs. course vacancy
   - Move students from waitlist when spots available
   - Send notifications for waitlist movements

2. **Capacity Adjustments**:
   - Increase course capacity if needed
   - Create additional class sessions if demand high
   - Communicate changes to enrolled students

---

## Verification Checklist

### Pre-Enrollment Launch
- [ ] All 25 courses created and published
- [ ] Course pricing verified (original, early bird, registration fees)
- [ ] Course schedules confirmed (dates, times, locations)
- [ ] WooCommerce sync working correctly
- [ ] Student database imported and verified
- [ ] Public enrollment form tested and functional
- [ ] Payment instruction templates ready
- [ ] Notification templates configured

### During Enrollment Period
- [ ] Monitor enrollment numbers daily
- [ ] Process payment confirmations
- [ ] Send enrollment confirmations
- [ ] Manage waitlists for popular courses
- [ ] Handle enrollment queries and changes
- [ ] Update course status (full/available)

### Post-Enrollment
- [ ] Final enrollment confirmations sent
- [ ] Course lists generated for teachers
- [ ] Attendance tracking set up
- [ ] Course materials prepared
- [ ] Welcome communications sent

---

## Command Reference

### Course Management
```bash
# Generate courses
python manage.py generate_term_courses [options]

# Update expired courses (if needed)
python manage.py update_expired_courses
```

### Student Management
```bash
# Import students
python manage.py import_students --file students.tsv [options]

# Match student names (data cleanup)
python manage.py match_student_names

# Delete students (if needed)
python manage.py delete_students
```

### System Monitoring
```bash
# Check WooCommerce sync
python manage.py test_woocommerce

# Monitor WooCommerce
python manage.py woocommerce_monitor

# Send reminders
python manage.py send_course_reminders
```

---

## Troubleshooting

### Course Creation Issues
- **Courses not appearing**: Check draft status, publish manually
- **Pricing incorrect**: Verify TSV file format and decimal places
- **WooCommerce sync failed**: Check API connection and credentials

### Student Import Issues
- **Duplicate students**: Use dry-run first, check existing records
- **Invalid data**: Clean TSV file, check date formats
- **Missing information**: Update student records in admin

### Enrollment Issues
- **Payment not tracking**: Update enrollment status manually
- **Notifications not sending**: Check email/SMS configuration
- **Capacity conflicts**: Verify course vacancy settings

---

## Support Contacts

- **Technical Issues**: Check Django admin logs and error messages
- **Course Content**: Review with teaching staff
- **Payment Queries**: Verify bank transfer instructions
- **System Access**: Ensure staff accounts have correct permissions

---

*Last Updated: September 2025*
*For Term 4 2025 Enrollment Period: October-December 2025*