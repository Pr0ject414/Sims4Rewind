# Sims4Rewind: Automatic Save Game Backup Tool

Sims4Rewind is a lightweight desktop application for Windows that automatically creates backups of your Sims 4 save files. It monitors your saves folder in real-time and uses file hashing to create backups only when a file has actually changed, saving disk space.

It's designed to be a "set it and forget it" tool that runs quietly in the system tray, giving you peace of mind that your precious saves are protected against corruption or accidental deletion.

*(You can take a screenshot of your app and place it in the project folder, then replace this text with: `![Application Screenshot](./screenshot.png)`)*

## Features

- **Automatic Backups:** Runs in the background and automatically backs up any changed `.save` file.
- **Efficient Hashing:** Compares file content hashes to prevent creating duplicate, unnecessary backups of unchanged files.
- **Configurable History:** Set how many backups you want to keep per save file. The oldest ones are automatically pruned.
- **Enhanced Restore Options:**
    - **Easy Restore:** Restore any backup with a single click from a clear, time-sorted list.
    - **"Restore to..." Functionality:** Restore a backup to a custom location, allowing for safe inspection or testing without overwriting your live save.
- **Backup Compression (.zip):** Option to save backups as `.zip` files, significantly reducing disk space usage.
- **Detailed Activity Log:** A dedicated tab in the main window provides a timestamped history of all application actions and errors, aiding in troubleshooting.
- **Desktop Notifications:** Receive non-intrusive desktop notifications for key events like backup creation, monitoring status changes, and errors.
- **Filterable View:** Easily filter the backup list to show backups for a specific save slot.
- **System Tray Integration:** Hides neatly in the system tray. The main window can be opened anytime from the tray icon.
- **Run on Startup:** Can be configured to launch automatically when you log in to Windows.

## How to Use (For Users)

1.  Download the latest release (`Sims4Rewind_vX.X.zip`) from the project's Releases page.
2.  Unzip the downloaded file. You will get a folder named `Sims4Rewind`.
3.  Run the `Sims4Rewind.exe` file inside that folder.

### First-Time Setup
- The first time you run the app, you will need to configure the paths.
- **Sims 4 Saves Folder:** Click "Browse..." and navigate to your saves folder. This is typically located at `Documents\Electronic Arts\The Sims 4\saves`.
- **Backup Location:** Click "Browse..." and choose an empty folder where you want to store your backups. It is highly recommended to use a folder on a separate physical drive if possible.
- **Start Monitoring:** Once configured, click the "Start Monitoring" button. The application will now run in the background. You can close the main window; it will minimize to the system tray.

> **Important:** If you enable "Start with Windows", do not move the application folder afterwards. If you need to move it, please disable the startup option first, move the folder, and then re-enable it to update the shortcut.

> **Note on Antivirus/Windows SmartScreen:**
> Because this is an unofficial application, Windows may show a security warning ("Windows protected your PC"). This is a standard precaution.
>
> To run the app, click **"More info"** on the blue screen, then click the **"Run anyway"** button. The application is completely safe and open-source.

## How to Build from Source (For Developers)

If you want to modify or build the application yourself, follow these steps.

### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads/)

### Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Sims4Rewind.git
    cd Sims4Rewind
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
3.  **Install the dependencies:**
    ```bash
    pip install PyQt6 watchdog Pillow pywin32 requests
    ```

### Running the Application
- To run the app in development mode:
  ```bash
  python app.py
  ```
- To run tests and clean up temporary files:
  ```bash
  python run_tests_and_clean.py
  ```
- To update the application icon from a new image in the `icon_source` folder:
  ```bash
  python update_icon.py
  ```
- To build the final distributable `.zip` file:
  ```bash
  python build.py
  ```
  The final package will be located in the `dist` folder.

---
This project was created with Python and the PyQt6 framework.

## Recent Refactoring
The application's internal structure has been significantly refactored to improve modularity, maintainability, and testability. Key changes include:
-   Separation of UI (View), business logic (Service), and UI state (ViewModel) into distinct modules.
-   Implementation of Dependency Injection for cleaner component management.
-   Improved test coverage and reliability through isolated unit and integration tests.