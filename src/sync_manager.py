import os
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

class SyncManager(QObject):
    sync_started = pyqtSignal(str)
    sync_finished = pyqtSignal(str, bool)
    sync_progress = pyqtSignal(str, int)
    sync_error = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.jobs = {}
        self.running_processes = {}

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
            self.sync_error.emit(name, "Sync job not found")
            return

        job = self.jobs[name]

        # Validate directories
        if not os.path.exists(job['source_dir']):
            self.sync_error.emit(name, f"Source directory does not exist: {job['source_dir']}")
            return

        # Build rsync command
        cmd = ['rsync'] + job['options'] + [job['source_dir'], job['dest_dir']]

        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            self.running_processes[name] = process
            self.sync_started.emit(name)

            # Poll for process completion
            stdout, stderr = process.communicate()

            # Check if successful
            if process.returncode == 0:
                self.sync_finished.emit(name, True)
            else:
                self.sync_error.emit(name, stderr)
                self.sync_finished.emit(name, False)

            # Clean up
            del self.running_processes[name]

        except Exception as e:
            self.sync_error.emit(name, str(e))
            self.sync_finished.emit(name, False)

    def start_all_sync(self):
        for name in self.jobs:
            self.start_sync(name)
