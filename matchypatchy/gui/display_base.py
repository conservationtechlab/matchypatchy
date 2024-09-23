"""
Base Gui View
"""
import os
import torch
from tqdm import tqdm 
import pandas as pd

from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel)
from PyQt6.QtCore import Qt

from .popup_survey import SurveyPopup
from .popup_site import SitePopup
from .popup_alert import AlertPopup
from .popup_species import SpeciesPopup

from ..database.media import import_csv
from ..database.site import fetch_sites

from ..database.roi import (fetch_roi, update_roi_embedding, 
                            update_roi_viewpoint, roi_knn)

from ..models import viewpoint
from ..models import miewid

from ..models.generator import dataloader



## GET DEVICE

class DisplayBase(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print('Using device:', self.device)
        
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
        self.get_viewpoint()
        self.get_embeddings()
        roi_knn(self.mpDB)


    def get_viewpoint(self):
        # TODO: Utilize probability for pairs/sequences

        # 1. fetch images
        media = self.mpDB.select("media", columns="id, filepath, pair_id, sequence_id")
        media = pd.DataFrame(media, columns=["id", "filepath", "pair_id", "sequence_id"])
        image_paths = pd.Series(media["filepath"].values,index=media["id"]).to_dict() 

        rois = fetch_roi(self.mpDB)
        rois = viewpoint.filter(rois)
        
        if len(rois) > 0:
            viewpoint_dl = dataloader(rois, image_paths, 
                                      viewpoint.IMAGE_HEIGHT, viewpoint.IMAGE_WIDTH)
            # 2. load viewpoint model
            model = viewpoint.load(self.device)
            # 3. update rows
            with torch.no_grad():
                for _, batch in tqdm(enumerate(viewpoint_dl)):
                    img = batch[0]
                    roi_id = batch[1].numpy()[0]
                    output = model(img.to(self.device))
                    value = torch.argmax(output, dim=1).cpu().detach().numpy()[0]
                    prob = torch.max(torch.nn.functional.softmax(output, dim=1), 1)[0]
                    prob = prob.cpu().detach().numpy()[0]
                    print(roi_id, value, prob)
                    update_roi_viewpoint(self.mpDB, roi_id, value)

        # Match Button
    def get_embeddings(self):
        # 1. fetch images
        image_paths = dict(self.mpDB.select("media", columns="id, filepath"))
        rois = fetch_roi(self.mpDB)
        rois = miewid.filter(rois)
        
        if len(rois) > 0:
            miew_dl = dataloader(miewid.filter(rois), image_paths, 
                                miewid.IMAGE_HEIGHT, miewid.IMAGE_WIDTH)
            # 2. load miewid 
            model = miewid.load(self.device)
            # 3. get embedding
            with torch.no_grad():
                for _, batch in tqdm(enumerate(miew_dl)):
                    img = batch[0]
                    roi_id = batch[1].numpy()[0]
                    # 
                    output = model.extract_feat(img.to(self.device))
                    output = output.cpu().detach().numpy()[0]
                    # 4. store embedding in table
                    emb_id = self.mpDB.add_emb(output)
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
