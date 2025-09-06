#!/usr/bin/env python
"""
Check template syntax for Django template files
"""
import os
import sys
import re

# Path to the template file
template_path = '/Users/changjiang/Dev/edupulse/templates/core/enrollments/public_enrollment.html'

def check_template_syntax(file_path):
    """Check Django template syntax for matching tags"""
    print(f"Checking template: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Track opening and closing tags
    tag_stack = []
    errors = []
    
    # Django template tag patterns
    opening_tags = re.compile(r'{%\s*(if|for|block|with|comment|spaceless|load|csrf_token)\b[^%]*%}')
    closing_tags = re.compile(r'{%\s*(endif|endfor|endblock|endwith|endcomment|endspaceless)\b[^%]*%}')
    
    for line_num, line in enumerate(lines, 1):
        # Find opening tags
        for match in opening_tags.finditer(line):
            tag_type = match.group(1)
            if tag_type in ['if', 'for', 'block', 'with', 'comment', 'spaceless']:
                tag_stack.append((tag_type, line_num, line.strip()))
                print(f"Line {line_num}: Found opening tag '{tag_type}': {line.strip()}")
        
        # Find closing tags
        for match in closing_tags.finditer(line):
            tag_type = match.group(1).replace('end', '')  # Remove 'end' prefix
            if tag_stack:
                last_tag, last_line, last_content = tag_stack[-1]
                if last_tag == tag_type:
                    tag_stack.pop()
                    print(f"Line {line_num}: Found matching closing tag 'end{tag_type}': {line.strip()}")
                else:
                    errors.append(f"Line {line_num}: Mismatched tag - expected 'end{last_tag}' but found 'end{tag_type}': {line.strip()}")
                    print(f"ERROR: Line {line_num}: Mismatched tag - expected 'end{last_tag}' but found 'end{tag_type}': {line.strip()}")
            else:
                errors.append(f"Line {line_num}: Unexpected closing tag 'end{tag_type}' with no matching opening: {line.strip()}")
                print(f"ERROR: Line {line_num}: Unexpected closing tag 'end{tag_type}' with no matching opening: {line.strip()}")
    
    # Check for unclosed tags
    for tag_type, line_num, content in tag_stack:
        errors.append(f"Line {line_num}: Unclosed tag '{tag_type}': {content}")
        print(f"ERROR: Line {line_num}: Unclosed tag '{tag_type}': {content}")
    
    print(f"\nSummary:")
    print(f"Total errors found: {len(errors)}")
    
    if errors:
        print("\nAll errors:")
        for error in errors:
            print(f"  {error}")
    else:
        print("No template syntax errors found!")
    
    return errors

if __name__ == "__main__":
    errors = check_template_syntax(template_path)
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)