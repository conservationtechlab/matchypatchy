"""
Filterbar Widget for MatchyPatchy GUI
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy, QCheckBox, QComboBox
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtCore import Qt

from matchypatchy.database.location import region_names, survey_names, station_names
from matchypatchy.database.individual import individual_names
from matchypatchy.database.media import media_without_rois
from matchypatchy.project import UsesProject


class FilterBar(UsesProject, QWidget):
    """
    Filter bar widget for selecting filters in MatchyPatchy GUI
    Default combobox size is 200px, can be adjusted via size parameter.
    """
    def __init__(self, parent, size=200):
        super().__init__(parent)
        self.project = parent.project
        self.size = size
        self.filters = {}
        self.valid_stations = dict(station_names(self.mpDB))
        self.valid_surveys = dict(survey_names(self.mpDB))

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
        layout.addWidget(self.individual_select, alignment=Qt.AlignmentFlag.AlignLeft)

        # No ROI Filter
        self.no_roi = QCheckBox("No ROI")
        self.no_roi.toggled.connect(self.select_no_roi)
        self.no_roi_mids = False
        layout.addWidget(self.no_roi, 0, alignment=Qt.AlignmentFlag.AlignLeft)

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
        self.project.data_changed.connect(self.lists_written)

    def lists_written(self, table):
        """
        Reload the region, survey, station and individual lists after one of them is written

        Connected to project.data_changed in __init__. The chosen filters stay
        put, matched by id; a choice that was deleted goes back to its placeholder
        (all). Unlike refresh_filters, which resets every filter on entering a view.
        """
        if table not in ("region", "survey", "station", "individual"):
            return
        region_id, survey_id, station_id, individual_id = (
            self._chosen_id(self.region_select, self.region_list_ordered),
            self._chosen_id(self.survey_select, self.survey_list_ordered),
            self._chosen_id(self.station_select, self.station_list_ordered),
            self._chosen_id(self.individual_select, self.individual_list_ordered))
        combos = (self.region_select, self.survey_select, self.station_select, self.individual_select)
        for combo in combos:
            combo.blockSignals(True)

        self.region_list_ordered = [(0, 'Region')] + region_names(self.mpDB)
        self._fill(self.region_select, self.region_list_ordered, region_id)
        # surveys of the chosen region, stations of the chosen survey(s), as select_region/select_survey do
        region_id = self._chosen_id(self.region_select, self.region_list_ordered)
        self.valid_surveys = dict(survey_names(self.mpDB, region_id=region_id or None))
        self.survey_list_ordered = [(0, 'Survey')] + list(self.valid_surveys.items())
        self._fill(self.survey_select, self.survey_list_ordered, survey_id)
        survey_id = self._chosen_id(self.survey_select, self.survey_list_ordered)
        if survey_id:
            survey_ids = [survey_id]
        elif region_id:
            survey_ids = list(self.valid_surveys)
        else:
            survey_ids = None
        self.valid_stations = dict(station_names(self.mpDB, survey_ids=survey_ids))
        self.station_list_ordered = [(0, 'Station')] + list(self.valid_stations.items())
        self._fill(self.station_select, self.station_list_ordered, station_id)
        self.individual_list_ordered = [(0, 'Individual')] + individual_names(self.mpDB)
        self._fill(self.individual_select, self.individual_list_ordered, individual_id)

        for combo in combos:
            combo.blockSignals(False)
        self.get_filters()

    @staticmethod
    def _chosen_id(combo, items):
        """Id of the combo's current item, 0 for the placeholder; a lists_written helper"""
        index = combo.currentIndex()
        return items[index][0] if 0 <= index < len(items) else 0

    @staticmethod
    def _fill(combo, items, chosen_id):
        """Replace the combo's items, choosing chosen_id or the placeholder; a lists_written helper"""
        combo.clear()
        combo.addItems([name for _, name in items])
        combo.setCurrentIndex(next((i for i, (item_id, _) in enumerate(items) if item_id == chosen_id), 0))

    def refresh_filters(self, prefilter=None):
        """
        Clear and Refresh Filters on Re-entry.

        Args:
            prefilter (dict, optional): Dictionary containing prefilter values to apply after refresh.
        """
        # block signals to prevent triggers
        self.region_select.blockSignals(True)
        self.survey_select.blockSignals(True)
        self.station_select.blockSignals(True)
        self.viewpoint_select.blockSignals(True)
        self.individual_select.blockSignals(True)
        self.unidentified.blockSignals(True)
        self.favorites.blockSignals(True)
        self.no_roi.blockSignals(True)

        # reset all filter selections to default, reload region, survey and individual lists in case they have changed
        self.region_select.clear()
        self.region_list_ordered = [(0, 'Region')] + region_names(self.mpDB)
        self.region_select.addItems([el[1] for el in self.region_list_ordered])

        self.survey_select.clear()
        self.survey_list_ordered = [(0, 'Survey')] + survey_names(self.mpDB)
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])

        # filter stations based on all surveys
        self.filter_stations()

        # individual list hidden until feature is implemented on QC
        self.individual_select.clear()
        self.individual_list_ordered = [(0, 'Individual')] + individual_names(self.mpDB)
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])

        # Reset viewpoint selection to default, no need to reset list
        self.viewpoint_select.setCurrentIndex(0)

        # Reset unidentified and favorites checkboxes
        self.unidentified_only = False
        self.favorites_only = False
        self.no_roi_mids = False
        self.unidentified.setChecked(False)
        self.favorites.setChecked(False)
        self.no_roi.setChecked(False)

        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                        'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                        'active_station': self.station_list_ordered[self.station_select.currentIndex()],
                        'active_viewpoint': self.viewpoint_list_ordered[self.viewpoint_select.currentIndex()],
                        'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()],
                        'unidentified_only': self.unidentified_only,
                        'favorites_only': self.favorites_only,
                        'no_roi_mids': self.no_roi_mids}

        if prefilter:
            # TODO: Implement prefiltering for other filter types as needed
            if 'no_roi_mids' in prefilter.keys():
                self.no_roi_mids = prefilter['no_roi_mids']
                if self.no_roi_mids is not False:
                    self.no_roi.setChecked(True)
                else:
                    self.no_roi.setChecked(False)

            if 'unidentified_only' in prefilter.keys():
                self.unidentified_only = prefilter['unidentified_only']
                self.unidentified.setChecked(self.unidentified_only)
            if 'favorites_only' in prefilter.keys():
                self.favorites_only = prefilter['favorites_only']
                self.favorites.setChecked(self.favorites_only)
            if 'individual_id' in prefilter.keys():
                iid = prefilter['individual_id']
                if iid == 0:
                    # the "Unidentified" row in Manage Individuals
                    self.unidentified_only = True
                    self.unidentified.setChecked(True)
                else:
                    # individual_id is a database id; find its position in the list
                    position = next((i for i, (ind_id, _) in enumerate(self.individual_list_ordered)
                                     if ind_id == iid), 0)
                    self.filters['active_individual'] = self.individual_list_ordered[position]
                    self.individual_select.setCurrentIndex(position)

        self.region_select.blockSignals(False)
        self.survey_select.blockSignals(False)
        self.station_select.blockSignals(False)
        self.viewpoint_select.blockSignals(False)
        self.individual_select.blockSignals(False)
        self.unidentified.blockSignals(False)
        self.favorites.blockSignals(False)
        self.no_roi.blockSignals(False)

    def select_region(self):
        """Handle selection of a region from the region combobox."""
        self.filters['active_region'] = self.region_list_ordered[self.region_select.currentIndex()]
        self.filter_surveys()
        self.filter_stations(survey_ids=list(self.valid_surveys.items()))

    def select_survey(self):
        """Handle selection of a survey from the survey combobox."""
        self.filters['active_survey'] = self.survey_list_ordered[self.survey_select.currentIndex()]
        if self.survey_select.currentIndex() > 0:
            self.filter_stations(survey_ids=[self.filters['active_survey']])
        # back on the "Survey" placeholder: every survey of the active region, or all stations
        elif self.region_select.currentIndex() > 0:
            self.filter_stations(survey_ids=list(self.valid_surveys.items()))
        else:
            self.filter_stations()

    def select_station(self):
        """Handle selection of a station from the station combobox."""
        self.filters['active_station'] = self.station_list_ordered[self.station_select.currentIndex()]

    def select_viewpoint(self):
        """Handle selection of a viewpoint from the viewpoint combobox."""
        self.filters['active_viewpoint'] = self.viewpoint_list_ordered[self.viewpoint_select.currentIndex()]

    def select_individual(self):
        """Handle selection of an individual from the individual combobox."""
        self.filters['active_individual'] = self.individual_list_ordered[self.individual_select.currentIndex()]

    def select_unidentified(self):
        """Toggle the unidentified only filter."""
        self.unidentified_only = not self.unidentified_only

    def select_favorites(self):
        """Toggle the favorites only filter."""
        self.favorites_only = not self.favorites_only

    def select_no_roi(self):
        """Toggle the No ROI filter."""
        if self.no_roi.isChecked():
            self.no_roi_mids = media_without_rois(self.mpDB)
        else:
            self.no_roi_mids = False

    def filter_surveys(self):
        """Filter surveys based on active region"""
        # block signals while updating combobox
        self.survey_select.blockSignals(True)
        self.survey_select.clear()
        if self.region_select.currentIndex() > 0:
            # get surveys in selected region
            region_id = self.filters['active_region'][0]
            self.valid_surveys = dict(survey_names(self.mpDB, region_id=region_id))
        else:
            # get all surveys
            self.valid_surveys = dict(survey_names(self.mpDB))
        # Update survey list to reflect active region
        self.survey_list_ordered = [(0, 'Survey')] + list(self.valid_surveys.items())
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        self.survey_select.blockSignals(False)

    def filter_stations(self, survey_ids=None):
        """
        Filter stations based on active survey(s)

        survey_ids None means all stations; an empty list (a region without
        surveys) means none
        """
        # block signals while updating combobox
        self.station_select.blockSignals(True)
        self.station_select.clear()
        if survey_ids is None:
            self.valid_stations = dict(station_names(self.mpDB))
        else:
            self.valid_stations = dict(station_names(self.mpDB, survey_ids=[s[0] for s in survey_ids]))

        # Update station list to reflect active survey
        self.station_list_ordered = [(0, 'Station')] + list(self.valid_stations.items())
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
                        'favorites_only': self.favorites_only,
                        'no_roi_mids': self.no_roi_mids}
        return self.filters

    def get_valid_stations(self):
        """Return the currently valid stations based on the active survey(s)"""
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

    def no_roi_visible(self, visible: bool):
        """Set no ROI checkbox visibility"""
        self.no_roi.setVisible(visible)


class FilterBox(QComboBox):
    """Custom QComboBox for filter selections with fixed width."""

    def __init__(self, initial_list, width):
        super().__init__()
        self.setModel(QStandardItemModel())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedWidth(width)
        self.addItems([el[1] for el in initial_list])
