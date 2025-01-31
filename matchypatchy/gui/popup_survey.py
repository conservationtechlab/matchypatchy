'''

'''
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIntValidator

from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.database.media import media_count


class SurveyPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage surveys")
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

        button_new = QPushButton("New")
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
        self.list.clear()
        self.survey_list_ordered = self.mpDB.select("survey", columns="id, name")
        self.survey_list = dict(self.survey_list_ordered)
        if self.survey_list_ordered:
            self.list.addItems([el[1] for el in self.survey_list_ordered])
        self.set_editdel()

    def add(self):
        dialog = SurveyFillPopup(self)
        if dialog.exec():
            region_id = self.mpDB.select("region", columns="id", row_cond=f"name='{dialog.get_region()}'", quiet=False)
            if not region_id:
                region_id = self.mpDB.add_region(dialog.get_region())
            else:
                region_id = region_id[0][0]
            self.mpDB.add_survey(dialog.get_name(), region_id,
                                 dialog.get_year_start(), dialog.get_year_start())
        del dialog
        self.surveys = self.update()

    def edit(self):
        selected_survey = self.list.currentRow()
        id = self.survey_list_ordered[selected_survey][0]
        cond = f'survey.id={id}'
        row = self.mpDB.select_join('survey', 'region', 'survey.region_id=region.id',
                                    columns='survey.id, survey.name, region.name, year_start, year_end',
                                    row_cond=cond, quiet=False)[0]
        name = row[0][1]
        region_name = '' if row[0][2] is None else row[0][2]
        year_start = '' if row[0][3] is None else row[0][3]
        year_end = '' if row[0][4] is None else row[0][4]

        dialog = SurveyFillPopup(self, name=name, region_name=region_name, year_start=year_start, year_end=year_end)

        if dialog.exec() and dialog.accepted:
            region_id = self.mpDB.select("region", columns="id", row_cond=f"name='{dialog.get_region()}'", quiet=False)
            if not region_id:
                region_id = self.mpDB.add_region(dialog.get_region())
            else:
                region_id = region_id[0][0]

            replace_dict = {"name": f"'{dialog.get_name()}'",
                            "region_id": region_id,
                            "year_start": dialog.get_year_start(),
                            "year_end": dialog.get_year_end()}
            self.mpDB.edit_row("survey", id, replace_dict, quiet=False)
        del dialog
        self.surveys = self.update()

    def delete(self):
        selected = self.list.currentItem().text()
        n = media_count(self.mpDB, self.survey_list_ordered[selected][0])
        dialog = AlertPopup(self, f'Are you sure you want to delete {selected}? This will remove {n} images.')
        if dialog.exec():
            row = self.survey_list_ordered[self.list.currentRow()][0]
            self.mpDB.delete("survey", f'id={row}')
            # self.mpDB.delete("")
        del dialog
        self.update()


class SurveyFillPopup(QDialog):
    def __init__(self, parent, name="", region_name="", year_start="", year_end=""):
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

        # region
        layout.addWidget(QLabel('Region'))
        self.region = QLineEdit()
        self.region.setText(str(region_name))
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

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
