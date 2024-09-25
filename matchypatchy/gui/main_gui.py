import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QMenuBar, QStackedLayout)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QSize, QObject, QEvent

from .display_base import DisplayBase
from .display_media import DisplayMedia
from .display_compare import DisplayCompare
from .popup_table import TableEditorPopup


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
