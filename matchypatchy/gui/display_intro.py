import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                             QMenuBar, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel,QSizePolicy)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QPixmap

from .popup_survey import SurveyPopup
from .popup_site import SitePopup

class MainWindow(QMainWindow):
    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        self.setWindowTitle("MatchyPatchy")
        self.setFixedSize(QSize(1200, 800))
        # Set the central widget of the Window.
        main_widget = QWidget(self)
        main_widget.setFocus()
        layout = QVBoxLayout()

        self.label = QLabel("Welcome to MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label,0)

        #image screen
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.image_label,1)

        self.image = QImage("C:/Users/Kyra/matchypatchy/IMAG0104.JPG")
        pixmap = QPixmap(self.image)
        self.image_label.setPixmap(pixmap)

        # list surveys
        survey_layout = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_layout.addWidget(survey_label,0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey_select,2)

        button_survey_new =  QPushButton("New Survey")
        button_survey_new.clicked.connect(self.new_survey)
        survey_layout.addWidget(button_survey_new,1)

        # Sites
        self.button_site_manage =  QPushButton("Manage Sites")
        self.button_site_manage.clicked.connect(self.new_site)
        survey_layout.addWidget(self.button_site_manage,1)
        self.button_manage_site_flag = False
        self.button_site_manage.setEnabled(self.button_manage_site_flag)

        self.update_survey()
        layout.addLayout(survey_layout)

        # Bottom Layer
        bottom_layer = QHBoxLayout()
        # Create three buttons
        button_validate = QPushButton("Validate DB")
        button_load = QPushButton("Load Data")
        button_match = QPushButton("Match")

        button_validate.clicked.connect(self.validate_db)
        button_load.clicked.connect(self.upload_media)
        button_match.clicked.connect(self.match)

        # Add buttons to the layout
        bottom_layer.addWidget(button_validate)
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        layout.addLayout(bottom_layer)

        # Set the layout for the window
        main_widget.setLayout(layout)
        self._createMenuBar()
        self.setCentralWidget(main_widget)
        
    def validate_db(self):
        tables = self.mpDB.validate()
        self.label.setText(str(tables))

    def _createMenuBar(self):
        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)
        # FILE
        file = menuBar.addMenu("File")
        Edit = menuBar.addMenu("Edit")
        view = menuBar.addMenu("View")
        Help = menuBar.addMenu("Help")

        file.addAction("New")

    def new_survey(self):
        dialog = SurveyPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_survey(dialog.get_name(),dialog.get_region(),
                                           dialog.get_year_start(),dialog.get_year_start())
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

    def upload_media(self):
        '''
        Add media from CSV (completed from animl)
        '''
        return True
               # fileName = QFileDialog.getOpenFileName(self,
       # tr("Open Image"), "/home/jana", tr("Image Files (*.png *.jpg *.bmp)"))

    def match(self):
        return True
        


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