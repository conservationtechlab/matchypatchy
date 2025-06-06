'''
Popup to add or edit species
'''
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                             QHBoxLayout, QPushButton, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6 import QtWidgets

from matchypatchy.gui.popup_alert import AlertPopup


class SpeciesPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage Species")
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()

        # SPECIES LIST
        self.list = QTableWidget()
        self.list.setColumnCount(2)
        self.list.setHorizontalHeaderLabels(['Scientific Name', 'Common Name'])
        self.list.setColumnWidth(0, 200)
        self.list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.list)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.itemSelectionChanged.connect(self.set_editdel)

        # Buttons
        button_layout = QHBoxLayout()
        button_new = QPushButton("New")
        self.button_edit = QPushButton("Edit")
        self.button_del = QPushButton("Delete")

        button_new.clicked.connect(self.add)
        self.button_edit.clicked.connect(self.edit)
        self.button_del.clicked.connect(self.delete)

        # not enabled until station is selected
        self.button_del.setEnabled(False)
        self.button_edit.setEnabled(False)

        button_layout.addWidget(button_new)
        button_layout.addWidget(self.button_edit)
        button_layout.addWidget(self.button_del)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update()

    def set_editdel(self):
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag)
        self.button_del.setEnabled(flag)

    def update(self):
        self.species_list_ordered = self.mpDB.select("species")
        self.list.setRowCount(len(self.species_list_ordered))

        # Add data to rows
        for row in range(len(self.species_list_ordered)):
            binomen = QTableWidgetItem(self.species_list_ordered[row][1])
            common = QTableWidgetItem(self.species_list_ordered[row][2])
            self.list.setItem(row, 0, binomen)
            self.list.setItem(row, 1, common)
        self.set_editdel()

    def add(self):
        dialog = SpeciesFillPopup(self)
        if dialog.exec():
            self.mpDB.add_species(dialog.get_binomen(), dialog.get_common())
        del dialog
        self.stations = self.update()

    def edit(self):
        selected_station = self.list.currentRow()
        id = self.species_list_ordered[selected_station][0]

        cond = f'id={id}'
        id, binomen, common = self.mpDB.select('species', row_cond=cond)[0]
        dialog = SpeciesFillPopup(self, binomen=binomen, common=common)
        if dialog.exec():
            replace_dict = {"binomen": dialog.get_binomen(), "common": dialog.get_common()}
            self.mpDB.edit_row("species", id, replace_dict)
        del dialog
        self.stations = self.update()

    def delete(self):
        selected = self.list.currentItem().text()
        dialog = AlertPopup(self, f'Are you sure you want to delete {selected}?')
        if dialog.exec():
            row = self.species_list_ordered[self.list.currentRow()][0]
            self.mpDB.delete("species", f'id={row}')
        del dialog
        self.update()


class SpeciesFillPopup(QDialog):
    def __init__(self, parent, binomen="", common=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Species")

        layout = QVBoxLayout()

        # Scientific Name
        layout.addWidget(QLabel('Scientific Name'))
        self.binomen = QLineEdit()
        self.binomen.setText(binomen)
        layout.addWidget(self.binomen)

        # Common Name
        layout.addWidget(QLabel('Common Name'))
        self.common = QLineEdit()
        self.common.setText(str(common))
        layout.addWidget(self.common)

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)
        self.checkInput()  # will enable ok button if in edit mode

        self.binomen.textChanged.connect(self.checkInput)
        self.common.textChanged.connect(self.checkInput)

        self.binomen.returnPressed.connect(lambda: self.common.setFocus())
        self.common.returnPressed.connect(self.accept_verify)

        self.setLayout(layout)

        self.binomen.setFocus()

    def checkInput(self):
        self.okButton.setEnabled(bool(self.get_binomen() and self.get_common()))

    def get_binomen(self):
        return self.binomen.text()

    def get_common(self):
        return self.common.text()

    def accept_verify(self):
        if self.get_binomen() and self.get_common():
            self.accept()
