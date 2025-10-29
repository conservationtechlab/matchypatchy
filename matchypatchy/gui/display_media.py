"""
GUI Window for viewing images
"""
import pandas as pd
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QDialog)
from PyQt6.QtCore import Qt

from matchypatchy.database.media import IMAGE_EXT

from matchypatchy.gui.media_table import MediaTable
from matchypatchy.gui.popup_alert import AlertPopup
from matchypatchy.gui.popup_media_edit import MediaEditPopup
from matchypatchy.gui.gui_assets import VerticalSeparator, StandardButton
from matchypatchy.gui.widget_filterbar import FilterBar


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
        button_return = StandardButton("Home")
        button_return.clicked.connect(self.home)
        first_layer.addWidget(button_return, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        button_match = StandardButton("Match")
        button_match.clicked.connect(self.match)
        first_layer.addWidget(button_match, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Divider
        first_layer.addWidget(VerticalSeparator())
        # Show Type
        first_layer.addWidget(QLabel("Show:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.show_type = QComboBox()
        self.show_type.addItems(["Full Images", "ROIs Only"])
        self.show_type.setCurrentIndex(self.data_type)
        self.show_type.currentIndexChanged.connect(self.change_type)
        first_layer.addWidget(self.show_type, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Divider
        first_layer.addWidget(VerticalSeparator())

        # Select All
        self.button_select = StandardButton("Select All")
        self.button_select.setCheckable(True)
        self.button_select.setChecked(False)
        self.button_select.clicked.connect(self.select_all)
        first_layer.addWidget(self.button_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Edit Rows
        self.button_edit = StandardButton("Edit Rows")
        self.button_edit.clicked.connect(self.edit_row_multiple)
        self.button_edit.setEnabled(False)
        first_layer.addWidget(self.button_edit, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Duplicate
        self.button_duplicate = StandardButton("Duplicate Rows")
        self.button_duplicate.clicked.connect(self.duplicate)
        self.button_duplicate.setEnabled(False)
        first_layer.addWidget(self.button_duplicate, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Delete
        self.button_delete = StandardButton("Delete Rows")
        self.button_delete.clicked.connect(self.delete)
        self.button_delete.setEnabled(False)
        first_layer.addWidget(self.button_delete, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # Save
        first_layer.addWidget(VerticalSeparator())
        button_save = StandardButton("Save")
        button_save.clicked.connect(self.save)
        first_layer.addWidget(button_save, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Undo
        self.button_undo = StandardButton("Undo")
        self.button_undo.clicked.connect(self.undo)
        self.button_undo.setEnabled(False)
        first_layer.addWidget(self.button_undo, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()

        layout.addLayout(first_layer)


        # FILTERS --------------------------------------------------------------
        second_layer = QHBoxLayout()
        second_layer.addSpacing(20)

        self.filterbar = FilterBar(self, 200)
        second_layer.addWidget(self.filterbar, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.filters = self.filterbar.get_filters()  # get initial filters

        button_filter = QPushButton("Filter Images")
        button_filter.clicked.connect(self.filter_table)
        second_layer.addWidget(button_filter)

        second_layer.addStretch()
        layout.addLayout(second_layer)

        # display rois or media
        self.media_table = MediaTable(self)
        layout.addWidget(self.media_table, stretch=1)
        self.setLayout(layout)


    # Return Home Button
    def home(self):
        if len(self.media_table.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="There are unsaved changes. Are you sure you want to return home?")
            if dialog.exec():
                self.parent._set_base_view()
                del dialog
            else:
                return
        # stop thumbnail loader thread and unlock db
        if self.media_table.image_loader_thread is not None and self.media_table.image_loader_thread.isRunning():
            self.media_table.image_loader_thread.requestInterruption()
            self.media_table.image_loader_thread.wait()
            self.media_table.loading_bar.close()
            self.parent._set_base_view()
        else:
            self.parent._set_base_view()

    # Move to Match View
    def match(self):
        if len(self.media_table.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="There are unsaved changes. Please save before matching.")
            if dialog.exec():
                del dialog
            return
        self.parent._set_compare_view()

    # FILTERS ------------------------------------------------------------------
    def refresh_filters(self, prefilter=None):
        """
        Update Dropdown Lists, Fill Filter Dict
        Allows refresh of dropdowns if re-entry into media view after updating database
        """
        # wipe previous selections
        self.select_all(reset=True)

        self.filterbar.refresh_filters(prefilter=prefilter)
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()
        print(self.filters)


    def filter_table(self):
        """
        Filter the media table based on the selected options
        Run after any setting is changed and filter button is pressed
        """
        self.filters = self.filterbar.get_filters()
        self.valid_stations = self.filterbar.get_valid_stations()
        self.media_table.filter()


    # 1. RUN ON ENTRY
    def load_table(self):
        # check if there are rois first
        roi_n = self.mpDB.count('roi')
        media_n = self.mpDB.count('media')

        if media_n == 0:
            dialog = AlertPopup(self, "No images found! Please import media.", title="Alert")
            if dialog.exec():
                self.home()
                del dialog
            return False

        else:
            if self.data_type == 1 and roi_n == 0:
                self.data_type = 0
                dialog = AlertPopup(self, "No rois found, defaulting to full images.", title="Alert")
                if dialog.exec():
                    del dialog
                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)

            self.media_table.load_data(self.data_type)
            return True


    # 2. RUN ON ENTRY
    def load_thumbnails(self):
        """
        Load Thumbnails

        Only run if self.media_table.load_data() returns true
        self.media_table.load_images() will trigger a self filter
        and a self refresh upon completion
        """
        self.media_table.load_images()

    def change_type(self):
        if len(self.media_table.edit_stack) > 0:
            dialog = AlertPopup(self, prompt="There are unsaved changes. Are you sure you want to change view?")
            cont = dialog.exec()
            del dialog
            if cont == QDialog.DialogCode.Rejected:
                self.show_type.blockSignals(True)
                self.show_type.setCurrentIndex(self.data_type)
                self.show_type.blockSignals(False)
                return

        self.data_type = self.show_type.currentIndex()
        # reload table
        data_available = self.load_table()
        if data_available:
            self.load_thumbnails()
        # Disable "Edit Rows" if not in ROI mode
        self.update_buttons()

    def handle_table_change(self, edit):
        """Slot to receive updates from QTableWidget"""
        row = edit[0]
        column = edit[1]
        item = self.media_table.table.item(row, column)
        if column == 0:
            self.check_selected_rows()
        self.check_undo_button()

    def save(self):
        # Undo last edit
        self.media_table.save_changes()
        self.check_undo_button()

    def undo(self):
        # Undo last edit
        self.media_table.undo()
        self.check_undo_button()

    def check_undo_button(self):
        if len(self.media_table.edit_stack) > 0:
            self.button_undo.setEnabled(True)
        else:
            self.button_undo.setEnabled(False)

    def update_buttons(self):
        has_selection = len(self.media_table.selectedRows()) > 0
        # Only allow edit in ROI mode
        self.button_edit.setEnabled(has_selection)
        #self.button_duplicate.setEnabled(has_selection)
        self.button_delete.setEnabled(has_selection)

    def edit_row(self, row):
        # EDIT ROI
        ext = self.media_table.data_filtered.at[row, "ext"]
        if self.data_type == 1:
            if ext in IMAGE_EXT:
                # only show single roi
                data = self.media_table.data_filtered.iloc[[row]]
                current_image_index = 0
            else: 
                # TODO Only show multiple frames if selected
                # display frames as well as video
                mid = int(self.media_table.data_filtered.at[row, "media_id"])
                data = self.media_table.data_filtered[self.media_table.data_filtered['media_id'] == mid]
                current_image_index = data.index.get_loc(row) + 1  # account for video row
                video_row = data.iloc[[0]].copy()
                for col in video_row.columns:
                    # clear columns so row registers as video
                    if col in ['frame', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']:
                        video_row.at[video_row.index[0], col] = None
                data = pd.concat([video_row, data], ignore_index=True)           
        else:
            # full image mode/video only mode
            data = self.media_table.data_filtered.iloc[[row]]
            current_image_index = 0
    
        dialog = MediaEditPopup(self, data, self.data_type, current_image_index=current_image_index)
        if dialog.exec():
            edit_stack = dialog.get_edit_stack()
            del dialog

            if edit_stack:
                edit_stack = self.media_table.transpose_edit_stack(edit_stack)
                self.check_undo_button()

                # if changes made, reload table
                data_available = self.load_table()
                if data_available:
                    self.load_thumbnails()

    def edit_row_multiple(self):
        selected_rows = self.media_table.selectedRows()
        data = self.media_table.data_filtered.iloc[selected_rows]
        current_image_index = 0

        dialog = MediaEditPopup(self, data, self.data_type, current_image_index=current_image_index)
        if dialog.exec():
            edit_stack = dialog.get_edit_stack()
            edit_stack = self.media_table.transpose_edit_stack(edit_stack)
            self.check_undo_button()
            del dialog
            # reload data
            data_available = self.load_table()
            if data_available:
                self.load_thumbnails()
        self.update_buttons()

    def select_all(self, reset=False):
        if reset:
            for row in range(self.media_table.table.rowCount()):
                self.media_table.select_row(row, overwrite=False)
        else:  #toggle based on select all button
            for row in range(self.media_table.table.rowCount()):
                self.media_table.select_row(row, overwrite=self.button_select.isChecked())

    def check_selected_rows(self):
        self.selected_rows = self.media_table.selectedRows()
        if len(self.selected_rows) > 0:
            self.button_edit.setEnabled(True)
            #self.button_duplicate.setEnabled(True)
            self.button_delete.setEnabled(True)
        else:
            self.button_edit.setEnabled(False)
            self.button_duplicate.setEnabled(False)
            self.button_delete.setEnabled(False)

    def duplicate(self):
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"Are you sure you want to duplicate {len(self.selected_rows)} files?", title="Warning")
            if dialog.exec():
                for row in self.selected_rows:
                    if self.data_type == 1:
                        id = int(self.media_table.data_filtered.at[row, "media_id"])
                        self.mpDB.copy("media", id)
                    else:
                        id = int(self.media_table.data_filtered.at[row, "id"])
                        self.mpDB.copy("media", id)
                del dialog

    def delete(self):
        if len(self.selected_rows) > 0:
            dialog = AlertPopup(self, f"""Are you sure you want to delete {len(self.selected_rows)} files? This cannot be undone.""", title="Warning")
            if dialog.exec():
                for row in self.selected_rows:
                    if self.data_type == 0:
                        id = int(self.media_table.data_filtered.at[row, "media_id"])
                        rois = self.media_table.data[self.media_table.data['media_id'] == id]
                        self.mpDB.delete('media', f'id={id}')
                        for i, row in rois.iterrows():
                            self.mpDB.delete('roi', f"id={row['id']}")
                    else:
                        id = int(self.media_table.data_filtered.at[row, "id"])
                        self.mpDB.delete('roi', f'id={id}')
                del dialog
                # Clear selection and update UI
                self.media_table.table.clearSelection()
                self.update_buttons()
                # Reload updated data and thumbnails
                data_available = self.load_table()
                if data_available:
                    self.load_thumbnails()
