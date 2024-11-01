"""
Base Gui View

Note:
    Because Displays are never deleted, all dialogs must be explicitly deleted

"""
import os

from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog, QDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_survey import SurveyFillPopup
from matchypatchy.gui.popup_site import SitePopup
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_species import SpeciesPopup
from matchypatchy.gui.popup_import_csv import ImportCSVPopup
from matchypatchy.gui.popup_import_folder import ImportFolderPopup

from matchypatchy.ml.sequence_thread import SequenceThread
from matchypatchy.ml.animl_thread import AnimlThread
from matchypatchy.ml.miew_thread import MiewThread


# TODO: add download models button/popup

class DisplayBase(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
        layout = QVBoxLayout()

        self.label = QLabel("Welcome To MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(20)
        layout.addWidget(self.label)
        layout.addSpacing(300)

        column_layout = QHBoxLayout()
        column_layout.addSpacing(100) # add spacing to left side

        # DB MANAGEMENT
        db_layer = QVBoxLayout()
        db_layer.addWidget(QLabel("Database Management"),
                           alignment=Qt.AlignmentFlag.AlignCenter)

        #Survey
        survey_layout = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_layout.addWidget(survey_label,0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey_select,1)
        button_survey_new = QPushButton("+")
        button_survey_new.clicked.connect(self.new_survey)
        survey_layout.addWidget(button_survey_new,0)
        db_layer.addLayout(survey_layout,0)
        
        # Sites
        self.button_site_manage = QPushButton("Manage Sites")
        self.button_site_manage.clicked.connect(self.new_site)
        db_layer.addWidget(self.button_site_manage)
        self.button_manage_site_flag = False
        self.button_site_manage.setEnabled(self.button_manage_site_flag)

        self.button_species_manage = QPushButton("Manage Species")
        self.button_species_manage.clicked.connect(self.manage_species)
        db_layer.addWidget(self.button_species_manage)

        self.button_media_manage = QPushButton("Manage Media")
        self.button_media_manage.clicked.connect(self.manage_media)
        db_layer.addWidget(self.button_media_manage)

        db_layer.addStretch()
        column_layout.addLayout(db_layer,1)
        column_layout.addSpacing(20)

        # IMPORT
        import_layer = QVBoxLayout()
        import_layer.addWidget(QLabel("Import and Process Data"),
                               alignment=Qt.AlignmentFlag.AlignCenter)

        
        button_load_csv = QPushButton("1. Import from CSV")
        button_load_folder = QPushButton("1. Import from Folder")
        button_process = QPushButton("2. Process")
        button_validate = QPushButton("3. Validate")
        button_match = QPushButton("4. Match")
        
        button_load_csv.clicked.connect(self.import_csv)
        button_load_folder.clicked.connect(self.import_folder)
        button_process.clicked.connect(self.process_images)
        button_validate.clicked.connect(self.validate)
        button_match.clicked.connect(self.match)

        # Add buttons to the layout
        load_layout = QHBoxLayout()
        load_layout.addWidget(button_load_csv)
        load_layout.addWidget(button_load_folder)
        import_layer.addLayout(load_layout)
        import_layer.addWidget(button_process)
        import_layer.addWidget(button_validate)
        import_layer.addWidget(button_match)

        import_layer.addStretch()
        column_layout.addLayout(import_layer,1) 
        column_layout.addSpacing(20)
        
        # OTHER
        other_layer = QVBoxLayout()
        other_layer.addWidget(QLabel("Other Options"),
                              alignment=Qt.AlignmentFlag.AlignCenter)

        button_download_ml = QPushButton("Download Models")
        other_layer.addWidget(button_download_ml)

        other_layer.addStretch()
        column_layout.addLayout(other_layer,1) 
        column_layout.addSpacing(100) # add spacing to right side

        layout.addLayout(column_layout)
        self.setLayout(layout)

        self.update_survey()

    def new_survey(self):
        dialog = SurveyFillPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_survey(dialog.get_name(), dialog.get_region(),
                                           dialog.get_year_start(), dialog.get_year_start())
            if confirm:
                self.update_survey()
        del dialog

    def update_survey(self):
        self.survey_select.clear() 
        survey_names = self.mpDB.select('survey', columns='id, name')
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

    # Manage Media Button
    def manage_media(self):
        self.parent._set_media_view()

    def import_csv(self):
        '''
        Add media from CSV
        '''
        # remove after finish testing
        self.mpDB.clear('media')
        self.mpDB.clear('roi')
        self.mpDB.clear('roi_emb')
        if self.select_survey():
            manifest = QFileDialog.getOpenFileName(self, "Open File", 
                                                   os.path.expanduser('~'),("CSV Files (*.csv)"))[0]
            if manifest:
                
                dialog = ImportCSVPopup(self, manifest)
                if dialog.exec():
                    del dialog                
        else:
            dialog = AlertPopup(self, "Please create a new survey before uploading.")
            if dialog.exec():
                del dialog
            
    def import_folder(self):
        """
        Add media from a folder
        """
        self.mpDB.clear('media')
        self.mpDB.clear('roi')
        self.mpDB.clear('roi_emb')
        if self.select_survey():
            directory = QFileDialog.getExistingDirectory(self, "Open File", 
                                                         os.path.expanduser('~'), 
                                                         QFileDialog.Option.ShowDirsOnly)
            if directory:
                dialog = ImportFolderPopup(self, directory)
                if dialog.exec() == QDialog.DialogCode.Rejected:
                   del dialog
                   self.import_folder()
                else:
                    del dialog 
        else:
            dialog = AlertPopup(self, "Please create a new survey before uploading.")
            if dialog.exec():
                del dialog

        
    def process_images(self):
        """
        Processes Sequence, MD, Animl, Viewpoint, Miew
        For any image/roi that doesn't have values for those already
        """
        dialog = AlertPopup(self, "Processing Images", title="Processing images...", progressbar=True)
        dialog.show()

        # 1. SEQUENCE 
        self.sequence_thread = SequenceThread(self.mpDB)
        self.sequence_thread.progress_update.connect(dialog.update)
        self.sequence_thread.start()

        # 2. ANIML (BBOX + SPECIES)
        self.animl_thread = AnimlThread(self.mpDB)
        self.animl_thread.progress_update.connect(dialog.update)
        self.animl_thread.start()

        #self.miew_thread = MiewThread(self.mpDB)
        #self.miew_thread.progress_update.connect(dialog.update)
        #self.miew_thread.start()
        
        if dialog.exec():
            del dialog
        
    # Validate Button
    def validate(self):
        self.parent._set_media_view()
        # return True

    # Validate Button
    def match(self):
        self.parent._set_compare_view()