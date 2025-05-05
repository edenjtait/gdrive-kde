"""
Common fixtures and mocks for tests with headless Qt support
"""
import os
import json
import pytest
import sys
from unittest.mock import MagicMock, patch

# Ensure headless operation
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import PyQt after setting environment variables
from PyQt6.QtWidgets import QApplication

# Create a global QApplication instance for all tests
app = None

def pytest_configure(config):
    """Initialize QApplication before tests run"""
    global app
    if app is None:
        app = QApplication.instance() or QApplication(sys.argv)

@pytest.fixture(scope="session")
def qapp():
    """Fixture to provide the QApplication instance"""
    global app
    if app is None:
        app = QApplication.instance() or QApplication(sys.argv)
    return app

# Mock for QDialog.exec and similar methods that need a display
@pytest.fixture(autouse=True)
def mock_exec_methods():
    """Automatically mock Qt exec methods that require a display"""
    with patch('PyQt6.QtWidgets.QDialog.exec', return_value=1), \
         patch('PyQt6.QtWidgets.QMessageBox.exec', return_value=1), \
         patch('PyQt6.QtWidgets.QFileDialog.exec', return_value=1):
        yield

class MockSyncManager:
    """Mock implementation of SyncManager for testing"""

    def __init__(self):
        self.jobs = {}
        self.running_processes = {}
        # Create signal mocks
        self.sync_started = MagicMock()
        self.sync_finished = MagicMock()
        self.sync_progress = MagicMock()
        self.sync_error = MagicMock()

    def add_job(self, name, source_dir, dest_dir, options=None, auto_sync=False, interval=60):
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
        if name in self.jobs:
            del self.jobs[name]

    def get_jobs(self):
        return self.jobs

    def clear_jobs(self):
        self.jobs = {}

    def start_sync(self, name):
        if name not in self.jobs:
            self.sync_error(name, "Sync job not found")
            return

        # Just emit signals for testing
        self.sync_started(name)
        self.sync_finished(name, True)

    def start_all_sync(self):
        for name in self.jobs:
            self.start_sync(name)

@pytest.fixture
def mock_sync_manager():
    """Fixture to provide a MockSyncManager instance"""
    return MockSyncManager()

# Helper function to create a temp config file for testing
def create_test_config(jobs=None):
    if jobs is None:
        jobs = []

    config_data = {'sync_jobs': jobs}
    config_dir = os.path.expanduser("~/.config/rsync-tray-test")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "test_config.json")

    with open(config_file, 'w') as f:
        json.dump(config_data, f)

    return config_file

# Helper to clean up test config
def remove_test_config():
    config_file = os.path.expanduser("~/.config/rsync-tray-test/test_config.json")
    if os.path.exists(config_file):
        os.remove(config_file)
