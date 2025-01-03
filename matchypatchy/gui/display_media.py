"""
GUI Window for viewing images
"""

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
from PyQt6.QtCore import Qt

from matchypatchy.gui.media_table import MediaTable
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
        self.region_list_ordered = [(0, 'Region')] 
        self.region_select.addItems([el[1] for el in self.region_list_ordered])
        first_layer.addWidget(self.region_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # SURVEY
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_list_ordered = [(0, 'Survey')]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])

        # SITE
        self.site_select = QComboBox()
        self.site_select.setFixedWidth(200)
        first_layer.addWidget(self.site_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.valid_sites = None
        self.site_list_ordered = [(0, 'Site')]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])

        # SPECIES
        self.species_select = QComboBox()
        self.species_select.setFixedWidth(200)
        first_layer.addWidget(self.species_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species_list_ordered = [(0, 'Species')]
        self.species_select.addItems([el[1] for el in self.species_list_ordered])

        # INDIVIDUAL
        self.individual_select = QComboBox()
        self.individual_select.setFixedWidth(200)
        first_layer.addWidget(self.individual_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.individual_list_ordered = [(0, 'Individual')]
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])

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

        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                'active_site': self.site_list_ordered[self.site_select.currentIndex()],
                'active_species': self.species_list_ordered[self.species_select.currentIndex()],
                'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()],
                'unidentified_only': self.unidentified_only,
                'favorites_only': self.favorites_only}

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
        
    def refresh_filters(self, prefilter=None):
        """
        Update Dropdown Lists, Fill Filter Dict
        Allows refresh of dropdowns if re-entry into media view after updating database
        """
        # block signals while updating lists
        self.region_select.blockSignals(True)
        self.survey_select.blockSignals(True)
        self.site_select.blockSignals(True)
        self.species_select.blockSignals(True)
        self.individual_select.blockSignals(True)

        self.region_select.clear()
        self.region_list_ordered = [(0, 'Region')] + list(self.mpDB.select('region', columns='id, name'))
        self.region_select.addItems([el[1] for el in self.region_list_ordered])

        self.survey_select.clear()
        self.survey_list_ordered = [(0, 'Survey')] + list(self.mpDB.select('survey', columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])

        self.site_select.clear()
        self.valid_sites = dict(self.mpDB.select("site", columns="id, name"))
        self.site_list_ordered = [(0, 'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])

        self.species_select.clear()
        self.species_list_ordered = [(0, 'Species')] + list(self.mpDB.select('species', columns='id, common'))
        self.species_select.addItems([el[1] for el in self.species_list_ordered])

        self.individual_select.clear()
        self.individual_list_ordered = [(0, 'Individual')] + list(self.mpDB.select('individual', columns='id, name'))
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])
        
        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                        'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                        'active_site': self.site_list_ordered[self.site_select.currentIndex()],
                        'active_species': self.species_list_ordered[self.species_select.currentIndex()],
                        'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()],
                        'unidentified_only': self.unidentified_only,
                        'favorites_only': self.favorites_only}

        if prefilter:
            self.filters.update({k: prefilter[k] for k in self.filters.keys() & prefilter.keys()})

        self.region_select.blockSignals(False)
        self.survey_select.blockSignals(False)
        self.site_select.blockSignals(False)
        self.species_select.blockSignals(False)
        self.individual_select.blockSignals(False)

    # 3. RUN ON ENTRY
    def load_thumbnails(self):
        """
        Load Thumbnails

        Only run if self.media_table.load_data() returns true
        self.media_table.load_images() will trigger a self filter
        and a self refresh upon completion
        """
        self.media_table.load_images()

    def filter_table(self):
        """
        Filter the media table based on the selected options
        Run after any setting is changed
        """
        print("filter table")
        self.media_table.filter()

    def select_unidentified(self):
        self.unidentified_only = not self.unidentified_only
        self.filters['undientified_only'] = self.unidentified_only
        self.filter_table()

    def select_favorites(self):
        self.favorites_only = not self.favorites_only
        self.filters['favorites_only'] = self.unidentified_only
        self.filter_table()

    def select_region(self):
        print("select region")
        self.filters['active_region'] = self.region_list_ordered[self.region_select.currentIndex()]
        self.filter_surveys()
        self.filter_sites(survey_ids=list(self.valid_surveys.items()))
        self.filter_table()

    def select_survey(self):
        self.filters['active_survey'] = self.survey_list_ordered[self.survey_select.currentIndex()]
        self.filter_sites(survey_ids=[self.filters['active_survey']])
        self.filter_table()

    def select_site(self):
        self.filters['active_site'] = self.site_list_ordered[self.site_select.currentIndex()]
        self.filter_table()

    def select_species(self):
        self.filters['active_species'] = self.species_list_ordered[self.species_select.currentIndex()]
        self.filter_table()

    def select_individual(self):
        self.filters['active_individual'] = self.individual_list_ordered[self.individual_select.currentIndex()]
        self.filter_table()

    def filter_surveys(self):
        # block signals while updating combobox
        self.survey_select.blockSignals(True)
        self.survey_select.clear()
        if self.region_select.currentIndex() > 0:
            # get surveys in selected region
            region_id = self.filters['active_region'][0]
            self.valid_surveys = dict(self.mpDB.select("survey", columns="id, name", row_cond=f'region_id={region_id}'))
        else:
            # get all surveys
            self.valid_surveys = dict(self.mpDB.select("survey", columns="id, name"))
        # Update survey list to reflect active region
        self.survey_list_ordered = [(0, 'Survey')] + [(k, v) for k, v in self.valid_surveys.items()]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.survey_select.blockSignals(False)
        

    def filter_sites(self, survey_ids=None):
        # block signals while updating combobox
        self.site_select.blockSignals(True)
        self.site_select.clear()
        survey_list = ",".join([str(s[0]) for s in survey_ids])
        selection = f'survey_id IN ({survey_list})'

        self.valid_sites = dict(self.mpDB.select("site", columns="id, name", row_cond=selection, quiet=False))
        # Update site list to reflect active survey
        self.site_list_ordered = [(0, 'Site')] + [(k, v) for k, v in self.valid_sites.items()]
        self.site_select.addItems([el[1] for el in self.site_list_ordered])
        self.site_select.blockSignals(False)        
