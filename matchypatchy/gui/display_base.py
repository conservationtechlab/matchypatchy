"""
Base Gui View
"""
import os
from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import Qt

from .popup_survey import SurveyPopup
from .popup_site import SitePopup
from .popup_alert import AlertPopup
from .popup_species import SpeciesPopup

from ..database.media import import_csv
from ..database.site import fetch_sites
from ..database.roi import fetch_roi, update_roi_embedding
from .. import sqlite_vec

from ..models.viewpoint import predict_viewpoint

from ..models import miewid
from ..models.generator import dataloader

import torch
from tqdm import tqdm



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
        first_layer.addWidget(self.survey_select, 2)

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

        self.update_survey()
        layout.addLayout(first_layer)

        # Bottom Layer
        bottom_layer = QHBoxLayout()
        # Create three buttons
        button_load = QPushButton("1. Load Data")
        button_match = QPushButton("2. Match")
        button_validate = QPushButton("3. Validate Images")

        
        button_load.clicked.connect(self.upload_media)
        button_match.clicked.connect(self.match)
        button_validate.clicked.connect(self.validate)

        # Add buttons to the layout
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        bottom_layer.addWidget(button_validate)
        layout.addLayout(bottom_layer) 
        
        self.setLayout(layout)

    def new_survey(self):
        dialog = SurveyPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_survey(dialog.get_name(), dialog.get_region(),
                                           dialog.get_year_start(), dialog.get_year_start())
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

    def manage_species(self):
        dialog = SpeciesPopup(self)
        if dialog.exec():
            del dialog

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
                import_csv(self.mpDB, manifest, valid_sites)
                
        else:
            dialog = AlertPopup(self, "Please create a new survey before uploading.")
            if dialog.exec():
                del dialog
        
    def match(self):
        #self.get_viewpoint()
        self.get_embeddings()

    def get_viewpoint(self):
        # 1. fetch images
        image_paths = dict(self.mpDB.fetch_columns("media", "filepath"))
        rois = fetch_roi(self.mpDB)
        roi_missing_viewpoint = rois[rois['Viewpoint'] is None]
        #dataloader = viewpoint_dataloader(rois,image_paths)
        # 2. run viewpoint model
        #predict_viewpoint(manifest, None)
        # 3. update rows 

    # Match Button
    def get_embeddings(self):
        # 1. fetch images
        image_paths = dict(self.mpDB.fetch_columns("media", "filepath"))
        rois = fetch_roi(self.mpDB)
        rois = rois[rois['emb_id'] == 'None']
        dataloader = dataloader(rois, image_paths, miewid.IMAGE_HEIGHT, miewid.IMAGE_WIDTH)
        # 2. run miewid 
        
        model = miewid.load_miew('/models/miew_id_all.bin')
        
        with torch.no_grad():
            for _, batch in tqdm(enumerate(dataloader)):
                img = batch[0]
                roi_id = batch[1].numpy()[0]
                print(roi_id)
                #output = model.extract_feat(img.to(device))
                output = output.numpy().squeeze()
                converted = sqlite_vec.serialize_float32(output)

                # 4. store embedding in table
                emb_id = self.mpDB.add_emb(converted)
                update_roi_embedding(self.mpDB, roi_id, emb_id)

        
    # Validate Button
    def validate(self):
        self.parent._set_media_view()
        # return True

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")
