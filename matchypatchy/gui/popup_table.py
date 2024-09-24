'''

'''
from PyQt6 import QtCore, QtWidgets

from .popup_confirm import ConfirmPopup
from .popup_survey import SurveyPopup

from ..database import survey 
from ..database import site  
from ..database import species 
from ..database import media 


class TableEditorPopup(QtWidgets.QDialog):
    def __init__(self, parent, table):
        super().__init__(parent)
        # get database object
        self.mpDB = parent.mpDB
        self.table = table

        self.fetch()

        print(self.data)

        self.setWindowTitle(f"Edit {self.table}")
        fullLayout = QtWidgets.QVBoxLayout(self)
        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        
        layout = QtWidgets.QVBoxLayout(self.container)
    

        self.list = QtWidgets.QTableWidget()  
        self.list.setRowCount(self.data.shape[0])
        self.list.setColumnCount(self.data.shape[1])
        self.list.setHorizontalHeaderLabels(self.data.columns.tolist())
        self.list.setColumnWidth(0, 200)
        self.list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.list) 
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.itemChanged.connect(self.edit)
 
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

    def fetch(self):
        if self.table == "survey":
            self.data = survey.fetch_surveys(self.mpDB)
            self.editable_columns = survey.user_editable_rows()
        elif self.table == "site":
            self.data = site.fetch_sites(self.mpDB)
            self.editable_columns = site.user_editable_rows()
        elif self.table == "species":
            self.data = species.fetch_species(self.mpDB)
            self.editable_columns = species.user_editable_rows()
        elif self.table == "media":
            self.data = media.fetch_media(self.mpDB)
            self.editable_columns = media.user_editable_rows()
        else:
            self.reject()

    def update(self):
        '''
        Update table

        TO DO: DO NOT ALLOW FOREIGN KEYS TO BE EDITED 
        '''
        self.fetch()
        for row in range(self.data.shape[0]):
            for column in range(self.data.shape[1]): # skip id column
                item = QtWidgets.QTableWidgetItem(str(self.data.iat[row, column]))
                if column in self.editable_columns:
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable) 
                self.list.setItem(row, column, item)

    def add(self):
        if self.table == "survey":
            dialog = SurveyPopup(self)
        elif self.table == "site":
            dialog = AddSurvey(self.mpDB)
        elif self.table == "species":
            dialog = fetch_species(self.mpDB)
            if dialog.exec():
                dialog = self.mpDB.add_species(dialog.get_binomen(),dialog.get_common())
        elif self.table == "media":
            dialog = fetch_media(self.mpDB)

        del dialog

        self.update()


    def edit(self):
        selected_site = self.list.currentRow()
        id = self.data.iloc[selected_site]

        dialog = AddPopup(self)
        if dialog.exec():
            replace_dict = {"binomen":f"'{dialog.get_binomen()}'", "common":f"'{dialog.get_common()}'"}
            confirm = self.mpDB.edit_row("species",id,replace_dict)
        del dialog
        self.sites = self.update()
    
    def delete(self):
        selected = self.list.currentItem().text()
        prompt = f'Are you sure you want to delete {selected}?'
        print(prompt)
        dialog = ConfirmPopup(self, prompt)
        if dialog.exec():
            row = self.species_list_ordered[self.list.currentRow()][0]
            cond = f'id={row}'
            self.mpDB.delete("species", cond)
        del dialog
        self.update()

