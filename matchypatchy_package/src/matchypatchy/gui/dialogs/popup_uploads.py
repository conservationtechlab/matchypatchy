"""
Popup to manage upload directories
"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QHeaderView, QFileDialog, QProgressBar, 
                             QAbstractItemView, QDialogButtonBox, QTableWidget, QTableWidgetItem)
from PyQt6.QtGui import QBrush, QColor

from matchypatchy.threads.animl_thread import VerifyNewBaseDirsThread
from matchypatchy.gui.dialogs.popup_alert import AlertPopup


class UploadManagerPopup(QDialog):
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
        self.button_edit.setEnabled(flag)

    def update(self):
        """Get upload directories list from mpDB"""
        self.base_dirs = self.mpDB._command("""SELECT u.id, u.base_dir, u.created_at, COUNT(media.id) AS count
                                                 FROM uploads u LEFT JOIN media ON media.base_dir_id = u.id
                                                 GROUP BY media.base_dir_id;""")
        if self.base_dirs is None:
            self.base_dirs = []
            
        self.list.setRowCount(len(self.base_dirs))

        for row in range(len(self.base_dirs)):
            self.list.setItem(row, 0, QTableWidgetItem(str(self.base_dirs[row][1])))
            self.list.setItem(row, 1, QTableWidgetItem(str(self.base_dirs[row][2])))
            self.list.setItem(row, 2, QTableWidgetItem(str(self.base_dirs[row][3])))

    def edit(self):
        """Edit selected individual"""
        new_directory = QFileDialog.getExistingDirectory(self, "Open File",
                                                         os.path.expanduser('~'),
                                                         QFileDialog.Option.ShowDirsOnly)
        if new_directory:
            self.updates.append((self.base_dirs[self.list.currentRow()][0], new_directory))
            # Update the table with the new directory path
            self.list.setItem(self.list.currentRow(), 0, QTableWidgetItem(str(new_directory)))
            self.button_save.setEnabled(True)
            self.button_verify.setEnabled(True)

    def verify(self):
        """Verify the new directory path"""
        if self.updates == []:
            # No updates to verify, good to go
            self.colorize(self.updates)
            return
        
        # Reset verification status and lists
        self.verified = False
        self.contains_errors = False
        self.errors = []
        self.not_in_db = []
        self.not_in_new_directory = []
        
        self.logger.info("Starting verification of new base directories")

        self.progress_bar.setRange(0, 0)
        self.build_thread = VerifyNewBaseDirsThread(self)
        self.build_thread.not_in_db.connect(self.get_not_in_db)
        self.build_thread.not_in_new_directory.connect(self.get_not_in_new_directory)
        self.build_thread.finished.connect(self.on_verify_finished)
        self.build_thread.start()

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

        # make the colors visible
        self.list.clearSelection()

    def log(self):
        """Log the verification results"""
        if self.contains_errors:
            dialog = AlertPopup(self, 
                                prompt=("Some files in the database could not be found in the new directory. ",
                                        "Results have been saved to the log."))
            dialog.exec()
            del dialog

            self.logger.info(f"Verification results for updates: {self.updates}")
            self.logger.info(f"Errors: {self.errors}")
            self.logger.info(f"Files discovered not in DB: {self.not_in_db}")
            self.logger.info(f"Files not in new directory: {self.not_in_new_directory}")


    def save(self):
        """Save changes to the selected upload directory"""
        print(self.updates)
        print(self.errors)

        # no updates, return early
        if self.updates == []:
            return

        # confirm if not verified before saving
        if not self.verified:
            dialog = AlertPopup(self, 
                                prompt=("Verification not completed. Saving without verification may cause "
                                        "inconsistencies in the database. Would you like to proceed?"))
            if dialog.exec() == QDialog.rejected:
                return
            del dialog

        # if there are errors, warn the user
        if self.contains_errors:
            dialog = AlertPopup(self, 
                                prompt=("There are missing files in the new directories. Saving may cause "
                                        "inconsistencies in the database. Would you like to proceed?"))
            if dialog.exec() == QDialog.rejected:
                return
            del dialog

        # proceed with saving changes to the database
        for u, update in enumerate(self.updates):
            missing = self.errors[u]
            # Only update if there are no errors
            if len(missing) == 0:  
                self.mpDB._command("""UPDATE uploads SET base_dir = ? WHERE id = ?""",
                                    (update[1], update[0]))
            # WARN USER: Skipping update due to missing files
            else:
                print(f"Skipping update for {update} due to missing files: {missing}")

        self.update()
        self.button_save.setEnabled(False)
