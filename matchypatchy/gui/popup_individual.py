"""
Create a new Individual Fillable Form

individual (id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            sex TEXT,
            age TEXT);'''
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
                             QLabel, QLineEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtWidgets


class IndividualPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage Individuals")
        self.parent = parent
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()
        # Individuals Table
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
        # not enabled until station is selected
        self.button_edit.setEnabled(False)
        self.button_view.setEnabled(False)
        button_layout.addWidget(self.button_edit)
        button_layout.addWidget(self.button_view)
        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update()

    def set_editview(self):
        """Enable/disable edit and view buttons based on selection"""
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag)
        self.button_view.setEnabled(flag)

    def update(self):
        """Update table with individuals from database"""
        self.individuals = self.mpDB._command("""SELECT individual.name, individual.id, COUNT(roi.individual_id) AS count
                                                 FROM individual LEFT JOIN roi ON roi.individual_id = individual.id
                                                 GROUP BY roi.individual_id;""")
        # get unidentified count
        self.nulls = self.mpDB.select("roi", "COUNT(*)", row_cond="individual_id IS NULL")[0][0]
        self.list.setRowCount(len(self.individuals) + 1)
        # Add unidentified row
        self.list.setItem(0, 0, QTableWidgetItem("Unidentified"))
        self.list.setItem(0, 1, QTableWidgetItem(str(self.nulls)))
        # Add data to rows
        for row in range(len(self.individuals)):
            self.list.setItem(row + 1, 0, QTableWidgetItem(self.individuals[row][0]))
            self.list.setItem(row + 1, 1, QTableWidgetItem(str(self.individuals[row][2])))

    def edit(self):
        """Edit selected individual"""
        # cannot edit unidentified
        if self.list.currentRow() == 0:
            return

        self.selected_ind = self.individuals[self.list.currentRow() - 1]
        id, name, sex, age = self.mpDB.select('individual', row_cond=f'id={self.selected_ind[1]}')[0]
        # open edit dialog with current values
        dialog = IndividualFillPopup(self, name=name, sex=sex, age=age)
        if dialog.exec():
            replace_dict = {"name": dialog.get_name(),
                            "sex": dialog.get_sex(),
                            "age": dialog.get_age()}
            # update database
            self.mpDB.edit_row("individual", id, replace_dict)
        del dialog
        # refetch data
        self.individuals = self.update()

    def view(self):
        """Go to media view filtered by individual"""
        if self.list.currentRow() == 0:
            filters = {"individual_id": 0}
        else:
            self.selected_ind = self.individuals[self.list.currentRow() - 1]
            filters = {"individual_id": self.selected_ind[1]}
        self.parent.set_filtered_view(filters)
        self.accept()


class IndividualFillPopup(QDialog):
    def __init__(self, parent, name=None, sex=None, age=None):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.setWindowTitle("Edit Individual")
        layout = QVBoxLayout()

        # Name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        self.name.setText(name)
        layout.addWidget(self.name)
        # Sex
        layout.addWidget(QLabel('Sex'))
        self.sex = QComboBox()
        self.sex.addItems(['Unknown', 'Male', 'Female'])
        layout.addWidget(self.sex)
        # Age
        layout.addWidget(QLabel('Age'))
        self.age = QComboBox()
        self.age.addItems(['Unknown', 'Juvenile', 'Subadult', 'Adult'])
        layout.addWidget(self.age)

        self.name.textChanged.connect(self.checkInput)
        self.sex.currentIndexChanged.connect(self.checkInput)
        self.age.currentIndexChanged.connect(self.checkInput)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)
        self.checkInput()  # will enable ok button if in edit mode

        self.setLayout(layout)

    def checkInput(self):
        self.okButton.setEnabled(bool(self.get_name()))

    def get_name(self):
        return self.name.text()

    def get_sex(self):
        return self.sex.currentText()

    def get_age(self):
        return self.age.currentText()

    def accept_verify(self):
        if self.get_name():
            self.accept()
