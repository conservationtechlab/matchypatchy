'''
Alert Popup displaying simple text and OK/Cancel buttons
Options for progress bar and cancel-only mode.
'''
from PyQt6.QtWidgets import QVBoxLayout, QDialogButtonBox, QLabel, QDialog, QProgressBar
from PyQt6.QtCore import Qt


class AlertPopup(QDialog):
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
            self.min = 0
            self.max = 100
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(self.min, self.max)
            self.progress_bar.setValue(self.counter)
            layout.addWidget(self.progress_bar)

        # buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        # disable OK button if cancel_only
        if cancel_only:
            ok_button = buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            ok_button.setEnabled(False)  # Disable the OK button

        layout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def update_prompt(self, prompt):
        """Update the prompt text"""
        self.prompt.setText(prompt)

    def set_min(self, min):
        """Update the progress bar maximum value"""
        self.min = min
        self.progress_bar.setRange(self.min, self.max)

    def set_max(self, max):
        """Update the progress bar maximum value"""
        self.max = max
        self.progress_bar.setRange(self.min, self.max)

    def set_counter(self, counter):
        """Update the progress bar to specific"""
        if counter < self.max:
            self.counter = counter
            self.progress_bar.setValue(self.counter)
        else:
            self.close()

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
