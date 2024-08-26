import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                             QMenuBar, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel)
from PyQt6.QtCore import QSize, Qt

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
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label)

        # list surveys
        survey_layout = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_layout.addWidget(survey_label,0)
        self.survey_select = QComboBox()
        self.update_survey()
        self.select_survey()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey_select,2)

        button_survey_new =  QPushButton("New Survey")
        button_survey_new.clicked.connect(self.new_survey)
        survey_layout.addWidget(button_survey_new,1)

        # Sites
        button_site_manage =  QPushButton("Manage Sites")
        button_site_manage.clicked.connect(self.new_site)
        survey_layout.addWidget(button_site_manage,1)

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
        self.survey_names_invert = dict((v,k) for k,v in survey_names.items()) # swap id,name
        self.survey_select.addItems(self.survey_names_invert.keys())        

    def select_survey(self):
        self.active_survey = [self.survey_names_invert[self.survey_select.currentText()],
                              self.survey_select.currentText()]
        print(self.active_survey)

    def new_site(self):
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
        


def main(mpDB):
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
    main()