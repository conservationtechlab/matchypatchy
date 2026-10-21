"""
Popup to manage upload directories
"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QHeaderView, QFileDialog, QProgressBar,
                             QAbstractItemView, QDialogButtonBox, QTableWidget, QTableWidgetItem)
from PyQt6.QtGui import QBrush, QColor

from matchypatchy.threads.animl_thread import VerifyNewBaseDirsThread
from matchypatchy.gui.dialogs.popup_alert import AlertPopup


class UploadManagerPopup(QDialog):
    """Popup dialog for managing upload directories"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage upload directories")
        self.mpDB = parent.mpDB
        self.logger = parent.logger
        self.setMinimumWidth(550)

        self.not_in_db = []
        self.not_in_new_directory = []
        self.verified = False
        self.contains_errors = False
        self.base_dirs = None
        self.updates = []
        self.errors = []
        self.build_thread = None
        self.verifying = False

        layout = QVBoxLayout()
        # Individuals Table
        self.list = QTableWidget()
        self.list.setColumnCount(3)
        self.list.setHorizontalHeaderLabels(['Directory', 'Date Added', 'Media Files'])
        self.list.setColumnWidth(0, 300)  # Set width for the 'Directory' column
        self.list.setColumnWidth(1, 150)  # Set width for the 'Date Added' column
        self.list.setColumnWidth(2, 100)  # Set width for the 'Count' column
        self.list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.list)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.itemSelectionChanged.connect(self.set_editdel)

        # Buttons
        button_layout = QHBoxLayout()
        self.button_edit = QPushButton("Select New Directory")
        self.button_edit.setEnabled(False)
        self.button_edit.pressed.connect(self.edit)
        button_layout.addWidget(self.button_edit)

        self.button_verify = QPushButton("Verify")
        self.button_verify.setEnabled(False)
        self.button_verify.pressed.connect(self.verify)
        button_layout.addWidget(self.button_verify)

        self.button_save = QPushButton("Save")
        self.button_save.setEnabled(False)
        self.button_save.pressed.connect(self.save)
        button_layout.addWidget(self.button_save)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        # Verification and save results
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Progress Bar (hidden at start)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        # initial load
        self.update()

    def set_editdel(self):
        """Set edit/delete button enabled state"""
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag and not self.verifying)

    def update(self):
        """Get upload directories list from mpDB"""
        self.list.clearContents()
        self.base_dirs = self.mpDB._command("""SELECT u.id, u.base_dir, u.created_at, COUNT(media.id) AS count
                                                 FROM uploads u LEFT JOIN media ON media.base_dir_id = u.id
                                                 GROUP BY u.id;""")
        if self.base_dirs is None:
            self.base_dirs = []

        self.list.setRowCount(len(self.base_dirs))

        for row, base_dir in enumerate(self.base_dirs):
            self.list.setItem(row, 0, QTableWidgetItem(str(base_dir[1])))
            self.list.setItem(row, 1, QTableWidgetItem(str(base_dir[2])))
            self.list.setItem(row, 2, QTableWidgetItem(str(base_dir[3])))

    def edit(self):
        """Edit selected individual"""
        new_directory = QFileDialog.getExistingDirectory(self, "Open File",
                                                         os.path.expanduser('~'),
                                                         QFileDialog.Option.ShowDirsOnly)
        if new_directory:
            self.updates.append((self.base_dirs[self.list.currentRow()][0], new_directory))
            # Update the table with the new directory path
            self.list.setItem(self.list.currentRow(), 0, QTableWidgetItem(str(new_directory)))
            # the new directory hasn't been verified yet
            self.verified = False
            self.button_save.setEnabled(True)
            self.button_verify.setEnabled(True)

    def verify(self):
        """Verify the new directory path"""
        # a verification is already running, replacing its thread would abort the app
        if self.verifying or (self.build_thread is not None and self.build_thread.isRunning()):
            return

        if self.updates == []:
            # No updates to verify, good to go
            self.colorize()
            return

        # Reset verification status and lists
        self.verified = False
        self.contains_errors = False
        self.errors = []
        self.not_in_db = []
        self.not_in_new_directory = []

        self.logger.info("Starting verification of new base directories")

        self.set_verifying(True)
        self.status_label.setText("Verifying new directories...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        # pass a copy so the results line up with the updates that were verified
        self.build_thread = VerifyNewBaseDirsThread(self, list(self.updates))
        self.build_thread.not_in_db.connect(self.get_not_in_db)
        self.build_thread.not_in_new_directory.connect(self.get_not_in_new_directory)
        self.build_thread.finished.connect(self.on_verify_finished)
        self.build_thread.start()

    def set_verifying(self, verifying):
        """Disable buttons while a verification is running"""
        self.verifying = verifying
        self.button_verify.setEnabled(not verifying and self.updates != [])
        self.button_save.setEnabled(not verifying and self.updates != [])
        self.set_editdel()

    # 2. Receive data from thread, check if valid
    def get_not_in_db(self, not_in_db):
        """Receive manifest from thread, proceed or alert no images found"""
        self.not_in_db = not_in_db

    def get_not_in_new_directory(self, not_in_new_directory):
        """Receive list of media not found in the new directory"""
        self.not_in_new_directory = not_in_new_directory

    def on_verify_finished(self):
        """Handle actions after verification thread finishes"""
        self.logger.info(f"Updated base directory attempts {self.updates}")
        self.verified = True
        self.progress_bar.hide()
        self.set_verifying(False)
        self.colorize()
        self.log()

    def colorize(self):
        """Colorize the rows based on verification results"""
        # set to green by default
        for row in range(self.list.rowCount()):
            for col in range(self.list.columnCount()):
                self.list.item(row, col).setBackground(QColor("#155206"))
                self.list.item(row, col).setForeground(QBrush(QColor("white")))

        # go through updated directories
        for u, update in enumerate(self.updates):
            row = next((i for i, base_dir in enumerate(self.base_dirs) if base_dir[0] == update[0]), None)
            if row is not None:
                missing = self.not_in_db[u] if u < len(self.not_in_db) else []
                missing_new = self.not_in_new_directory[u] if u < len(self.not_in_new_directory) else []

                print(f"Missing in DB: {missing}, Missing in new directory: {missing_new}")

                # If there are missing files in the new directory, mark the row as red
                if len(missing_new) > 0:
                    for col in range(self.list.columnCount()):
                        self.list.item(row, col).setBackground(QColor("#6e0e1b"))
                        self.list.item(row, col).setForeground(QBrush(QColor("white")))
                    self.errors.append(missing_new)
                    self.contains_errors = True

                else:
                    self.errors.append([])
            else:
                # keep errors aligned with updates
                self.errors.append([])

        # make the colors visible
        self.list.clearSelection()

    def log(self):
        """Log the verification results"""
        if self.contains_errors:
            missing = sum(len(e) for e in self.errors)
            self.status_label.setText(f"{missing} files in the database could not be found at their paths in the "
                                      "new directories (rows in red). Results have been saved to the log.")

            self.logger.info(f"Verification results for updates: {self.updates}")
            self.logger.info(f"Errors: {self.errors}")
            self.logger.info(f"Files discovered not in DB: {self.not_in_db}")
            self.logger.info(f"Files not in new directory: {self.not_in_new_directory}")
        else:
            self.status_label.setText("All files were found in the new directories.")

    def save(self):
        """Save changes to the selected upload directory"""
        # no updates, return early
        if self.updates == []:
            return

        # confirm if not verified before saving
        if not self.verified:
            dialog = AlertPopup(self,
                                prompt=("Verification not completed. Saving without verification may cause "
                                        "inconsistencies in the database. Would you like to proceed?"))
            proceed = dialog.exec()
            del dialog
            if not proceed:
                return

        # if there are errors, warn the user
        # TODO: Choose what will happen
        if self.contains_errors:
            dialog = AlertPopup(self,
                                prompt=("There are missing files in the new directories. This will only update "
                                        "chosen paths with all available files. Would you like to proceed?"))
            proceed = dialog.exec()
            del dialog
            if not proceed:
                return

        # proceed with saving changes to the database
        saved = 0
        failed = []
        skipped = []
        for u, update in enumerate(self.updates):
            # no verification results when saving unverified
            missing = self.errors[u] if u < len(self.errors) else []
            # Only update if there are no errors
            if len(missing) == 0:
                if self.mpDB.update_base_dir(update[0], update[1]):
                    saved += 1
                else:
                    self.logger.warning(f"Failed to update base directory for {update}")
                    failed.append(update)
            # WARN USER: Skipping update due to missing files
            else:
                self.logger.warning(f"Skipping update for {update} due to missing files: {missing}")
                skipped.append((update, len(missing)))

        # saved, start over so the same updates aren't applied again
        total = len(self.updates)
        self.updates = []
        self.errors = []
        self.verified = False
        self.contains_errors = False
        self.update()
        self.button_save.setEnabled(False)
        self.button_verify.setEnabled(False)

        # report what wasn't saved in the popup, those rows keep their current directory
        message = f"Saved {saved} of {total} directories."
        if failed:
            dirs = ", ".join(update[1] for update in failed)
            message += f" Could not update {dirs}, the directory may already belong to another upload."
        if skipped:
            dirs = ", ".join(f"{update[1]} ({n} files missing)" for update, n in skipped)
            message += f" Skipped {dirs}."
        if failed or skipped:
            message += " Rows in red were not changed."
            unsaved = set(update[0] for update in failed) | set(update[0] for update, _ in skipped)
            for row, base_dir in enumerate(self.base_dirs):
                if base_dir[0] in unsaved:
                    for col in range(self.list.columnCount()):
                        self.list.item(row, col).setBackground(QColor("#6e0e1b"))
                        self.list.item(row, col).setForeground(QBrush(QColor("white")))
        self.status_label.setText(message)
