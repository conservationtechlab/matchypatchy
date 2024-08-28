'''

'''
from PyQt6 import QtCore, QtWidgets

class ConfirmPopup(QtWidgets.QDialog):
    def __init__(self, prompt):
        super().__init__()
        
        self.prompt = prompt
        
        self.setWindowTitle("Confirm")
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
        
        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)