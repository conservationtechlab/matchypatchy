"""
Creat or edit site
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets
from matchypatchy.gui.popup_alert import AlertPopup


class SitePopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage Sites")
        self.mpDB = parent.mpDB
        self.survey_id = parent.active_survey

        layout = QVBoxLayout()
        # SITE LIST
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

        # not enabled until site is selected
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
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag)
        self.button_del.setEnabled(flag)

    def update(self):
        self.list.clear()
        cond = f'survey_id={self.survey_id[0]}'
        self.site_list_ordered = self.mpDB.select("site", columns="id, name", row_cond=cond)
        self.site_list = dict(self.site_list_ordered)
        if self.site_list_ordered:
            self.list.addItems([el[1] for el in self.site_list_ordered])
        self.set_editdel()

    def add(self):
        dialog = SiteFillPopup(self)
        if dialog.exec():
            self.mpDB.add_site(dialog.get_name(), dialog.get_lat(),
                               dialog.get_long(), self.survey_id[0])
        del dialog
        self.sites = self.update()

    def edit(self):
        selected_site = self.list.currentRow()
        id = self.site_list_ordered[selected_site][0]
        cond = f'id={id}'
        id, name, lat, long = self.mpDB.select('site', columns='id, name, lat, long', row_cond=cond)[0]
        dialog = SiteFillPopup(self, name=name, lat=lat, long=long)
        if dialog.exec():
            replace_dict = {"name": f"'{dialog.get_name()}'", "lat": dialog.get_lat(), "long": dialog.get_long()}
            self.mpDB.edit_row("site", id, replace_dict)
        del dialog
        self.sites = self.update()

    def delete(self):
        selected = self.list.currentItem().text()
        dialog = AlertPopup(self, f'Are you sure you want to delete {selected}?')
        if dialog.exec():
            row = self.site_list_ordered[self.list.currentRow()][0]
            self.mpDB.delete("site", f'id={row}')
        del dialog
        self.update()


class SiteFillPopup(QDialog):
    def __init__(self, parent, name="", lat="", long=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Site")

        layout = QVBoxLayout()

        title = QLabel(f'Edit Site for {parent.survey_id[1]}',
                       objectName='title', alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        self.name.setText(name)
        layout.addWidget(self.name)

        # latitude
        layout.addWidget(QLabel('Latitude'))
        self.lat = QLineEdit()
        self.lat.setText(str(lat))
        layout.addWidget(self.lat)

        # longitude
        layout.addWidget(QLabel('Longitude'))
        self.long = QLineEdit()
        self.long.setText(str(long))
        layout.addWidget(self.long)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)
        self.checkInput()  # will enable ok button if in edit mode

        self.name.textChanged.connect(self.checkInput)
        self.lat.textChanged.connect(self.checkInput)
        self.long.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(lambda: self.lat.setFocus())
        self.lat.returnPressed.connect(lambda: self.long.setFocus())
        self.long.returnPressed.connect(self.accept_verify)
        self.name.setFocus()

        self.setLayout(layout)

    def checkInput(self):
        # year end not necessary
        self.okButton.setEnabled(bool(self.get_name() and self.get_lat() and self.get_long()))

    def get_name(self):
        return self.name.text()

    def get_lat(self):
        return self.lat.text()

    def get_long(self):
        return self.long.text()

    def accept_verify(self):
        if self.get_name() and self.get_lat() and self.get_long():
            self.accept()
