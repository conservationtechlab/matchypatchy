'''

'''
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIntValidator

from matchypatchy.gui.popup_alert import AlertPopup


class SurveyPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage surveys")
        #inherit survey information, db object
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()

        # survey LIST
        # fetch from database 
        self.list = QListWidget()
        layout.addWidget(self.list) 
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.list.itemSelectionChanged.connect(self.set_editdel)
 
        # Buttons
        button_layout = QHBoxLayout()

        button_new =  QPushButton("New")
        self.button_edit = QPushButton("Edit") 
        self.button_del = QPushButton("Delete")

        button_new.clicked.connect(self.add)
        self.button_edit.clicked.connect(self.edit)
        self.button_del.clicked.connect(self.delete)

        # not enabled until survey is selected
        self.button_del.setEnabled(False)
        self.button_edit.setEnabled(False)

        button_layout.addWidget(button_new)
        button_layout.addWidget(self.button_edit)
        button_layout.addWidget(self.button_del)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        
        self.update()


    def set_editdel(self):
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow()+1) 
        self.button_edit.setEnabled(flag)
        self.button_del.setEnabled(flag)

    def update(self):
        self.list.clear()
        self.survey_list_ordered = self.mpDB.select("survey", columns="id, name")
        self.survey_list = dict(self.survey_list_ordered)
        if self.survey_list_ordered:
            self.list.addItems([el[1] for el in self.survey_list_ordered])
        self.set_editdel()   

    def add(self):
        dialog = SurveyFillPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_survey(dialog.get_name(), dialog.get_region(),
                                           dialog.get_year_start(), dialog.get_year_start())
        del dialog
        self.surveys = self.update()

    def edit(self):
        selected_survey = self.list.currentRow()
        id = self.survey_list_ordered[selected_survey][0]
        cond = f'id={id}'
        id, name, region, year_start, year_end = self.mpDB.select('survey',
                                                                  columns='id, name, region, year_start, year_end', 
                                                                  row_cond=cond)[0]
        region = '' if region is None else region
        year_start = '' if year_start is None else year_start
        year_end = '' if year_end is None else year_end

        dialog = SurveyFillPopup(self, name=name, region=region, year_start=year_start, year_end=year_end)

        if dialog.exec() and dialog.accepted:
            replace_dict = {"name":f"'{dialog.get_name()}'", 
                            "region":f"'{dialog.get_region()}'", 
                            "year_start":dialog.get_year_start(), 
                            "year_end":dialog.get_year_end()}
            
            confirm = self.mpDB.edit_row("survey", id, replace_dict, quiet=False)
        del dialog
        self.surveys = self.update()
    
    def delete(self):
        selected = self.list.currentItem().text()
        prompt = f'Are you sure you want to delete {selected}?'
        dialog = AlertPopup(self, prompt)
        if dialog.exec():
            row = self.survey_list_ordered[self.list.currentRow()][0]
            cond = f'id={row}'
            self.mpDB.delete("survey",cond)
        del dialog
        self.update()

            
class SurveyFillPopup(QDialog):
    def __init__(self, parent, name="", region="", year_start="", year_end=""):
        super().__init__(parent)
        self.setWindowTitle("Survey")
        layout = QVBoxLayout()

        title = QLabel('Enter a new Survey', objectName='title', 
                       alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        self.name.setText(str(name))
        layout.addWidget(self.name)

        #region
        layout.addWidget(QLabel('Region'))
        self.region = QLineEdit()
        self.region.setText(str(region))
        layout.addWidget(self.region)

        # start year
        layout.addWidget(QLabel('Start Year'))
        self.year_start = QLineEdit()
        self.year_start.setValidator(QIntValidator(0, 3000))
        self.year_start.setText(str(year_start))
        layout.addWidget(self.year_start)

        # end year
        layout.addWidget(QLabel('End Year'))
        self.year_end = QLineEdit()
        self.year_end.setValidator(QIntValidator(0, 3000))
        self.year_end.setText(str(year_end))
        layout.addWidget(self.year_end)

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.name.textChanged.connect(self.check_input)
        self.region.textChanged.connect(self.check_input)

        self.name.returnPressed.connect(lambda: self.region.setFocus())
        self.region.returnPressed.connect(lambda: self.year_start.setFocus())
        self.year_start.returnPressed.connect(lambda: self.year_end.setFocus())
        self.year_end.returnPressed.connect(self.accept_verify)

        self.name.setFocus()
        self.check_input()

        self.setLayout(layout)

    def check_input(self):
        self.okButton.setEnabled(bool(self.get_name() and self.get_region()))

    def get_name(self):
        return self.name.text()

    def get_region(self):
        return self.region.text()
    
    def get_year_start(self):
        return self.year_start.text()

    def get_year_end(self):
        return self.year_end.text()

    def accept_verify(self):
        if self.get_name() and self.get_region():
            self.accept()
