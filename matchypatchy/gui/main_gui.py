"""
MAIN GUI

Functions for MenuBar

Display Pages:
    0. DisplayBase
    1. DisplayMedia
    2. DisplayCompare
"""
import sys
import logging
from typing import Optional

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QFileDialog,
                             QMenuBar, QStackedLayout, QMenu)
from PyQt6.QtGui import QAction, QGuiApplication

from matchypatchy.gui.display_base import DisplayBase
from matchypatchy.gui.display_media import DisplayMedia
from matchypatchy.gui.display_compare import DisplayCompare
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_config import ConfigPopup
from matchypatchy.gui.popup_ml import MLDownloadPopup
from matchypatchy.gui.popup_readme import AboutPopup, READMEPopup, LicensePopup
from matchypatchy.gui.popup_survey import SurveyPopup
from matchypatchy.gui.popup_station import StationPopup

from matchypatchy.database.media import export_data

class MainWindow(QMainWindow):
    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        self.setWindowTitle("MatchyPatchy")
        screen_resolution = QGuiApplication.primaryScreen().geometry()
        #print(screen_resolution)
        self.setMinimumSize(1200, 900)
        # resize to full screen if small screen
        if screen_resolution.width() < 1600:
            self.resize(screen_resolution.width(), screen_resolution.height())

        # Create Menu Bar
        self._createMenuBar()
        # Create container
        container = QWidget(self)
        container.setFocus()

        # Create Page Views
        self.Base = DisplayBase(self)
        self.Media = DisplayMedia(self)
        self.Compare = DisplayCompare(self)
        self.pages = QStackedLayout()
        self.pages.addWidget(self.Base)
        self.pages.addWidget(self.Media)
        self.pages.addWidget(self.Compare)

        # Set the layout for the window
        container.setLayout(self.pages)
        self._set_base_view()
        self.setCentralWidget(container)

    # MENU BAR -----------------------------------------------------------------
    def _createMenuBar(self):
        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)
        # FILE
        file = menuBar.addMenu("File")
        edit = menuBar.addMenu("Edit")
        #view = menuBar.addMenu("View")
        help = menuBar.addMenu("Help")

        file.addAction("New")

        # FILE IMPORT
        file_import = QMenu("Import", self)
        file.addMenu(file_import)

        #file_import_station = QAction("Stations", self)
        #file_import_station.triggered.connect(lambda: self.import_popup('station'))
        #file_import.addAction(file_import_station)

        #file_import_media = QAction("Media", self)
        #file_import_media.triggered.connect(lambda: self.import_popup('media'))
        #file_import.addAction(file_import_media)

        file_export = QAction("Export", self)
        file_export.triggered.connect(self.export)
        file.addAction(file_export)

        file_download_model = QAction("Download Models", self)
        file_download_model.triggered.connect(self.download_ml)
        file.addAction(file_download_model)

        # EDIT
        edit_survey = QAction("Surveys", self)
        edit_survey.triggered.connect(self.manage_survey)
        edit_station = QAction("Stations", self)
        edit_station.triggered.connect(self.manage_station)
        edit_media = QAction("Media", self)
        edit_media.triggered.connect(self.manage_media)
        edit_configuration = QAction("Configuration", self)
        edit_configuration.triggered.connect(self.edit_config)

        edit.addAction(edit_survey)
        edit.addAction(edit_station)
        edit.addAction(edit_media)
        edit.addSeparator()
        edit.addAction(edit_configuration)

        # VIEW

        # HELP
        help_about = QAction("About", self)
        help_about.triggered.connect(self.about)
        help_readme = QAction("View README", self)
        help_readme.triggered.connect(self.help)
        help_license = QAction("View License", self)
        help_license.triggered.connect(self.license)

        help.addAction(help_about)
        help.addAction(help_readme)
        help.addAction(help_license)

    # PAGE VIEWS ---------------------------------------------------------------
    def _set_base_view(self):
        self.pages.setCurrentIndex(0)
        self.Base.setFocus()

    def _set_media_view(self, filters: Optional[dict]=None):
        self.pages.setCurrentIndex(1)
        self.Media.setFocus()
        self.Media.refresh_filters(filters)
        self.Media.load_table()
        self.Media.update_count_label()

    def _set_compare_view(self):
        self.pages.setCurrentIndex(2)
        self.Compare.setFocus()
        self.Compare.refresh_filters()
        self.Compare.calculate_neighbors()
 
    # FILE =====================================================================
    def new(self):
        pass

    def import_popup(self, table):
        """
        Launch file browser
        """
        pass

    def export(self):
        data = export_data(self.mpDB)
        if data is not None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
            if file_path:
              # add csv if user didnt enter
                if not file_path.endswith(".csv"):
                    file_path += ".csv"

                with open(file_path, 'w') as file:
                    data.to_csv(file)
                logging.info(f"Data exported to: {file_path}")
        else:
            dialog = AlertPopup(self, prompt="No data to export.")
            if dialog.exec():
                del dialog

    def download_ml(self):
        dialog = MLDownloadPopup(self)
        if dialog.exec():
            del dialog


    # EDIT =====================================================================
    def edit_config(self):
        dialog = ConfigPopup(self)
        if dialog.exec():
            del dialog
        self.Base.update_survey()

    def manage_survey(self):
        dialog = SurveyPopup(self)
        if dialog.exec():
            self.Base.update_survey()
            del dialog

    def manage_station(self):
        self.Base.select_survey()
        dialog = StationPopup(self, active_survey=self.Base.active_survey)
        if dialog.exec():
            del dialog

    def manage_media(self):
        self._set_media_view()


    # VIEW =====================================================================
    
        
    # HELP =====================================================================
    def about(self):
        dialog = AboutPopup(self)
        if dialog.exec():
            del dialog

    def help(self):
        dialog = READMEPopup(self)
        if dialog.exec():
            del dialog

    def license(self):
        dialog = LicensePopup(self)
        if dialog.exec():
            del dialog


# ==============================================================================
# MAIN FUNCTION 
# ==============================================================================
def main_display(mpDB, warning=None):
    """
    Launch GUI

    Args:
        mpDB: matchypatchy database object
    """
    app = QApplication(sys.argv)
    window = MainWindow(mpDB)
    window.show()
    
    if warning:
        dialog = AlertPopup(window, prompt=warning)
        if dialog.exec():
            del dialog

    sys.exit(app.exec())


if __name__ == "__main__":
    main_display()
