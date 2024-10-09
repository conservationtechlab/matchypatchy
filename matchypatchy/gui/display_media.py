"""
GUI Window for viewing images
"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from .media_table import MediaTable
from .widget_progressbar import ProgressPopup

# TODO:
# MAKE MEDIA EDITABLE

class DisplayMedia(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
        layout = QVBoxLayout()
        
        first_layer = QHBoxLayout()
        # Home Button
        return_button = QPushButton("Home")
        return_button.clicked.connect(self.home)
        return_button.setFixedWidth(100)
        first_layer.addWidget(return_button, 0,  alignment=Qt.AlignmentFlag.AlignLeft)

        # FILTERS
        survey_label = QLabel("Filter:")
        survey_label.setFixedWidth(50)
        first_layer.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # SURVEY 
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_list_ordered = [(0,'Survey')]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.active_survey = self.survey_list_ordered[0]

        # SITE
        self.site_select = QComboBox()
        self.site_select.setFixedWidth(200)
        first_layer.addWidget(self.site_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.valid_sites = None
        self.site_list_ordered = [(0,'Site')]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
        self.active_site = self.site_list_ordered[0]

        # SPECIES 
        self.species_select = QComboBox()
        self.species_select.setFixedWidth(200)
        first_layer.addWidget(self.species_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species_list_ordered = [(0,'Species')]
        self.species_select.addItems([el[1] for el in self.species_list_ordered])
        self.active_species = self.species_list_ordered[0]

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # MEDIA TABLE
        self.media_table = MediaTable(self)
        layout.addWidget(self.media_table, stretch=1)
        self.setLayout(layout)


    def home(self):
        self.parent._set_base_view()

    def refresh_filters(self):
        """
        Update Dropdown Lists
        """
        self.survey_select.clear()
        self.survey_list_ordered = [(0,'Survey')] + list(self.mpDB.select('survey',columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]

        self.site_select.clear()
        self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0,'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
        self.active_site = self.site_list_ordered[self.site_select.currentIndex()]

        self.species_select.clear()
        self.species_list_ordered = [(0,'Species')] + list(self.mpDB.select('species',columns='id, common'))
        self.species_select.addItems([el[1] for el in self.species_list_ordered])
        self.active_species = self.species_list_ordered[self.species_select.currentIndex()]

    def connect(self):
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        self.site_select.currentIndexChanged.connect(self.select_site)
        self.species_select.currentIndexChanged.connect(self.select_species)

    def update_table(self):
        self.loading_bar = ProgressPopup(self, "Loading images...")
        self.loading_bar.show()
        self.media_table.update()


    def select_survey(self):
        print('survey changed')
        self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]
        self.update_table()

    def select_site(self):
        print('site changed')
        self.active_site = self.site_list_ordered[self.site_select.currentIndex()]
        self.update_table()
        
    def select_species(self):
        print('species changed')
        self.active_species = self.species_list_ordered[self.species_select.currentIndex()]
        self.update_table()

    def filter_sites(self):
        # Update site list to reflect active survey
        self.site_select.clear()
        if self.survey_select.currentIndex() > 0:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name", row_cond=f'survey_id={self.active_survey[0]}'))
        else:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0,'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")



