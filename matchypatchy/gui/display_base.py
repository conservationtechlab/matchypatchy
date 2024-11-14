"""
Base Gui View

Note:
    Because Displays are never deleted, all dialogs must be explicitly deleted

"""
import os

from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog, QDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import Qt

from matchypatchy.gui.popup_survey import SurveyPopup
from matchypatchy.gui.popup_site import SitePopup
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_species import SpeciesPopup
from matchypatchy.gui.popup_import_csv import ImportCSVPopup
from matchypatchy.gui.popup_import_folder import ImportFolderPopup
from matchypatchy.gui.popup_ml import MLDownloadPopup, MLOptionsPopup

from matchypatchy.ml.sequence_thread import SequenceThread
from matchypatchy.ml.animl_thread import AnimlThread
from matchypatchy.ml.reid_thread import ReIDThread


class DisplayBase(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB

        container = QWidget()
        container.setObjectName("mainBorderWidget")
        #container.setStyleSheet("#mainBorderWidget { border: 20px solid gray; }")
        layout = QVBoxLayout()

        self.label = QLabel("Welcome To MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(20)
        layout.addWidget(self.label)
        # TODO: add logo
        layout.addSpacing(500)
        layout.addStretch()

        column_layout = QHBoxLayout()
        column_layout.addSpacing(100)  # add spacing to left side

        # DB MANAGEMENT
        border_db = QWidget()
        border_db.setObjectName("borderWidget")
        border_db.setStyleSheet("#borderWidget { border: 1px solid gray; }")
        db_layer = QVBoxLayout()
        db_label = QLabel("Database Management")
        db_label.setObjectName("QLabel_Base")
        db_layer.addWidget(db_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Survey
        survey_layout = QHBoxLayout()
        survey_label = QLabel("Survey:")
        survey_layout.addWidget(survey_label, 0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey_select, 1)
        button_survey_new = QPushButton("Manage Surveys")
        button_survey_new.clicked.connect(self.new_survey)
        survey_layout.addWidget(button_survey_new, 1)
        db_layer.addLayout(survey_layout)

        button_site_manage = QPushButton("Manage Sites")
        button_species_manage = QPushButton("Manage Species")
        button_media_manage = QPushButton("Manage Media")
        button_individual_manage = QPushButton("Manage Individuals")

        button_site_manage.clicked.connect(self.new_site)
        button_species_manage.clicked.connect(self.manage_species)
        button_media_manage.clicked.connect(self.validate)
        button_individual_manage.clicked.connect(self.manage_individual)

        db_layer.addWidget(button_site_manage)
        db_layer.addWidget(button_species_manage)
        db_layer.addWidget(button_media_manage)
        db_layer.addWidget(button_individual_manage)

        border_db.setLayout(db_layer)
        column_layout.addWidget(border_db, 1)
        column_layout.addSpacing(20)  # gap between sections

        # MAIN PROCESS
        border_import = QWidget()
        border_import.setObjectName("borderWidget")
        border_import.setStyleSheet("#borderWidget { border: 1px solid gray; }")
        import_layer = QVBoxLayout()
        import_label = QLabel("Import and Process Data")
        import_label.setObjectName("QLabel_Base")
        import_layer.addWidget(import_label, alignment=Qt.AlignmentFlag.AlignCenter)

        button_load_csv = QPushButton("1. Import from CSV")
        button_load_folder = QPushButton("1. Import from Folder")
        button_process = QPushButton("2. Process")
        button_validate = QPushButton("3. Validate")
        button_match = QPushButton("4. Match")
        button_export = QPushButton("5.Export")

        button_load_csv.clicked.connect(self.import_csv)
        button_load_folder.clicked.connect(self.import_folder)
        button_process.clicked.connect(self.process_images)
        button_validate.clicked.connect(self.validate)
        button_match.clicked.connect(self.match)
        button_export.clicked.connect(self.export)

        load_layout = QHBoxLayout()
        load_layout.addWidget(button_load_csv)
        load_layout.addWidget(button_load_folder)
        import_layer.addLayout(load_layout)
        import_layer.addWidget(button_process)
        import_layer.addWidget(button_validate)
        import_layer.addWidget(button_match)
        import_layer.addWidget(button_export)

        border_import.setLayout(import_layer)
        column_layout.addWidget(border_import, 1)
        column_layout.addSpacing(20)

        # OTHER
        border_other = QWidget()
        border_other.setObjectName("borderWidget")
        border_other.setStyleSheet("#borderWidget { border: 1px solid gray; }")
        other_layer = QVBoxLayout()
        other_label = QLabel("Other Options")
        other_label.setObjectName("QLabel_Base")
        other_layer.addWidget(other_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ML models
        button_configuration = QPushButton("Configuration")
        button_download_ml = QPushButton("Download Models")
        button_ph1 = QPushButton("Placeholder")
        button_ph2 = QPushButton("Placeholder")
        button_ph3 = QPushButton("Placeholder")

        other_layer.addWidget(button_configuration)
        other_layer.addWidget(button_download_ml)
        other_layer.addWidget(button_ph1)
        other_layer.addWidget(button_ph2)
        other_layer.addWidget(button_ph3)

        button_configuration.clicked.connect(self.edit_config)
        button_download_ml.clicked.connect(self.download_ml)

        border_other.setLayout(other_layer)
        column_layout.addWidget(border_other, 1)
        column_layout.addSpacing(100)  # add spacing to right side

        layout.addLayout(column_layout)
        layout.addSpacing(50)  # add spacing to bottom

        self.setStyleSheet("QPushButton, QComboBox { height: 40px; }"
                           "#QLabel_Base { font-size: 16px; }")
        container.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(container)
        self.setLayout(main_layout)

        self.update_survey()

    # Database Management ------------------------------------------------------
    def update_survey(self):
        self.survey_select.clear()
        survey_names = self.mpDB.select('survey', columns='id, name')
        self.survey_list = dict(survey_names)
        self.survey_list_ordered = list(survey_names)
        if self.survey_list_ordered:
            self.survey_select.addItems([el[1] for el in survey_names])

    def new_survey(self):
        dialog = SurveyPopup(self)
        if dialog.exec():
            self.update_survey()
            del dialog

    def select_survey(self):
        try:
            self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]
            return True
        except IndexError:
            self.active_survey = (0, None)
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

    def manage_individual(self):
        # TODO
        pass

    # MAIN PROCESS -------------------------------------------------------------
    # STEP 1: Import from CSV
    def import_csv(self):
        '''
        Add media from CSV
        '''
        # remove after finish testing
        self.mpDB.clear('media')
        self.mpDB.clear('roi')
        self.mpDB.clear('roi_emb')
        self.select_survey()
        manifest = QFileDialog.getOpenFileName(self, "Open File",
                                               os.path.expanduser('~'),
                                               ("CSV Files (*.csv)"))[0]
        if manifest:
            dialog = ImportCSVPopup(self, manifest)
            if dialog.exec():
                del dialog

    # STEP 1: Import from FOLDER
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
                    self.import_folder()
                del dialog
        else:
            dialog = AlertPopup(self, "Please create a new survey before uploading.")
            if dialog.exec():
                del dialog

    # STEP 2: Process Button
    def process_images(self):
        """
        Processes Sequence, MD, Animl, Viewpoint, Miew
        For any image/roi that doesn't have values for those already
        """
        dialog = AlertPopup(self, "Processing Images", title="Processing images...", progressbar=True)
        dialog.show()

        animl_options = MLOptionsPopup(self)
        result = animl_options.exec()
        if result == QDialog.DialogCode.Accepted:

            sequence_checked = animl_options.select_sequence()
            detector_key = animl_options.select_detector()
            classifier_key = animl_options.select_classifier()
            reid_key = animl_options.select_reid()
            viewpoint_key = animl_options.select_viewpoint()

            # 1. SEQUENCE
            self.sequence_thread = SequenceThread(self.mpDB, sequence_checked)
            self.sequence_thread.progress_update.connect(dialog.update)
            self.sequence_thread.start()

            # 2. ANIML (BBOX + SPECIES)
            self.animl_thread = AnimlThread(self.mpDB, detector_key, classifier_key)
            self.animl_thread.progress_update.connect(dialog.update)

            # 3. REID AND VIEWPOINT
            self.miew_thread = ReIDThread(self.mpDB, reid_key, viewpoint_key)
            self.miew_thread.progress_update.connect(dialog.update)

            # chain threads
            self.animl_thread.finished.connect(self.miew_thread.start)
            self.miew_thread.finished.connect(dialog.accept)
            self.animl_thread.start()

        # processing canceled
        else:
            del animl_options
            dialog.reject()
            del dialog

    # STEP 3: Validate/Manage Media Button
    def validate(self):
        self.parent._set_media_view()

    # STEP 4: Match Button
    def match(self):
        self.parent._set_compare_view()

    # STEP 5: Export Button
    def export(self):
        # TODO
        pass

    # OTHER OPTIONS ------------------------------------------------------------
    def edit_config(self):
        # TODO
        pass

    def download_ml(self):
        dialog = MLDownloadPopup(self)
        if dialog.exec():
            del dialog
