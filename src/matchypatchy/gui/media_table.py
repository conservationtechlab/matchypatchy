"""
Widget for displaying list of Media
"""
import pandas as pd
from PyQt6.QtGui import QPixmap, QPixmapCache

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal, QAbstractTableModel

from matchypatchy.database.media import EditObject
from matchypatchy.database.thumbnails import THUMBNAIL_SIZE
from matchypatchy.threads.model_download_thread import load_model
from matchypatchy.database.location import fetch_stations, fetch_cameras
from matchypatchy.database.media import fetch_individual
from matchypatchy.project import UsesProject


class MediaTable(UsesProject, QAbstractTableModel):
    """Widget for displaying list of Media"""

    THUMBNAIL_CACHE_KB = 64 * 1024  # about 400 thumbnails at 200px
    ORDER_COLUMN = "_row_order"  # position each row arrived in, not shown

    user_edit = pyqtSignal(EditObject)

    def __init__(self, parent, headers):
        super().__init__(parent)
        self.parent = parent
        self.project = parent.project
        self.VIEWPOINTS = load_model('VIEWPOINTS')
        self.INDIVIDUALS = fetch_individual(self.mpDB)
        self.STATIONS = fetch_stations(self.mpDB, reset_index=True)
        self.CAMERAS = fetch_cameras(self.mpDB, reset_index=True)

        self.project.data_changed.connect(self.names_written)
        # room for a few screens of thumbnails, Qt's default 10MB holds about 60
        QPixmapCache.setCacheLimit(self.THUMBNAIL_CACHE_KB)

        self._data_filtered = pd.DataFrame()
        self.header_dict = headers
        self._columns = [x[0] for x in headers.values()]
        self._headers = [x[1] for x in headers.values()]

    def names_written(self, table):
        """
        Reload the individual, station and camera names after one of them is written

        Connected to project.data_changed in __init__, so renamed or new names
        show without reloading the table.
        """
        lookups = {"individual": ("INDIVIDUALS", fetch_individual),
                   "station": ("STATIONS", lambda db: fetch_stations(db, reset_index=True)),
                   "camera": ("CAMERAS", lambda db: fetch_cameras(db, reset_index=True))}
        if table not in lookups:
            return
        name, fetch = lookups[table]
        setattr(self, name, fetch(self.mpDB))
        self.layoutChanged.emit()

    def _thumbnail(self, path):
        """
        Thumbnail at THUMBNAIL_SIZE, from the pixmap cache once it has been loaded

        Called by data() for the thumbnail column, which runs on every repaint and
        used to read the file from disk each time. Kept out of data() for the cache
        and the scaling: thumbnails saved before THUMBNAIL_SIZE went from 150 to 200px
        are stretched to fill the row like new ones. QPixmapCache drops the least
        recently used pixmaps, so scrolling a large project doesn't hold them all.
        """
        pixmap = QPixmapCache.find(path)
        if pixmap is None:
            pixmap = QPixmap(path)
            if not pixmap.isNull() and max(pixmap.width(), pixmap.height()) < THUMBNAIL_SIZE:
                pixmap = pixmap.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                                       Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            QPixmapCache.insert(path, pixmap)
        return pixmap

    def rowCount(self, parent=QModelIndex()):
        return len(self._data_filtered)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers) if self._headers else 0

    def selectedRows(self):
        """Return a list of selected row indices based on the 'select' column."""
        return self._data_filtered.index[self._data_filtered['select'] == 1].tolist()

    def selectedIds(self):
        """Return the ids (roi or media) of rows ticked in the 'select' column."""
        if self._data_filtered.empty or 'id' not in self._data_filtered.columns:
            return []
        return self._data_filtered.loc[self._data_filtered['select'] == 1, 'id'].tolist()

    def selectAll(self, select=True):
        """Select or deselect all rows based on the 'select' column."""
        self._data_filtered['select'] = 1 if select else 0
        self.layoutChanged.emit()

    def flags(self, index):
        """Return the item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        # add bounds checking for column index
        col = index.column()
        if col < 0 or col >= len(self._columns):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        base_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

        # Checkbox
        if self._columns[index.column()] in ["select", "reviewed", "favorite"]:
            return base_flags | Qt.ItemFlag.ItemIsUserCheckable

        # Combobox
        if self._columns[index.column()] in ["viewpoint", "sex"]:
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

        # Add bounds checking
        if col < 0 or col >= len(self._columns):
            return None

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
                    return self._thumbnail(str(self.cfg.THUMBNAIL_DIR / thumbnail_path))
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

        # camera
        if self._columns[col] == "camera_id":
            if role == Qt.ItemDataRole.DisplayRole:
                camera_id = self._data_filtered.at[row, self._columns[col]]
                if pd.isna(camera_id):
                    return None
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
                if pd.isna(iid):
                    return None
                try:
                    name = self.INDIVIDUALS.at[iid, "name"]
                except KeyError:
                    name = None
                return name

        # sex, shown as Unknown for identified rois without one
        if self._columns[col] == "sex":
            if role == Qt.ItemDataRole.DisplayRole:
                value = self._data_filtered.at[row, self._columns[col]]
                if pd.isna(value):
                    iid = self._data_filtered.at[row, "individual_id"]
                    return None if pd.isna(iid) else 'Unknown'
                return str(value)

        # roi count, clicked to show those rois
        if self._columns[col] == "roi_count" and self._data_filtered.at[row, "roi_count"]:
            if role == Qt.ItemDataRole.ToolTipRole:
                return "Click to show these ROIs"

        if role == Qt.ItemDataRole.DisplayRole:
            # Return the raw data directly from your memory structure
            if pd.isna(self._data_filtered.at[row, self._columns[col]]):
                return None
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

        elif reference in ['individual_id', 'sex']:
            iid = self._data_filtered.at[row, "individual_id"]
            if iid is None:
                return False
            old_value = self._data_filtered.at[row, reference]
            new_value = str(value)
            # Unknown sex is stored as NULL ('None' from older versions too)
            if reference == 'sex' and new_value in ('Unknown', 'None'):
                new_value = None
            
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

    def receiveData(self, data, headers=None, selected_ids=None):
        """
        Receiver of loaded data from the FetchTableThread

        selected_ids re-ticks rows by id, since row positions change when the
        data is re-filtered or re-sorted
        """
        # remember the order rows arrived in, to go back to when sorting is turned off
        self._data_filtered = data.assign(**{self.ORDER_COLUMN: range(len(data))})
        if headers is not None:
            self.updateHeaderDict(headers)

        if selected_ids is not None and 'id' in self._data_filtered.columns:
            self._data_filtered['select'] = self._data_filtered['id'].isin(selected_ids).astype(int)

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
        """
        Sorts the underlying data; None/NaN are treated as the smallest value.

        column -1 comes from the view when the sort indicator is cleared,
        and puts the rows back in the order they arrived in.
        """
        if self._data_filtered.empty:
            return

        if column < 0:
            if self.ORDER_COLUMN in self._data_filtered.columns:
                self.layoutAboutToBeChanged.emit()
                self._data_filtered = self._data_filtered.sort_values(self.ORDER_COLUMN).reset_index(drop=True)
                self.layoutChanged.emit()
            return

        if column >= len(self._columns):
            return

        if column == 1: # do not sort by thumbnail
            return

        col_name = self._columns[column]
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
