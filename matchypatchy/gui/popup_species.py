'''

'''
from PyQt6 import QtCore, QtWidgets

from ..database import mpdb
from .popup_confirm import ConfirmPopup

class SpeciesPopup(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        #inherit survey information, db object
        self.mpDB = parent.mpDB

        fullLayout = QtWidgets.QVBoxLayout(self)
        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        
        layout = QtWidgets.QVBoxLayout(self.container)
        # SITE LIST
        # fetch from database 
        self.site_select = QtWidgets.QListWidget()
        layout.addWidget(self.site_select) 
        self.site_select.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.site_select.itemSelectionChanged.connect(self.set_editdel)
 
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_survey_new =  QtWidgets.QPushButton("New")
        button_survey_new.clicked.connect(self.add)
        button_layout.addWidget(button_survey_new)

        self.button_site_edit = QtWidgets.QPushButton("Edit")
        self.button_site_edit.clicked.connect(self.edit)
        self.button_site_edit.setEnabled(False)
        button_layout.addWidget(self.button_site_edit)
        
        self.button_site_del = QtWidgets.QPushButton("Delete")
        self.button_site_del.clicked.connect(self.delete)
        self.button_site_del.setEnabled(False)
        button_layout.addWidget(self.button_site_del)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)
        
        self.update()


    def set_editdel(self):
        # currentRow() returns -1 if nothing selected
        flag = bool(self.site_select.currentRow()+1) 
        self.button_site_edit.setEnabled(flag)
        self.button_site_del.setEnabled(flag)

    def update(self):
        self.site_select.clear()
        sites = self.mpDB.fetch_table("species")
        self.site_list = dict(sites)
        self.site_list_ordered = sites
        if self.site_list_ordered:
            self.site_select.addItems([el[1] for el in sites])
        self.set_editdel()   

    def add(self):
        dialog = SpeciesFillPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_species(dialog.get_binomen(),dialog.get_common())
        del dialog
        self.sites = self.update()

    def edit(self):
        selected_site = self.site_select.currentRow()
        id = self.site_list_ordered[selected_site][0]
        cond = f'id={id}'
        id, binomen, common = self.mpDB.fetch_rows('species',cond)[0]
        dialog = SpeciesFillPopup(self, binomen=binomen, common=common)
        if dialog.exec():
            replace_dict = {"binomen":dialog.get_binomen(), "common":dialog.get_common()}
            confirm = self.mpDB.edit_row("species",id,replace_dict)
        del dialog
        self.sites = self.update()
    
    def delete(self):
        selected = self.site_select.currentItem().text()
        prompt = f'Are you sure you want to delete {selected}?'
        print(prompt)
        dialog = ConfirmPopup(self, prompt)
        if dialog.exec():
            row = self.site_list_ordered[self.site_select.currentRow()][0]
            cond = f'id={row}'
            self.mpDB.delete("species", cond)
        del dialog
        self.update_sites()


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
