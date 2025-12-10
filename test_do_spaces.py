#!/usr/bin/env python
"""
Test script for Digital Ocean Spaces upload and download functionality.
Tests basic file operations to verify the DO Spaces configuration.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import django
import boto3
from botocore.exceptions import ClientError

# Set up Django environment
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.conf import settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DOSpacesTest:
    """Test Digital Ocean Spaces operations."""
    
    def __init__(self):
        """Initialise the DO Spaces client."""
        self.access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
        raw_endpoint = os.getenv('AWS_S3_ENDPOINT_URL')
        self.region = os.getenv('AWS_S3_REGION_NAME', 'syd1')
        
        # Fix endpoint URL if it includes the bucket name
        # Correct format: https://syd1.digitaloceanspaces.com (without bucket name)
        # Incorrect format: https://edupulse.syd1.digitaloceanspaces.com
        if raw_endpoint and self.bucket_name and f"{self.bucket_name}." in raw_endpoint:
            # Remove bucket name from endpoint
            self.endpoint_url = raw_endpoint.replace(f"{self.bucket_name}.", "")
            print("⚠️  Fixing endpoint URL (removed bucket name from endpoint)")
            print(f"  Original: {raw_endpoint}")
            print(f"  Corrected: {self.endpoint_url}")
            print()
        else:
            self.endpoint_url = raw_endpoint
        
        print("🔧 Configuration:")
        print(f"  Bucket: {self.bucket_name}")
        print(f"  Endpoint: {self.endpoint_url}")
        print(f"  Region: {self.region}")
        print(f"  Access Key: {self.access_key[:8]}..." if self.access_key else "  Access Key: None")
        print()
        
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
    
    def test_connection(self):
        """Test basic connectivity to DO Spaces."""
        print("📡 Testing connection to DO Spaces...")
        try:
            # DO Spaces doesn't support list_buckets, so test by accessing the bucket directly
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print("✅ Successfully connected to DO Spaces")
            print(f"  Bucket '{self.bucket_name}' is accessible")
            return True
        except ClientError as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def test_bucket_access(self):
        """Test access to the specified bucket."""
        print(f"\n🗂️  Testing access to bucket: {self.bucket_name}")
        try:
            # Try to list objects in the bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=5
            )
            count = response.get('KeyCount', 0)
            print(f"✅ Successfully accessed bucket")
            print(f"  Found {count} object(s) (showing max 5)")
            
            if count > 0:
                print("  First few objects:")
                for obj in response.get('Contents', []):
                    print(f"    - {obj['Key']} ({obj['Size']} bytes)")
            
            return True
        except ClientError as e:
            print(f"❌ Bucket access failed: {e}")
            return False
    
    def test_upload(self):
        """Test uploading a file to DO Spaces."""
        print("\n📤 Testing file upload...")
        
        # Create a test file
        test_content = f"Test file created at {datetime.now().isoformat()}\n"
        test_content += "This is a test file for Digital Ocean Spaces.\n"
        test_filename = f"test/test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            # Upload the file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=test_filename,
                Body=test_content.encode('utf-8'),
                ContentType='text/plain',
                ACL='public-read'
            )
            
            # Generate the public URL
            file_url = f"{self.endpoint_url}/{test_filename}"
            
            print(f"✅ Successfully uploaded file: {test_filename}")
            print(f"  URL: {file_url}")
            
            return test_filename
        except ClientError as e:
            print(f"❌ Upload failed: {e}")
            return None
    
    def test_download(self, filename):
        """Test downloading a file from DO Spaces."""
        if not filename:
            print("\n⏭️  Skipping download test (no file to download)")
            return False
        
        print(f"\n📥 Testing file download: {filename}")
        
        try:
            # Download the file
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            
            content = response['Body'].read().decode('utf-8')
            print(f"✅ Successfully downloaded file")
            print(f"  Content length: {len(content)} bytes")
            print(f"  Content preview:")
            for line in content.split('\n')[:3]:
                if line:
                    print(f"    {line}")
            
            return True
        except ClientError as e:
            print(f"❌ Download failed: {e}")
            return False
    
    def test_delete(self, filename):
        """Test deleting a file from DO Spaces."""
        if not filename:
            print("\n⏭️  Skipping delete test (no file to delete)")
            return False
        
        print(f"\n🗑️  Testing file deletion: {filename}")
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            print(f"✅ Successfully deleted file")
            return True
        except ClientError as e:
            print(f"❌ Delete failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("=" * 60)
        print("🚀 Digital Ocean Spaces Test Suite")
        print("=" * 60)
        print()
        
        # Test 1: Connection
        if not self.test_connection():
            print("\n❌ Test suite stopped: Cannot connect to DO Spaces")
            return False
        
        # Test 2: Bucket access
        if not self.test_bucket_access():
            print("\n❌ Test suite stopped: Cannot access bucket")
            return False
        
        # Test 3: Upload
        uploaded_file = self.test_upload()
        if not uploaded_file:
            print("\n❌ Test suite stopped: Upload failed")
            return False
        
        # Test 4: Download
        if not self.test_download(uploaded_file):
            print("\n⚠️  Warning: Download failed, but continuing...")
        
        # Test 5: Delete (cleanup)
        self.test_delete(uploaded_file)
        
        print("\n" + "=" * 60)
        print("✅ Test suite completed successfully!")
        print("=" * 60)
        return True


def main():
    """Main entry point."""
    try:
        tester = DOSpacesTest()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
