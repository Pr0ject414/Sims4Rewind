# =====================================================================
# FILE: build.py
# =====================================================================
# This script automates the entire build process for the Sims4Rewind
# application. It updates resources, packages the application, organizes
# the output into a folder, creates a distributable .zip archive, and
# cleans up all temporary files.
#
# To use, simply run: python build.py
# =====================================================================

import os
import sys
import shutil
import subprocess
import hashlib
import crypto_utils # Import the new crypto_utils

# --- Configuration ---
APP_NAME = "Sims4Rewind"

def get_app_version(app_file):
    """Reads the app.py file to extract the __version__ string."""
    with open(app_file, 'r') as f:
        for line in f:
            if '__version__' in line:
                # Extract version string, e.g., __version__ = "1.0.0"
                version = line.split('=')[1].strip().strip('\'"')
                return version
    raise RuntimeError("__version__ not found in app.py")

ENTRY_POINT = "app.py"

APP_VERSION = get_app_version(ENTRY_POINT)
ICON_UPDATER_SCRIPT = "update_icon.py"
ICON_FILE = "app.ico"

# --- Derived Configuration ---
DIST_DIR = 'dist'
RELEASE_DIR_NAME = f"{APP_NAME}" # The name of the folder inside the zip
RELEASE_DIR_PATH = os.path.join(DIST_DIR, RELEASE_DIR_NAME)
ARCHIVE_NAME = f"{APP_NAME}_latest"
HASH_FILE_NAME = "hash.txt"
SIGNATURE_FILE_NAME = "signature.sig"
PUBLIC_KEY_FILE_NAME = "public_key.pem"
PRIVATE_KEY_FILE_NAME = "private_key.pem"

def run_command(command, description):
    """Runs a command and checks for errors."""
    print(f"--- {description} ---")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            cwd=script_dir
        )
        print(result.stdout)
        print("Success!\n")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed.")
        print(f"Return Code: {e.returncode}")
        print("\n--- STDOUT ---")
        print(e.stdout)
        print("\n--- STDERR ---")
        print(e.stderr)
        sys.exit(1)

def calculate_file_hash(file_path, hash_algo=hashlib.sha256):
    """Calculates the hash of a file."""
    hasher = hash_algo()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    """Main function to run the build process."""
    print(f"Starting build process for {APP_NAME} v{APP_VERSION}...")

    # Ensure keys exist for signing
    if not os.path.exists(PRIVATE_KEY_FILE_NAME) or not os.path.exists(PUBLIC_KEY_FILE_NAME):
        print("--- Generating RSA keys for signing ---")
        crypto_utils.generate_keys(PRIVATE_KEY_FILE_NAME, PUBLIC_KEY_FILE_NAME)

    # Step 1: Run the icon updater script
    run_command(
        [sys.executable, ICON_UPDATER_SCRIPT],
        "Step 1: Updating icon resources"
    )

    # Step 2: Run PyInstaller
    pyinstaller_command = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--icon={ICON_FILE}",
        "--add-data=private_update/updater_config.py;private_update",
        "--add-data=private_update/updater_google_drive.py;private_update",
        "--add-data=private_update/updater.py;private_update",
        "--add-data=private_update/version.py;private_update",
        "--add-data=public_key.pem;.", # Add public key to the app bundle
        ENTRY_POINT
    ]
    run_command(pyinstaller_command, "Step 2: Packaging application with PyInstaller")

    # Step 3: Organize output files
    print("--- Step 3: Organizing release files ---")
    try:
        if os.path.exists(RELEASE_DIR_PATH):
            shutil.rmtree(RELEASE_DIR_PATH) # Clean up from previous build if it exists
        os.makedirs(RELEASE_DIR_PATH)
        print(f"Created release directory: {RELEASE_DIR_PATH}")

        original_exe = os.path.join(DIST_DIR, f"{os.path.splitext(ENTRY_POINT)[0]}.exe")
        destination_exe = os.path.join(RELEASE_DIR_PATH, f"{APP_NAME}.exe")
        
        print(f"Moving '{original_exe}' to '{destination_exe}'")
        shutil.move(original_exe, destination_exe)
        print("Success!\n")
    except Exception as e:
        print(f"ERROR: Failed to organize release files: {e}")
        sys.exit(1)

    # Step 4: Create zip archive
    print("--- Step 4: Creating distributable .zip archive ---")
    try:
        archive_path_without_ext = os.path.join(DIST_DIR, ARCHIVE_NAME)
        final_zip_path = f"{archive_path_without_ext}.zip"
        shutil.make_archive(archive_path_without_ext, 'zip', RELEASE_DIR_PATH)
        print(f"Successfully created archive: {final_zip_path}")
        
        # Calculate hash of the created zip file
        zip_hash = calculate_file_hash(final_zip_path)
        print(f"Calculated hash of {os.path.basename(final_zip_path)}: {zip_hash}")

        # Create hash.txt file
        hash_file_path = os.path.join(DIST_DIR, HASH_FILE_NAME)
        with open(hash_file_path, 'w') as f:
            f.write(zip_hash)
        print(f"Created hash file: {hash_file_path}")

        # Create version.txt file in the main directory
        version_file_path = "version.txt"
        with open(version_file_path, 'w') as f:
            f.write(APP_VERSION)
        print(f"Created version file: {version_file_path}")

        # Sign the zip file
        signature_file_path = os.path.join(DIST_DIR, SIGNATURE_FILE_NAME)
        crypto_utils.sign_file(final_zip_path, PRIVATE_KEY_FILE_NAME, signature_file_path)

        # Step 4.1: Move the zip file, hash file, signature file, and version file to the Google Drive location
        google_drive_path = r"G:\My Drive\Sims4Rewind"
        
        destination_zip_path = os.path.join(google_drive_path, os.path.basename(final_zip_path))
        destination_hash_path = os.path.join(google_drive_path, HASH_FILE_NAME)
        destination_signature_path = os.path.join(google_drive_path, SIGNATURE_FILE_NAME)
        destination_version_path = os.path.join(google_drive_path, os.path.basename(version_file_path))
        
        print(f"Moving {final_zip_path} to {destination_zip_path}")
        shutil.move(final_zip_path, destination_zip_path)
        print("Successfully moved zip to Google Drive location!")

        print(f"Moving {hash_file_path} to {destination_hash_path}")
        shutil.move(hash_file_path, destination_hash_path)
        print("Successfully moved hash file to Google Drive location!")

        print(f"Moving {signature_file_path} to {destination_signature_path}")
        shutil.move(signature_file_path, destination_signature_path)
        print("Successfully moved signature file to Google Drive location!")

        print(f"Moving {version_file_path} to {destination_version_path}")
        shutil.move(version_file_path, destination_version_path)
        print("Successfully moved version file to Google Drive location!")
        
        print("Success!\n")
    except Exception as e:
        print(f"ERROR: Failed to create zip archive or move files: {e}")
        sys.exit(1)

    # Step 5: Final cleanup
    print("--- Step 5: Cleaning up temporary files ---")
    try:
        shutil.rmtree('build')
        print("Removed 'build' directory.")
        
        spec_file = f"{os.path.splitext(ENTRY_POINT)[0]}.spec"
        os.remove(spec_file)
        print(f"Removed '{spec_file}' file.")
        
        shutil.rmtree(RELEASE_DIR_PATH)
        print(f"Removed temporary release directory: {RELEASE_DIR_PATH}")
        print("Success!\n")
    except Exception as e:
        print(f"Warning: Failed during cleanup, but build is complete. Error: {e}")

    print("=========================================================")
    print("BUILD COMPLETE! Your distributable file is ready:")
    print(os.path.abspath(f"{os.path.join(DIST_DIR, ARCHIVE_NAME)}.zip"))
    print("=========================================================")

if __name__ == "__main__":
    main()