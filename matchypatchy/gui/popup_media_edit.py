import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt
from matchypatchy.algo.models import load

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPixmap



class MediaEditPopup(QDialog):
    def __init__(self, parent, ids):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Batch Edit ROI Viewpoint")
        self.setFixedSize(900, 600)
        self.mpDB = parent.mpDB
        self.ids = ids  # List of ROI IDs
        self.data = self.load_selected_media()
        self.current_image_index = 0


        # Load Viewpoint options
        self.VIEWPOINTS = load('VIEWPOINTS')

        # Layout
        layout = QVBoxLayout()

        # Title
        title = QLabel("Batch Edit ROI Viewpoint")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Image Display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(400)  # Adjust height as needed
        layout.addWidget(self.image_label)

        # Navigation Buttons
        img_nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.show_previous_image)
        self.next_btn.clicked.connect(self.show_next_image)
        img_nav_layout.addWidget(self.prev_btn)
        img_nav_layout.addWidget(self.next_btn)
        layout.addLayout(img_nav_layout)

        # Show the first image
        self.update_image()

        # Viewpoint Selection
        viewpoint_layout = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(80)
        viewpoint_layout.addWidget(viewpoint_label)

        self.viewpoint = QComboBox()
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])  # Skip 'any'
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)
        viewpoint_layout.addWidget(self.viewpoint)

        layout.addLayout(viewpoint_layout)

        # Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

        # Set the current viewpoint for selected ROIs
        self.refresh_viewpoint()

    def load_selected_media(self):
        """
        Fetch `roi` data for the selected ROI IDs.
        """
        ids_str = ', '.join(map(str, self.ids))  # Convert list of IDs to a comma-separated string

        # Query `roi` table and join with `media` to get file paths
        data = self.mpDB.select(
            table="roi JOIN media ON roi.media_id = media.id",
            columns="roi.id AS roi_id, media.filepath, roi.viewpoint",
            row_cond=f"roi.id IN ({ids_str})"
        )

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=["roi_id", "filepath", "viewpoint"]).replace({float('nan'): None}).reset_index(drop=True)
        print(df)
        print(df.columns)
        return df
    
    def update_image(self):
        if not self.data.empty:
            filepath = self.data.iloc[self.current_image_index]["filepath"]
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(400, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled)
            else:
                self.image_label.setText(f"Could not load image: {filepath}")
        else:
            self.image_label.setText("No image selected.")
        #Enable/disable buttons based on current index
        self.prev_btn.setEnabled(self.current_image_index > 0)
        self.next_btn.setEnabled(self.current_image_index < len(self.data) - 1)


    def show_next_image(self):
        if self.current_image_index < len(self.data) - 1:
            self.current_image_index += 1
            self.update_image()

    def show_previous_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.update_image()


    def refresh_viewpoint(self):
        """
        Set the dropdown to the most common viewpoint among selected ROIs.
        """
        viewpoints = self.data["viewpoint"].astype(str).unique()
        most_common = viewpoints[0] if len(viewpoints) == 1 else "Multiple"
        print(self.VIEWPOINTS)
        '''
        {'Any': 'Any', 'None': 'None', '0': 'Left', '1': 'Right'}
        '''
        
         # If viewpoint is None, set index to 0 (default to 'None' in dropdown)
        if most_common == "None" or most_common not in self.VIEWPOINTS:
            self.viewpoint.setCurrentIndex(0)
        else:
            self.viewpoint.setCurrentIndex(self.viewpoint.findText(self.VIEWPOINTS.get(most_common, "None")))

    def change_viewpoint(self):
        """
        Update `viewpoint` for all selected ROIs.
        """
        viewpoint_keys = list(self.VIEWPOINTS.keys())
        selected_viewpoint_key = viewpoint_keys[self.viewpoint.currentIndex() + 1]  # Adjust for 'any' skipping

        for _, row in self.data.iterrows():
            roi_id = row["roi_id"]
            if selected_viewpoint_key == 'None':
                self.mpDB.edit_row('roi', roi_id, {"viewpoint": "NULL"}, quiet=False)
                new_viewpoint = None
            else:
                self.mpDB.edit_row('roi', roi_id, {"viewpoint": int(selected_viewpoint_key)}, quiet=False)
                new_viewpoint = int(selected_viewpoint_key)
            # Update UI data with a string key
            #print(self.parent.media_table.data_filtered.at[row.name, "viewpoint"])
            #print(str(new_viewpoint)

            self.parent.media_table.data_filtered.at[row.name, "viewpoint"] = str(new_viewpoint) if new_viewpoint is not None else "None"

        print(self.parent.media_table.data_filtered["viewpoint"])


        self.parent.media_table.refresh_table()  # Refresh UI
