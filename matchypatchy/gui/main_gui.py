import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QMenuBar, QStackedLayout)
from PyQt6.QtCore import QSize

from .display_base import DisplayBase
from .display_media import DisplayMedia
from .display_compare import DisplayCompare

class MainWindow(QMainWindow):
    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        self.setWindowTitle("MatchyPatchy")
        self.setFixedSize(QSize(1200, 800))
        self._createMenuBar()
        
        # Create Page Views
        container = QWidget(self)
        container.setFocus()
        
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
        view = menuBar.addMenu("View")
        Help = menuBar.addMenu("Help")

        file.addAction("New")
    
    def _set_base_view(self):
        self.pages.setCurrentIndex(0)
    
    def _set_media_view(self):
        self.pages.setCurrentIndex(1)
    
    def _set_compare_view(self):
        self.pages.setCurrentIndex(2)
        

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