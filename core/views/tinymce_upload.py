"""
TinyMCE image upload handler with automatic compression
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.conf import settings
from core.image_utils import optimize_uploaded_image
import os
from datetime import datetime


@login_required
@csrf_exempt  # TinyMCE doesn't send CSRF token by default
def tinymce_upload_image(request):
    """
    Handle image uploads from TinyMCE editor with automatic compression
    Returns JSON with image location URL
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    
    uploaded_file = request.FILES['file']
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if uploaded_file.content_type not in allowed_types:
        return JsonResponse({
            'error': f'Invalid file type. Allowed: {", ".join(allowed_types)}'
        }, status=400)
    
    # Validate file size (max 10MB before compression)
    max_size = 10 * 1024 * 1024  # 10MB
    if uploaded_file.size > max_size:
        return JsonResponse({
            'error': f'File too large. Maximum size: {max_size / 1024 / 1024}MB'
        }, status=400)
    
    try:
        # Optimize/compress image automatically
        original_size = uploaded_file.size
        optimized_file = optimize_uploaded_image(uploaded_file)
        compressed_size = optimized_file.size
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'email_images/{timestamp}_{optimized_file.name}'
        
        # Save file using default storage (DO Spaces or local)
        file_path = default_storage.save(filename, optimized_file)
        
        # Get full URL
        file_url = default_storage.url(file_path)
        
        # Log compression results
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        print(f"Image uploaded: {file_path}")
        print(f"Size: {original_size / 1024:.1f}KB → {compressed_size / 1024:.1f}KB ({compression_ratio:.1f}% reduction)")
        
        return JsonResponse({
            'location': file_url
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Upload failed: {str(e)}'
        }, status=500)
