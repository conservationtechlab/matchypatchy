"""
GUI Window for viewing images
"""

from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QFrame)
from PyQt6.QtCore import Qt

from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_roi import ROIPopup


class DisplayMedia(QWidget):
    def __init__(self, parent, data_type=1):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        # 0 for Media, 1 for ROI
        self.data_type = data_type
        layout = QVBoxLayout()

        # First Layer ----------------------------------------------------------
        first_layer = QHBoxLayout()
        # Home Button
        first_layer.addSpacing(10)
        button_return = QPushButton("Home")
        button_return.clicked.connect(self.home)
        button_return.setFixedWidth(100)
        first_layer.addWidget(button_return, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        #Divider
        line = QFrame()
        line.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)
        line.setLineWidth(0)
        first_layer.addWidget(line)

        #Show Type
        first_layer.addWidget(QLabel("Show:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.show_type = QComboBox()
        self.show_type.addItems(["Full Images", "Crops Only"])
        self.show_type.setCurrentIndex(self.data_type)
        self.show_type.currentIndexChanged.connect(self.change_type)
        first_layer.addWidget(self.show_type, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Save
        button_save = QPushButton("Save")
        button_save.clicked.connect(self.save)
        button_save.setFixedWidth(100)
        first_layer.addWidget(button_save, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Undo
        button_undo = QPushButton("Undo")
        button_undo.clicked.connect(self.undo)
        button_undo.setFixedWidth(100)
        first_layer.addWidget(button_undo, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Divider
        line = QFrame()
        line.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)
        line.setLineWidth(0)
        first_layer.addWidget(line)

        # Select All
        self.button_select = QPushButton("Select All") 
        self.button_select.setCheckable(True)
        self.button_select.setChecked(False)
        self.button_select.clicked.connect(self.select_all)
        self.button_select.setFixedWidth(100)
        first_layer.addWidget(self.button_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Edit Rows
        self.button_edit = QPushButton("Edit Rows")
        self.button_edit.clicked.connect(self.edit_row_multiple)
        self.button_edit.setFixedWidth(100)
        self.button_edit.setEnabled(False)
        first_layer.addWidget(self.button_edit, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Duplicate
        self.button_duplicate = QPushButton("Duplicate Rows")
        self.button_duplicate.clicked.connect(self.duplicate)
        self.button_duplicate.setFixedWidth(100)
        self.button_duplicate.setEnabled(False)
        first_layer.addWidget(self.button_duplicate, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Delete
        self.button_delete = QPushButton("Delete Rows")
        self.button_delete.clicked.connect(self.delete)
        self.button_delete.setFixedWidth(100)
        self.button_delete.setEnabled(False)
        first_layer.addWidget(self.button_delete, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # FILTERS --------------------------------------------------------------
        second_layer = QHBoxLayout()
        second_layer.addSpacing(20)
        survey_label = QLabel("Filter:")
        survey_label.setFixedWidth(50)
        second_layer.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # REGION
        self.region_select = QComboBox()
        self.region_select.setFixedWidth(200)
        self.region_list_ordered = [(0, 'Region')] 
        self.region_select.addItems([el[1] for el in self.region_list_ordered])
        second_layer.addWidget(self.region_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # SURVEY
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        second_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.survey_list_ordered = [(0, 'Survey')]
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])
        # STATION
        self.station_select = QComboBox()
        self.station_select.setFixedWidth(200)
        second_layer.addWidget(self.station_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.valid_stations = None
        self.station_list_ordered = [(0, 'Station')]
        self.station_select.addItems([el[1] for el in self.station_list_ordered])
        # SPECIES
        self.species_select = QComboBox()
        self.species_select.setFixedWidth(200)
        second_layer.addWidget(self.species_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.species_list_ordered = [(0, 'Species')]
        self.species_select.addItems([el[1] for el in self.species_list_ordered])
        # INDIVIDUAL
        self.individual_select = QComboBox()
        self.individual_select.setFixedWidth(200)
        second_layer.addWidget(self.individual_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.individual_list_ordered = [(0, 'Individual')]
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])
        # UNIDENTIFIED
        unidentified = QPushButton("Unidentified")
        unidentified.setCheckable(True)
        unidentified.toggled.connect(self.select_unidentified)
        self.unidentified_only = False
        second_layer.addWidget(unidentified, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # FAVORITE
        favorites = QPushButton("Favorites")
        favorites.setCheckable(True)
        favorites.toggled.connect(self.select_favorites)
        self.favorites_only = False
        second_layer.addWidget(favorites, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        second_layer.addStretch()
        layout.addLayout(second_layer)

        # display rois or media
        self.media_table = MediaTable(self)
        layout.addWidget(self.media_table, stretch=1)
        self.setLayout(layout)

        self.region_select.currentIndexChanged.connect(self.select_region)
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        self.station_select.currentIndexChanged.connect(self.select_station)
        self.species_select.currentIndexChanged.connect(self.select_species)
        self.individual_select.currentIndexChanged.connect(self.select_individual)

        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                'active_station': self.station_list_ordered[self.station_select.currentIndex()],
                'active_species': self.species_list_ordered[self.species_select.currentIndex()],
                'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()],
                'unidentified_only': self.unidentified_only,
                'favorites_only': self.favorites_only}

    # Return Home Button
    def home(self):
        self.parent._set_base_view()

    # 1. RUN ON ENTRY
    def load_table(self):
        # check if there are rois first
        roi_n = self.mpDB.count('roi')
        media_n = self.mpDB.count('media')
        if self.data_type == 1 and roi_n == 0:
            self.data_type = 0
            dialog = AlertPopup(self, "No rois found, defaulting to full images.", title="Alert")
            if dialog.exec():
                del dialog
            self.show_type.setCurrentIndex(self.data_type)

        if self.data_type == 0 and media_n == 0:
            dialog = AlertPopup(self, "No images found! Please import media.", title="Alert")
            if dialog.exec():
                self.home()
                del dialog
            return False
        
        self.media_table.load_data(self.data_type)
        return True
        
    def refresh_filters(self, prefilter=None):
        """
        Update Dropdown Lists, Fill Filter Dict
        Allows refresh of dropdowns if re-entry into media view after updating database
        """
        # block signals while updating lists
        self.region_select.blockSignals(True)
        self.survey_select.blockSignals(True)
        self.station_select.blockSignals(True)
        self.species_select.blockSignals(True)
        self.individual_select.blockSignals(True)

        self.region_select.clear()
        self.region_list_ordered = [(0, 'Region')] + list(self.mpDB.select('region', columns='id, name'))
        self.region_select.addItems([el[1] for el in self.region_list_ordered])

        self.survey_select.clear()
        self.survey_list_ordered = [(0, 'Survey')] + list(self.mpDB.select('survey', columns='id, name'))
        self.survey_select.addItems([el[1] for el in self.survey_list_ordered])

        self.station_select.clear()
        self.valid_stations = dict(self.mpDB.select("station", columns="id, name"))
        self.station_list_ordered = [(0, 'Station')] + [(k, v) for k, v in self.valid_stations.items()]
        self.station_select.addItems([el[1] for el in self.station_list_ordered])

        self.species_select.clear()
        self.species_list_ordered = [(0, 'Species')] + list(self.mpDB.select('species', columns='id, common'))
        self.species_select.addItems([el[1] for el in self.species_list_ordered])

        self.individual_select.clear()
        self.individual_list_ordered = [(0, 'Individual')] + list(self.mpDB.select('individual', columns='id, name'))
        self.individual_select.addItems([el[1] for el in self.individual_list_ordered])
        
        self.filters = {'active_region': self.region_list_ordered[self.region_select.currentIndex()],
                        'active_survey': self.survey_list_ordered[self.survey_select.currentIndex()],
                        'active_station': self.station_list_ordered[self.station_select.currentIndex()],
                        'active_species': self.species_list_ordered[self.species_select.currentIndex()],
                        'active_individual': self.individual_list_ordered[self.individual_select.currentIndex()],
                        'unidentified_only': self.unidentified_only,
                        'favorites_only': self.favorites_only}

        print(prefilter)
        if prefilter:
            if 'individual_id' in prefilter.keys():
                self.filters['active_individual'] = self.individual_list_ordered[prefilter['individual_id']]
                self.individual_select.setCurrentIndex(prefilter['individual_id'])
            
            # TODO: update dropdowns

        print(self.filters)

        self.region_select.blockSignals(False)
        self.survey_select.blockSignals(False)
        self.station_select.blockSignals(False)
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

    def change_type(self):
        self.data_type = self.show_type.currentIndex()
        # reload table
        data_available = self.load_table()
        if data_available:
            self.load_thumbnails()

    def handle_table_change(self, row, column):
        """Slot to receive updates from QTableWidget"""
        item = self.media_table.table.item(row, column)
        if column == 0:
            self.check_selected_rows()
        print(row, column)

    def save(self):
        # Undo last edit
        self.media_table.save_changes()

    def undo(self):
        # Undo last edit
        self.media_table.undo()

    def edit_row(self, rid, crop):
        if crop:
            dialog = ROIPopup(self, rid)
            if dialog.exec():
                del dialog
        # media popup
        else:
            print('Media Edit not available')
            pass

    def edit_row_multiple(self):
        pass


    def select_all(self):
        for row in range(self.media_table.table.rowCount()):
            self.media_table.select_row(row, overwrite=self.button_select.isChecked())

    def check_selected_rows(self):
        self.selected_rows = self.media_table.selectedRows()
        print("Selected rows:", self.selected_rows)
        if len(self.selected_rows) > 0:
            self.button_edit.setEnabled(True)
            self.button_duplicate.setEnabled(True)
            self.button_delete.setEnabled(True)
        else:
            self.button_edit.setEnabled(False)
            self.button_duplicate.setEnabled(False)
            self.button_delete.setEnabled(False)

    def duplicate(self): 
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"Are you sure you want to duplicate {len(self.selected_rows)} files?", title="Warning")
            if dialog.exec():
                # TODO
                del dialog
     
    def delete(self):
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"""Are you sure you want to delete {len(self.selected_rows)} files? This cannot be undone.""", title="Warning")
            if dialog.exec():
                # TODO
                del dialog

    # Filters ------------------------------------------------------------------
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
        self.filter_stations(survey_ids=list(self.valid_surveys.items()))
        self.filter_table()

    def select_survey(self):
        self.filters['active_survey'] = self.survey_list_ordered[self.survey_select.currentIndex()]
        if self.survey_select.currentIndex() == 0:
            self.filter_stations()
        else:
            self.filter_stations(survey_ids=[self.filters['active_survey']])

        self.filter_table()

    def select_station(self):
        self.filters['active_station'] = self.station_list_ordered[self.station_select.currentIndex()]
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

    def filter_stations(self, survey_ids=None):
        # block signals while updating combobox
        self.station_select.blockSignals(True)
        self.station_select.clear()
        print(survey_ids)
        if survey_ids:
            survey_list = ",".join([str(s[0]) for s in survey_ids])
            selection = f'survey_id IN ({survey_list})'

            self.valid_stations = dict(self.mpDB.select("station", columns="id, name", row_cond=selection, quiet=False))
        else:
            self.valid_stations = dict(self.mpDB.select("station", columns="id, name"))
        # Update station list to reflect active survey
        self.station_list_ordered = [(0, 'Station')] + [(k, v) for k, v in self.valid_stations.items()]
        self.station_select.addItems([el[1] for el in self.station_list_ordered])
        self.station_select.blockSignals(False)        

