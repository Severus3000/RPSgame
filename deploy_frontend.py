import boto3
import os
import mimetypes
import sys

# Configuration
S3_BUCKET_NAME = "rpsgame-bucket"  # Must match bucket name in aws_setup.py
FRONTEND_DIR = "frontend"
REGION = "us-east-1"

# Initialize S3 client
s3_client = boto3.client('s3', region_name=REGION)

def upload_file(file_path, bucket, key):
    """Upload a file to S3 bucket"""
    # Determine content type based on file extension
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'
    
    extra_args = {'ContentType': content_type}
    
    # Add caching headers for different file types
    if file_path.endswith('.html'):
        extra_args['CacheControl'] = 'max-age=300'  # 5 minutes for HTML
    elif file_path.endswith('.css') or file_path.endswith('.js'):
        extra_args['CacheControl'] = 'max-age=86400'  # 1 day for CSS/JS
    elif file_path.endswith('.jpg') or file_path.endswith('.png') or file_path.endswith('.gif'):
        extra_args['CacheControl'] = 'max-age=604800'  # 1 week for images
    
    print(f"Uploading: {file_path} -> s3://{bucket}/{key}")
    try:
        s3_client.upload_file(file_path, bucket, key, ExtraArgs=extra_args)
        return True
    except Exception as e:
        print(f"Upload error: {e}")
        return False

def deploy_frontend():
    """Deploy the frontend files to S3"""
    # Check if frontend directory exists
    if not os.path.isdir(FRONTEND_DIR):
        print(f"Frontend directory '{FRONTEND_DIR}' not found!")
        return False
    
    # First, try to read the API URL from file
    api_url = None
    try:
        with open("api_url.txt", "r") as f:
            api_url = f.read().strip()
        print(f"Using API URL: {api_url}")
    except FileNotFoundError:
        print("api_url.txt not found. Make sure to run aws_setup.py first.")
        return False
    
    # Update the frontend code to use the API URL
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            content = f.read()
        
        # Replace API_ENDPOINT_URL with the actual API Gateway URL
        content = content.replace("API_ENDPOINT_URL", api_url)
        
        # Write updated content back
        with open(index_path, "w") as f:
            f.write(content)
        print("Updated index.html with API URL")
    else:
        print(f"index.html not found in {FRONTEND_DIR}!")
        return False
    
    success_count = 0
    error_count = 0
    
    # Walk through the frontend directory and upload files
    for root, dirs, files in os.walk(FRONTEND_DIR):
        for file in files:
            local_path = os.path.join(root, file)
            # Remove the frontend directory prefix for the S3 key
            s3_key = os.path.relpath(local_path, FRONTEND_DIR)
            
            if upload_file(local_path, S3_BUCKET_NAME, s3_key):
                success_count += 1
            else:
                error_count += 1
    
    print(f"Deployment complete: {success_count} files uploaded, {error_count} errors")
    
    # Print the website URL
    website_url = f"http://{S3_BUCKET_NAME}.s3-website-{REGION}.amazonaws.com"
    print(f"Website available at: {website_url}")
    return True

if __name__ == "__main__":
    print("Deploying frontend to S3...")
    if deploy_frontend():
        print("Frontend deployment successful!")
    else:
        print("Frontend deployment failed!")
        sys.exit(1)