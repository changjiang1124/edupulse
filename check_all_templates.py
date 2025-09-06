#!/usr/bin/env python
"""
Find and fix similar template syntax errors across all templates
"""
import os
import sys
import re
from pathlib import Path

# Add the project directory to Python path
sys.path.append('/Users/changjiang/Dev/edupulse')

template_dirs = [
    '/Users/changjiang/Dev/edupulse/templates',
    '/Users/changjiang/Dev/edupulse/accounts/templates',
    '/Users/changjiang/Dev/edupulse/academics/templates',
    '/Users/changjiang/Dev/edupulse/students/templates',
    '/Users/changjiang/Dev/edupulse/facilities/templates',
    '/Users/changjiang/Dev/edupulse/enrollment/templates'
]

def check_template_files():
    """Find all HTML template files and check for syntax issues"""
    print("🔍 Scanning for template files...")
    
    template_files = []
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        template_files.append(os.path.join(root, file))
    
    print(f"Found {len(template_files)} template files")
    
    problematic_templates = []
    
    for template_file in template_files:
        print(f"\n📄 Checking: {template_file}")
        try:
            issues = check_template_syntax(template_file)
            if issues:
                problematic_templates.append((template_file, issues))
                print(f"❌ Issues found: {len(issues)}")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print("✅ No issues")
        except Exception as e:
            print(f"❌ Error reading file: {str(e)}")
    
    print(f"\n📊 Summary:")
    print(f"Total templates: {len(template_files)}")
    print(f"Problematic templates: {len(problematic_templates)}")
    
    if problematic_templates:
        print("\n🚨 Templates with issues:")
        for template_file, issues in problematic_templates:
            print(f"\n{template_file}:")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print("\n🎉 All templates look good!")
    
    return problematic_templates

def check_template_syntax(file_path):
    """Check Django template syntax for matching tags"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Track opening and closing tags
    tag_stack = []
    errors = []
    
    # Django template tag patterns
    opening_tags = re.compile(r'{%\s*(if|for|block|with|comment|spaceless)\b[^%]*%}')
    closing_tags = re.compile(r'{%\s*(endif|endfor|endblock|endwith|endcomment|endspaceless)\b[^%]*%}')
    
    for line_num, line in enumerate(lines, 1):
        # Find opening tags
        for match in opening_tags.finditer(line):
            tag_type = match.group(1)
            if tag_type in ['if', 'for', 'block', 'with', 'comment', 'spaceless']:
                tag_stack.append((tag_type, line_num, line.strip()))
        
        # Find closing tags
        for match in closing_tags.finditer(line):
            tag_type = match.group(1).replace('end', '')  # Remove 'end' prefix
            if tag_stack:
                last_tag, last_line, last_content = tag_stack[-1]
                if last_tag == tag_type:
                    tag_stack.pop()
                else:
                    errors.append(f"Line {line_num}: Mismatched tag - expected 'end{last_tag}' but found 'end{tag_type}'")
            else:
                errors.append(f"Line {line_num}: Unexpected closing tag 'end{tag_type}' with no matching opening")
    
    # Check for unclosed tags
    for tag_type, line_num, content in tag_stack:
        errors.append(f"Line {line_num}: Unclosed tag '{tag_type}': {content[:50]}...")
    
    return errors

if __name__ == "__main__":
    check_template_files()