'''
Alert Popup displaying simple text and OK/Cancel buttons
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
