"""
Create a new Individual Fillable Form

individual (id INTEGER PRIMARY KEY,
            species_id INTEGER,
            name TEXT NOT NULL,
            sex TEXT,
            FOREIGN KEY(species_id) REFERENCES species (id));'''
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
                             QLabel, QLineEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtCore, QtWidgets

class IndividualPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage Individuals")
        self.parent = parent
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()

        # INDIVIDUALS
        self.list = QTableWidget()
        self.list.setColumnCount(2)
        self.list.setHorizontalHeaderLabels(['Name', 'Number of Images'])
        self.list.setColumnWidth(0, 200)
        self.list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.list)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.itemSelectionChanged.connect(self.set_editview)

        # Buttons
        button_layout = QHBoxLayout()

        self.button_edit = QPushButton("Edit")
        self.button_view = QPushButton("View")

        self.button_edit.clicked.connect(self.edit)
        self.button_view.clicked.connect(self.view)

        # not enabled until site is selected
        self.button_edit.setEnabled(False)
        self.button_view.setEnabled(False)


        button_layout.addWidget(self.button_edit)
        button_layout.addWidget(self.button_view)
        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update()

    def set_editview(self):
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag)
        self.button_view.setEnabled(flag)

    def update(self):
        print(self.mpDB.count('individual'))


        self.individuals = self.mpDB._command("""SELECT individual.name, roi.individual_id, COUNT(roi.individual_id) AS count
                                                 FROM individual LEFT JOIN roi ON roi.individual_id = individual.id
                                                 GROUP BY roi.individual_id;""")
        self.nulls = self.mpDB.select("roi", "COUNT(*)", row_cond="individual_id IS NULL")[0][0]
        self.list.setRowCount(len(self.individuals) + 1)

        self.list.setItem(0, 0, QTableWidgetItem("Unidentified"))
        self.list.setItem(0, 1, QTableWidgetItem(str(self.nulls)))

        # Add data to rows
        for row in range(len(self.individuals)):
            self.list.setItem(row + 1, 0, QTableWidgetItem(self.individuals[row][0]))
            self.list.setItem(row + 1, 1, QTableWidgetItem(str(self.individuals[row][2])))

    def edit(self):
        # cannot edit unidentified
        if self.list.currentRow() == 0:
            return
        
        self.selected_ind = self.individuals[self.list.currentRow() - 1]

        id, species_id, name, sex = self.mpDB.select('individual', row_cond=f'id={self.selected_ind[1]}')[0]

        dialog = IndividualFillPopup(self, species_id=species_id, name=name, sex=sex)
        if dialog.exec():
            replace_dict = {"name": f"'{dialog.get_name()}'", 
                            "sex": f"'{dialog.get_sex()}'", 
                            "species_id": f"'{dialog.get_species_id()}'", }
            self.mpDB.edit_row("individual", id, replace_dict)
        del dialog
        # refetch data
        self.sites = self.update()
        

    def view(self):
        # set to media view filtered by individual
        if self.list.currentRow() == 0:
            filters = {"individual_id": 0}
        
        else:
            self.selected_ind = self.individuals[self.list.currentRow() - 1]
            filters = {"individual_id": self.selected_ind[1]}
        self.parent.set_filtered_view(filters)
        self.accept()


class IndividualFillPopup(QDialog):
    def __init__(self, parent, species_id=None, name=None, sex=None):
        super().__init__(parent)
        self.species_id = species_id
        self.mpDB = parent.mpDB

        self.setWindowTitle("Edit Individual")

        layout = QVBoxLayout()

        # species
        self.species_combo = QComboBox()
        layout.addWidget(self.species_combo)
        self.set_species_options()

        # name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        self.name.setText(name)
        layout.addWidget(self.name)

        # sex
        layout.addWidget(QLabel('Sex'))
        self.sex = QLineEdit()
        self.sex.setText(sex)
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
        self.species_list = [(None, "Species")] + list(options)
        self.species_combo.addItems([el[1] for el in self.species_list])
        if self.species_id is not None:
            set_to_index = next((i for i, t in enumerate(self.species_list) if t[0] == self.species_id), None)
            self.species_combo.setCurrentIndex(set_to_index)

    def checkInput(self):
        self.okButton.setEnabled(bool(self.get_name()))

    def get_name(self):
        return self.name.text()

    def get_sex(self):
        return self.sex.text()

    def get_species_id(self):
        # return id only
        return self.species_list[self.species_combo.currentIndex()][0]

    def accept_verify(self):
        if self.get_name():
            self.accept()
