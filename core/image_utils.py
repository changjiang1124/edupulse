"""
Image compression utilities for optimizing uploaded images
"""
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


# Compression thresholds (best practices)
MAX_IMAGE_WIDTH = 1920  # Maximum width in pixels
MAX_IMAGE_HEIGHT = 1920  # Maximum height in pixels
MAX_FILE_SIZE = 500 * 1024  # 500KB
JPEG_QUALITY = 85  # Quality for JPEG compression (85 is optimal)
WEBP_QUALITY = 85  # Quality for WebP compression


def should_compress_image(image_file):
    """
    Determine if image needs compression based on file size
    
    Args:
        image_file: UploadedFile object
        
    Returns:
        bool: True if compression is needed
    """
    return image_file.size > MAX_FILE_SIZE


def compress_image(image_file, force_jpeg=False):
    """
    Compress and optimize an image file
    
    Args:
        image_file: UploadedFile object
        force_jpeg: Convert PNG to JPEG (unless transparency needed)
        
    Returns:
        InMemoryUploadedFile: Compressed image file
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if forcing JPEG (preserve transparency if needed)
        original_format = img.format
        has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
        
        if force_jpeg and not has_transparency and img.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB for JPEG
            if img.mode == 'P':
                img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            else:
                background.paste(img)
            img = background
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        # Resize if too large
        if img.width > MAX_IMAGE_WIDTH or img.height > MAX_IMAGE_HEIGHT:
            img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
        
        # Determine output format
        if has_transparency and not force_jpeg:
            output_format = 'PNG'
            save_kwargs = {'optimize': True}
        else:
            output_format = 'JPEG'
            save_kwargs = {'quality': JPEG_QUALITY, 'optimize': True}
        
        # Save to BytesIO
        output = BytesIO()
        img.save(output, format=output_format, **save_kwargs)
        output.seek(0)
        
        # Create new InMemoryUploadedFile
        file_extension = 'jpg' if output_format == 'JPEG' else 'png'
        original_name = image_file.name
        name_without_ext = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
        new_filename = f"{name_without_ext}.{file_extension}"
        
        compressed_file = InMemoryUploadedFile(
            output,
            'ImageField',
            new_filename,
            f'image/{file_extension}',
            sys.getsizeof(output),
            None
        )
        
        return compressed_file
        
    except Exception as e:
        print(f"Image compression failed: {e}")
        # Return original file if compression fails
        image_file.seek(0)
        return image_file


def optimize_uploaded_image(image_file):
    """
    Main function to optimize uploaded images
    Automatically determines if compression is needed
    
    Args:
        image_file: UploadedFile object
        
    Returns:
        UploadedFile: Optimized image (or original if no optimization needed)
    """
    if not should_compress_image(image_file):
        # Image is already small enough
        return image_file
    
    # Compress the image
    return compress_image(image_file, force_jpeg=True)
