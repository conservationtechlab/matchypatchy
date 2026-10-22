"""
MAIN GUI

Functions for MenuBar

Display Pages:
    0. DisplayBase
    1. DisplayMedia
    2. DisplayCompare
"""
import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QFileDialog,
                             QMenuBar, QStackedLayout, QMenu)
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtCore import QSettings, QTimer

from matchypatchy.gui.display_base import DisplayBase
from matchypatchy.gui.display_media import DisplayMedia
from matchypatchy.gui.display_compare import DisplayCompare
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_config import ConfigPopup
from matchypatchy.gui.dialogs.popup_ml import MLDownloadPopup
from matchypatchy.gui.dialogs.popup_readme import READMEPopup
from matchypatchy.gui.dialogs.popup_survey import SurveyPopup
from matchypatchy.gui.dialogs.popup_import_csv import ImportCSVPopup
from matchypatchy.gui.dialogs.popup_import_folder import ImportFolderPopup
from matchypatchy.gui.dialogs.popup_station import StationPopup

from matchypatchy import __version__
from matchypatchy.project import Project
from matchypatchy.database.filesystem import _is_network_path


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main GUI class for the MatchyPatchy application."""
    def __init__(self):
        super().__init__()
        # Initialize main window settings and components
        self.settings = QSettings("SDZWA", "MatchyPatchy")
        # the platform's own size, used until the user picks one in the config
        # (-1 when the system font is sized in pixels, then use a common size)
        self.system_font_size = QApplication.instance().font().pointSize()
        if self.system_font_size <= 0:
            self.system_font_size = 10
        # before the views are built, so they lay out at the saved size
        self.apply_font_size(self.font_size())
        # the open project, kept for the life of the window; views read cfg and db through it
        self.project = Project()
        # load previous home dir or start fresh, falling back to a default project
        # if the saved project or its database cannot be loaded
        self._startup_project()

        # set up main window
        self.setWindowTitle(f"MatchyPatchy v{__version__}")
        self._set_window_size()

        # Create Menu Bar
        self._createMenuBar()
        # Create container
        container = QWidget(self)
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
        # views show the previous project's data until they reload, which they do on entry
        self.project.changed.connect(self._set_base_view)

    @property
    def mpDB(self):
        """Database of the open project"""
        return self.project.db

    @property
    def cfg(self):
        """Config of the open project"""
        return self.project.cfg

    # MENU BAR -----------------------------------------------------------------
    def _createMenuBar(self):
        """Create the menu bar for the main window."""
        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)
        # FILE
        file = menuBar.addMenu("File")
        edit = menuBar.addMenu("Edit")
        # view = menuBar.addMenu("View")
        help = menuBar.addMenu("Help")

        # FILE IMPORT
        file_import = QMenu("Import", self)
        file_import.addAction("Import CSV", self.import_csv)
        file_import.addAction("Import Folder", self.import_folder)
        file.addMenu(file_import)

        file_export = QAction("Export", self)
        file_export.triggered.connect(self.export)
        file.addAction(file_export)

        file_download_model = QAction("Download ML Models", self)
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

    # FONT SIZE ----------------------------------------------------------------
    def font_size(self):
        """
        Saved default font size in pt, the system's size if never set or unreadable

        Read in __init__ and by ConfigPopup to fill its font size field. Stored in
        QSettings rather than the project config so it stays the same across projects.
        Falls back to the system size rather than a fixed one because platforms
        differ (Windows 9pt, macOS 13pt, where a point is also smaller on screen).
        """
        try:
            return int(self.settings.value("font_size", self.system_font_size))
        except (TypeError, ValueError):
            return self.system_font_size

    def apply_font_size(self, size):
        """
        Set the app's default font size without saving it

        Called in __init__ with the saved size, and by ConfigPopup to preview a size
        while it's edited and to put the old size back on Cancel. Kept separate from
        save_font_size so the preview isn't written until Save. Widgets with a size
        in their stylesheet keep it.
        """
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(size)
        app.setFont(font)

    def save_font_size(self, size):
        """
        Apply the default font size and keep it for next time, called by ConfigPopup on Save

        Saving the system's size clears the setting instead, so the app keeps following
        the system if it changes or the settings move to another platform.
        """
        if size == self.system_font_size:
            self.settings.remove("font_size")
        else:
            self.settings.setValue("font_size", size)
        self.apply_font_size(size)

    # PAGE VIEWS ---------------------------------------------------------------

    def _set_window_size(self):
        """Set the window size based on user preferences and screen resolution."""

        # get the screen resolution
        screen_resolution = QGuiApplication.primaryScreen().availableGeometry()

        # get preferred window size from settings
        preferred_width = self.settings.value("preferred_width", None)
        preferred_height = self.settings.value("preferred_height", None)

        if preferred_width is None:
            default_width = 1500
            minimum_width = 1446
            if screen_resolution.width() > minimum_width:
                preferred_width = min(int(screen_resolution.width() * 0.9), default_width)
            else:
                preferred_width = screen_resolution.width()

        if preferred_height is None:
            default_height = 900
            minimum_height = 859
            if screen_resolution.height() > minimum_height:
                preferred_height = min(int(screen_resolution.height() * 0.9), default_height)
            else:
                preferred_height = screen_resolution.height()

        preferred_width = int(preferred_width)
        preferred_height = int(preferred_height)
        self.resize(preferred_width, preferred_height)

        self.settings.setValue("preferred_width", str(preferred_width))
        self.settings.setValue("preferred_height", str(preferred_height))


    def _set_base_view(self):
        """Switch to the base view page.""" 
        self.pages.setCurrentIndex(0)
        self.Base.setFocus()

    def _set_media_view(self, filters: Optional[dict] = None):
        """Switch to the media view page and apply optional filters.""" 
        self.pages.setCurrentIndex(1)
        self.Media.setFocus()
        # wait to load
        QTimer.singleShot(100, lambda: self.Media.refresh_filters(filters))
        QTimer.singleShot(100, self.Media.load_table)

    def _set_compare_view(self):
        """Switch to the compare view page.""" 
        self.pages.setCurrentIndex(2)
        self.Compare.setFocus()
        # wait to load
        QTimer.singleShot(100, self.Compare.refresh_filters)
        self.Compare.initialize()

    def _set_manual_view(self, selected_ids=None):
        """Switch to the manual comparison view page with selected IDs.""" 
        self.pages.setCurrentIndex(2)
        self.Compare.setFocus()
        # wait to load, reset filters before comparing so stale filters are not applied
        QTimer.singleShot(100, lambda: self._load_manual_view(selected_ids))

    def _load_manual_view(self, selected_ids=None):
        """Reset compare filters, then compare the selected IDs."""
        self.Compare.refresh_filters()
        self.Compare.compare_manual(selected_ids=selected_ids)

    # FILE =====================================================================
    def import_csv(self):
        """Add media from a CSV manifest"""
        selected_survey = self.Base.select_survey()
        if not selected_survey:
            dialog = AlertPopup(self, "Please select a survey before importing.")
            dialog.exec()
            del dialog
            return
        else:
            self.active_survey = self.Base.active_survey
            manifest = QFileDialog.getOpenFileName(self, "Open File",
                                                   os.path.expanduser('~'),
                                                   ("CSV Files (*.csv)"))[0]
            if manifest:
                logger.info(f"Importing from manifest: {manifest}")
                dialog = ImportCSVPopup(self, manifest)
                dialog.exec()
                del dialog

    # STEP 1: Import from FOLDER
    def import_folder(self):
        """Add media from a folder"""
        selected_survey = self.Base.select_survey()
        if not selected_survey:
            dialog = AlertPopup(self, "Please select a survey before importing.")
            dialog.exec()
            del dialog
            return
        else:
            self.active_survey = self.Base.active_survey
            directory = QFileDialog.getExistingDirectory(self, "Open File",
                                                         os.path.expanduser('~'),
                                                         QFileDialog.Option.ShowDirsOnly)
            if directory:
                dialog = ImportFolderPopup(self, directory)
                logger.info(f"Importing from directory: {directory}")
                dialog.exec()
                # ask for another directory only if this one had no images, not on Cancel
                no_images = dialog.no_images
                del dialog
                if no_images:
                    self.import_folder()

    def export(self):
        """Export database to CSV (same export as the Home screen's)"""
        self.Base.export()

    def download_ml(self):
        dialog = MLDownloadPopup(self)
        dialog.exec()
        del dialog

    # EDIT =====================================================================

    def load_home_dir(self):
        """Last selected project path, None if none was saved"""
        return self.settings.value("home_dir", None)  # None is default

    def _startup_project(self):
        """Open the saved project, or fall back to a default project so the app can still launch"""
        saved_dir = self.load_home_dir()
        candidates = [Path.cwd() / "MatchyPatchy-Share",
                      Path.home() / "MatchyPatchy-Share"]

        failed = []
        if saved_dir:
            if Path(saved_dir).exists():
                candidates.insert(0, saved_dir)
            else:
                # eg. an unmounted drive: opening it would create an empty project there,
                # and the setting is kept so the project opens again once it's back
                logger.error(f"Saved project folder {saved_dir} not found")
                failed.append(str(saved_dir))

        for home_dir in candidates:
            if str(home_dir) in failed:
                continue
            try:
                self.project.open(home_dir)
            except Exception as e:
                logger.error(f"Could not load project at {home_dir}: {e}", exc_info=True)
                failed.append(str(home_dir))
                continue
            logger.info(f"Configuration loaded from {self.cfg.HOME_DIR}")
            logger.info(f"Database initialized at: {str(self.cfg.DB_DIR)}")
            # first launch: remember the default project
            if not saved_dir:
                self.settings.setValue("home_dir", str(home_dir))
            break
        else:
            raise RuntimeError(f"Could not load or create a project at any of: {failed}")

        if failed:
            # leave the saved home_dir setting alone so the project loads next time if it becomes available
            msg = (f"Could not load the project database at:\n{failed[0]}\n\n"
                   f"A default project was opened instead at:\n{self.cfg.HOME_DIR}\n\n"
                   f"Use Edit > Configuration to select another project. See the log for details.")
            # show after the main window is up
            QTimer.singleShot(0, lambda: AlertPopup(self, prompt=msg).exec())

    def save_home_dir(self, path):
        """Save selected path"""
        self.settings.setValue("home_dir", str(path))
        self.cfg.update_home_dir(path)

    def new_project(self, home_dir):
        """Create a new project in the specified home directory."""
        home_dir = Path(home_dir)

        is_remote, fs_info = _is_network_path(home_dir)
        if is_remote:
            msg = (
                f"The selected database location appears to be a network/SMB share "
                f"(detected: {fs_info}). \n SQLite does not reliably support network "
                f"filesystems and this can cause database corruption or lock errors.\n\n"
                f"Please choose a folder on your local hard drive first and then sync to the network location instead."
            )
            logger.error(msg)
            dialog = AlertPopup(self, prompt=msg)
            dialog.exec()
            del dialog
            return
        
        logger.info(f"Creating project folder: {str(home_dir)}.")
        try:
            self.project.open(home_dir)
        except Exception as e:
            logger.error(f"Could not create project at {home_dir}: {e}", exc_info=True)
            dialog = AlertPopup(self, prompt=f"Could not create project at {home_dir}:\n{e}")
            dialog.exec()
            del dialog
            return
        # save settings
        self.settings.setValue("home_dir", str(home_dir))

    def change_project(self, project_folder):
        """Change the current project to the specified project folder."""
        try:
            self.project.open(project_folder)
            valid = True
        except Exception as e:
            logger.error(f"Could not load project at {project_folder}: {e}", exc_info=True)
            valid = False
        # Check if the database key is valid
        if valid:
            self.settings.setValue("home_dir", str(project_folder))
            logger.info(f"Updating project folder to {str(project_folder)}.")
            return True
        # not valid
        else:
            logger.warning(f"Database at {str(project_folder)} is invalid. User prompted to select another path or delete.")
            dialog = AlertPopup(self, prompt="Database is invalid. Please select another path or delete.")
            dialog.exec()
            del dialog
            return False

    def edit_config(self):
        """Open the configuration editing popup."""
        dialog = ConfigPopup(self)
        dialog.exec()
        del dialog

    def manage_survey(self):
        """Open the survey management popup."""
        dialog = SurveyPopup(self)
        dialog.exec()
        del dialog

    def manage_station(self):
        """Open the station management popup."""
        if not self.Base.select_survey():
            dialog = AlertPopup(self, "Please select a survey before managing stations.")
            dialog.exec()
            del dialog
            return
        dialog = StationPopup(self, active_survey=self.Base.active_survey)
        dialog.exec()
        del dialog

    def manage_media(self):
        """Switch to the media management view."""
        self._set_media_view()

    # VIEW =====================================================================

    # HELP =====================================================================
    def about(self):
        """Open About Popup"""
        dialog = READMEPopup(self, doc_type="ABOUT")
        dialog.exec()
        del dialog

    def help(self):
        """Open README Popup"""
        dialog = READMEPopup(self, doc_type="README")
        dialog.exec()
        del dialog

    def license(self):
        """Open License Popup"""
        dialog = READMEPopup(self, doc_type="LICENSE")
        dialog.exec()
        del dialog

    # CLOSE EVENT ==============================================================

    def resizeEvent(self, a0):
        preferred_width = a0.size().width()
        preferred_height = a0.size().height()
        self.settings.setValue("preferred_width", str(preferred_width))
        self.settings.setValue("preferred_height", str(preferred_height))
        return super().resizeEvent(a0)


    def closeEvent(self, event):
        """Close database connection when window closes"""
        self.project.close()
        event.accept()
