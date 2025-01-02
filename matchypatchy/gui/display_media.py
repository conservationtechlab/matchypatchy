"""
GUI Window for viewing images
"""

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
from PyQt6.QtCore import Qt

from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.popup_alert import ProgressPopup


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

    # Return Home Button
    def home(self):
        self.parent._set_base_view()

    # 1. RUN ON ENTRY
    def refresh_filters(self, filters=None):
        """
        Update Dropdown Lists
        """
        print("One")
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
            if "survey_id" in filters:
                self.active_survey = [filters['survey_id']]
            # TODO: does not check if site_id in valid sites
            if "site_id" in filters:
                self.active_site = [filters["site_id"]]
            if "species_id" in filters:
                self.active_species = [filters["species_id"]]
            if "individual_id" in filters:
                self.active_individual = [filters["individual_id"]]


    # 2. RUN ON ENTRY
    def connect_filters(self):
        print("Two")
        # connect combobox selection AFTER they've been populated
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        self.site_select.currentIndexChanged.connect(self.select_site)
        self.species_select.currentIndexChanged.connect(self.select_species)
        self.individual_select.currentIndexChanged.connect(self.select_individual)

    # 3. RUN ON ENTRY
    def load_table(self):
        print("Three")
        self.loading_bar = ProgressPopup(self, "Loading images...")
        self.media_table.load()

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

    def filter_sites(self):
        # Update site list to reflect active survey
        self.site_select.clear()
        if self.survey_select.currentIndex() > 0:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name", row_cond=f'survey_id={self.active_survey[0]}'))
        else:
            self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0, 'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
