#!/usr/bin/env python3

import sys
import json
import os
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

from sync_manager import SyncManager
from config_dialog import ConfigDialog

class RsyncTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("Rsync Folder Manager")

        # Initialize the sync manager
        self.sync_manager = SyncManager()

        # Load configs
        self.config_file = os.path.expanduser("~/.config/rsync-tray/config.json")
        self.load_config()

        # Set up the tray icon
        self.setup_tray()

        # Set up auto-sync timers
        self.setup_timers()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon()

        try:
            self.tray_icon.setIcon(QIcon.fromTheme("folder-sync",
                                                QIcon("icons/sync-icon.png")))
        except AttributeError:
            self.tray_icon.setIcon(QIcon("icons/sync-icon.png"))

        # Create the tray menu
        tray_menu = QMenu()

        config_action = QAction("Configure Syncs", self.app)
        config_action.triggered.connect(self.show_config_dialog)

        sync_action = QAction("Sync Now", self.app)
        sync_action.triggered.connect(self.sync_all)

        about_action = QAction("About", self.app)
        about_action.triggered.connect(self.show_about)

        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.app.quit)

        tray_menu.addAction(config_action)
        tray_menu.addAction(sync_action)
        tray_menu.addSeparator()
        tray_menu.addAction(about_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.activated.connect(self.tray_activated)

        self.tray_icon.setToolTip("Rsync Folder Manager")
        self.tray_icon.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_config_dialog()

    def show_config_dialog(self):
        dialog = ConfigDialog(self.sync_manager, self.config_file)
        if dialog.exec():
            self.load_config()
            self.setup_timers()

    def sync_all(self):
        self.tray_icon.setToolTip("Syncing...")
        for job_name in self.sync_manager.get_jobs():
            self.sync_manager.start_sync(job_name)

    def show_about(self):
        QMessageBox.about(None, "About Rsync Folder Manager",
                         "A simple application to manage folder synchronization using rsync.")

    def load_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)

                # Clear existing jobs
                self.sync_manager.clear_jobs()

                # Add jobs from config
                for job in config.get('sync_jobs', []):
                    self.sync_manager.add_job(
                        name=job.get('name', ''),
                        source_dir=job.get('source_dir', ''),
                        dest_dir=job.get('dest_dir', ''),
                        options=job.get('options', []),
                        auto_sync=job.get('auto_sync', False),
                        interval=job.get('interval', 60)
                    )
        except Exception as e:
            print(f"Error loading config: {e}")

    def setup_timers(self):
        # Clear existing timers
        for timer in getattr(self.app, '_timers', []):
            timer.stop()

        self.app._timers = []

        # Set up new timers for auto-sync jobs
        for job_name, job in self.sync_manager.get_jobs().items():
            if job.get('auto_sync') and job.get('interval') > 0:
                timer = QTimer(self.app)
                timer.timeout.connect(lambda name=job_name:
                                     self.sync_manager.start_sync(name))
                timer.start(job.get('interval') * 60 * 1000)  # minutes to ms
                self.app._timers.append(timer)

    def run(self):
        # Run initial sync if configured
        QTimer.singleShot(5000, self.sync_all)

        # Start event loop
        return self.app.exec()

if __name__ == "__main__":
    app = RsyncTrayApp()
    sys.exit(app.run())
