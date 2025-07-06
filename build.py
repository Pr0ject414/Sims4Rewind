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

# --- Configuration ---
APP_NAME = "Sims4Rewind"
APP_VERSION = "1.0"  # You can update this version number for future releases
ENTRY_POINT = "main.py"
ICON_UPDATER_SCRIPT = "update_icon.py"
ICON_FILE = "app.ico"

# --- Derived Configuration ---
DIST_DIR = 'dist'
RELEASE_DIR_NAME = f"{APP_NAME}" # The name of the folder inside the zip
RELEASE_DIR_PATH = os.path.join(DIST_DIR, RELEASE_DIR_NAME)
ARCHIVE_NAME = f"{APP_NAME}_v{APP_VERSION}"

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

def main():
    """Main function to run the build process."""
    print(f"Starting build process for {APP_NAME} v{APP_VERSION}...")

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
        shutil.make_archive(archive_path_without_ext, 'zip', RELEASE_DIR_PATH)
        print(f"Successfully created archive: {archive_path_without_ext}.zip")
        print("Success!\n")
    except Exception as e:
        print(f"ERROR: Failed to create zip archive: {e}")
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
    print(f"BUILD COMPLETE! Your distributable file is ready:")
    print(os.path.abspath(f"{os.path.join(DIST_DIR, ARCHIVE_NAME)}.zip"))
    print("=========================================================")

if __name__ == "__main__":
    main()