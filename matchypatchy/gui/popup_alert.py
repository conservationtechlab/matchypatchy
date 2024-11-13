'''
Alert Popup displaying simple text and OK/Cancel buttons
ProgressBar Popup 
'''
from PyQt6.QtWidgets import QVBoxLayout, QDialogButtonBox, QLabel, QDialog, QProgressBar
from PyQt6.QtCore import Qt


class AlertPopup(QDialog):
    def __init__(self, parent, prompt, title="Alert", progressbar=False):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        
        self.prompt = QLabel(prompt, objectName='title', 
                            alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.prompt)

        if progressbar:
            self.progress_bar = QProgressBar()
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setRange(0,0)
            layout.addWidget(self.progress_bar)
 
        # buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        buttonBox.accepted.connect(self.accept)  
        buttonBox.rejected.connect(self.reject)

    def update(self, prompt):
        self.prompt.setText(prompt)


class ProgressPopup(QDialog):
    def __init__(self, parent, prompt):
        super().__init__(parent)
        self.setWindowTitle("Progress")
        self.layout = QVBoxLayout()

        self.counter = 0
        self.min = 0
        self.max = 100
        
        self.label = QLabel(prompt)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(self.min, self.max)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)


    def update_progress(self):
        """Update the progress bar based on the counter value."""
        self.counter += 1
        print(self.counter)
        self.progress_bar.setValue(self.counter)  # Update progress bar value

        if self.counter >= self.max:  # Stop the timer when progress reaches 100
            self.close()

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