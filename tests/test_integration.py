import unittest
import os
import sys
import json
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Ensure headless operation
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import PyQt6 components
from PyQt6.QtWidgets import QApplication

# Make sure we have a QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

# Fix Python path to find src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import our mock helper
from mock_helper import MockSyncManager, patch_main_app

# Helper function to create a temporary config file
def create_test_config(jobs=None):
    if jobs is None:
        jobs = []

    config_data = {'sync_jobs': jobs}
    config_dir = tempfile.mkdtemp()
    config_file = os.path.join(config_dir, "config.json")

    with open(config_file, 'w') as f:
        json.dump(config_data, f)

    return config_file, config_dir

class TestIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test environment"""
        # Create temp directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_dir, "source")
        self.dest_dir = os.path.join(self.temp_dir, "dest")
        os.makedirs(self.source_dir)
        os.makedirs(self.dest_dir)

        # Create a test file in source directory
        with open(os.path.join(self.source_dir, "test_file.txt"), "w") as f:
            f.write("Test content")

    def tearDown(self):
        """Clean up after tests"""
        # Remove temp directories
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Clean up any config directories created in tests
        if hasattr(self, 'config_dir') and os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)

    def test_sync_manager_config_integration(self):
        """Test integration between SyncManager and config loading"""
        # Setup mock instance that tracks calls correctly
        mock_syncmgr = MockSyncManager()

        # Create a test config file with sync jobs
        config_file, self.config_dir = create_test_config([
            {
                "name": "job1",
                "source_dir": "/test/source1",
                "dest_dir": "/test/dest1",
                "options": ["-av"],
                "auto_sync": True,
                "interval": 30
            },
            {
                "name": "job2",
                "source_dir": "/test/source2",
                "dest_dir": "/test/dest2",
                "options": ["-avz", "--delete"],
                "auto_sync": False,
                "interval": 60
            }
        ])

        # Import RsyncTrayApp using direct import to avoid module errors
        from src.main import RsyncTrayApp

        # Create app with proper mocked components
        patchers, qapp_mock, tray_mock, action_mock, icon_mock, timer_mock = patch_main_app()

        # Start all patchers
        for patcher in patchers:
            patcher.start()

        # Add SyncManager patch
        syncmgr_patcher = patch('src.main.SyncManager', return_value=mock_syncmgr)
        syncmgr_patcher.start()

        try:
            # Patch os.path.expanduser to return our config file
            with patch('src.main.os.path.expanduser', return_value=config_file), \
                 patch('src.main.os.path.exists', return_value=True), \
                 patch.object(RsyncTrayApp, 'setup_tray'), \
                 patch.object(RsyncTrayApp, 'setup_timers'):

                app = RsyncTrayApp()
                app.load_config()

                # Verify add_job was called for each job in the config
                self.assertEqual(mock_syncmgr.add_job.call_count, 2)
        finally:
            # Stop all patchers
            for patcher in patchers:
                patcher.stop()
            syncmgr_patcher.stop()

    @patch('subprocess.Popen')
    def test_sync_with_real_directories(self, mock_popen):
        """Test sync with real directories (but mocked subprocess)"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Import SyncManager directly
        from src.sync_manager import SyncManager

        # Create a SyncManager instance
        sync_manager = SyncManager()

        # Add a job with real directories
        sync_manager.add_job(
            name="real-dir-test",
            source_dir=self.source_dir,
            dest_dir=self.dest_dir,
            options=["-av"]
        )

        # Connect to signals
        start_handler = MagicMock()
        finish_handler = MagicMock()
        sync_manager.sync_started.connect(start_handler)
        sync_manager.sync_finished.connect(finish_handler)

        # Run sync
        sync_manager.start_sync("real-dir-test")

        # Verify signals were emitted
        self.assertEqual(start_handler.call_count, 1)
        start_handler.assert_called_with("real-dir-test")

        self.assertEqual(finish_handler.call_count, 1)
        finish_handler.assert_called_with("real-dir-test", True)

        # Verify subprocess was called with correct arguments
        self.assertEqual(mock_popen.call_count, 1)
        cmd_args = mock_popen.call_args[0][0]
        self.assertEqual(cmd_args[0], "rsync")
        self.assertIn("-av", cmd_args)
        self.assertEqual(cmd_args[-2], self.source_dir)
        self.assertEqual(cmd_args[-1], self.dest_dir)

    def test_app_config_integration(self):
        """Test integration between RsyncTrayApp and config loading"""
        # Create a mock SyncManager that tracks calls correctly
        mock_syncmgr = MockSyncManager()

        # Create test config file with jobs
        config_file, self.config_dir = create_test_config([
            {
                "name": "test-job",
                "source_dir": self.source_dir,
                "dest_dir": self.dest_dir,
                "options": ["-av"],
                "auto_sync": True,
                "interval": 30
            }
        ])

        # Import app directly
        from src.main import RsyncTrayApp

        # Set up proper patches for PyQt components
        patchers, qapp_mock, tray_mock, action_mock, icon_mock, timer_mock = patch_main_app()

        # Start all patchers
        for patcher in patchers:
            patcher.start()

        # Add SyncManager patch
        syncmgr_patcher = patch('src.main.SyncManager', return_value=mock_syncmgr)
        syncmgr_patcher.start()

        try:
            # Create app with mocked components
            with patch('src.main.os.path.expanduser', return_value=config_file), \
                 patch('src.main.os.path.exists', return_value=True), \
                 patch.object(RsyncTrayApp, 'setup_tray'), \
                 patch.object(RsyncTrayApp, 'setup_timers'):

                app = RsyncTrayApp()
                app.load_config()

                # Verify jobs were added from config
                self.assertEqual(mock_syncmgr.add_job.call_count, 1)
        finally:
            # Stop all patchers
            for patcher in patchers:
                patcher.stop()
            syncmgr_patcher.stop()

    @patch('subprocess.Popen')
    def test_error_handling(self, mock_popen):
        """Test error handling during sync"""
        # Set up mock process to simulate an error
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        # Import SyncManager directly
        from src.sync_manager import SyncManager

        # Create a SyncManager instance
        sync_manager = SyncManager()

        # Add a job
        sync_manager.add_job(
            name="error-test",
            source_dir=self.source_dir,
            dest_dir=self.dest_dir,
            options=["-av"]
        )

        # Connect to signals
        error_handler = MagicMock()
        finish_handler = MagicMock()
        sync_manager.sync_error.connect(error_handler)
        sync_manager.sync_finished.connect(finish_handler)

        # Run sync
        sync_manager.start_sync("error-test")

        # Verify error handling
        self.assertEqual(error_handler.call_count, 1)
        error_args = error_handler.call_args[0]
        self.assertEqual(error_args[0], "error-test")
        # Don't check exact error message as it can vary

        self.assertEqual(finish_handler.call_count, 1)
        finish_handler.assert_called_with("error-test", False)

if __name__ == '__main__':
    unittest.main()
