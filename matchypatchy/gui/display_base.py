"""
Base Gui View
"""
import sys
import os
from PyQt6.QtWidgets import (QApplication, QPushButton, QWidget, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import Qt

from .popup_survey import SurveyPopup
from .popup_site import SitePopup
from .popup_alert import AlertPopup
from .popup_species import SpeciesPopup
from ..database.media import fetch_sites, import_csv


class DisplayBase(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        layout = QVBoxLayout(self)

        self.label = QLabel("Welcome to MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label)

        # Surveys
        survey_layout = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_layout.addWidget(survey_label, 0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey_select, 2)

        button_survey_new = QPushButton("New Survey")
        button_survey_new.clicked.connect(self.new_survey)
        survey_layout.addWidget(button_survey_new, 1)

        # Sites
        self.button_site_manage = QPushButton("Manage Sites")
        self.button_site_manage.clicked.connect(self.new_site)
        survey_layout.addWidget(self.button_site_manage, 1)
        self.button_manage_site_flag = False
        self.button_site_manage.setEnabled(self.button_manage_site_flag)

        self.button_species_manage = QPushButton("Manage Species")
        self.button_species_manage.clicked.connect(self.manage_species)
        survey_layout.addWidget(self.button_species_manage, 1)

        self.update_survey()
        layout.addLayout(survey_layout)

        # Bottom Layer
        bottom_layer = QHBoxLayout()
        # Create three buttons
        button_validate = QPushButton("Validate Images")
        button_load = QPushButton("Load Data")
        button_match = QPushButton("Match")

        button_validate.clicked.connect(self.validate)
        button_load.clicked.connect(self.upload_media)
        button_match.clicked.connect(self.match)

        # Add buttons to the layout
        bottom_layer.addWidget(button_validate)
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        layout.addLayout(bottom_layer) 


    def new_survey(self):
        dialog = SurveyPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_survey(dialog.get_name(), dialog.get_region(),
                                           dialog.get_year_start(), dialog.get_year_start())
            if confirm:
                self.update_survey()
        del dialog

    def update_survey(self):
        self.survey_select.clear() 
        survey_names = self.mpDB.fetch_columns(table='survey',columns='name')
        self.survey_list = dict(survey_names)
        self.survey_list_ordered = list(survey_names)
        if self.survey_list_ordered:
            self.survey_select.addItems([el[1] for el in survey_names])
        self.button_manage_site_flag = self.select_survey()
        self.button_site_manage.setEnabled(self.button_manage_site_flag)     

    def select_survey(self):
        try:
            self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]
            return True
        except IndexError:
            return False

    def new_site(self):
        self.select_survey()
        # create new from scratch, be able to import list from another survey
        dialog = SitePopup(self)
        if dialog.exec():
            del dialog

    def manage_species(self):
        dialog = SpeciesPopup(self)
        if dialog.exec():
            del dialog

    # Validate Button
    def validate(self):
        self.parent._set_media_view()
        # return True

    # Upload Button
    def upload_media(self):
        '''
        Add media from CSV
        '''
        if self.select_survey():
            manifest = QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'),("CSV Files (*.csv)"))[0]
            print(manifest)
            valid_sites = fetch_sites(self.mpDB, self.active_survey[0])
            import_csv(self.mpDB, manifest, valid_sites)
        else:
            dialog = AlertPopup(self, "Please create a new survey before uploading.")
            if dialog.exec():
                del dialog


    # Match Button
    def match(self):
        # run miewID 
        # store embeddings in database
        # 
        print('Test')

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")
        


def main_display(mpDB):
    """
    Launch GUI

    Args:
        mpDB: matchypatchy database object
    """
    app = QApplication(sys.argv)

    window = MainWindow(mpDB)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main_display()