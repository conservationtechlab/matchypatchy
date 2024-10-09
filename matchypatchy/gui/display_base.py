"""
Base Gui View
"""
import os
import pandas as pd

from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from .popup_survey import SurveyFillPopup
from .popup_site import SitePopup
from .popup_alert import AlertPopup
from .popup_species import SpeciesPopup

from ..database.import_manifest import import_manifest
from ..database.site import fetch_sites

from ..database.roi import (fetch_roi, update_roi_embedding, 
                            update_roi_viewpoint, match)

from animl.reid import viewpoint
from animl.reid import miewid


class DisplayBase(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
        layout = QVBoxLayout()

        self.label = QLabel("Welcome to MatchyPatchy")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label)

        # Surveys
        first_layer = QHBoxLayout()
        survey_label = QLabel("Survey:")
        first_layer.addWidget(survey_label, 0)
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        first_layer.addWidget(self.survey_select, 1)

        button_survey_new = QPushButton("New Survey")
        button_survey_new.clicked.connect(self.new_survey)
        first_layer.addWidget(button_survey_new, 1)

        # Sites
        self.button_site_manage = QPushButton("Manage Sites")
        self.button_site_manage.clicked.connect(self.new_site)
        first_layer.addWidget(self.button_site_manage, 1)
        self.button_manage_site_flag = False
        self.button_site_manage.setEnabled(self.button_manage_site_flag)

        self.button_species_manage = QPushButton("Manage Species")
        self.button_species_manage.clicked.connect(self.manage_species)
        first_layer.addWidget(self.button_species_manage, 1)

        self.button_media_manage = QPushButton("Manage Media")
        self.button_media_manage.clicked.connect(self.manage_media)
        first_layer.addWidget(self.button_media_manage, 1)

        self.update_survey()
        layout.addLayout(first_layer)

        # Bottom Layer
        bottom_layer = QHBoxLayout()
        # Create three buttons
        button_load = QPushButton("1. Load Data")
        button_match = QPushButton("2. Match")
        button_validate = QPushButton("3. Validate Images")

        
        button_load.clicked.connect(self.upload_media)
        button_match.clicked.connect(self.process_images)
        button_validate.clicked.connect(self.validate)

        # Add buttons to the layout
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        bottom_layer.addWidget(button_validate)
        layout.addLayout(bottom_layer) 
        
        self.setLayout(layout)

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
        survey_names = self.mpDB.select('survey',columns='id, name')
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

    # Upload Button
    def upload_media(self):
        '''
        Add media from CSV
        '''
        # remove after finish testing
        self.mpDB.clear('media')
        self.mpDB.clear('roi')
        self.mpDB.clear('roi_emb')
        if self.select_survey():
            manifest = QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'),("CSV Files (*.csv)"))[0]
            if manifest:
                valid_sites = fetch_sites(self.mpDB, self.active_survey[0])
                import_manifest(self.mpDB, manifest, valid_sites)
                
        else:
            dialog = AlertPopup(self, "Please create a new survey before uploading.")
            if dialog.exec():
                del dialog
        
    def process_images(self):
        # Figure out how to add loading bar
        dialog = AlertPopup(self, "Processing Images", title="Processing Images")
        dialog.show()
        self.animl_thread = AnimlThread(self.mpDB)

        # Connect signals from the thread to the main thread
        self.animl_thread.progress_update.connect(dialog.update)
        self.animl_thread.start()
        
        if dialog.exec():
            del dialog
        
    # Validate Button
    def validate(self):
        self.parent._set_compare_view()
        # return True

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")


class AnimlThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        media = self.mpDB.select("media", columns="id, filepath, pair_id, sequence_id")
        self.media = pd.DataFrame(media, columns=["id", "filepath", "pair_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 

        self.viewpoint_filepath = os.path.join(os.getcwd(), "viewpoint_jaguar.pt")
        self.miew_filepath = os.path.join(os.getcwd(), "miewid.bin")
        
    
    def run(self):
        self.progress_update.emit("Calculating bounding box...")
        self.get_bbox()
        self.progress_update.emit("Calculating viewpoint...")
        self.get_viewpoint()
        self.progress_update.emit("Calculating embeddings...")
        self.get_embeddings()
        self.progress_update.emit("Matching images...")
        match(self.mpDB)
        self.progress_update.emit("Processing complete!")

    def get_bbox(self):
        # TODO: add MD step, assumes no rois yet
        pass

    def get_viewpoint(self):
        # TODO: Utilize probability for pairs/sequences
        self.rois = fetch_roi(self.mpDB)
        viewpoints = viewpoint.matchypatchy(self.rois, self.image_paths, self.viewpoint_filepath)
    
        for v in viewpoints:
            roi_id = v[0]
            value = v[1]
            prob = v[2] 
            print(roi_id, value, prob)
            self.mpDB.edit_row("roi", roi_id, {"viewpoint":value})

        # Match Button
    def get_embeddings(self):
        # 1. fetch images
        self.rois = fetch_roi(self.mpDB)
        embs = miewid.matchypatchy(self.rois, self.image_paths, self.miew_filepath)
        for e in embs:
            roi_id = e[0]
            emb = e[1]
            emb_id = self.mpDB.add_emb(emb)
            self.mpDB.edit_row("roi", roi_id, {"emb_id":emb_id})