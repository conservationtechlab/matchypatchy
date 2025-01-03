"""
GUI Window for viewing images
"""

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
from PyQt6.QtCore import Qt

from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.popup_alert import ProgressPopup
from matchypatchy.gui.popup_alert import AlertPopup


class DisplayMedia(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB

        layout = QVBoxLayout()

        first_layer = QHBoxLayout()
        # Home Button
        first_layer.addSpacing(10)
        return_button = QPushButton("Home")
        return_button.clicked.connect(self.home)
        return_button.setFixedWidth(100)
        first_layer.addWidget(return_button, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # FILTERS
        survey_label = QLabel("Filter:")
        survey_label.setFixedWidth(50)
        first_layer.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # REGION
        self.region_select = QComboBox()
        self.region_select.setFixedWidth(200)
        # filter out null entries, duplicates, dict will be {Name: [surveyids]}
        self.region_list_ordered = [(0, 'Region')] 
        self.region_select.addItems([el[1] for el in self.region_list_ordered])
        first_layer.addWidget(self.region_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # SURVEY
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_list_ordered = [(0, 'Survey')]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.active_survey = self.survey_list_ordered[0]

        # SITE
        self.site_select = QComboBox()
        self.site_select.setFixedWidth(200)
        first_layer.addWidget(self.site_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.valid_sites = None
        self.site_list_ordered = [(0, 'Site')]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
        self.active_site = self.site_list_ordered[0]

        # SPECIES
        self.species_select = QComboBox()
        self.species_select.setFixedWidth(200)
        first_layer.addWidget(self.species_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species_list_ordered = [(0, 'Species')]
        self.species_select.addItems([el[1] for el in self.species_list_ordered])
        self.active_species = self.species_list_ordered[0]

        # INDIVIDUAL
        self.individual_select = QComboBox()
        self.individual_select.setFixedWidth(200)
        first_layer.addWidget(self.individual_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.individual_list_ordered = [(0, 'Individual')]
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])
        self.active_individual = self.individual_list_ordered[0]

        # UNIDENTIFIED
        unidentified = QPushButton("Unidentified")
        unidentified.setCheckable(True)
        unidentified.toggled.connect(self.select_unidentified)
        self.unidentified_only = False
        first_layer.addWidget(unidentified, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # FAVORITE
        favorites = QPushButton("Favorites")
        favorites.setCheckable(True)
        favorites.toggled.connect(self.select_favorites)
        self.favorites_only = False
        first_layer.addWidget(favorites, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # display rois or media
        self.media_table = MediaTable(self)
        layout.addWidget(self.media_table, stretch=1)
        self.setLayout(layout)

        self.region_select.currentIndexChanged.connect(self.select_region)
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        self.site_select.currentIndexChanged.connect(self.select_site)
        self.species_select.currentIndexChanged.connect(self.select_species)
        self.individual_select.currentIndexChanged.connect(self.select_individual)


    # Return Home Button
    def home(self):
        self.parent._set_base_view()

    # 1. RUN ON ENTRY
    def load_table(self):
        data_available = self.media_table.load_data()
        if not data_available:
            dialog = AlertPopup(self, "No images found! Please import media.", title="Alert")
            if dialog.exec():
                self.home()
                del dialog
            return False
        return True
        
    # 2. RUN ON ENTRY
    def refresh_filters(self, filters=None):
        """
        Update Dropdown Lists
        """
        self.region_select.blockSignals(True)
        self.survey_select.blockSignals(True)
        self.site_select.blockSignals(True)
        self.species_select.blockSignals(True)
        self.individual_select.blockSignals(True)

        self.region_select.clear()
        self.region_list_ordered = [(0, 'Region')] + list(self.mpDB.select('region', columns='id, name'))
        self.region_select.addItems([el[1] for el in self.region_list_ordered])
        self.active_region = self.region_list_ordered[self.region_select.currentIndex()]

        self.survey_select.clear()
        self.survey_list_ordered = [(0, 'Survey')] + list(self.mpDB.select('survey', columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]

        self.site_select.clear()
        self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0, 'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
        self.active_site = self.site_list_ordered[self.site_select.currentIndex()]

        self.species_select.clear()
        self.species_list_ordered = [(0, 'Species')] + list(self.mpDB.select('species', columns='id, common'))
        self.species_select.addItems([el[1] for el in self.species_list_ordered])
        self.active_species = self.species_list_ordered[self.species_select.currentIndex()]

        self.individual_select.clear()
        self.individual_list_ordered = [(0, 'Individual')] + list(self.mpDB.select('individual', columns='id, name'))
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])
        self.active_individual = self.individual_list_ordered[self.individual_select.currentIndex()]

        if filters:
            print(filters)
            # media_table.filter() expecting [id, name]
            if "region_id" in filters:
                self.active_region = [filters['region_id']]
            if "survey_id" in filters:
                self.active_survey = [filters['survey_id']]
            # TODO: does not check if site_id in valid sites
            if "site_id" in filters:
                self.active_site = [filters["site_id"]]
            if "species_id" in filters:
                self.active_species = [filters["species_id"]]
            if "individual_id" in filters:
                self.active_individual = [filters["individual_id"]]

        self.region_select.blockSignals(False)
        self.survey_select.blockSignals(False)
        self.site_select.blockSignals(False)
        self.species_select.blockSignals(False)
        self.individual_select.blockSignals(False)

    # 3. RUN ON ENTRY
    def load_thumbnails(self):
        self.loading_bar = ProgressPopup(self, "Loading images...")
        self.media_table.load_images()

    # 4. RUN ON ENTRY
    def filter_table(self):
        """
        Filter the media table based on the selected options
        Run after any setting is changed
        """
        self.media_table.filter()

    def select_unidentified(self):
        self.unidentified_only = not self.unidentified_only
        self.filter_table()

    def select_favorites(self):
        self.favorites_only = not self.favorites_only
        self.filter_table()

    def select_region(self):
        self.active_region = self.region_list_ordered[self.region_select.currentIndex()]
        self.filter_surveys()
        self.filter_table()

    def select_survey(self):
        self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]
        self.filter_sites()
        self.filter_table()

    def select_site(self):
        self.active_site = self.site_list_ordered[self.site_select.currentIndex()]
        self.filter_table()

    def select_species(self):
        self.active_species = self.species_list_ordered[self.species_select.currentIndex()]
        self.filter_table()

    def select_individual(self):
        self.active_individual = self.individual_list_ordered[self.individual_select.currentIndex()]
        self.filter_table()

    def filter_surveys(self):
        # Update site list to reflect active survey
        self.survey_select.clear()
        print(self.active_region)
        if self.region_select.currentIndex() > 0:
            self.valid_surveys = dict(self.mpDB.select("survey", columns="id, name", row_cond=f'region_id={self.active_region[0]}'))
        else:
            self.valid_surveys = dict(self.mpDB.select("survey", columns="id, name"))
        self.survey_list_ordered = [(0, 'Survey')] + [(k, v) for k, v in self.valid_surveys.items()]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])

    def filter_sites(self):
        # Update site list to reflect active survey
        self.site_select.clear()
        if self.survey_select.currentIndex() > 0:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name", row_cond=f'survey_id={self.active_survey[0]}'))
        else:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0, 'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
