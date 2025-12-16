"""
Base Gui View
Contains main dashboard with options to
import, process, validate, match, and export data

Also contains database management options for
surveys, stations, individuals, and downloading ML models
"""
import os
import logging

from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog, QDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage

from matchypatchy.gui.popup_survey import SurveyPopup
from matchypatchy.gui.popup_station import StationPopup
from matchypatchy.gui.popup_individual import IndividualPopup
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_import_csv import ImportCSVPopup
from matchypatchy.gui.popup_import_folder import ImportFolderPopup
from matchypatchy.gui.popup_ml import MLOptionsPopup

from matchypatchy.algo.sequence_thread import SequenceThread
from matchypatchy.algo.animl_thread import AnimlThread
from matchypatchy.algo.reid_thread import ReIDThread

from matchypatchy.database.media import export_data
from matchypatchy import config


<<<<<<< HEAD


=======
>>>>>>> da65254 (update gui docstrings)
class DisplayBase(QWidget):
    LOGO = config.resource_path("assets/graphics/logo.png")

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        padding = 120

        container = QWidget()
        container.setObjectName("mainBorderWidget")
        layout = QVBoxLayout()

        self.label = QLabel("Welcome To MatchyPatchy")
        self.label.setObjectName("Title")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(20)
        self.label.setStyleSheet("""#Title {font-size: 22px;}""")
        layout.addWidget(self.label)
        layout.addSpacing(20)

        self.logo = QLabel("Logo", alignment=Qt.AlignmentFlag.AlignCenter)
        self.logo.setFixedSize(600, 400)
        self.logo.setObjectName("borderWidget")
        logo_img = QImage(self.LOGO)
        self.logo.setPixmap(QPixmap.fromImage(logo_img))
        layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        column_layout = QHBoxLayout()
        column_layout.addSpacing(padding)  # add padding to left side
        column_layout.addStretch()

        # MAIN PROCESS ---------------------------------------------------------
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
        button_process.clicked.connect(self.select_models)
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
        column_layout.addSpacing(40)

        # DB MANAGEMENT --------------------------------------------------------
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
        survey_label.setStyleSheet("font-size: 16px;")
        survey_layout.addWidget(survey_label, 0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        survey_layout.addWidget(self.survey_select, 1)
        button_survey_new = QPushButton("Manage Surveys")
        button_survey_new.clicked.connect(self.manage_survey)
        survey_layout.addWidget(button_survey_new, 1)
        db_layer.addLayout(survey_layout)

        button_station_manage = QPushButton("Manage Stations")
        button_media_manage = QPushButton("Manage Media")
        button_individual_manage = QPushButton("Manage Individuals")
        button_download_models = QPushButton("Download ML Models")

        button_station_manage.clicked.connect(self.manage_station)
        button_media_manage.clicked.connect(self.validate)
        button_individual_manage.clicked.connect(self.manage_individual)
        button_download_models.clicked.connect(self.parent.download_ml)

        db_layer.addWidget(button_station_manage)
        db_layer.addWidget(button_media_manage)
        db_layer.addWidget(button_individual_manage)
        db_layer.addWidget(button_download_models)

        border_db.setLayout(db_layer)
        column_layout.addWidget(border_db, 1)
        column_layout.addSpacing(padding)  # add spacing to right side
        column_layout.addStretch()
        layout.addLayout(column_layout)
        layout.addSpacing(50)  # add spacing to bottom
        layout.addStretch()

        self.setStyleSheet("QPushButton, QComboBox { height: 40px; font-size: 16px;}"
                           "#QLabel_Base { font-size: 16px; }")
        container.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(container)
        self.setLayout(main_layout)

        self.update_survey()

    # ==========================================================================
    # Database Management Functions
    # ==========================================================================
    def update_survey(self):
        """Update survey dropdown list"""
        self.survey_select.clear()
        survey_names = self.mpDB.select('survey', columns='id, name')
        self.survey_list = dict(survey_names)
        self.survey_list_ordered = list(survey_names)
        if self.survey_list_ordered:
            self.survey_select.addItems([el[1] for el in survey_names])

    def manage_survey(self):
        """Launch Survey Management Popup"""
        dialog = SurveyPopup(self)
        if dialog.exec():
            self.update_survey()
            del dialog

    def select_survey(self):
        """Set active survey based on dropdown selection"""
        try:
            self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]
            return True
        except IndexError:
            self.active_survey = (0, None)
            return False

    def manage_station(self):
        """Launch Station Management Popup"""
        self.select_survey()
        dialog = StationPopup(self, self.active_survey)
        if dialog.exec():
            del dialog

    def manage_individual(self):
        """Launch Individual Management Popup"""
        dialog = IndividualPopup(self)
        if dialog.exec():
            del dialog

    def set_filtered_view(self, filters):
        """Set media view with filters applied, called from IndividualPopup"""
        self.parent._set_media_view(filters=filters)

    # ==========================================================================
    # MAIN PROCESS
    # ==========================================================================
    # STEP 1: Import from CSV
    def import_csv(self):
        """Add media from a CSV manifest"""
        survey_selected = self.select_survey()
        if not survey_selected:
            dialog = AlertPopup(self, "Please select a survey before importing.")
            if dialog.exec():
                del dialog
            return
        else:
            manifest = QFileDialog.getOpenFileName(self, "Open File",
                                                   os.path.expanduser('~'),
                                                   ("CSV Files (*.csv)"))[0]
            if manifest:
                logging.info(f"Importing from manifest: {manifest}")
                dialog = ImportCSVPopup(self, manifest)
                if dialog.exec():
                    del dialog

    # STEP 1: Import from FOLDER
    def import_folder(self):
        """Add media from a folder"""
        survey_selected = self.select_survey()
        if not survey_selected:
            dialog = AlertPopup(self, "Please select a survey before importing.")
            if dialog.exec():
                del dialog
            return
        else:
            directory = QFileDialog.getExistingDirectory(self, "Open File",
                                                         os.path.expanduser('~'),
                                                         QFileDialog.Option.ShowDirsOnly)
            if directory:
                dialog = ImportFolderPopup(self, directory)
                logging.info(f"Importing from directory: {directory}")
                if dialog.exec() == QDialog.DialogCode.Rejected:
                    self.import_folder()
                del dialog

    # STEP 2: Process Button
    def select_models(self):
        """
        Processes Sequence, MD, Animl, Viewpoint, Miew
        For any image/roi that doesn't have values for those already
        """
        ml_options_dialog = MLOptionsPopup(self)
        result = ml_options_dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            mloptions = ml_options_dialog.return_selections()
            del ml_options_dialog
            self.process_images(mloptions)

        # processing rejected
        else:
            del ml_options_dialog

    def process_images(self, mloptions):
        """Process images using selected machine learning options"""
        if self.mpDB.count("media") > 0:
            config.add(mloptions)
            dialog = AlertPopup(self, "Processing Images...",
                                title="Processing Images",
                                progressbar=True, cancel_only=True)
            dialog.show()

            # 1. SEQUENCE
            dialog.set_max(0)
            self.sequence_thread = SequenceThread(self.mpDB, mloptions['sequence_checked'])
            self.sequence_thread.prompt_update.connect(dialog.update_prompt)
            self.sequence_thread.start()
            # 2. ANIML (BBOX)
            dialog.set_max(100)
            dialog.set_counter(0)
            self.animl_thread = AnimlThread(self.mpDB, mloptions['DETECTOR_KEY'])
            self.animl_thread.prompt_update.connect(dialog.update_prompt)
            self.animl_thread.progress_update.connect(dialog.set_value)
            # 3. REID AND VIEWPOINT
            dialog.set_max(100)
            dialog.set_counter(0)
            self.miew_thread = ReIDThread(self.mpDB, mloptions['REID_KEY'],
                                          mloptions['VIEWPOINT_KEY'])
            self.miew_thread.prompt_update.connect(dialog.update_prompt)
            self.miew_thread.progress_update.connect(dialog.set_value)
            # chain threads
            self.animl_thread.finished.connect(self.miew_thread.start)
            self.animl_thread.finished.connect(dialog.reset_counter)
            self.miew_thread.done.connect(dialog.accept)
            self.animl_thread.start()
            # allow cancellation
            dialog.rejected.connect(self.sequence_thread.requestInterruption)
            dialog.rejected.connect(self.animl_thread.requestInterruption)
            dialog.rejected.connect(self.miew_thread.requestInterruption)
        else:
            dialog = AlertPopup(self, "No images to process.")
            dialog.show()

        if dialog.exec():
            del dialog

    # STEP 3: Validate/Manage Media Button
    def validate(self):
        """Open media view to validate/manage media"""
        self.parent._set_media_view()

    # STEP 4: Match Button
    def match(self):
        """Open compare view to match ROIs"""
        self.parent._set_compare_view()

    # STEP 5: Export Button
    def export(self):
        """Export database to CSV"""
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

    # ==========================================================================
    # OTHER OPTIONS
    # ==========================================================================
    def clear_data(self):
        """
        Clear all media and ROIs from the database
        USED FOR DEBUGGING PURPOSES ONLY
        """
        dialog = AlertPopup(self, "This will delete all media and ROIs. Are you sure you want continue?")
        if dialog.exec():
            self.mpDB.info()
            logging.warning("DELETING DATA")
            self.mpDB.clear("media")
            self.mpDB.clear("media_thumbnails")
            self.mpDB.clear("roi")
            self.mpDB.clear("roi_thumbnails")
            self.mpDB.clear("sequence")
            self.mpDB.clear("individual")
            self.mpDB.clear_emb()
        del dialog
