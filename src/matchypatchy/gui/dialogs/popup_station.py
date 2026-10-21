"""
Popups to create or edit station
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtCore import QLocale
from PyQt6 import QtCore, QtWidgets

from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.project import UsesProject


class StationPopup(UsesProject, QDialog):
    """Popup dialog for managing stations (add/edit/delete)"""
    def __init__(self, parent, active_survey):
        super().__init__(parent)
        self.setWindowTitle("Manage stations")
        self.project = parent.project
        self.survey_id = active_survey

        layout = QVBoxLayout()
        # station LIST
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
        # stations belong to a survey
        button_new.setEnabled(bool(self.survey_id[0]))
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
        # initial load
        self.update()

    def set_editdel(self):
        """Set edit/delete button enabled state"""
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag)
        self.button_del.setEnabled(flag)

    def update(self):
        """Update station list from DB"""
        self.list.clear()
        cond = f'survey_id={self.survey_id[0]}'
        self.station_list_ordered = self.mpDB.select("station", columns="id, name", row_cond=cond)
        self.station_list = dict(self.station_list_ordered)
        if self.station_list_ordered:
            self.list.addItems([el[1] for el in self.station_list_ordered])
        self.set_editdel()

    def add(self):
        """Add new station"""
        dialog = StationFillPopup(self)
        if dialog.exec():
            station_id = self.mpDB.add_station(dialog.get_name(), dialog.get_lat(),
                                               dialog.get_long(), self.survey_id[0])
            if station_id is None:
                self._warn(f"Could not add station '{dialog.get_name()}', see the log for details.")
        del dialog
        # refresh the station list after adding a new station
        self.update()

    def edit(self):
        """Edit selected station"""
        selected_station = self.list.currentRow()
        station_id = self.station_list_ordered[selected_station][0]
        cond = f'id={station_id}'
        station_id, name, lat, long = self.mpDB.select('station', columns='id, name, lat, long', row_cond=cond)[0]
        dialog = StationFillPopup(self, name=name, lat=lat, long=long)
        if dialog.exec():
            replace_dict = {"name": dialog.get_name(), "lat": dialog.get_lat(), "long": dialog.get_long()}
            if not self.mpDB.edit_row("station", station_id, replace_dict, allow_none=True):
                self._warn(f"Could not save station '{dialog.get_name()}', see the log for details.")
        del dialog
        # refresh the station list after editing a station
        self.update()

    def _warn(self, prompt):
        """Show a single alert"""
        dialog = AlertPopup(self, prompt)
        dialog.exec()
        del dialog

    def delete(self):
        """Delete selected station"""
        selected = self.list.currentItem().text()
        dialog = AlertPopup(self, f'Are you sure you want to delete {selected}?')
        if dialog.exec():
            row = self.station_list_ordered[self.list.currentRow()][0]
            self.mpDB.delete("station", f'id={row}')
        del dialog
        # refresh the station list after deleting a station
        self.update()


class StationFillPopup(QDialog):
    """
    Popup dialog for adding or editing a station.
    """
    def __init__(self, parent, name="", lat=None, long=None):
        super().__init__(parent)
        self.setWindowTitle("Edit station")
        layout = QVBoxLayout()
        title = QLabel(f'Edit station for {parent.survey_id[1]}',
                       objectName='title', alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # name
        layout.addWidget(QLabel('Name'))
        self.name = QLineEdit()
        self.name.setText(name)
        layout.addWidget(self.name)

        # latitude / longitude: optional, stations imported from folders have none
        layout.addWidget(QLabel('Latitude'))
        self.lat = QLineEdit()
        self.lat.setValidator(self._coordinate_validator(90))
        self.lat.setText('' if lat is None else str(lat))
        layout.addWidget(self.lat)

        layout.addWidget(QLabel('Longitude'))
        self.long = QLineEdit()
        self.long.setValidator(self._coordinate_validator(180))
        self.long.setText('' if long is None else str(long))
        layout.addWidget(self.long)

        # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)
        self.checkInput()  # will enable ok button if in edit mode

        self.name.textChanged.connect(self.checkInput)
        self.lat.textChanged.connect(self.checkInput)
        self.long.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(self.lat.setFocus)
        self.lat.returnPressed.connect(self.long.setFocus)
        self.long.returnPressed.connect(self.accept_verify)
        self.name.setFocus()

        self.setLayout(layout)

    @staticmethod
    def _coordinate_validator(limit):
        """Validator for a coordinate within +-limit, '.' as decimal point"""
        validator = QDoubleValidator(-limit, limit, 8)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        validator.setLocale(QLocale.c())
        return validator

    @staticmethod
    def _coordinate(text, limit):
        """Coordinate text to float, None when empty; ValueError if not a coordinate"""
        text = text.strip()
        if not text:
            return None
        value = float(text)
        if not -limit <= value <= limit:
            raise ValueError(f"{value} outside +-{limit}")
        return value

    def _valid(self):
        """Name given and coordinates empty or valid"""
        try:
            self._coordinate(self.lat.text(), 90)
            self._coordinate(self.long.text(), 180)
        except ValueError:
            return False
        return bool(self.get_name())

    def checkInput(self):
        """Enable the OK button when a name is given and coordinates are empty or valid"""
        self.okButton.setEnabled(self._valid())

    def get_name(self):
        """Get the name value"""
        return self.name.text()

    def get_lat(self):
        """Latitude as float, None when empty"""
        return self._coordinate(self.lat.text(), 90)

    def get_long(self):
        """Longitude as float, None when empty"""
        return self._coordinate(self.long.text(), 180)

    def accept_verify(self):
        """Accept the dialog if a name is given and coordinates are valid"""
        if self._valid():
            self.accept()
