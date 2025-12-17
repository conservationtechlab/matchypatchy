"""
Filterbar Widget for MatchyPatchy GUI
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy, QCheckBox, QComboBox
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtCore import Qt


class FilterBar(QWidget):
    """
    Filter bar widget for selecting filters in MatchyPatchy GUI
    Default combobox size is 200px, can be adjusted via size parameter.
    """
    def __init__(self, parent, size=200):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        self.size = size
        self.filters = {}
        self.valid_stations = dict(self.mpDB.select("station", columns="id, name"))

        layout = QHBoxLayout()
        # Filter label
        layout.addWidget(QLabel("Filter:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Region
        self.region_list_ordered = [(0, 'Region')]
        self.region_select = FilterBox(self.region_list_ordered, self.size)
        self.region_select.currentIndexChanged.connect(self.select_region)
        layout.addWidget(self.region_select, alignment=Qt.AlignmentFlag.AlignLeft)
        # Survey
        self.survey_list_ordered = [(0, 'Survey')]
        self.survey_select = FilterBox(self.survey_list_ordered, self.size)
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        layout.addWidget(self.survey_select, alignment=Qt.AlignmentFlag.AlignLeft)
        # Station
        self.station_list_ordered = [(0, 'Station')]
        self.station_select = FilterBox(self.station_list_ordered, self.size)
        self.station_select.currentIndexChanged.connect(self.select_station)
        layout.addWidget(self.station_select, alignment=Qt.AlignmentFlag.AlignLeft)
        # Viewpoint
        self.viewpoint_list_ordered = [(0, 'Viewpoint'), (1, 'Left'), (2, 'Right')]
        self.viewpoint_select = FilterBox(self.viewpoint_list_ordered, self.size)
        self.viewpoint_select.currentIndexChanged.connect(self.select_viewpoint)
        layout.addWidget(self.viewpoint_select, alignment=Qt.AlignmentFlag.AlignLeft)
        # Individual
        self.individual_list_ordered = [(0, 'Individual')]
        self.individual_select = FilterBox(self.individual_list_ordered, self.size)
        self.individual_select.currentIndexChanged.connect(self.select_individual)
        self.individual_select.setVisible(False)  # Disabled until feature is implemented
        layout.addWidget(self.individual_select, alignment=Qt.AlignmentFlag.AlignLeft)

        # UNIDENTIFIED
        self.unidentified = QCheckBox("Unidentified")
        self.unidentified.toggled.connect(self.select_unidentified)
        self.unidentified_only = False
        layout.addWidget(self.unidentified, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # FAVORITE
        self.favorites = QCheckBox("Favorites")
        self.favorites.toggled.connect(self.select_favorites)
        self.favorites_only = False
        layout.addWidget(self.favorites, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)

    def refresh_filters(self, prefilter=None):
        """
        Clear and Refresh Filters on Re-entry
        """
        self.region_select.blockSignals(True)
        self.survey_select.blockSignals(True)
        self.station_select.blockSignals(True)
        self.individual_select.blockSignals(True)

        self.region_select.clear()
        self.region_list_ordered = [(0, 'Region')] + list(self.mpDB.select('region', columns='id, name'))
        self.region_select.addItems([el[1] for el in self.region_list_ordered])

        self.survey_select.clear()
        self.survey_list_ordered = [(0, 'Survey')] + list(self.mpDB.select('survey', columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])

        # individual list hidden until feature is implemented on QC
        self.individual_select.clear()
        self.individual_list_ordered = [(0, 'Individual')] + list(self.mpDB.select('individual', columns='id, name'))
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])

        self.filter_stations()

        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                        'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                        'active_station': self.station_list_ordered[self.station_select.currentIndex()],
                        'active_viewpoint': self.viewpoint_list_ordered[self.viewpoint_select.currentIndex()],
                        'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()]}

        if prefilter:
            if 'individual_id' in prefilter.keys():
                self.filters['active_individual'] = self.individual_list_ordered[prefilter['individual_id']]
                self.individual_select.setCurrentIndex(prefilter['individual_id'])

        self.region_select.blockSignals(False)
        self.survey_select.blockSignals(False)
        self.station_select.blockSignals(False)
        self.individual_select.blockSignals(False)

    def select_region(self):
        self.filters['active_region'] = self.region_list_ordered[self.region_select.currentIndex()]
        self.filter_surveys()
        self.filter_stations(survey_ids=list(self.valid_surveys.items()))

    def select_survey(self):
        self.filters['active_survey'] = self.survey_list_ordered[self.survey_select.currentIndex()]
        self.filter_stations(survey_ids=[self.filters['active_survey']])

    def select_station(self):
        self.filters['active_station'] = self.station_list_ordered[self.station_select.currentIndex()]

    def select_viewpoint(self):
        self.filters['active_viewpoint'] = self.viewpoint_list_ordered[self.viewpoint_select.currentIndex()]

    def select_individual(self):
        self.filters['active_individual'] = self.individual_list_ordered[self.individual_select.currentIndex()]

    def select_unidentified(self):
        self.unidentified_only = not self.unidentified_only

    def select_favorites(self):
        self.favorites_only = not self.favorites_only

    def filter_surveys(self):
        """Filter surveys based on active region"""
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

    def filter_stations(self, survey_ids=None):
        """Filter stations based on active survey(s)"""
        # block signals while updating combobox
        self.station_select.blockSignals(True)
        self.station_select.clear()
        if survey_ids:
            survey_list = ",".join([str(s[0]) for s in survey_ids])
            selection = f'survey_id IN ({survey_list})'
            self.valid_stations = dict(self.mpDB.select("station", columns="id, name", row_cond=selection))
        else:
            self.valid_stations = dict(self.mpDB.select("station", columns="id, name"))

        # Update station list to reflect active survey
        self.station_list_ordered = [(0, 'Station')] + [(k, v) for k, v in self.valid_stations.items()]
        self.station_select.addItems([el[1] for el in self.station_list_ordered])
        self.station_select.blockSignals(False)

    def get_filters(self):
        """Return current filter selections as a dictionary"""
        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                        'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                        'active_station': self.station_list_ordered[self.station_select.currentIndex()],
                        'active_viewpoint': self.viewpoint_list_ordered[self.viewpoint_select.currentIndex()],
                        'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()],
                        'unidentified_only': self.unidentified_only,
                        'favorites_only': self.favorites_only}
        return self.filters

    def get_valid_stations(self):
        return self.valid_stations

    def viewpoint_visible(self, visible: bool):
        """Set viewpoint combobox visibility"""
        self.viewpoint_select.setVisible(visible)

    def individual_visible(self, visible: bool):
        """Set individual combobox visibility"""
        self.individual_select.setVisible(visible)

    def unidentified_visible(self, visible: bool):
        """Set unidentified checkbox visibility"""
        self.unidentified.setVisible(visible)

    def favorites_visible(self, visible: bool):
        """Set favorites checkbox visibility"""
        self.favorites.setVisible(visible)


class FilterBox(QComboBox):
    def __init__(self, initial_list, width):
        super().__init__()
        self.setModel(QStandardItemModel())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedWidth(width)
        self.addItems([el[1] for el in initial_list])
