'''

'''

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets

from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_survey import SurveyFillPopup
from matchypatchy.gui.popup_site import SiteFillPopup
from matchypatchy.gui.popup_species import SpeciesFillPopup

from matchypatchy.database import survey 
from matchypatchy.database import site  
from matchypatchy.database import species 
from matchypatchy.database import media 


class TableEditorPopup(QDialog):
    def __init__(self, parent, table):
        super().__init__(parent)
        # get database object
        self.mpDB = parent.mpDB
        self.table = table

        self.fetch()

        print(self.data)

        self.setWindowTitle(f"Edit {self.table}")
        self.setFixedSize(600, 425)
        layout = QVBoxLayout()

        self.list = QTableWidget()  
        self.list.setColumnCount(self.data.shape[1])
        self.list.setHorizontalHeaderLabels(self.data.columns.tolist())
        self.list.setColumnWidth(0, 25)  # set id column to be small
        self.list.horizontalHeader().setStretchLastSection(True)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.itemChanged.connect(self.edit)
        layout.addWidget(self.list) 

        # Buttons
        button_layout = QHBoxLayout()
        button_new = QPushButton("New")
        button_new.clicked.connect(self.add)
        button_layout.addWidget(button_new)

        self.button_save = QPushButton("Save")
        self.button_save.clicked.connect(self.edit)
        self.button_save.setEnabled(False)
        button_layout.addWidget(self.button_save)

        self.button_del = QPushButton("Delete")
        self.button_del.clicked.connect(self.delete)
        self.button_del.setEnabled(False)
        button_layout.addWidget(self.button_del)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update()

    def fetch(self):
        # REFACTOR THIS?
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
        self.list.setRowCount(self.data.shape[0])
        self.list.setColumnCount(self.data.shape[1])
        for row in range(self.data.shape[0]):
            for column in range(self.data.shape[1]): # skip id column
                item = QTableWidgetItem(str(self.data.iat[row, column]))
                if column in self.editable_columns:
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable) 
                self.list.setItem(row, column, item)

    def add(self):
        if self.table == "survey":
            dialog = SurveyFillPopup(self)
            if dialog.exec():
                confirm = self.mpDB.add_survey(dialog.get_name(), dialog.get_region(),
                                           dialog.get_year_start(), dialog.get_year_start())
        elif self.table == "site":
            dialog = SiteFillPopup(self.mpDB)
            if dialog.exec():
                confirm = self.mpDB.add_site(dialog.get_name(),dialog.get_lat(),
                                             dialog.get_long(),self.survey_id[0])
        elif self.table == "species":
            dialog = SpeciesFillPopup(self.mpDB)
            if dialog.exec():
                confirm = self.mpDB.add_species(dialog.get_binomen(),dialog.get_common())
        elif self.table == "media":
            dialog = None

        del dialog

        self.fetch()
        self.update()


    def edit(self):
        # TODO
        self.button_save.setEnabled(True)
        # confirm changes button?
        selected_site = self.list.currentRow()
        id = self.data.iloc[selected_site]
        print(id)
        replace = dict()

        #self.mpDB.edit_row(self.table, id, replace)

        #self.sites = self.update()

    def delete(self):
        selected = self.list.currentItem().text()
        prompt = f'Are you sure you want to delete {selected}?'
        print(prompt)
        dialog = AlertPopup(self, prompt)
        if dialog.exec():
            row = self.data.loc[self.list.currentRow(),'id']
            cond = f'id={row}'
            self.mpDB.delete(self.table, cond)
        del dialog
        self.update()
