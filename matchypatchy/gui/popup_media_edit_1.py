import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QDialogButtonBox, QFrame, QTextEdit)
from PyQt6.QtCore import Qt
from matchypatchy.algo.models import load

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPixmap
import matchypatchy.database.media as db_roi
from matchypatchy.gui.widget_image import ImageWidget
from matchypatchy.database.location import fetch_station_names_from_id


class MediaEditPopup(QDialog):
    def __init__(self, parent, roi_id):
        super().__init__(parent)
        self.setWindowTitle("Edit ROI Metadata")
        self.setFixedSize(900, 500)
        self.mpDB = parent.mpDB
        self.rid = roi_id

        # Load data
        self.data = self.load()
        self.individuals = []
        self.VIEWPOINTS = load('VIEWPOINTS')

        # Layout
        main_layout = QVBoxLayout()

        # Top row with filepath
        top = QHBoxLayout()
        top.addWidget(QLabel(self.data.at[0, "filepath"]), alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(top)

        # Image and Metadata
        content = QHBoxLayout()

        # Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.load(image_path=self.data.at[0, "filepath"],
                        bbox=db_roi.get_bbox(self.data.iloc[0]), crop=False)
        self.image.setFixedSize(500, 350)
        content.addWidget(self.image)

        # Metadata panel
        info_layout = QVBoxLayout()
        gap = 80

        def add_meta_row(label_text, value):
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(gap)
            row.addWidget(label)
            row.addWidget(QLabel(str(value)))
            info_layout.addLayout(row)

        survey_info = fetch_station_names_from_id(self.mpDB, self.data.at[0, "station_id"])
        add_meta_row("Timestamp:", self.data.at[0, "timestamp"])
        add_meta_row("Station:", survey_info["station_name"])
        add_meta_row("Survey:", survey_info["survey_name"])
        add_meta_row("Region:", survey_info["region_name"])
        add_meta_row("Sequence ID:", self.data.at[0, "sequence_id"])
        add_meta_row("External ID:", self.data.at[0, "external_id"])

        info_layout.addSpacing(10)
        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        info_layout.addWidget(line)

        # Editable: Name
        name_row = QHBoxLayout()
        name_label = QLabel("Name:")
        name_label.setFixedWidth(gap)
        self.name = QComboBox()
        self.refresh_names()
        self.name.currentIndexChanged.connect(self.change_name)
        name_row.addWidget(name_label)
        name_row.addWidget(self.name)
        info_layout.addLayout(name_row)

        # Editable: Sex
        sex_row = QHBoxLayout()
        sex_label = QLabel("Sex:")
        sex_label.setFixedWidth(gap)
        self.sex = QComboBox()
        self.sex.addItems(["Unknown", "Male", "Female"])
        self.sex.currentIndexChanged.connect(self.change_sex)
        sex_row.addWidget(sex_label)
        sex_row.addWidget(self.sex)
        info_layout.addLayout(sex_row)

        # Editable: Viewpoint
        vp_row = QHBoxLayout()
        vp_label = QLabel("Viewpoint:")
        vp_label.setFixedWidth(gap)
        self.viewpoint = QComboBox()
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])  # skip 'Any'
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)
        vp_row.addWidget(vp_label)
        vp_row.addWidget(self.viewpoint)
        info_layout.addLayout(vp_row)

        content.addLayout(info_layout)
        main_layout.addLayout(content)

        # OK / Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)
        self.refresh_values()

    def load(self):
        data, cols = self.mpDB.all_media(row_cond=f"roi.id={self.rid}")
        return pd.DataFrame(data, columns=cols).replace({float('nan'): None}).reset_index(drop=True)

    def refresh_names(self):
        self.individuals = [(0, 'Unknown', 'Unknown')] + self.mpDB.select("individual", "id, name, sex")
        self.name.blockSignals(True)
        self.name.clear()
        self.name.addItems([ind[1] for ind in self.individuals])
        self.name.blockSignals(False)

    def refresh_values(self):
        # Name
        iid = self.data.at[0, "individual_id"]
        if iid is None:
            self.name.setCurrentIndex(0)
            self.sex.setDisabled(True)
        else:
            self.name.setCurrentIndex(iid)
            self.sex.setDisabled(False)

        # Sex
        current_sex = self.data.at[0, "sex"]
        if current_sex is None:
            self.sex.setCurrentIndex(0)
        else:
            self.sex.setCurrentIndex(self.sex.findText(str(current_sex)))

        # Viewpoint
        vp_val = str(self.data.at[0, "viewpoint"])
        vp_display = self.VIEWPOINTS.get(vp_val, "None")
        self.viewpoint.setCurrentIndex(self.viewpoint.findText(vp_display))

    def change_name(self):
        selected = self.individuals[self.name.currentIndex()]
        iid = selected[0]
        self.mpDB.edit_row("roi", self.rid, {"individual_id": iid})
        self.sex.setDisabled(iid == 0)
        self.sex.setCurrentIndex(self.sex.findText(selected[2]) if iid > 0 else 0)

    def change_sex(self):
        iid = self.individuals[self.name.currentIndex()][0]
        sex = self.sex.currentText()
        if iid > 0:
            self.mpDB.edit_row("individual", iid, {"sex": f"'{sex}'"})

    def change_viewpoint(self):
        keys = list(self.VIEWPOINTS.keys())
        selected = keys[self.viewpoint.currentIndex() + 1]  # skip 'Any'
        self.mpDB.edit_row("roi", self.rid, {"viewpoint": "NULL" if selected == "None" else int(selected)})
