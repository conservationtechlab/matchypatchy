import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt
from matchypatchy.algo.models import load

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPixmap
import matchypatchy.database.media as db_roi
from matchypatchy.gui.widget_image import ImageWidget



class MediaEditPopup(QDialog):
    def __init__(self, parent, ids):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Batch Edit ROI Viewpoint")
        self.setFixedSize(900, 600)
        self.mpDB = parent.mpDB

        # --- DEBUG: print roi and media tables ---

        print("=== ROI TABLE ===")
        roi_data = self.mpDB.select(table="roi", columns="*")
        roi_df = pd.DataFrame(roi_data)
        if hasattr(self.mpDB, "cursor") and hasattr(self.mpDB.cursor, "description"):
            roi_df.columns = [col[0] for col in self.mpDB.cursor.description]
        print(roi_df.head(10))  # or .to_string() for full output
        print(roi_df.columns)

        print("\n=== MEDIA TABLE ===")
        media_data = self.mpDB.select(table="media", columns="*")
        media_df = pd.DataFrame(media_data)
        if hasattr(self.mpDB, "cursor") and hasattr(self.mpDB.cursor, "description"):
            media_df.columns = [col[0] for col in self.mpDB.cursor.description]
        print(media_df.head(10))
        print(media_df.columns)

        # -----------------------------------------

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

        # Image with bounding box
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.image.setFixedHeight(400)
        layout.addWidget(self.image, 1)

        # Navigation Buttons
        img_nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.show_previous_image)
        self.next_btn.clicked.connect(self.show_next_image)
        img_nav_layout.addWidget(self.prev_btn)
        img_nav_layout.addWidget(self.next_btn)
        layout.addLayout(img_nav_layout)

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

        # Show the first image
        self.update_image()
        # Set the current viewpoint for selected ROIs
        self.refresh_viewpoint()



    def load_selected_media(self):
        """
        Fetch all columns from both `roi` and `media` tables for the selected ROI IDs.
        """
        ids_str = ', '.join(map(str, self.ids))
        print(f"Selected ROI IDs: {ids_str}")

        data, col_names = self.mpDB.select_join(
            table="roi",
            join_table="media",
            join_cond="roi.media_id = media.id",
            columns="roi.*, media.*",
            row_cond=f"roi.id IN ({ids_str})",
            quiet=False
        )
        print(f"Query returned {len(data)} rows with {len(col_names)} columns")
        if data:
            print(col_names)

        df = pd.DataFrame(data, columns=col_names)
        df = df.replace({float('nan'): None}).reset_index(drop=True)
        print("Filepaths from media table:")
        print(df["filepath"].head(5).to_list())

        print("Bounding box columns from roi:")
        print(df[["bbox_x", "bbox_y", "bbox_w", "bbox_h"]].head(5))

        print("=== Merged ROI + MEDIA Table ===")
        print(df.head(10).to_string())
        print("Columns:", list(df.columns))

        return df

    def update_image(self):
        if not self.data.empty:
            filepath = self.data.iloc[self.current_image_index]["filepath"]
            roi_row = self.data.iloc[self.current_image_index]
            self.image.load(image_path=filepath,
                            bbox=db_roi.get_bbox(roi_row),
                            crop=False)
        else:
            self.image.setText("No image selected.")

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
            roi_id = row["media_id"]
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

#TO DO:
#show bounding boxes of the selected images fix load_selected_media 
#edit other fields 
#show meta data 
    