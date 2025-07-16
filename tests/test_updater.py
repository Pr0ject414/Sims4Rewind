
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import tempfile
import shutil
import zipfile
import requests

# Add the project root to the path to allow importing the updater modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from private_update.updater_google_drive import GoogleDriveUpdater
from private_update import version as local_version
from private_update import updater_config
from private_update.updater import perform_update

class TestUpdaterCore(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory structure to simulate an app installation."""
        self.test_dir = tempfile.mkdtemp()
        self.app_dir = os.path.join(self.test_dir, 'Sims4Rewind')
        self.zip_dir = os.path.join(self.test_dir, 'zip_location')
        os.makedirs(self.app_dir)
        os.makedirs(self.zip_dir)

        # Create a dummy application file
        with open(os.path.join(self.app_dir, 'Sims4Rewind.exe'), 'w') as f:
            f.write('old version')

        # Create a dummy update zip
        self.zip_path = os.path.join(self.zip_dir, 'update.zip')
        with zipfile.ZipFile(self.zip_path, 'w') as zf:
            zf.writestr('Sims4Rewind.exe', 'new version')
            zf.writestr('new_file.txt', 'a new file')

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_perform_update_success(self):
        """Test the entire update process in a simulated environment."""
        mock_log = MagicMock()
        
        # --- Execution ---
        success, _ = perform_update(
            downloaded_zip_path=self.zip_path,
            app_install_dir=self.app_dir,
            executable_name='Sims4Rewind.exe',
            log_func=mock_log
        )

        # --- Assertions ---
        self.assertTrue(success)
        
        # Verify new files are in place
        self.assertTrue(os.path.exists(os.path.join(self.app_dir, 'Sims4Rewind.exe')))
        self.assertTrue(os.path.exists(os.path.join(self.app_dir, 'new_file.txt')))

        # Verify the content of the updated file
        with open(os.path.join(self.app_dir, 'Sims4Rewind.exe'), 'r') as f:
            self.assertEqual(f.read(), 'new version')

        # Verify the old backup directory was cleaned up
        self.assertFalse(os.path.exists(self.app_dir + '_old'))
        
        # Verify the zip file was cleaned up
        self.assertFalse(os.path.exists(self.zip_path))

        mock_log.assert_any_call("Updater: Cleaning up temporary files and old app backup.")


class TestGoogleDriveUpdater(unittest.TestCase):

    def setUp(self):
        """Set up a fresh updater instance for each test."""
        self.log_callback = MagicMock()
        self.updater = GoogleDriveUpdater(log_callback=self.log_callback)
        # Mock the User-Agent
        self.updater.user_agent = "Test-Agent/1.0"
        self.headers = {'User-Agent': self.updater.user_agent}

    def tearDown(self):
        """Clean up after each test."""
        # Ensure the SIGNATURE_TXT_URL is reset to its original value
        # This is important if a test modifies it (e.g., test_check_for_update_placeholder_url)
        updater_config.SIGNATURE_TXT_URL = "https://drive.google.com/uc?export=download&id=PLACEHOLDER_SIGNATURE_ID"

    @patch('private_update.updater_google_drive.requests.get')
    @patch('private_update.updater_google_drive.SIGNATURE_TXT_URL', "https://example.com/signature.txt")
    def test_check_for_update_new_version_available(self, mock_get):
        """Test that a new version is correctly detected."""
        mock_response = MagicMock()
        mock_response.text = "99.9.9"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        local_version.__version__ = "1.0.0" # Ensure local version is lower

        update_available, latest_version = self.updater.check_for_update()

        self.assertTrue(update_available)
        self.assertEqual(latest_version, "99.9.9")
        mock_get.assert_called_once_with(updater_config.VERSION_TXT_URL, headers=self.headers)
        self.log_callback.assert_any_call("New version 99.9.9 available!")

    @patch('private_update.updater_google_drive.requests.get')
    @patch('private_update.updater_google_drive.SIGNATURE_TXT_URL', "https://example.com/signature.txt")
    def test_check_for_update_no_new_version(self, mock_get):
        """Test that no update is detected when versions are the same."""
        mock_response = MagicMock()
        mock_response.text = "1.0.0"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        local_version.__version__ = "1.0.0"

        update_available, latest_version = self.updater.check_for_update()

        self.assertFalse(update_available)
        self.assertEqual(latest_version, "1.0.0")
        self.log_callback.assert_any_call("No new updates available.")

    @patch('private_update.updater_google_drive.requests.get')
    @patch('private_update.updater_google_drive.SIGNATURE_TXT_URL', "https://example.com/signature.txt")
    def test_check_for_update_network_error(self, mock_get):
        """Test that network errors are handled gracefully."""
        mock_get.side_effect = requests.exceptions.RequestException("Network Error")

        update_available, latest_version = self.updater.check_for_update()

        self.assertFalse(update_available)
        self.log_callback.assert_any_call("Error checking for updates: Network Error")

    def test_check_for_update_placeholder_url(self):
        """Test that the update check is skipped if the URL is a placeholder."""
        original_url = updater_config.SIGNATURE_TXT_URL
        updater_config.SIGNATURE_TXT_URL = "PLACEHOLDER"
        
        update_available, _ = self.updater.check_for_update()
        
        self.assertFalse(update_available)
        self.log_callback.assert_called_with("Update check skipped: Updater is not configured (placeholder URL found).")
        
        # Restore original value
        updater_config.SIGNATURE_TXT_URL = original_url

    @patch('private_update.updater_google_drive.crypto_utils')
    @patch('private_update.updater_google_drive.requests.get')
    @patch('private_update.updater_google_drive.SIGNATURE_TXT_URL', "https://example.com/signature.txt")
    @patch('builtins.open', new_callable=mock_open)
    def test_download_update_success(self, mock_open_file, mock_get, mock_crypto_utils):
        """Test the successful download and verification of an update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # --- Mock Setup ---
            mock_zip_content = b'zip_file_content'
            mock_hash_content = 'd3add13d87f6a4427812a6273382731009ed8422f5048e4855329258b3364039' # sha256 of 'zip_file_content'
            mock_sig_content = b'signature'

            # Mock the responses for zip, hash, and signature
            mock_zip_response = MagicMock()
            mock_zip_response.iter_content.return_value = [mock_zip_content]
            mock_zip_response.raise_for_status.return_value = None

            mock_hash_response = MagicMock()
            mock_hash_response.text = mock_hash_content
            mock_hash_response.raise_for_status.return_value = None
            
            mock_sig_response = MagicMock()
            mock_sig_response.content = mock_sig_content
            mock_sig_response.raise_for_status.return_value = None

            mock_get.side_effect = [
                mock_zip_response,
                mock_hash_response,
                mock_sig_response
            ]
            
            mock_crypto_utils.verify_signature.return_value = True
            
            # Mock _calculate_file_hash
            with patch.object(self.updater, '_calculate_file_hash', return_value=mock_hash_content):
                # Mock os.path.exists for the public key
                def mock_os_path_exists(path):
                    if "public_key.pem" in path:
                        return True
                    return False

                with patch('os.path.exists', side_effect=mock_os_path_exists):
                    # --- Execution ---
                    result_path = self.updater.download_update(temp_dir=temp_dir)

            # --- Assertions ---
            self.assertIsNotNone(result_path)
            self.assertTrue(result_path.endswith('.zip'))
            
            # Check that the downloaded file has the correct content
            # This assertion now relies on mock_open_file capturing the write
            mock_open_file.assert_any_call(os.path.join(temp_dir, "Sims4Rewind_update.zip"), 'wb')
            mock_open_file().write.assert_any_call(mock_zip_content)
        
            mock_crypto_utils.verify_signature.assert_called_once()
            self.log_callback.assert_any_call("Signature verification successful.")

    @patch('private_update.updater_google_drive.requests.get')
    def test_download_update_hash_mismatch(self, mock_get):
        """Test that a download fails if the hash does not match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # --- Mock Setup ---
            mock_zip_content = b'zip_file_content'
            mock_hash_content = 'incorrect_hash' # Deliberately wrong hash

            mock_zip_response = MagicMock()
            mock_zip_response.iter_content.return_value = [mock_zip_content]
            mock_zip_response.raise_for_status.return_value = None

            mock_hash_response = MagicMock()
            mock_hash_response.text = mock_hash_content
            mock_hash_response.raise_for_status.return_value = None

            mock_get.side_effect = [mock_zip_response, mock_hash_response]

            # --- Execution ---
            result_path = self.updater.download_update(temp_dir=temp_dir)

            # --- Assertions ---
            self.assertIsNone(result_path)
            self.log_callback.assert_any_call("Hash verification failed! Downloaded file may be corrupted or tampered with.")

    @patch('subprocess.Popen')
    @patch('shutil.copy2')
    @patch('tempfile.mkdtemp')
    def test_install_update_launches_correctly(self, mock_mkdtemp, mock_copy, mock_popen):
        """Test that the installer script is launched with the correct arguments."""
        # --- Mock Setup ---
        fake_temp_dir = "/tmp/updater123"
        mock_mkdtemp.return_value = fake_temp_dir
        
        # --- Execution ---
        # Assume we are running from a source file
        with patch('sys.frozen', False, create=True):
            self.updater.install_update("/path/to/update.zip")

        # --- Assertions ---
        mock_copy.assert_called_once()
        mock_popen.assert_called_once()
        
        # Check the arguments passed to Popen
        popen_args = mock_popen.call_args[0][0]
        self.assertEqual(popen_args[0], sys.executable)
        self.assertEqual(popen_args[1], os.path.join(fake_temp_dir, 'updater.py'))
        self.assertEqual(popen_args[2], '/path/to/update.zip')
        self.assertTrue(os.path.isabs(popen_args[3])) # app_install_dir
        self.assertEqual(popen_args[4], 'app.py') # executable_name

if __name__ == '__main__':
    unittest.main()

