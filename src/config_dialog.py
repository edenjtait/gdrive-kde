import json
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QListWidget, QListWidgetItem,
                           QLineEdit, QCheckBox, QSpinBox, QFileDialog,
                           QFrame, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt

class ConfigDialog(QDialog):
    def __init__(self, sync_manager, config_file):
        super().__init__()

        self.sync_manager = sync_manager
        self.config_file = config_file
        self.jobs = sync_manager.get_jobs().copy()

        self.setWindowTitle("Configure Sync Jobs")
        self.resize(600, 400)

        self.setup_ui()
        self.populate_job_list()

    def setup_ui(self):
        layout = QHBoxLayout()

        # Left side (job list)
        left_layout = QVBoxLayout()
        self.job_list = QListWidget()
        self.job_list.currentItemChanged.connect(self.job_selected)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_job)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_job)
        self.remove_btn.setEnabled(False)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)

        left_layout.addWidget(QLabel("Sync Jobs:"))
        left_layout.addWidget(self.job_list)
        left_layout.addLayout(btn_layout)

        # Right side (job details)
        self.detail_widget = QFrame()
        self.detail_layout = QGridLayout()
        self.detail_widget.setLayout(self.detail_layout)
        self.detail_widget.setFrameShape(QFrame.Shape.StyledPanel)

        # Job details fields
        self.name_edit = QLineEdit()
        self.source_edit = QLineEdit()
        self.source_btn = QPushButton("Browse...")
        self.source_btn.clicked.connect(lambda: self.browse_dir(self.source_edit))

        self.dest_edit = QLineEdit()
        self.dest_btn = QPushButton("Browse...")
        self.dest_btn.clicked.connect(lambda: self.browse_dir(self.dest_edit))

        self.auto_sync = QCheckBox("Auto sync")
        self.interval = QSpinBox()
        self.interval.setMinimum(1)
        self.interval.setMaximum(1440)  # 24 hours in minutes
        self.interval.setValue(60)
        self.interval.setSuffix(" min")

        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText("-av --delete")

        # Add fields to layout
        row = 0
        self.detail_layout.addWidget(QLabel("Name:"), row, 0)
        self.detail_layout.addWidget(self.name_edit, row, 1, 1, 2)

        row += 1
        self.detail_layout.addWidget(QLabel("Source:"), row, 0)
        self.detail_layout.addWidget(self.source_edit, row, 1)
        self.detail_layout.addWidget(self.source_btn, row, 2)

        row += 1
        self.detail_layout.addWidget(QLabel("Destination:"), row, 0)
        self.detail_layout.addWidget(self.dest_edit, row, 1)
        self.detail_layout.addWidget(self.dest_btn, row, 2)

        row += 1
        self.detail_layout.addWidget(QLabel("Options:"), row, 0)
        self.detail_layout.addWidget(self.options_edit, row, 1, 1, 2)

        row += 1
        auto_layout = QHBoxLayout()
        auto_layout.addWidget(self.auto_sync)
        auto_layout.addWidget(QLabel("Interval:"))
        auto_layout.addWidget(self.interval)
        auto_layout.addStretch()
        self.detail_layout.addLayout(auto_layout, row, 0, 1, 3)

        # Save button
        row += 1
        self.save_btn = QPushButton("Save Job")
        self.save_btn.clicked.connect(self.save_job)
        self.detail_layout.addWidget(self.save_btn, row, 1, 1, 2, Qt.AlignmentFlag.AlignRight)

        # Disable details until a job is selected
        self.detail_widget.setEnabled(False)

        # Dialog buttons
        buttons_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_btn)
        buttons_layout.addWidget(self.cancel_btn)

        # Main layout
        layout.addLayout(left_layout, 1)
        layout.addWidget(self.detail_widget, 2)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def browse_dir(self, line_edit):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            line_edit.setText(directory)

    def populate_job_list(self):
        self.job_list.clear()
        for name in self.jobs:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.job_list.addItem(item)

    def job_selected(self, current, previous):
        self.detail_widget.setEnabled(current is not None)
        self.remove_btn.setEnabled(current is not None)

        if current is None:
            return

        job_name = current.data(Qt.ItemDataRole.UserRole)
        job = self.jobs.get(job_name, {})

        self.name_edit.setText(job.get('name', ''))
        self.source_edit.setText(job.get('source_dir', ''))
        self.dest_edit.setText(job.get('dest_dir', ''))
        self.auto_sync.setChecked(job.get('auto_sync', False))
        self.interval.setValue(job.get('interval', 60))

        options = job.get('options', [])
        self.options_edit.setText(' '.join(options))

    def add_job(self):
        job_name = f"Job-{len(self.jobs) + 1}"
        self.jobs[job_name] = {
            'name': job_name,
            'source_dir': '',
            'dest_dir': '',
            'options': ['-av', '--delete'],
            'auto_sync': False,
            'interval': 60
        }

        item = QListWidgetItem(job_name)
        item.setData(Qt.ItemDataRole.UserRole, job_name)
        self.job_list.addItem(item)
        self.job_list.setCurrentItem(item)

    def remove_job(self):
        current = self.job_list.currentItem()
        if current is None:
            return

        job_name = current.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(self, "Remove Job",
                                    f"Are you sure you want to remove '{job_name}'?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            del self.jobs[job_name]
            self.job_list.takeItem(self.job_list.row(current))

    def save_job(self):
        current = self.job_list.currentItem()
        if current is None:
            return

        old_name = current.data(Qt.ItemDataRole.UserRole)
        new_name = self.name_edit.text()

        if not new_name:
            QMessageBox.warning(self, "Error", "Job name cannot be empty")
            return

        options_text = self.options_edit.text().strip()
        if not options_text:
            options = ['-av', '--delete']
        else:
            options = options_text.split()

        # Create updated job
        job = {
            'name': new_name,
            'source_dir': self.source_edit.text(),
            'dest_dir': self.dest_edit.text(),
            'options': options,
            'auto_sync': self.auto_sync.isChecked(),
            'interval': self.interval.value()
        }

        # Validate
        if not job['source_dir'] or not job['dest_dir']:
            QMessageBox.warning(self, "Error", "Source and destination directories are required")
            return

        # If name changed, we need to update the dict key and list item
        if old_name != new_name:
            del self.jobs[old_name]
            current.setText(new_name)
            current.setData(Qt.ItemDataRole.UserRole, new_name)

        self.jobs[new_name] = job

        QMessageBox.information(self, "Success", f"Job '{new_name}' saved")

    def accept(self):
        # Save all jobs to the sync manager
        self.sync_manager.clear_jobs()
        for job_name, job in self.jobs.items():
            self.sync_manager.add_job(
                name=job['name'],
                source_dir=job['source_dir'],
                dest_dir=job['dest_dir'],
                options=job['options'],
                auto_sync=job['auto_sync'],
                interval=job['interval']
            )

        # Save to config file
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({'sync_jobs': list(self.jobs.values())}, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save config: {e}")

        super().accept()
