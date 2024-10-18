"""
Create a new Individual Fillable Form
"""


from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QLabel, QLineEdit,
                             QDialogButtonBox, )


class IndividualFillPopup(QDialog):
    def __init__(self, parent, species_id=None):
        super().__init__(parent)
        self.species_id = species_id
        self.mpDB = parent.mpDB
        self.setWindowTitle("New Individual")

        buttonSize = self.fontMetrics().height() 

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(buttonSize * 2, buttonSize, buttonSize * 2, buttonSize)

        # species
        self.combo = QComboBox()
        layout.addWidget()

        # name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        layout.addWidget(self.name)

        # sex
        layout.addWidget(QLabel('Sex'))
        self.sex = QLineEdit()
        layout.addWidget(self.sex)


        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False) 
        self.checkInput() # will enable ok button if in edit mode

        self.name.textChanged.connect(self.checkInput)
        self.sex.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(lambda:
                self.sex.setFocus())
        self.sex.returnPressed.connect(self.accept_verify)

        self.name.setFocus()

    def set_species_options(self):
        options = self.mpDB.select("species", columns = "id, common")
        self.list = list(options)
        self.combo.addItems([el[1] for el in self.list])
        if self.species_id is not None:
            set_to_index = next((i for i, t in enumerate(self.list) if t[0] == self.species_id), None)
            self.combo.setCurrentIndex(set_to_index)

    def checkInput(self):
        # year end not necessary
        self.okButton.setEnabled(bool(self.get_name()))

    def get_name(self):
        return self.name.text()

    def get_sex(self):
        return self.sex.text()
    
    def get_species_id(self):
        # return id only
        return self.list[self.combo.currentIndex()][0]


    def accept_verify(self):
        if self.get_name():
            self.accept()
