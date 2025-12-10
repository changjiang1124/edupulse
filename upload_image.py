#!/usr/bin/env python
"""
Image upload utility for Digital Ocean Spaces.
Uploads images to DO Spaces and returns the public URL.

Usage:
    python upload_image.py path/to/image.jpg
    python upload_image.py path/to/folder/  # Upload all images in folder
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import mimetypes

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ImageUploader:
    """Upload images to Digital Ocean Spaces."""
    
    # Supported image formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
    
    def __init__(self):
        """Initialise the DO Spaces client."""
        self.access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
        raw_endpoint = os.getenv('AWS_S3_ENDPOINT_URL')
        self.region = os.getenv('AWS_S3_REGION_NAME', 'syd1')
        
        # Fix endpoint URL if it includes the bucket name
        if raw_endpoint and self.bucket_name and f"{self.bucket_name}." in raw_endpoint:
            self.endpoint_url = raw_endpoint.replace(f"{self.bucket_name}.", "")
        else:
            self.endpoint_url = raw_endpoint
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.endpoint_url]):
            raise ValueError("Missing required DO Spaces configuration in .env file")
        
        # Create S3 client for DO Spaces
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
    
    def is_image_file(self, file_path):
        """Check if the file is a supported image format."""
        return Path(file_path).suffix.lower() in self.SUPPORTED_FORMATS
    
    def get_content_type(self, file_path):
        """Determine the content type of the file."""
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'
    
    def upload_image(self, local_path, remote_path=None, folder='images'):
        """
        Upload an image to DO Spaces.
        
        Args:
            local_path: Path to the local image file
            remote_path: Optional custom path in the bucket (e.g., 'custom/folder/image.jpg')
            folder: Default folder to upload to (default: 'images')
        
        Returns:
            Public URL of the uploaded image, or None if failed
        """
        local_path = Path(local_path)
        
        if not local_path.exists():
            print(f"❌ File not found: {local_path}")
            return None
        
        if not local_path.is_file():
            print(f"❌ Not a file: {local_path}")
            return None
        
        if not self.is_image_file(local_path):
            print(f"❌ Not a supported image format: {local_path}")
            print(f"   Supported formats: {', '.join(self.SUPPORTED_FORMATS)}")
            return None
        
        # Generate remote path if not provided
        if remote_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{local_path.name}"
            remote_path = f"{folder}/{filename}"
        
        try:
            # Read and upload the file
            with open(local_path, 'rb') as f:
                content_type = self.get_content_type(str(local_path))
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=remote_path,
                    Body=f.read(),
                    ContentType=content_type,
                    ACL='public-read'
                )
            
            # Generate the public URL
            file_url = f"{self.endpoint_url}/{self.bucket_name}/{remote_path}"
            
            return file_url
            
        except ClientError as e:
            print(f"❌ Upload failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def upload_directory(self, directory_path, folder='images'):
        """
        Upload all images in a directory.
        
        Args:
            directory_path: Path to the directory containing images
            folder: Folder to upload to in DO Spaces
        
        Returns:
            List of tuples (local_path, url) for successfully uploaded images
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            print(f"❌ Directory not found: {directory_path}")
            return []
        
        if not directory_path.is_dir():
            print(f"❌ Not a directory: {directory_path}")
            return []
        
        # Find all image files
        image_files = [
            f for f in directory_path.iterdir()
            if f.is_file() and self.is_image_file(f)
        ]
        
        if not image_files:
            print(f"⚠️  No image files found in: {directory_path}")
            return []
        
        print(f"📁 Found {len(image_files)} image(s) to upload")
        print()
        
        results = []
        for idx, image_file in enumerate(image_files, 1):
            print(f"[{idx}/{len(image_files)}] Uploading: {image_file.name}")
            url = self.upload_image(image_file, folder=folder)
            
            if url:
                print(f"✅ Success: {url}")
                results.append((str(image_file), url))
            else:
                print(f"❌ Failed to upload: {image_file.name}")
            print()
        
        return results


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("📸 Image Upload Utility for Digital Ocean Spaces")
        print()
        print("Usage:")
        print("  python upload_image.py <file_or_directory> [folder]")
        print()
        print("Examples:")
        print("  python upload_image.py photo.jpg")
        print("  python upload_image.py photo.jpg student_photos")
        print("  python upload_image.py ./photos/")
        print("  python upload_image.py ./photos/ event_photos")
        print()
        print("Supported formats: .jpg, .jpeg, .png, .gif, .webp, .svg, .bmp, .ico")
        sys.exit(1)
    
    path = sys.argv[1]
    folder = sys.argv[2] if len(sys.argv) > 2 else 'images'
    
    try:
        uploader = ImageUploader()
        
        path_obj = Path(path)
        
        if path_obj.is_file():
            # Upload single file
            print(f"📤 Uploading: {path_obj.name}")
            print()
            
            url = uploader.upload_image(path_obj, folder=folder)
            
            if url:
                print(f"✅ Upload successful!")
                print(f"📎 URL: {url}")
                print()
                print("Copy the URL above to use in your application.")
                sys.exit(0)
            else:
                print("❌ Upload failed")
                sys.exit(1)
        
        elif path_obj.is_dir():
            # Upload directory
            results = uploader.upload_directory(path_obj, folder=folder)
            
            if results:
                print("=" * 60)
                print(f"✅ Successfully uploaded {len(results)} image(s)")
                print("=" * 60)
                print()
                print("Uploaded URLs:")
                for local_path, url in results:
                    print(f"  {Path(local_path).name}")
                    print(f"  → {url}")
                    print()
                sys.exit(0)
            else:
                print("❌ No images were uploaded")
                sys.exit(1)
        
        else:
            print(f"❌ Path not found: {path}")
            sys.exit(1)
    
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print()
        print("Please check your .env file configuration.")
        print("See docs/DO_SPACES_SETUP.md for details.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
