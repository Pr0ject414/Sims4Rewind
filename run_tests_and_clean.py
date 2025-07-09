import subprocess
import shutil
import os

def run_tests_and_clean():
    print("Running tests...")
    # Run pytest and capture its return code
    result = subprocess.run(['pytest'], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print("Tests passed. Deleting __pycache__ and .pytest_cache folders...")
        
        # Delete __pycache__ folders
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                shutil.rmtree(os.path.join(root, '__pycache__'))
                print(f"Deleted: {os.path.join(root, '__pycache__')}")
        
        # Delete .pytest_cache folder
        if os.path.exists('.pytest_cache'):
            shutil.rmtree('.pytest_cache')
            print("Deleted: .pytest_cache")
            
        print("Cleanup complete.")
    else:
        print(f"Tests failed with exit code {result.returncode}. Skipping cleanup.")

if __name__ == "__main__":
    run_tests_and_clean()
