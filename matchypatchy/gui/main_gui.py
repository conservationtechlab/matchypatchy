"""
MAIN GUI

Functions for MenuBar

Display Pages:
    1. DisplayBase
    2. DisplayMedia
    3. DisplayCompare
    4. DisplaySingle
"""
import sys
import os
from typing import Optional

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QFileDialog,
                             QMenuBar, QStackedLayout, QMenu)
from PyQt6.QtGui import QAction

from matchypatchy.gui.display_base import DisplayBase
from matchypatchy.gui.display_media import DisplayMedia
from matchypatchy.gui.display_compare import DisplayCompare
from matchypatchy.gui.display_single import DisplaySingle
from matchypatchy.gui.popup_dropdown import DropdownPopup

from matchypatchy.database import site
from matchypatchy.database import species


class MainWindow(QMainWindow):
    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        self.setWindowTitle("MatchyPatchy")
        self.setMinimumSize(1600, 900)
        self.resize(1600, 900)

        # Create Menu Bar
        self._createMenuBar()
        # Create container
        container = QWidget(self)
        container.setFocus()

        # Create Page Views
        self.Intro = DisplayBase(self)
        self.Media = DisplayMedia(self)
        self.Compare = DisplayCompare(self)
        self.Single = DisplaySingle(self)
        self.pages = QStackedLayout()
        self.pages.addWidget(self.Intro)
        self.pages.addWidget(self.Media)
        self.pages.addWidget(self.Compare)
        self.pages.addWidget(self.Single)

        # Set the layout for the window
        container.setLayout(self.pages)
        self._set_base_view()
        self.setCentralWidget(container)

    def _createMenuBar(self):
        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)
        # FILE
        file = menuBar.addMenu("File")
        edit = menuBar.addMenu("Edit")
        view = menuBar.addMenu("View")
        Help = menuBar.addMenu("Help")

        file.addAction("New")

        # FILE IMPORT
        file_import = QMenu("Import", self)
        file.addMenu(file_import)

        file_import_site = QAction("Sites", self)
        file_import_site.triggered.connect(lambda: self.import_popup('site'))
        file_import.addAction(file_import_site)

        file_import_species = QAction("Species", self)
        file_import_species.triggered.connect(lambda: self.import_popup('species'))
        file_import.addAction(file_import_species)

        file_import_media = QAction("Media", self)
        file_import_media.triggered.connect(lambda: self.import_popup('media'))
        file_import.addAction(file_import_media)

        # EDIT
        edit_preferences = QAction("Preferences", self)
        edit_survey = QAction("Surveys", self)
        edit_site = QAction("Sites", self)
        edit_species = QAction("Species", self)
        edit_media = QAction("Media", self)

        edit.addAction(edit_preferences)
        edit.addAction(edit_survey)
        edit.addAction(edit_site)
        edit.addAction(edit_species)
        edit.addAction(edit_media)

    def _set_base_view(self):
        self.pages.setCurrentIndex(0)
        self.Intro.setFocus()

    def _set_media_view(self, filters: Optional[dict]=None):
        self.pages.setCurrentIndex(1)
        self.Media.setFocus()
        self.Media.refresh_filters(filters)
        self.Media.connect_filters()
        self.Media.load_table()

    def _set_compare_view(self):
        self.pages.setCurrentIndex(2)
        self.Compare.setFocus()
        self.Compare.calculate_neighbors()

    def _set_single_view(self):
        self.pages.setCurrentIndex(3)
        self.Compare.setFocus()


    def import_popup(self, table):
        """
        Launch file browser
        """
        # SPECIES
        if table == "species":
            file_path = QFileDialog.getOpenFileName(self, "Open File",
                                                    os.path.expanduser('~'),
                                                    ("CSV Files (*.csv)"))[0]
            site.import_csv(self.mpDB, file_path)

        else:
            # select survey first
            dialog = DropdownPopup(self, 'survey', 'name')
            if dialog.exec():
                survey_id = dialog.get_selection()[0]
                print(survey_id)
            del dialog
            file_path = QFileDialog.getOpenFileName(self, "Open File",
                                                    os.path.expanduser('~'),
                                                    ("CSV Files (*.csv)"))[0]

            # SITE
            if table == "site":
                site.import_csv(self.mpDB, file_path, survey_id=survey_id)


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
