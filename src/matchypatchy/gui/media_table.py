"""
Widget for displaying list of Media
"""
import pandas as pd
from PyQt6.QtGui import QPixmap

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal, QAbstractTableModel

from matchypatchy.database.media import EditObject
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.database.location import fetch_stations, fetch_cameras
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
        self.INDIVIDUALS = fetch_individual(self.mpDB)
        self.STATIONS = fetch_stations(self.mpDB, reset_index=True)
        self.CAMERAS = fetch_cameras(self.mpDB, reset_index=True)

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
                if isinstance(thumbnail_path, str) and thumbnail_path:
                    pixmap = QPixmap(str(self.thumbnail_dir / thumbnail_path))
                    return pixmap
            # Suppress text display
            if role == Qt.ItemDataRole.DisplayRole:
                return None

        # station
        if self._columns[col] == "station_id":
            if role == Qt.ItemDataRole.DisplayRole:
                station_id = int(self._data_filtered.at[row, self._columns[col]])
                try:
                    name = self.STATIONS.loc[station_id, "name"]
                except KeyError:
                    name = None
                return name

        # station
        if self._columns[col] == "camera_id":
            if role == Qt.ItemDataRole.DisplayRole:
                camera_id = self._data_filtered.at[row, self._columns[col]]
                try:
                    name = self.CAMERAS.loc[int(camera_id), "name"]
                except KeyError:
                    name = None
                return name

        # viewpoint 
        if self._columns[col] == "viewpoint":
            if role == Qt.ItemDataRole.DisplayRole:
                value = self._data_filtered.at[row, self._columns[col]]
                value = str(value) if not pd.isna(value) else 'None'
                return self.VIEWPOINTS.get(value, value)

        # individual
        if self._columns[col] == "individual_id":
            if role == Qt.ItemDataRole.DisplayRole:
                iid = self._data_filtered.at[row, self._columns[col]]
                try:
                    name = self.INDIVIDUALS.at[iid, "name"]
                except KeyError:
                    name = str(iid)
                return name

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
            print(f"Key for {value}: {key}")
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

    def receiveData(self, data, headers=None, selected_rows=None):
        """Receiver of loaded data from the FetchTableThread"""
        self._data_filtered = data
        if headers is not None:
            self.updateHeaderDict(headers)

        if selected_rows is not None:
            self._data_filtered['select'] = 0
            self._data_filtered.loc[selected_rows, 'select'] = 1

        # Fetch and reset index for stations and individuals
        self.INDIVIDUALS = fetch_individual(self.mpDB)
        self.STATIONS = fetch_stations(self.mpDB, reset_index=True)
        self.CAMERAS = fetch_cameras(self.mpDB, reset_index=True)
        self.layoutChanged.emit()

    def updateHeaderDict(self, headers):
        if headers is not None:
            self.header_dict = headers
            self._columns = [x[0] for x in headers.values()]
            self._headers = [x[1] for x in headers.values()]

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
        """Sorts the underlying data; None/NaN are treated as the smallest value."""
        if self._data_filtered.empty:
            return

        col_name = self._columns[column]
        if col_name == "thumbnail_path":  # do not sort by thumbnail
            return

        ascending = order == Qt.SortOrder.AscendingOrder

        self.layoutAboutToBeChanged.emit()
        try:
            self._data_filtered = self._data_filtered.sort_values(
                by=col_name,
                ascending=ascending,
                key=self._sort_key,
                # None acts as the lowest value: first when ascending, last when descending
                na_position="first" if ascending else "last",
                kind="mergesort",).reset_index(drop=True)
        except Exception as e:
            print(f"Sort failed on column {col_name}: {e}")
        finally:
            self.layoutChanged.emit()

    def _sort_key(self, series):
        """Key function for sort_values: maps IDs to displayed names, handles None/NaN,
        and avoids mixed-type comparisons."""
        name = series.name

        # Sort by what the user actually sees for lookup columns
        if name == "station_id":
            series = series.map(lambda v: self.STATIONS["name"].get(int(v)) if pd.notna(v) else None)
        elif name == "camera_id":
            series = series.map(lambda v: self.CAMERAS["name"].get(int(v)) if pd.notna(v) else None)
        elif name == "individual_id":
            series = series.map(lambda v: self.INDIVIDUALS["name"].get(v, str(v)) if pd.notna(v) else None)
        elif name == "viewpoint":
            series = series.map(lambda v: self.VIEWPOINTS.get(str(v), str(v)) if pd.notna(v) else None)

        # Numeric column (ignoring nulls)? Sort numerically.
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() == series.notna().sum():
            return numeric

        # Otherwise compare everything as lowercase strings, keeping nulls as nulls
        return series.map(lambda v: None if pd.isna(v) else str(v).lower())
