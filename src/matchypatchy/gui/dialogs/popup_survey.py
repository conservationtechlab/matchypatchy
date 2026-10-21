'''
Popup for adding/editing/deleting surveys
'''

from datetime import datetime
import zoneinfo
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                             QListWidget, QLineEdit, QLabel, QDialogButtonBox)
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIntValidator

from matchypatchy.database.location import TZ_CONVERT_DICT
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.database.media import media_count
from matchypatchy.database.mpdb import sql_text
from matchypatchy.project import UsesProject


class SurveyPopup(UsesProject, QDialog):
    """Popup dialog for managing surveys (add/edit/delete)"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Manage surveys")
        self.project = parent.project

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
        """Set edit/delete buttons enabled if survey selected"""
        # currentRow() returns -1 if nothing selected
        flag = bool(self.list.currentRow() + 1)
        self.button_edit.setEnabled(flag)
        self.button_del.setEnabled(flag)

    def update(self):
        """Update survey list from database"""
        self.list.clear()
        self.survey_list_ordered = self.mpDB.select("survey", columns="id, name")
        self.survey_list = dict(self.survey_list_ordered)
        if self.survey_list_ordered:
            self.list.addItems([el[1] for el in self.survey_list_ordered])
        self.set_editdel()

    def _warn(self, prompt):
        """Show a single alert"""
        dialog = AlertPopup(self, prompt)
        dialog.exec()
        del dialog

    @staticmethod
    def _year(text):
        """Year field text to int, None when empty"""
        return int(text) if text else None

    def _region_id(self, name, timezone):
        """Id of the region with this name, adding it if new; None if it couldn't be added"""
        rows = self.mpDB.select("region", columns="id, timezone", row_cond=f"name={sql_text(name)}")
        if rows:
            region_id, stored = rows[0]
            self._set_region_timezone(region_id, name, stored, str(timezone))
            return region_id
        return self.mpDB.add_region(name, str(timezone))

    def _set_region_timezone(self, region_id, name, stored, timezone):
        """Update an existing region's timezone, asking first if it already has a different one"""
        if stored and TZ_CONVERT_DICT.get(stored, stored) == timezone:
            return
        if stored:
            # regions are shared between surveys, changing one changes them all
            dialog = AlertPopup(self, f"Region '{name}' has timezone {stored}.\n"
                                      f"Change it to {timezone} for every survey in this region?",
                                title="Change timezone")
            confirmed = dialog.exec()
            del dialog
            if not confirmed:
                return
        if not self.mpDB.edit_row("region", region_id, {"timezone": timezone}):
            self._warn(f"Could not change the timezone of region '{name}', see the log for details.")

    def add(self):
        """Add a new survey"""
        dialog = SurveyFillPopup(self)
        if dialog.exec():
            name = dialog.get_name()
            region_id = self._region_id(dialog.get_region(), dialog.get_timezone())
            if region_id is None:
                self._warn(f"Could not add region '{dialog.get_region()}', see the log for details.")
            else:
                survey_id = self.mpDB.add_survey(name, region_id,
                                                 self._year(dialog.get_year_start()),
                                                 self._year(dialog.get_year_end()))
                if survey_id is None:
                    self._warn(f"Could not add survey '{name}', a survey with that name may already exist.")
        del dialog
        # refresh the survey list after adding a new survey
        self.update()

    def edit(self):
        """Edit selected survey"""
        selected_survey = self.list.currentRow()
        survey_id = self.survey_list_ordered[selected_survey][0]
        # read the region separately, the survey may have none (region_id NULL)
        name, region_id, year_start, year_end = self.mpDB.select(
            'survey', columns='name, region_id, year_start, year_end', row_cond=f'id={survey_id}')[0]
        region = self.mpDB.select('region', columns='name, timezone',
                                  row_cond=f'id={region_id}') if region_id is not None else []
        region_name, timezone = region[0] if region else ('', None)
        # regions without a stored timezone (e.g. from CSV import) show local time
        tz_kwargs = {'timezone': timezone} if timezone else {}

        dialog = SurveyFillPopup(self, name=name, region_name=region_name, **tz_kwargs,
                                 year_start='' if year_start is None else year_start,
                                 year_end='' if year_end is None else year_end)

        if dialog.exec():
            region_id = self._region_id(dialog.get_region(), dialog.get_timezone())
            if region_id is None:
                self._warn(f"Could not add region '{dialog.get_region()}', see the log for details.")
            else:
                replace_dict = {"name": dialog.get_name(),
                                "region_id": region_id,
                                "year_start": self._year(dialog.get_year_start()),
                                "year_end": self._year(dialog.get_year_end())}
                if not self.mpDB.edit_row("survey", survey_id, replace_dict, allow_none=True):
                    self._warn(f"Could not rename the survey to '{dialog.get_name()}', "
                               "a survey with that name may already exist.")
        del dialog
        # refresh the survey list after editing a survey
        self.update()

    def delete(self):
        """Delete selected survey"""
        selected_survey = self.list.currentRow()
        survey_id, selected = self.survey_list_ordered[selected_survey]
        _, n = media_count(self.mpDB, survey_id)
        dialog = AlertPopup(self, f'Are you sure you want to delete {selected}? This will remove {n} images.')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # delete survey, should cascade to stations and media
            self.mpDB.delete("survey", f'id={survey_id}')

        del dialog
        # refresh the survey list after deleting a survey
        self.update()


class SurveyFillPopup(QDialog):
    """Popup to fill in new survey details"""

    def __init__(self, parent,
                 name: str = "",
                 region_name: str = "",
                 timezone: zoneinfo.ZoneInfo = datetime.now().astimezone().tzinfo,
                 year_start: str = "",
                 year_end: str = ""):
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
        # timezone
        layout.addWidget(QLabel('Timezone'))
        self.timezone = QComboBox()
        self.timezone.setFixedHeight(20)
        self.timezone.addItems(sorted(zoneinfo.available_timezones()))
        self.timezone.setEditable(True)

        # convert common abbreviations to IANA names if needed
        iana_name = TZ_CONVERT_DICT.get(str(timezone), str(timezone))
        if iana_name in zoneinfo.available_timezones():
            self.timezone.setCurrentIndex(self.timezone.findText(iana_name))
        layout.addWidget(self.timezone)

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
        self.name.returnPressed.connect(self.region.setFocus)
        self.region.returnPressed.connect(self.year_start.setFocus)
        self.year_start.returnPressed.connect(self.year_end.setFocus)
        self.year_end.returnPressed.connect(self.accept_verify)
        self.name.setFocus()
        self.check_input()

        self.setLayout(layout)

    def check_input(self):
        """Enable OK button only if required fields are filled"""
        self.okButton.setEnabled(bool(self.get_name() and self.get_region()))

    def get_name(self):
        """Get the name value"""
        return self.name.text()

    def get_region(self):
        """Get the region value"""
        return self.region.text()

    def get_timezone(self):
        """Get the timezone value"""
        return self.timezone.currentText()

    def get_year_start(self):
        """Get the start year value"""
        return self.year_start.text()

    def get_year_end(self):
        """Get the end year value"""
        return self.year_end.text()

    def accept_verify(self):
        """Verify the input fields and accept the dialog if all required fields have values"""
        if self.get_name() and self.get_region():
            self.accept()
