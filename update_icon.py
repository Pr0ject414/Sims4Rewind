# =====================================================================
# FILE: update_icon.py
# =====================================================================
# This script automates the process of updating the application icon.
# It takes an image from the 'icon_source' folder, converts it to a
# multi-size .ico file, saves it, base64 encodes it, and updates resources.py.

import os
import base64
import io
import re
import sys

# --- Configuration ---
# Get the absolute path of the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_IMAGE_FOLDER = os.path.join(SCRIPT_DIR, "icon_source")
RESOURCES_FILE = os.path.join(SCRIPT_DIR, "resources.py")
ICON_VARIABLE_NAME = "ICON_DATA_REWIND"
OUTPUT_ICON_FILE = os.path.join(SCRIPT_DIR, "app.ico") # <-- ADDED: Path for the output .ico

def update_icon_resource(Image):
    """
    Finds an image, converts it to a base64-encoded .ico in memory,
    and updates the resources file.

    Args:
        Image: The Pillow Image module.
    """
    # 1. Find the source image
    source_image_path = None
    try:
        for file in os.listdir(SOURCE_IMAGE_FOLDER):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                source_image_path = os.path.join(SOURCE_IMAGE_FOLDER, file)
                break
    except FileNotFoundError:
        print(f"Error: The source directory '{SOURCE_IMAGE_FOLDER}' was not found.")
        sys.exit(1)

    if not source_image_path:
        print(f"Error: No image file found in the '{SOURCE_IMAGE_FOLDER}' directory.")
        sys.exit(1)

    print(f"Processing image: {source_image_path}")

    # 2. Convert image to a multi-size .ico file
    try:
        img = Image.open(source_image_path)
        icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # --- CHANGE: Save the icon to a physical file for PyInstaller ---
        img.save(OUTPUT_ICON_FILE, format='ICO', sizes=icon_sizes)
        print(f"Successfully created icon file: {OUTPUT_ICON_FILE}")

        # Use an in-memory binary stream for the base64 encoding
        with io.BytesIO() as ico_stream:
            img.save(ico_stream, format='ICO', sizes=icon_sizes)
            ico_data = ico_stream.getvalue()

    except Exception as e:
        print(f"Error converting image to .ico: {e}")
        sys.exit(1)

    # 3. Base64 encode the .ico data
    encoded_data = base64.b64encode(ico_data)

    # 4. Update the resources.py file
    try:
        with open(RESOURCES_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = re.compile(
            f"({ICON_VARIABLE_NAME}\\s*=\\s*b(""" + r'"""' + r"|'''))" +
            f".*?" +
            r"(\2)",
            re.DOTALL
        )

        formatted_data = '\n'.join(encoded_data.decode('ascii')[i:i+78] for i in range(0, len(encoded_data), 78))

        def replacer(match):
            return f"{match.group(1)}\n{formatted_data}\n{match.group(3)}"

        new_content, num_replacements = pattern.subn(replacer, content)

        if num_replacements == 0:
            print(f"Error: Could not find the variable '{ICON_VARIABLE_NAME}' in {RESOURCES_FILE}.")
            print("Please ensure the file contains a block like: ICON_DATA_REWIND = b'''...''' or b\"\"\"...\"\"\"")
            sys.exit(1)

        with open(RESOURCES_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"Successfully updated '{ICON_VARIABLE_NAME}' in {RESOURCES_FILE}.")

    except FileNotFoundError:
        print(f"Error: The resources file '{RESOURCES_FILE}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while updating {RESOURCES_FILE}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("Error: The 'Pillow' library is required to run this script.", file=sys.stderr)
        print("Please install it using your preferred package manager, e.g., 'pip install Pillow'", file=sys.stderr)
        sys.exit(1)
    else:
        update_icon_resource(Image)