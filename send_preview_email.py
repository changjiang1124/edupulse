import os
import django
import sys
from django.conf import settings

# Setup Django environment
# Add the project directory to the sys.path
sys.path.append('/Users/changjiang/Dev/edupulse')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

# Mock objects
class MockStudent:
    def get_full_name(self):
        return "TEST Email"
    
    @property
    def contact_email(self):
        return "cj+GUU@carebridge.com.au"
        
    @property
    def contact_phone(self):
        return "0412 999 888"

class MockCourse:
    @property
    def name(self):
        return "Other Teacher's Course"

class MockEnrollment:
    def __init__(self):
        self.course_fee = "150.00"
        self.created_at = timezone.now()
        
    def get_reference_id(self):
        return "PAS-031-077"

def send_test():
    student = MockStudent()
    course = MockCourse()
    enrollment = MockEnrollment()
    
    context = {
        'student': student,
        'course': course,
        'enrollment': enrollment,
        'enrollment_url': "https://edupulse.perthartschool.com.au/admin/enrollment/enrollment/1/change/", # Mock URL
        'current_year': timezone.now().year,
    }
    
    subject = "New Enrolment Submitted - TEST Email for Other Teacher's Course"
    
    # Render the template we just modified
    html_content = render_to_string('core/emails/new_enrollment_admin_notice.html', context)
    text_content = f"New enrollment for {student.get_full_name()}"
    
    to_email = "cj@carebridge.com.au"
    
    print(f"Sending email to {to_email}...")
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")
    
    try:
        email.send()
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_test()
