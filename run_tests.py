#!/usr/bin/env python3
"""
Comprehensive test runner for rsync-tray tests
Handles PyQt initialization, module imports, and test discovery
"""

import sys
import os
import unittest
import importlib
import tempfile

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add src directory to Python path
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

# Set QT_QPA_PLATFORM environment variable for headless operation
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Also set XDG_RUNTIME_DIR if not already set
if "XDG_RUNTIME_DIR" not in os.environ:
    runtime_dir = tempfile.mkdtemp()
    os.environ["XDG_RUNTIME_DIR"] = runtime_dir
    os.makedirs(runtime_dir, exist_ok=True)

def ensure_directories_in_src():
    """Ensure source directory has proper imports by creating __init__.py if needed"""
    init_file = os.path.join(src_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Created by test runner to enable imports\n")
        print(f"Created {init_file}")

def create_mock_helper():
    """Create mock_helper.py in tests directory if it doesn't exist"""
    mock_helper_path = os.path.join(project_root, 'tests', 'mock_helper.py')
    if not os.path.exists(mock_helper_path):
        tests_dir = os.path.join(project_root, 'tests')
        os.makedirs(tests_dir, exist_ok=True)

        with open(mock_helper_path, 'w') as f:
            f.write('''"""
Helper module for creating consistent mocks across tests
"""

import sys
from unittest.mock import MagicMock, patch

class MockSyncManager:
    """
    Consistent implementation of SyncManager mock for testing
    Ensures signal methods are proper MagicMock objects
    """

    def __init__(self):
        self.jobs = {}
        self.running_processes = {}

        # Create mock signals - properly make these MagicMock objects
        self.sync_started = MagicMock()
        self.sync_finished = MagicMock()
        self.sync_progress = MagicMock()
        self.sync_error = MagicMock()

        # Make add_job a MagicMock so we can track calls
        self._real_add_job = self.add_job
        self.add_job = MagicMock(side_effect=self._real_add_job)

        # Same for other methods we want to track
        self._real_clear_jobs = self.clear_jobs
        self.clear_jobs = MagicMock(side_effect=self._real_clear_jobs)

        self._real_start_sync = self.start_sync
        self.start_sync = MagicMock(side_effect=self._real_start_sync)

    def add_job(self, name, source_dir, dest_dir, options=None, auto_sync=False, interval=60):
        """Add a sync job (real implementation)"""
        if options is None:
            options = ['-av', '--delete']

        self.jobs[name] = {
            'name': name,
            'source_dir': source_dir,
            'dest_dir': dest_dir,
            'options': options,
            'auto_sync': auto_sync,
            'interval': interval
        }

    def remove_job(self, name):
        """Remove a job"""
        if name in self.jobs:
            del self.jobs[name]

    def get_jobs(self):
        """Get all jobs"""
        return self.jobs

    def clear_jobs(self):
        """Clear all jobs"""
        self.jobs = {}

    def start_sync(self, name):
        """Start a sync job"""
        if name not in self.jobs:
            self.sync_error(name, "Sync job not found")
            return

        # Just emit signals for testing
        self.sync_started(name)
        self.sync_finished(name, True)

    def start_all_sync(self):
        """Start all sync jobs"""
        for name in self.jobs:
            self.start_sync(name)

def create_pyqt_app_mock():
    """
    Create a properly structured mock for QApplication
    """
    app_mock = MagicMock()
    app_mock._timers = []
    return app_mock

def create_system_tray_mock():
    """
    Create a properly structured mock for QSystemTrayIcon
    """
    tray_mock = MagicMock()
    tray_mock.contextMenu.return_value = MagicMock()
    return tray_mock

def patch_subprocess():
    """
    Create a properly structured mock for subprocess.Popen
    """
    popen_mock = MagicMock()
    process_mock = MagicMock()
    process_mock.communicate.return_value = ("Output", "")
    process_mock.returncode = 0
    popen_mock.return_value = process_mock

    # Apply the patch
    patcher = patch('subprocess.Popen', popen_mock)
    return patcher, popen_mock

def patch_main_app():
    """
    Patch the main application components properly
    """
    # Create the mocks first
    qapp_mock = create_pyqt_app_mock()
    tray_mock = create_system_tray_mock()
    menu_mock = MagicMock()
    action_mock = MagicMock()
    icon_mock = MagicMock()
    timer_mock = MagicMock()
    msgbox_mock = MagicMock()

    # Create the patchers
    patchers = [
        patch('src.main.QApplication', return_value=qapp_mock),
        patch('src.main.QSystemTrayIcon', return_value=tray_mock),
        patch('src.main.QMenu', return_value=menu_mock),
        patch('src.main.QAction', side_effect=lambda *args, **kwargs: MagicMock()),  # Fixes QAction overload issue
        patch('src.main.QIcon', return_value=icon_mock),
        patch('src.main.QTimer', return_value=timer_mock),
        patch('src.main.QMessageBox', msgbox_mock),
    ]

    return patchers, qapp_mock, tray_mock, action_mock, icon_mock, timer_mock
''')
        print(f"Created {mock_helper_path}")

def run_tests():
    """Run all unit tests with proper PyQt initialization and module imports"""
    # Ensure directories can be imported
    ensure_directories_in_src()

    # Create mock helper
    create_mock_helper()

    # First, import PyQt after setting environment variables
    try:
        from PyQt6.QtWidgets import QApplication

        # Ensure we have a QApplication instance before any tests run
        app = QApplication.instance() or QApplication(sys.argv)

        print(f"Successfully initialized PyQt with platform: {os.environ.get('QT_QPA_PLATFORM')}")
        print(f"QApplication instance: {app}")
    except ImportError:
        print("Warning: PyQt6 not available. GUI tests will fail.")

    # Verify the module structure
    print("\nChecking module structure:")
    for module_name in ["src.main", "src.sync_manager", "src.config_dialog"]:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ Successfully imported {module_name}")
        except ImportError as e:
            print(f"✗ Failed to import {module_name}: {e}")

    # Print path information
    print(f"\nProject root: {project_root}")
    print(f"Source directory: {src_dir}")
    print(f"Python path: {sys.path[:5]}")

    # Discover and run tests
    test_dir = os.path.join(project_root, 'tests')
    print(f"\nLooking for tests in: {test_dir}")

    # Find and load all tests
    test_suite = unittest.defaultTestLoader.discover(test_dir)

    # Run tests with better error reporting
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print("\nTest Summary:")
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())
