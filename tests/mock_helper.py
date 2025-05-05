"""
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
