'''

'''
from PyQt6 import QtCore, QtWidgets

class SurveyPopup(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Survey")
        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)

        
        buttonSize = self.fontMetrics().height() 

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(
            buttonSize * 2, buttonSize, buttonSize * 2, buttonSize)

        title = QtWidgets.QLabel(
            'Enter a new Survey', 
            objectName='title', alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # name
        layout.addWidget(QtWidgets.QLabel('Name'))
        self.name = QtWidgets.QLineEdit()
        layout.addWidget(self.name)

        #region
        layout.addWidget(QtWidgets.QLabel('Region'))
        self.region = QtWidgets.QLineEdit()
        layout.addWidget(self.region)

        # start year
        layout.addWidget(QtWidgets.QLabel('Start Year'))
        self.year_start = QtWidgets.QLineEdit()
        layout.addWidget(self.year_start)

        layout.addWidget(QtWidgets.QLabel('End Year'))
        self.year_end = QtWidgets.QLineEdit()
        layout.addWidget(self.year_end)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.name.textChanged.connect(self.checkInput)
        self.region.textChanged.connect(self.checkInput)
        self.year_start.textChanged.connect(self.checkInput)
        self.year_end.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(lambda:
                self.region.setFocus())
        self.region.returnPressed.connect(lambda:
                self.year_start.setFocus())
        self.year_start.returnPressed.connect(lambda:
                self.year_end.setFocus())
        self.year_end.returnPressed.connect(self.accept_verify)

        self.name.setFocus()

    def checkInput(self):
        # year end not necessary
        self.okButton.setEnabled(bool(self.get_name() and self.get_region() and self.get_year_start()))

    def get_name(self):
        return self.name.text()

    def get_region(self):
        return self.region.text()
    
    def get_year_start(self):
        return self.year_start.text()

    def get_year_end(self):
        return self.year_end.text()

    def accept_verify(self):
        if self.get_name() and self.get_region() and self.get_year_start():
            self.accept()
