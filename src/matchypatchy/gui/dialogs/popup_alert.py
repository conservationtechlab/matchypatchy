'''
Alert Popup displaying simple text and OK/Cancel buttons
Options for progress bar and cancel-only mode.
'''
from PyQt6.QtWidgets import QVBoxLayout, QDialogButtonBox, QLabel, QDialog, QProgressBar
from PyQt6.QtCore import Qt


class AlertPopup(QDialog):
    """
    Popup for displaying alerts with optional progress bar and cancel-only mode.
    """
    def __init__(self, parent, prompt, title="Alert", progressbar=False, cancel_only=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout()
        self.prompt = QLabel(prompt, objectName='title',
                             alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.prompt)

        # progress bar
        if progressbar:
            self.counter = 0
            self.progress_min = 0
            self.progress_max = 100
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(self.progress_min, self.progress_max)
            self.progress_bar.setValue(self.counter)
            layout.addWidget(self.progress_bar)

        # buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # disable OK button if cancel_only
        if cancel_only:
            ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            ok_button.setEnabled(False)  # Disable the OK button

        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def update_prompt(self, prompt):
        """Update the prompt text"""
        self.prompt.setText(prompt)

    def allow_ok(self):
        """
        Enable OK and disable Cancel once the work behind a cancel_only popup is done.

        Called by DisplayBase._finish_processing when processing ends with errors: the popup
        stays open to show them and is closed with OK, since Cancel would only try to
        cancel work that has already finished.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)

    def set_min(self, min):
        """Update the progress bar maximum value"""
        self.progress_min = min
        self.progress_bar.setRange(self.progress_min, self.progress_max)

    def set_max(self, max):
        """Update the progress bar maximum value"""
        self.progress_max = max
        self.progress_bar.setRange(self.progress_min, self.progress_max)

    def show_progress_text(self):
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")   # shows percentage, e.g. 42%

    def set_counter(self, counter):
        """Update the progress bar to specific"""
        if counter < self.progress_max:
            self.counter = counter
            self.progress_bar.setValue(self.counter)
        else:
            self.accept()

    def set_value(self, counter):
        """Update the progress bar to specific"""
        self.counter = counter
        self.progress_bar.setValue(self.counter)

    def no_counter(self):
        """Update the progress bar to specific"""
        self.progress_bar.setRange(0, 0)

    def reset_counter(self):
        """Update the progress bar to specific"""
        self.set_value(0)
