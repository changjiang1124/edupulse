#!/usr/bin/env python
"""
Test Django template compilation directly
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/changjiang/Dev/edupulse')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.template.loader import get_template
from django.template import TemplateDoesNotExist, TemplateSyntaxError

def test_template_compilation():
    """Test if template can be compiled"""
    template_name = 'core/enrollments/public_enrollment.html'
    
    print(f"Testing template compilation: {template_name}")
    
    try:
        template = get_template(template_name)
        print("✅ Template compiled successfully!")
        
        # Try to render with minimal context
        test_context = {
            'form': None,
            'courses': [],
            'messages': [],
            'selected_course': None
        }
        
        try:
            rendered = template.render(test_context)
            print("✅ Template renders successfully!")
            print(f"Rendered content length: {len(rendered)} characters")
        except Exception as e:
            print(f"❌ Template rendering failed: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            
    except TemplateDoesNotExist as e:
        print(f"❌ Template not found: {str(e)}")
    except TemplateSyntaxError as e:
        print(f"❌ Template syntax error: {str(e)}")
        print(f"Error details: {e.template_debug}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_template_compilation()