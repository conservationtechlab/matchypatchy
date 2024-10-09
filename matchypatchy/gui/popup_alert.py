'''
Alert Popup displaying simple text and OK button
'''
from PyQt6.QtWidgets import QVBoxLayout, QDialogButtonBox, QLabel, QDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class AlertPopup(QDialog):
    def __init__(self, parent, prompt, title="Alert"):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        
        self.prompt = QLabel(prompt, objectName='title', 
                            alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.prompt)
 
        # buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(buttonBox, alignment=Qt.AlignmentFlag.AlignCenter)
        buttonBox.accepted.connect(self.accept)


    def update(self, prompt):
        self.prompt.setText(prompt)
