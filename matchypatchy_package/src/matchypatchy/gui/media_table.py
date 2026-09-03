"""
Widget for displaying list of Media
"""
import pandas as pd
from PyQt6.QtGui import QPixmap

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal, QAbstractTableModel

from matchypatchy.database.media import EditObject
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.database.location import fetch_stations
from matchypatchy.database.media import fetch_individual


class MediaTable(QAbstractTableModel):
    """Widget for displaying list of Media"""

    user_edit = pyqtSignal(EditObject)

    def __init__(self, parent, headers):
        super().__init__(parent)
        self.parent = parent
        self.cfg = parent.cfg
        self.mpDB = parent.mpDB
        self.thumbnail_dir = self.cfg.THUMBNAIL_DIR
        self.VIEWPOINTS = load_model('VIEWPOINTS')
        self.STATIONS = fetch_stations(self.mpDB, reset_index=True)
        self.updateIndividuals()

        self._data_filtered = pd.DataFrame()
        self.header_dict = headers
        self._columns = [x[0] for x in headers.values()]
        self._headers = [x[1] for x in headers.values()]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data_filtered)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers) if self._headers else 0

    def selectedRows(self):
        """Return a list of selected row indices based on the 'select' column."""
        return self._data_filtered.index[self._data_filtered['select'] == 1].tolist()

    def selectAll(self, select=True):
        """Select or deselect all rows based on the 'select' column."""
        self._data_filtered['select'] = 1 if select else 0
        self.layoutChanged.emit()

    def flags(self, index):
        """Return the item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        base_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

        # Checkbox
        if self._columns[index.column()] in ["select", "reviewed", "favorite"]:
            return base_flags | Qt.ItemFlag.ItemIsUserCheckable

        # Combobox
        if self._columns[index.column()] in ["viewpoint", "age", "sex"]:
            return base_flags | Qt.ItemFlag.ItemIsEditable 


        if self._columns[index.column()] in ["external_id", "comment"]:
            return base_flags | Qt.ItemFlag.ItemIsEditable

        return base_flags

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Only called for cells visible on the screen."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        #print(f"Accessing row {row}, column {col}")
        if self._columns[col] in ["select", "reviewed", "favorite"]:
            if role == Qt.ItemDataRole.CheckStateRole:
                return (
                    Qt.CheckState.Checked
                    if self._data_filtered.at[row, self._columns[col]]
                    else Qt.CheckState.Unchecked
                )
            # Suppress text display in the checkbox column
            if role == Qt.ItemDataRole.DisplayRole:
                return None

        # thumbnail
        if self._columns[col] == "thumbnail_path":
            if role == Qt.ItemDataRole.DecorationRole:
                thumbnail_path = self._data_filtered.at[row, self._columns[col]]
                if thumbnail_path:
                    pixmap = QPixmap(str(self.thumbnail_dir / thumbnail_path))
                    return pixmap
            # Suppress text display
            if role == Qt.ItemDataRole.DisplayRole:
                return None

        # station
        if self._columns[col] == "station_id":
            if role == Qt.ItemDataRole.DisplayRole:
                id = int(self._data_filtered.at[row, self._columns[col]])
                return self.STATIONS.loc[id, "name"]

        # viewpoint 
        if self._columns[col] == "viewpoint":
            if role == Qt.ItemDataRole.DisplayRole:
                value = str(self._data_filtered.at[row, self._columns[col]])
                return self.VIEWPOINTS.get(value, value)

        # individual
        if self._columns[col] == "individual_id":
            if role == Qt.ItemDataRole.DisplayRole:
                id = self._data_filtered.at[row, self._columns[col]]
                if id is not None:
                    return self.INDIVIDUALS.at[id, "name"]
                return str(id)

        if role == Qt.ItemDataRole.DisplayRole:
            # Return the raw data directly from your memory structure
            return str(self._data_filtered.at[row, self._columns[col]])

        return None   

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):

        if not index.isValid():
            return False

        col = index.column()
        row = index.row()
        reference = self._columns[col]

        # rois
        if "individual_id" in self._columns:
            rid = int(self._data_filtered.at[row, "id"])
            media_id = int(self._data_filtered.at[row, "media_id"])
        else:
            rid = None
            media_id = int(self._data_filtered.at[row, "id"])

        # Handle checkable columns (select, reviewed, favorite)
        if reference in ["select", "reviewed", "favorite"]:
            old_value = int(self._data_filtered.at[row, reference])
            new_value = int(value == Qt.CheckState.Checked.value)

        elif reference == 'viewpoint':
            old_value = self._data_filtered.at[row, reference]
            key = [k for k, v in self.VIEWPOINTS.items() if v == value][0]
            new_value = None if key == 'None' else int(key)

        elif reference in ['individual_id', 'sex', 'age']:
            iid = self._data_filtered.at[row, "individual_id"]
            if iid is None:
                return False
            old_value = self._data_filtered.at[row, reference]
            new_value = str(value)
            
        # Handle editable columns
        else:
            old_value = self._data_filtered.at[row, reference]
            new_value = value

        print(f"Row: {row}, Column: {col} ({reference})")
        print(f"Old value: {old_value}, New value: {new_value}")

        # update data
        self._data_filtered.at[row, reference] = new_value

        # create edit object
        edit = EditObject(rid=rid,
                          mid=media_id,
                          reference=reference,
                          previous_value=old_value,
                          new_value=new_value)

        self.user_edit.emit(edit)
        self.dataChanged.emit(index, index, [role])
        return True

    def receiveData(self, data, headers=None):
        """Receiver of loaded data from the FetchTableThread"""
        self._data_filtered = data
        if headers is not None:
            self.updateHeaderDict(headers)

        # Fetch and reset index for stations and individuals
        self.updateIndividuals()
        self.layoutChanged.emit()

    def updateHeaderDict(self, headers):
        if headers is not None:
            self.header_dict = headers
            self._columns = [x[0] for x in headers.values()]
            self._headers = [x[1] for x in headers.values()]

    def updateIndividuals(self):
        self.INDIVIDUALS = fetch_individual(self.mpDB)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Provide header data for the table view."""
        # column names
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        # row numbers
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
            
        return super().headerData(section, orientation, role)

    def sort(self, column, order):
        """Sorts the underlying Python data instantly."""
        if self._data_filtered.empty:
            return

        if column == 1: # do not sort by thumbnail
            return

        self.layoutAboutToBeChanged.emit()
        # Sort the python list in place
        ascending = order == Qt.SortOrder.AscendingOrder
        self._data_filtered.sort_values(by=self._columns[column], ascending=ascending, inplace=True)
        self._data_filtered.reset_index(inplace=True, drop=True)

        self.layoutChanged.emit()
