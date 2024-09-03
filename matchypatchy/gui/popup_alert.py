'''

'''
from PyQt6 import QtCore, QtWidgets

class AlertPopup(QtWidgets.QDialog):
    def __init__(self, parent, prompt):
        super().__init__(parent)
        
        self.prompt = prompt
        
        self.setWindowTitle("Alert")
        fullLayout = QtWidgets.QVBoxLayout(self)
        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        layout = QtWidgets.QVBoxLayout(self.container)
        
        
        title = QtWidgets.QLabel(self.prompt, 
            objectName='title', alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
 
        # buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        button_layout.addWidget(buttonBox, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        buttonBox.accepted.connect(self.accept)
        layout.addLayout(button_layout)