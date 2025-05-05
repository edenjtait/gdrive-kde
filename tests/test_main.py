import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch

# Ensure headless operation
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import PyQt6 components
from PyQt6.QtWidgets import QApplication, QDialog, QSystemTrayIcon
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

# Make sure we have a QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

# Fix Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import MockSyncManager
from mock_helper import MockSyncManager, patch_main_app

class TestRsyncTrayApp(unittest.TestCase):

    def setUp(self):
        """Set up test environment"""
        # Create patches for PyQt6 classes using our helper function
        self.patchers, self.mock_qapp, self.mock_systray, self.mock_action, self.mock_icon, self.mock_timer = patch_main_app()

        # Start all patches
        for patcher in self.patchers:
            patcher.start()

        # Create a mock SyncManager that tracks calls correctly
        self.mock_sync_mgr = MockSyncManager()
        self.sync_patcher = patch('src.main.SyncManager', return_value=self.mock_sync_mgr)
        self.sync_patcher.start()

        # Set up app instance
        self.app_instance = self.mock_qapp
        self.app_instance._timers = []

        # Set up tray icon
        self.tray_instance = self.mock_systray

        # For QTimer.singleShot
        self.mock_timer.singleShot = MagicMock()

        # For QIcon.fromTheme
        icon_instance = self.mock_icon
        self.mock_icon.fromTheme = MagicMock(return_value=icon_instance)

        # Set up a test config file
        jobs = [
            {
                'name': 'job1',
                'source_dir': '/test/source1',
                'dest_dir': '/test/dest1',
                'options': ['-av'],
                'auto_sync': True,
                'interval': 30
            },
            {
                'name': 'job2',
                'source_dir': '/test/source2',
                'dest_dir': '/test/dest2',
                'options': ['-avz', '--delete'],
                'auto_sync': False,
                'interval': 60
            }
        ]
        config_data = {'sync_jobs': jobs}

        # Create temp config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)

    def tearDown(self):
        """Clean up test environment"""
        # Stop all patches
        for patcher in self.patchers:
            patcher.stop()
        self.sync_patcher.stop()

        # Clean up temp files
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_load_config(self):
        """Test loading config from file"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray'), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch('src.main.os.path.expanduser', return_value=self.config_file), \
             patch('src.main.os.path.exists', return_value=True):

            app = RsyncTrayApp()

            # Reset the mock to clear any calls during initialization
            self.mock_sync_mgr.add_job.reset_mock()

            # Call load_config directly
            app.load_config()

            # Check that jobs were loaded
            self.assertEqual(self.mock_sync_mgr.add_job.call_count, 2)

    def test_load_config_no_file(self):
        """Test loading config when file doesn't exist"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create a nonexistent path
        nonexistent_config = os.path.join(self.temp_dir, "nonexistent.json")

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray'), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch('src.main.os.path.expanduser', return_value=nonexistent_config), \
             patch('src.main.os.path.exists', return_value=False):

            app = RsyncTrayApp()

            # Reset the mock to clear any calls during initialization
            self.mock_sync_mgr.add_job.reset_mock()

            # Call load_config directly
            app.load_config()

            # Check that no jobs were loaded
            self.assertEqual(self.mock_sync_mgr.add_job.call_count, 0)

    def test_load_config_exception(self):
        """Test handling exceptions when loading config"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray'), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch('src.main.os.path.expanduser', return_value=self.config_file), \
             patch('src.main.os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=Exception("Test exception")):

            app = RsyncTrayApp()

            # Reset the mock to clear any calls during initialization
            self.mock_sync_mgr.add_job.reset_mock()

            # Call load_config directly
            app.load_config()

            # Check that no jobs were loaded (exception was handled)
            self.assertEqual(self.mock_sync_mgr.add_job.call_count, 0)

    def test_setup_timers(self):
        """Test setting up auto-sync timers"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray'), \
             patch.object(RsyncTrayApp, 'load_config'):

            app = RsyncTrayApp()

            # Create a timer for testing
            timer = MagicMock()
            app.app._timers = [timer]

            # Set up the sync_manager with jobs
            app.sync_manager.jobs = {
                "auto-job": {
                    'name': "auto-job",
                    'source_dir': "/test/source",
                    'dest_dir': "/test/dest",
                    'auto_sync': True,
                    'interval': 30
                },
                "manual-job": {
                    'name': "manual-job",
                    'source_dir': "/test/source2",
                    'dest_dir': "/test/dest2",
                    'auto_sync': False
                }
            }

            with patch('src.main.QTimer') as mock_timer_class:
                    # Run setup_timers
                app.setup_timers()

                # Verify a QTimer was created
                self.assertEqual(mock_timer_class.call_count, 1)

            # Check that the old timer was stopped
            self.assertEqual(timer.stop.call_count, 1)

            # Check that a new timer was created for the auto-sync job
            self.assertEqual(self.mock_timer.call_count, 1)
            timer_instance = self.mock_timer.return_value
            self.assertEqual(timer_instance.start.call_count, 1)
            timer_instance.start.assert_called_with(30 * 60 * 1000)  # 30 mins in ms

    def test_tray_activated(self):
        """Test tray icon activation"""
        # Import the app and ActivationReason here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray', lambda self: None), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch.object(RsyncTrayApp, 'load_config'), \
             patch.object(RsyncTrayApp, 'show_config_dialog') as mock_show_config:

            app = RsyncTrayApp()

            # We need to manually set the tray_icon attribute since we bypassed setup_tray
            app.tray_icon = self.mock_systray

            # Test activation with Trigger reason
            # Make sure this patching is correct
            with patch.object(RsyncTrayApp, 'show_config_dialog') as mock_show_config:
                # Then simulate the signal properly
                app.tray_icon.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
                # Or call the signal handler directly
                app.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
            self.assertEqual(mock_show_config.call_count, 1)

    def test_show_config_dialog(self):
        """Test showing the config dialog"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Mock ConfigDialog
        dialog_instance = MagicMock()
        dialog_instance.exec.return_value = True

        with patch('src.main.ConfigDialog', return_value=dialog_instance), \
             patch.object(RsyncTrayApp, 'setup_tray', lambda self: None), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch.object(RsyncTrayApp, 'load_config'):

            app = RsyncTrayApp()

            # Clear any previous calls
            app.load_config.reset_mock()
            app.setup_timers.reset_mock()

            # Call show_config_dialog
            app.show_config_dialog()

            # Verify dialog was created and shown
            self.assertEqual(dialog_instance.exec.call_count, 1)

            # Since dialog returned True, load_config and setup_timers should be called
            self.assertEqual(app.load_config.call_count, 1)
            self.assertEqual(app.setup_timers.call_count, 1)

    def test_sync_all(self):
        """Test syncing all jobs"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray', lambda self: None), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch.object(RsyncTrayApp, 'load_config'):

            app = RsyncTrayApp()

            # We need to manually set the tray_icon attribute since we bypassed setup_tray
            app.tray_icon = self.mock_systray

            # Set up jobs in the sync manager
            app.sync_manager.jobs = {
                "job1": {'name': "job1", 'source_dir': "/test/source1", 'dest_dir': "/test/dest1"},
                "job2": {'name': "job2", 'source_dir': "/test/source2", 'dest_dir': "/test/dest2"}
            }

            # Reset mocks
            self.mock_sync_mgr.start_sync.reset_mock()
            self.tray_instance.setToolTip.reset_mock()

            # Run sync_all
            app.sync_all()

            # Verify start_sync was called for each job
            self.assertEqual(self.mock_sync_mgr.start_sync.call_count, 2)

            # Verify tray tooltip was updated
            self.assertEqual(self.tray_instance.setToolTip.call_count, 1)
            self.tray_instance.setToolTip.assert_called_with("Syncing...")

    def test_show_about(self):
        """Test showing the about dialog"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray'), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch.object(RsyncTrayApp, 'load_config'):

            app = RsyncTrayApp()
            app.show_about()

            # Verify about dialog was shown
            self.assertTrue(hasattr(app, 'about'))

    def test_run(self):
        """Test running the application"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'setup_tray'), \
             patch.object(RsyncTrayApp, 'setup_timers'), \
             patch.object(RsyncTrayApp, 'load_config'), \
             patch.object(RsyncTrayApp, 'sync_all'):

            app = RsyncTrayApp()

            # Reset mocks
            self.mock_timer.singleShot.reset_mock()
            self.app_instance.exec.reset_mock()

            # Patch the static method properly
            with patch('src.main.QTimer.singleShot') as mock_single_shot:
                # Run the app
                app.run()

                # Verify QTimer.singleShot was called
                self.assertEqual(mock_single_shot.call_count, 1)

            # Verify QTimer.singleShot was called
            self.assertEqual(self.mock_timer.singleShot.call_count, 1)
            self.mock_timer.singleShot.assert_called_with(5000, app.sync_all)

            # Verify app.exec was called
            self.assertEqual(self.app_instance.exec.call_count, 1)

    def test_setup_tray_with_theme_icon(self):
        """Test setting up tray with theme icon"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Mock icon theme availability
        self.mock_icon.fromTheme.return_value = self.mock_icon

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'load_config'), \
             patch.object(RsyncTrayApp, 'setup_timers'):

            app = RsyncTrayApp()

            # Reset mocks to clear initialization calls
            self.tray_instance.setIcon.reset_mock()
            self.tray_instance.setContextMenu.reset_mock()
            self.tray_instance.activated.connect.reset_mock()
            self.tray_instance.setToolTip.reset_mock()
            self.tray_instance.show.reset_mock()

            # Call setup_tray explicitly
            app.setup_tray()

            # Verify QSystemTrayIcon methods were called
            self.assertEqual(self.tray_instance.setIcon.call_count, 1)
            self.assertEqual(self.tray_instance.setContextMenu.call_count, 1)
            self.assertEqual(self.tray_instance.activated.connect.call_count, 1)
            self.assertEqual(self.tray_instance.setToolTip.call_count, 1)
            self.assertEqual(self.tray_instance.show.call_count, 1)

    def test_setup_tray_with_fallback_icon(self):
        """Test setting up tray with fallback icon when theme icon fails"""
        # Import the app here to use our mocked dependencies
        from src.main import RsyncTrayApp

        # Make fromTheme raise AttributeError to simulate theme icon failure
        self.mock_icon.fromTheme.side_effect = AttributeError("No theme support")

        # Create app with our patched dependencies
        with patch.object(RsyncTrayApp, 'load_config'), \
             patch.object(RsyncTrayApp, 'setup_timers'):

            app = RsyncTrayApp()

            # Reset mocks to clear initialization calls
            self.tray_instance.setIcon.reset_mock()
            self.tray_instance.setContextMenu.reset_mock()
            self.tray_instance.activated.connect.reset_mock()
            self.tray_instance.setToolTip.reset_mock()
            self.tray_instance.show.reset_mock()

            # Call setup_tray explicitly
            app.setup_tray()

            # Verify QSystemTrayIcon methods were called
            self.assertEqual(self.tray_instance.setIcon.call_count, 1)
            self.assertEqual(self.tray_instance.setContextMenu.call_count, 1)
            self.assertEqual(self.tray_instance.activated.connect.call_count, 1)
            self.assertEqual(self.tray_instance.setToolTip.call_count, 1)
            self.assertEqual(self.tray_instance.show.call_count, 1)

if __name__ == '__main__':
    unittest.main()
