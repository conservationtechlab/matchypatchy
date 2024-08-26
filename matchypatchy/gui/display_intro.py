import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget,
                             QMenuBar, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel)
from PyQt6.QtCore import QSize, Qt

from .forms import SurveyPopup

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
        survey_names = self.mpDB.fetch_column(table='survey',column='name')
        survey_layout = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_layout.addWidget(survey_label,0)
        self.survey_select = QComboBox()
        self.survey_select.addItems(survey_names)
        survey_layout.addWidget(self.survey_select,2)
        button_survey_new =  QPushButton("New Survey")
        button_survey_new.clicked.connect(self.new_survey)
        survey_layout.addWidget(button_survey_new,1)
        #sites
        button_site_manage =  QPushButton("Manage Sites")
        button_site_manage.clicked.connect(self.new_site)
        survey_layout.addWidget(button_site_manage,1)

        layout.addLayout(survey_layout)




        # Create a horizontal layout for the buttons
        bottom_layer = QHBoxLayout()

        # Create three buttons
        button_validate = QPushButton("Validate DB")
        button_load = QPushButton("Load Data")
        button_match = QPushButton("Match")

        button_validate.clicked.connect(self.get_tables)
        button_load.clicked.connect(self.add_media)

        # Add buttons to the layout
        bottom_layer.addWidget(button_validate)
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        layout.addLayout(bottom_layer)

        # Set the layout for the window
        main_widget.setLayout(layout)
        self._createMenuBar()
        self.setCentralWidget(main_widget)
        
    def get_tables(self):
        
        tables = self.mpDB.validate()
        print(tables)
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
                self.survey_select.addItems([dialog.get_name()])
        del dialog

    def new_site(self):
        # create new from scratch, be able to import list from another survey
        dialog = SurveyPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_survey(dialog.get_name(),dialog.get_region(),
                                 dialog.get_year_start(),dialog.get_year_start())
            if confirm:
                self.survey_select.addItems([dialog.get_name()])
        del dialog

    def add_media(self):
        '''
        Add media from CSV (completed from animl)
        '''
               # fileName = QFileDialog.getOpenFileName(self,
       # tr("Open Image"), "/home/jana", tr("Image Files (*.png *.jpg *.bmp)"))
        


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