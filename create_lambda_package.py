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

# Get Poetry virtual environment path
print("Finding Poetry virtual environment path...")
poetry_env_cmd = ["poetry", "env", "info", "-p"]
poetry_env_path = subprocess.check_output(poetry_env_cmd, universal_newlines=True).strip()
site_packages_path = os.path.join(poetry_env_path, "lib", "python3.13", "site-packages")  # Adjust for your Python version

if not os.path.exists(site_packages_path):
    print(f"Error: Poetry virtual environment path not found: {site_packages_path}")
    sys.exit(1)

print(f"Using Poetry virtual environment at: {site_packages_path}")

# Copy dependencies from Poetry's site-packages
print("Copying dependencies from Poetry virtual environment...")
shutil.copytree(site_packages_path, OUTPUT_DIR, dirs_exist_ok=True)

# Verify that pydantic_core is copied
pydantic_core_path = os.path.join(OUTPUT_DIR, "pydantic_core")
if not os.path.exists(pydantic_core_path):
    print("Error: pydantic_core is missing! Trying to install it manually...")

    # Manually install pydantic_core
    subprocess.run([
        sys.executable, "-m", "pip", "install", "pydantic-core",
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--target", OUTPUT_DIR
    ], check=True)

if os.path.exists(pydantic_core_path):
    print("✅ pydantic_core successfully copied!")
else:
    print("❌ Error: pydantic_core is still missing. Lambda may fail.")

# Copy application code
print("Copying application code...")
try:
    shutil.copytree("RockPaperScissor", os.path.join(OUTPUT_DIR, "RockPaperScissor"))
    print("Successfully copied application code")
except Exception as e:
    print(f"Error copying application code: {str(e)}")
    sys.exit(1)

# Create zip file with correct Lambda structure
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

    # Optional: Check if `pydantic_core` is inside the zip
    print("\nChecking for pydantic_core in ZIP file:")
    with zipfile.ZipFile(ZIP_FILENAME, 'r') as zipf:
        for name in zipf.namelist():
            if 'pydantic_core' in name or 'pydantic' in name:
                print(name)

except Exception as e:
    print(f"Error creating ZIP file: {str(e)}")
    sys.exit(1)

print("Lambda package creation complete!")
