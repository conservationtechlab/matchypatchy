import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QFileDialog,
                             QMenuBar, QStackedLayout, QMenu)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QSize, QObject, QEvent

from .display_base import DisplayBase
from .display_media import DisplayMedia
from .display_compare import DisplayCompare
from .popup_table import TableEditorPopup
from .popup_dropdown import DropdownPopup

from ..database import site
from ..database import species
from ..database.import_manifest import import_manifest


class MainWindow(QMainWindow):
    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        self.setWindowTitle("MatchyPatchy")
        self.setFixedSize(QSize(1200, 800))
        self._createMenuBar()
        # Create container
        container = QWidget(self)
        container.setFocus()

        # Create Page Views
        self.Intro = DisplayBase(self)
        self.Media = DisplayMedia(self)
        self.Compare = DisplayCompare(self)
        self.pages = QStackedLayout()
        self.pages.addWidget(self.Intro)
        self.pages.addWidget(self.Media)
        self.pages.addWidget(self.Compare)

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
        edit.addAction(edit_preferences)

        edit_survey = QAction("Surveys", self)
        edit_survey.triggered.connect(lambda: self.edit_popup('survey'))
        edit.addAction(edit_survey)

        edit_site = QAction("Sites", self)
        edit_site.triggered.connect(lambda: self.edit_popup('site'))
        edit.addAction(edit_site)

        edit_species = QAction("Species", self)
        edit_species.triggered.connect(lambda: self.edit_popup('species'))
        edit.addAction(edit_species)

        edit_media = QAction("Media", self)
        edit_media.triggered.connect(lambda: self.edit_popup('media'))
        edit.addAction(edit_media)


    def _set_base_view(self):
        self.pages.setCurrentIndex(0)
        self.Intro.setFocus()

    def _set_media_view(self):
        self.pages.setCurrentIndex(1)
        self.Media.setFocus()

    def _set_compare_view(self):
        self.pages.setCurrentIndex(2)
        self.Compare.setFocus()

    def edit_popup(self, table):
        dialog = TableEditorPopup(self, table)
        if dialog.exec():
            del dialog

    def import_popup(self, table):
        """
        Launch file browser
        """
        # SPECIES
        if table == "species":
            file_path = QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'),("CSV Files (*.csv)"))[0]
            site.import_csv(self.mpDB, file_path)

        else:
            # select survey first
            dialog = DropdownPopup(self, 'survey', 'name')
            if dialog.exec():
                survey_id = dialog.get_selection()[0]
                print(survey_id)
            del dialog
            file_path = QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'),("CSV Files (*.csv)"))[0]

            # SITE
            if table == "site":
                site.import_csv(self.mpDB, file_path, survey_id=survey_id)

            # MEDIA
            elif table == "media":
                valid_sites = site.fetch_sites(self.mpDB, survey_id)
                import_manifest(self.mpDB, file_path, valid_sites)


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
