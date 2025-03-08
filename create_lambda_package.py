import os
import subprocess
import shutil
import zipfile
import sys

# Configuration
OUTPUT_DIR = "lambda_package"
ZIP_FILENAME = "lambda.zip"

print("Creating Lambda deployment package...")

# Clean previous builds
if os.path.exists(OUTPUT_DIR):
    print(f"Removing existing {OUTPUT_DIR} directory...")
    shutil.rmtree(OUTPUT_DIR)
if os.path.exists(ZIP_FILENAME):
    print(f"Removing existing {ZIP_FILENAME} file...")
    os.remove(ZIP_FILENAME)

# Create output directory
os.makedirs(OUTPUT_DIR)
print(f"Created {OUTPUT_DIR} directory")

# Create a requirements.txt file manually
print("Creating requirements.txt file...")
requirements = [
    "boto3>=1.24.0",
    "mangum>=0.14.0",
    "uvicorn>=0.15.0",
    "fastapi>=0.100",
    "pydantic>=2.0",
    "numpy>=2.2.3"
]

with open("requirements.txt", "w") as f:
    f.write("\n".join(requirements))

# Install dependencies into package directory
print("Installing dependencies from requirements.txt...")
try:
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "-r", "requirements.txt",
        "--target", OUTPUT_DIR
    ], check=True)
    print("Successfully installed dependencies")
except subprocess.CalledProcessError as e:
    print(f"Error installing dependencies: {str(e)}")
    sys.exit(1)

# Copy application code
print("Copying application code...")
try:
    shutil.copytree("RockPaperScissor", os.path.join(OUTPUT_DIR, "RockPaperScissor"))
    print("Successfully copied application code")
except Exception as e:
    print(f"Error copying application code: {str(e)}")
    sys.exit(1)

# Create zip file
print("Creating ZIP file...")
try:
    with zipfile.ZipFile(ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, OUTPUT_DIR)
                zipf.write(file_path, arcname)
    
    zip_size = os.path.getsize(ZIP_FILENAME) / (1024 * 1024)  # Convert to MB
    print(f"Lambda package created: {ZIP_FILENAME} ({zip_size:.2f} MB)")
except Exception as e:
    print(f"Error creating ZIP file: {str(e)}")
    sys.exit(1)

print("Lambda package creation complete!")