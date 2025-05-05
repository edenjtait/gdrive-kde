import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch, call

# Ensure headless operation
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import PyQt6 components
from PyQt6.QtWidgets import QApplication

# Make sure we have a QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

# Fix Python path to find src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import mock helper
from mock_helper import MockSyncManager, patch_main_app

class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        """Set up test environment"""
        # Create temp directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_dir, "source")
        self.dest_dir = os.path.join(self.temp_dir, "dest")
        os.makedirs(self.source_dir)
        os.makedirs(self.dest_dir)

    def tearDown(self):
        """Clean up after tests"""
        # Remove temp directories
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('subprocess.Popen')
    def test_sync_with_symlinks(self, mock_popen):
        """Test syncing with symlinks"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Create a real file and symlink in source directory
        with open(os.path.join(self.source_dir, "test_file.txt"), "w") as f:
            f.write("Test content")

        symlink_path = os.path.join(self.source_dir, "test_symlink")
        try:
            os.symlink(os.path.join(self.source_dir, "test_file.txt"), symlink_path)
        except OSError:
            # Skip symlink creation on platforms that don't support it (e.g. Windows without admin)
            self.skipTest("Symlink creation not supported on this platform/user")

        # Create SyncManager with our mocked subprocess
        from src.sync_manager import SyncManager
        sync_manager = SyncManager()

        # Add job with symlinks option
        sync_manager.add_job(
            name="symlink-test",
            source_dir=self.source_dir,
            dest_dir=self.dest_dir,
            options=["-av", "--delete", "-L"]  # -L preserves symlinks
        )

        # Connect to signals
        start_handler = MagicMock()
        finish_handler = MagicMock()
        sync_manager.sync_started.connect(start_handler)
        sync_manager.sync_finished.connect(finish_handler)

        # Run sync
        sync_manager.start_sync("symlink-test")

        # Verify signals
        self.assertEqual(start_handler.call_count, 1)
        start_handler.assert_called_with("symlink-test")

        self.assertEqual(finish_handler.call_count, 1)
        finish_handler.assert_called_with("symlink-test", True)

        # Verify correct command was run
        self.assertEqual(mock_popen.call_count, 1)
        cmd_args = mock_popen.call_args[0][0]
        self.assertEqual(cmd_args[0], "rsync")
        self.assertIn("-av", cmd_args)
        self.assertIn("--delete", cmd_args)
        self.assertIn("-L", cmd_args)
        self.assertEqual(cmd_args[-2], self.source_dir)
        self.assertEqual(cmd_args[-1], self.dest_dir)

    @patch('subprocess.Popen')
    def test_multiple_sync_jobs(self, mock_popen):
        """Test running multiple sync jobs"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Create SyncManager with our mocked subprocess
        from src.sync_manager import SyncManager
        sync_manager = SyncManager()

        # Create source directories for multiple jobs
        job1_source = os.path.join(self.temp_dir, "job1_source")
        job1_dest = os.path.join(self.temp_dir, "job1_dest")
        job2_source = os.path.join(self.temp_dir, "job2_source")
        job2_dest = os.path.join(self.temp_dir, "job2_dest")

        os.makedirs(job1_source)
        os.makedirs(job1_dest)
        os.makedirs(job2_source)
        os.makedirs(job2_dest)

        # Create test files
        with open(os.path.join(job1_source, "job1_file.txt"), "w") as f:
            f.write("Job 1 content")

        with open(os.path.join(job2_source, "job2_file.txt"), "w") as f:
            f.write("Job 2 content")

        # Add multiple jobs
        sync_manager.add_job(
            name="job1",
            source_dir=job1_source,
            dest_dir=job1_dest,
            options=["-av"]
        )

        sync_manager.add_job(
            name="job2",
            source_dir=job2_source,
            dest_dir=job2_dest,
            options=["-avz", "--delete"]
        )

        # Connect to signals
        start_handler = MagicMock()
        finish_handler = MagicMock()
        sync_manager.sync_started.connect(start_handler)
        sync_manager.sync_finished.connect(finish_handler)

        # Run all sync jobs
        sync_manager.start_all_sync()

        # Verify signals for both jobs
        self.assertEqual(start_handler.call_count, 2)
        self.assertEqual(finish_handler.call_count, 2)

        # Verify correct commands were run
        self.assertEqual(mock_popen.call_count, 2)

    @patch('subprocess.Popen')
    def test_file_modification(self, mock_popen):
        """Test syncing modified files"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Create SyncManager with our mocked subprocess
        from src.sync_manager import SyncManager
        sync_manager = SyncManager()

        # Create a test file in source directory
        test_file_path = os.path.join(self.source_dir, "test_file.txt")
        with open(test_file_path, "w") as f:
            f.write("Initial content")

        # Add sync job
        sync_manager.add_job(
            name="mod-test",
            source_dir=self.source_dir,
            dest_dir=self.dest_dir,
            options=["-av"]
        )

        # Run first sync
        sync_manager.start_sync("mod-test")

        # Modify the file
        with open(test_file_path, "w") as f:
            f.write("Modified content")

        # Reset mocks
        mock_popen.reset_mock()

        # Run second sync
        sync_manager.start_sync("mod-test")

        # Verify sync was run
        self.assertEqual(mock_popen.call_count, 1)
        cmd_args = mock_popen.call_args[0][0]
        self.assertEqual(cmd_args[0], "rsync")
        self.assertEqual(cmd_args[-2], self.source_dir)
        self.assertEqual(cmd_args[-1], self.dest_dir)

    @patch('subprocess.Popen')
    def test_dry_run_option(self, mock_popen):
        """Test rsync --dry-run option"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Would transfer test_file.txt", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Create SyncManager with our mocked subprocess
        from src.sync_manager import SyncManager
        sync_manager = SyncManager()

        # Create a test file in source directory
        test_file_path = os.path.join(self.source_dir, "test_file.txt")
        with open(test_file_path, "w") as f:
            f.write("Test content")

        # Add sync job with dry-run option
        sync_manager.add_job(
            name="dry-run-test",
            source_dir=self.source_dir,
            dest_dir=self.dest_dir,
            options=["-av", "--dry-run"]
        )

        # Run sync
        sync_manager.start_sync("dry-run-test")

        # Verify correct command was run
        self.assertEqual(mock_popen.call_count, 1)
        cmd_args = mock_popen.call_args[0][0]
        self.assertEqual(cmd_args[0], "rsync")
        self.assertIn("-av", cmd_args)
        self.assertIn("--dry-run", cmd_args)
        self.assertEqual(cmd_args[-2], self.source_dir)
        self.assertEqual(cmd_args[-1], self.dest_dir)

    @patch('subprocess.Popen')
    def test_permission_handling(self, mock_popen):
        """Test handling permission errors"""
        # Set up mock process to simulate a permission error
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "rsync: send_files failed to open: Permission denied (13)")
        mock_process.returncode = 13
        mock_popen.return_value = mock_process

        # Create SyncManager with our mocked subprocess
        from src.sync_manager import SyncManager
        sync_manager = SyncManager()

        # Add sync job
        sync_manager.add_job(
            name="perm-test",
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
        sync_manager.start_sync("perm-test")

        # Verify error was handled
        self.assertEqual(error_handler.call_count, 1)
        error_args = error_handler.call_args[0]
        self.assertEqual(error_args[0], "perm-test")
        self.assertIn("Permission denied", error_args[1])

        self.assertEqual(finish_handler.call_count, 1)
        finish_handler.assert_called_with("perm-test", False)

    def test_full_app_flow(self):
        """Test the full application flow (with mocked UI components)"""
        # Set up proper patches for PyQt components with our helper function
        patchers, qapp_mock, tray_mock, action_mock, icon_mock, timer_mock = patch_main_app()

        # Start all patchers
        for patcher in patchers:
            patcher.start()

        try:
            # Create a mock for ConfigDialog
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = True

            # Create a mock for QAction
            mock_action = MagicMock()

            # Create a MockSyncManager and patch SyncManager
            mock_syncmgr = MockSyncManager()

            # Import the app directly
            from src.main import RsyncTrayApp

            # Patch the problematic QAction constructor
            with patch('src.main.QAction', return_value=mock_action), \
                 patch('src.main.ConfigDialog', return_value=mock_dialog), \
                 patch('src.main.QTimer.singleShot'), \
                 patch('src.main.SyncManager', return_value=mock_syncmgr):

                # Create app with mocked components
                app = RsyncTrayApp()

                # Add a test job
                app.sync_manager.add_job(
                    name="test-job",
                    source_dir=self.source_dir,
                    dest_dir=self.dest_dir,
                    auto_sync=True,
                    interval=30
                )

                # Reset mocks to clear initialization calls
                mock_dialog.exec.reset_mock()
                mock_syncmgr.start_sync.reset_mock()

                # Show config dialog
                app.show_config_dialog()

                # Verify dialog was shown
                self.assertEqual(mock_dialog.exec.call_count, 1)

                # Run sync
                app.sync_all()

                # Verify sync was triggered
                self.assertEqual(mock_syncmgr.start_sync.call_count, 1)
                mock_syncmgr.start_sync.assert_called_with("test-job")
        finally:
            # Stop all patchers
            for patcher in patchers:
                patcher.stop()

if __name__ == '__main__':
    unittest.main()
