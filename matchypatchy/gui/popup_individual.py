"""
Create a new Individual Fillable Form
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QListWidget,
                             QLabel, QLineEdit, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets

class IndividualPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage Individuals")
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()
        # SITE LIST
        self.list = QListWidget()
        layout.addWidget(self.list)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        # Buttons
        button_layout = QHBoxLayout()
                # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)


class IndividualFillPopup(QDialog):
    def __init__(self, parent, species_id=None):
        super().__init__(parent)
        self.species_id = species_id
        self.mpDB = parent.mpDB

        self.setWindowTitle("New Individual")

        layout = QVBoxLayout()

        # species
        self.species_combo = QComboBox()
        layout.addWidget(self.species_combo)
        self.set_species_options()

        # name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        layout.addWidget(self.name)

        # sex
        layout.addWidget(QLabel('Sex'))
        self.sex = QLineEdit()
        layout.addWidget(self.sex)

        self.name.textChanged.connect(self.checkInput)
        self.sex.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(lambda: self.sex.setFocus())
        self.sex.returnPressed.connect(self.accept_verify)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)
        self.checkInput()  # will enable ok button if in edit mode

        self.setLayout(layout)

    def set_species_options(self):
        options = self.mpDB.select("species", columns="id, common")
        self.list = [(None, "Species")] + list(options)
        self.species_combo.addItems([el[1] for el in self.list])
        if self.species_id is not None:
            set_to_index = next((i for i, t in enumerate(self.list) if t[0] == self.species_id), None)
            self.species_combo.setCurrentIndex(set_to_index)

    def checkInput(self):
        self.okButton.setEnabled(bool(self.get_name()))

    def get_name(self):
        return self.name.text()

    def get_sex(self):
        return self.sex.text()

    def get_species_id(self):
        # return id only
        return self.list[self.species_combo.currentIndex()][0]

    def accept_verify(self):
        if self.get_name():
            self.accept()
