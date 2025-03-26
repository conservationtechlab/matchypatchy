import pandas as pd
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QDialogButtonBox, QFrame, QTextEdit)
from PyQt6.QtCore import Qt
from matchypatchy.algo.models import load

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPixmap
import matchypatchy.database.media as db_roi
from matchypatchy.gui.widget_image import ImageWidget

'''
QVBoxLayout (main_layout)
│
├── QLabel: filepath
├── QHBoxLayout (content_layout)
│   ├── ImageWidget (left side)
│   └── QWidget (metadata_container)
│       └── QVBoxLayout (metadata_layout)
│           ├── Non-editable labels (timestamp, station, etc.)
│           ├── QFrame separator (horizontal line)
│           ├── Editable fields: (added in a loop)
│           │   ├── Name (QComboBox)
│           │   ├── Sex (QComboBox)
│           │   ├── Species (QComboBox)
│           │   └── Viewpoint (QComboBox)
│           └── Comment (QTextEdit)
├── QHBoxLayout (Previous / Next buttons)
└── QDialogButtonBox (OK / Cancel)

'''

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
        main_layout = QVBoxLayout()

        '''
        # Title
        title = QLabel("Batch Edit ROI Viewpoint")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        '''

        # Top: filepath
        self.filepath_label = QLabel()
        self.filepath_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.filepath_label)

        # Image + metadata horizontal layout
        content_layout = QHBoxLayout()

        # Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.image.setFixedHeight(400)
        self.image.setFixedWidth(550)  # Adjusted width to make image smaller

        content_layout.addWidget(self.image, 3)

        # Metadata panel
        metadata_container = QWidget()
        metadata_container.setObjectName("borderWidget")
        metadata_container.setStyleSheet("""#borderWidget { border: 1px solid black; }""")
        metadata_layout = QVBoxLayout()

        horizontal_gap = 80
        vertical_gap = 8

        def add_row(label_txt):
            row = QHBoxLayout()
            label = QLabel(label_txt)
            label.setFixedWidth(horizontal_gap)
            val = QLabel()
            row.addWidget(label)
            row.addWidget(val)
            metadata_layout.addLayout(row)
            metadata_layout.addSpacing(vertical_gap)
            return val

        self.timestamp_label = add_row("Timestamp: ")
        self.station_label = add_row("Station: ")
        self.survey_label = add_row("Survey: ")
        self.region_label = add_row("Region: ")
        self.sequence_id_label = add_row("Sequence ID: ")
        self.external_id_label = add_row("External ID: ")
        metadata_container.setLayout(metadata_layout)
        content_layout.addWidget(metadata_container, 1)
        main_layout.addLayout(content_layout)


        #Editable fields
        self.name = QComboBox()
        self.sex = QComboBox()
        self.sex.addItems(['Unknown', 'Male', 'Female'])
        self.species = QComboBox()
        self.comment = QTextEdit()
        self.comment.setFixedHeight(60)
        self.viewpoint = QComboBox()
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])

        self.name.currentIndexChanged.connect(self.change_name)
        self.sex.currentIndexChanged.connect(self.change_sex)
        self.species.currentIndexChanged.connect(self.change_species)
        self.comment.textChanged.connect(self.change_comment)
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)


        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        line.setLineWidth(2)
        metadata_layout.addWidget(line)

        for label_txt, widget in [
            ("Name: ", self.name),
            ("Sex: ", self.sex),
            ("Species: ", self.species),
            ("Viewpoint: ", self.viewpoint)
        ]:
            row = QHBoxLayout()
            label = QLabel(label_txt)
            label.setFixedWidth(horizontal_gap)
            row.addWidget(label)
            row.addWidget(widget)
            metadata_layout.addLayout(row)
            metadata_layout.addSpacing(vertical_gap)

        comment_row = QHBoxLayout()
        comment_label = QLabel("Comment: ")
        comment_label.setFixedWidth(horizontal_gap)
        comment_row.addWidget(comment_label)
        comment_row.addWidget(self.comment)
        metadata_layout.addLayout(comment_row)


        '''
        # Viewpoint Selection
        viewpoint_layout = QHBoxLayout()
        viewpoint_label = QLabel("Viewpoint: ")
        viewpoint_label.setFixedWidth(80)
        viewpoint_layout.addWidget(viewpoint_label)

        self.viewpoint = QComboBox()
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])  # Skip 'any'
        self.viewpoint.currentIndexChanged.connect(self.change_viewpoint)
        viewpoint_layout.addWidget(self.viewpoint)

        main_layout.addLayout(viewpoint_layout)
        '''


 

        # Navigation Buttons
        img_nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.show_previous_image)
        self.next_btn.clicked.connect(self.show_next_image)
        img_nav_layout.addWidget(self.prev_btn)
        img_nav_layout.addWidget(self.next_btn)
        main_layout.addLayout(img_nav_layout)


        # OK/cancel buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        main_layout.addWidget(buttonBox)



        self.setLayout(main_layout)

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
            # Update filepath label
            self.filepath_label.setText(filepath)
            
            # Update metadata labels
            self.timestamp_label.setText(str(roi_row.get("timestamp", "N/A")))
            self.station_label.setText(str(roi_row.get("station_id", "N/A")))
            self.survey_label.setText(str(roi_row.get("survey", "N/A")))
            self.region_label.setText(str(roi_row.get("region", "N/A")))
            self.sequence_id_label.setText(str(roi_row.get("sequence_id", "N/A")))
            self.external_id_label.setText(str(roi_row.get("external_id", "N/A")))
                
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
    
    #Editable fields

    #Viewpoint
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


    #name
    def refresh_name(self):
        names = self.data["name"].dropna().unique()
        most_common = names[0] if len(names) == 1 else "Multiple"
        self.name.setCurrentText(str(most_common))



    def change_name(self):
        pass

    #sex

    def change_sex(self):
        pass

    #species
    def change_species(self):
        pass

    #comment
    def change_comment(self):
        pass




#TO DO:
#edit other fields: name, sex, species,comment, fav 
    