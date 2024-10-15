'''

'''
from PyQt6 import QtCore, QtWidgets

from .popup_alert import AlertPopup

class SpeciesPopup(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage Species")
        #inherit survey information, db object
        self.mpDB = parent.mpDB

        fullLayout = QtWidgets.QVBoxLayout(self)
        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        
        layout = QtWidgets.QVBoxLayout(self.container)
        # SPECIES LIST

        self.list = QtWidgets.QTableWidget()  
        self.list.setColumnCount(2)
        self.list.setHorizontalHeaderLabels(['Scientific Name', 'Common Name'])
        self.list.setColumnWidth(0, 200)
        self.list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.list) 
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.itemSelectionChanged.connect(self.set_editdel)
 
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_new =  QtWidgets.QPushButton("New")
        button_new.clicked.connect(self.add)
        button_layout.addWidget(button_new)

        self.button_edit = QtWidgets.QPushButton("Edit")
        self.button_edit.clicked.connect(self.edit)
        self.button_edit.setEnabled(False)
        button_layout.addWidget(self.button_edit)
        
        self.button_del = QtWidgets.QPushButton("Delete")
        self.button_del.clicked.connect(self.delete)
        self.button_del.setEnabled(False)
        button_layout.addWidget(self.button_del)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)
        
        self.update()


    def set_editdel(self):
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow()+1) 
        self.button_edit.setEnabled(flag)
        self.button_del.setEnabled(flag)

    def update(self):
        #self.species_model.clear()
        self.species_list_ordered = self.mpDB.select("species")
        self.list.setRowCount(len(self.species_list_ordered))

        # Add data to rows
        for row in range(len(self.species_list_ordered)):
            binomen = QtWidgets.QTableWidgetItem(self.species_list_ordered[row][1])
            common = QtWidgets.QTableWidgetItem(self.species_list_ordered[row][2])
            self.list.setItem(row, 0, binomen)
            self.list.setItem(row, 1, common)
        self.set_editdel()   

    def add(self):
        dialog = SpeciesFillPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_species(dialog.get_binomen(),dialog.get_common())
        del dialog
        self.sites = self.update()

    def edit(self):
        selected_site = self.list.currentRow()
        id = self.species_list_ordered[selected_site][0]

        cond = f'id={id}'
        id, binomen, common = self.mpDB.select('species', row_cond=cond)[0]
        dialog = SpeciesFillPopup(self, binomen=binomen, common=common)
        if dialog.exec():
            replace_dict = {"binomen":f"'{dialog.get_binomen()}'", "common":f"'{dialog.get_common()}'"}
            confirm = self.mpDB.edit_row("species",id,replace_dict)
        del dialog
        self.sites = self.update()
    
    def delete(self):
        selected = self.list.currentItem().text()
        prompt = f'Are you sure you want to delete {selected}?'
        print(prompt)
        dialog = AlertPopup(self, prompt)
        if dialog.exec():
            row = self.species_list_ordered[self.list.currentRow()][0]
            cond = f'id={row}'
            self.mpDB.delete("species", cond)
        del dialog
        self.update()


class SpeciesFillPopup(QtWidgets.QDialog):
    def __init__(self, parent, binomen="", common=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Species")
        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        layout = QtWidgets.QVBoxLayout(self.container)

        # Scientific Name
        layout.addWidget(QtWidgets.QLabel('Scientific Name'))
        self.binomen = QtWidgets.QLineEdit()
        self.binomen.setText(binomen)
        layout.addWidget(self.binomen)

        # Common Name
        layout.addWidget(QtWidgets.QLabel('Common Name'))
        self.common = QtWidgets.QLineEdit()
        self.common.setText(str(common))
        layout.addWidget(self.common)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False) 
        self.checkInput() # will enable ok button if in edit mode

        self.binomen.textChanged.connect(self.checkInput)
        self.common.textChanged.connect(self.checkInput)

        self.binomen.returnPressed.connect(lambda: self.common.setFocus())
        self.common.returnPressed.connect(self.accept_verify)

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
