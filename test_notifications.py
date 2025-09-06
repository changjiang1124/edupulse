"""
Test script for notification system
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/changjiang/Dev/edupulse')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from core.services import NotificationService
from enrollment.models import Enrollment
from students.models import Student
from academics.models import Course
from django.utils import timezone
from datetime import timedelta


def test_notification_system():
    """Test the notification system with sample data"""
    print("🔔 Testing EduPulse Notification System")
    print("=" * 50)
    
    # Test 1: Find existing enrollments for testing
    print("\n1. Testing with existing enrollments:")
    recent_enrollments = Enrollment.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('student', 'course')[:3]
    
    if recent_enrollments.exists():
        for enrollment in recent_enrollments:
            print(f"   📋 Enrollment: {enrollment.student.get_full_name()} - {enrollment.course.name}")
            print(f"      Email: {enrollment.student.primary_contact_email or enrollment.student.email}")
            print(f"      Status: {enrollment.get_status_display()}")
            
            # Test enrollment confirmation email
            try:
                result = NotificationService.send_enrollment_confirmation(enrollment)
                print(f"      ✅ Confirmation email: {'Sent' if result else 'Failed'}")
            except Exception as e:
                print(f"      ❌ Confirmation email error: {str(e)}")
                
            # Test welcome email if enrollment is confirmed
            if enrollment.status == 'confirmed':
                try:
                    result = NotificationService.send_welcome_email(enrollment)
                    print(f"      ✅ Welcome email: {'Sent' if result else 'Failed'}")
                except Exception as e:
                    print(f"      ❌ Welcome email error: {str(e)}")
            
            print()
    else:
        print("   ℹ️  No recent enrollments found for testing")
    
    # Test 2: Course reminders
    print("\n2. Testing course reminders:")
    try:
        tomorrow_count = NotificationService.send_bulk_course_reminders(days_ahead=1)
        print(f"   📧 Tomorrow's reminders: {tomorrow_count} sent")
        
        next_week_count = NotificationService.send_bulk_course_reminders(days_ahead=7)
        print(f"   📧 Next week reminders: {next_week_count} sent")
    except Exception as e:
        print(f"   ❌ Course reminder error: {str(e)}")
    
    # Test 3: System health check
    print("\n3. System Health Check:")
    
    # Check email configuration
    try:
        from core.models import EmailSettings
        email_config = EmailSettings.get_active_config()
        if email_config:
            print(f"   ✅ Email backend: {email_config.get_email_backend_type_display()}")
            print(f"   📤 SMTP server: {email_config.smtp_host}:{email_config.smtp_port}")
        else:
            print("   ⚠️  No active email configuration found")
    except Exception as e:
        print(f"   ❌ Email config error: {str(e)}")
    
    # Check SMS configuration
    try:
        from core.models import SMSSettings
        sms_config = SMSSettings.get_active_config()
        if sms_config:
            print(f"   ✅ SMS backend: {sms_config.get_sms_backend_type_display()}")
        else:
            print("   ⚠️  No active SMS configuration found")
    except Exception as e:
        print(f"   ❌ SMS config error: {str(e)}")
    
    # Check template files
    template_files = [
        'core/emails/enrollment_confirmation.html',
        'core/emails/enrollment_confirmation.txt',
        'core/emails/welcome.html',
        'core/emails/welcome.txt',
        'core/emails/course_reminder.html',
        'core/emails/course_reminder.txt',
        'core/emails/attendance_notice.html',
        'core/emails/attendance_notice.txt'
    ]
    
    print(f"   📄 Email templates: {len(template_files)} files")
    
    from django.template.loader import get_template
    missing_templates = []
    for template in template_files:
        try:
            get_template(template)
        except:
            missing_templates.append(template)
    
    if missing_templates:
        print(f"   ❌ Missing templates: {missing_templates}")
    else:
        print("   ✅ All email templates found")
    
    print("\n" + "=" * 50)
    print("🎉 Notification System Test Complete!")


if __name__ == '__main__':
    test_notification_system()