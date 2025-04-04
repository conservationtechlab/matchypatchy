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

        self.ids = ids  # List of ROI IDs
        self.data = self.load_selected_media()
        self.current_image_index = 0
        self.fields_changed = {
            "name": False,
            "sex": False,
            #"species": False,
            "viewpoint": False,
            "favorite": False,
        }


        # Load Viewpoint options
        self.VIEWPOINTS = load('VIEWPOINTS')

        # Layout
        main_layout = QVBoxLayout()

        # Top: filepath
        self.filepath_label = QLabel()
        self.filepath_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filepath_label.setStyleSheet("padding: 0px; margin: 0px; font-size: 10pt;")
        self.filepath_label.setFixedHeight(20)  # 👈 Set max height explicitly
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
        self.sex.addItems(['— Mixed —','Unknown', 'Male', 'Female'])
        self.species = QComboBox()
        #self.comment = QTextEdit()
        #self.comment.setFixedHeight(60)
        self.viewpoint = QComboBox()
        self.viewpoint.addItem("— Mixed —")  # Index 0
        self.viewpoint.addItems(list(self.VIEWPOINTS.values())[1:])
        self.favorite = QComboBox()
        self.favorite.addItems(["— Mixed —", "Not Favorite", "Favorite"])
        # Connect signals to flags only
        self.name.currentIndexChanged.connect(lambda: self.mark_field_changed("name"))
        self.sex.currentIndexChanged.connect(lambda: self.mark_field_changed("sex"))
        self.species.currentIndexChanged.connect(lambda: self.mark_field_changed("species"))
        self.viewpoint.currentIndexChanged.connect(lambda: self.mark_field_changed("viewpoint"))
        self.favorite.currentIndexChanged.connect(lambda: self.mark_field_changed("favorite"))


        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        line.setLineWidth(2)
        metadata_layout.addWidget(line)

        for label_txt, widget in [
            ("Name: ", self.name),
            ("Sex: ", self.sex),
            ("Species: ", self.species),
            ("Viewpoint: ", self.viewpoint),
            ("Favorite: ", self.favorite),
        ]:
            row = QHBoxLayout()
            label = QLabel(label_txt)
            label.setFixedWidth(horizontal_gap)
            row.addWidget(label)
            row.addWidget(widget)
            metadata_layout.addLayout(row)
            metadata_layout.addSpacing(vertical_gap)

 

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
        self.load_individuals()

        self.refresh_values()

    def refresh_values(self):
        print("\n[refresh_values] Running refresh...")

        # --- Name ---
        if not self.fields_changed["name"]:
            unique_ids = self.data["individual_id"].unique()
            self.name.blockSignals(True)
            # Convert None/NaN to a consistent value (e.g., 0 for 'Unknown')
            cleaned_ids = [0 if pd.isna(uid) else int(uid) for uid in unique_ids]
            print(f"[refresh_values] Cleaned individual_ids: {cleaned_ids}")

            if len(set(cleaned_ids)) == 1:
                iid = cleaned_ids[0]
                index = next((i for i, (id, _, _) in enumerate(self.individuals) if id == iid), 1)
                print(f"[refresh_values] Setting name to {self.individuals[index][1]}")
                self.name.setCurrentIndex(index)
                self.sex.setDisabled(iid == 0)
            else:
                print("[refresh_values] Name is mixed — setting to '— Mixed —'")
                self.name.setCurrentIndex(0)  # Index 0 = "— Mixed —"
                self.sex.setDisabled(True)

            self.name.blockSignals(False)
        # --- Sex ---
        if not self.fields_changed["sex"]:
            unique_sexes = self.data["sex"].dropna().unique()
            print(f"[refresh_values] Unique sexes: {unique_sexes}")
            self.sex.blockSignals(True)

            if len(unique_sexes) == 1:
                sex_text = unique_sexes[0]
                index = self.sex.findText(str(sex_text))
                print(f"[refresh_values] Setting sex to {sex_text}")
                self.sex.setCurrentIndex(index)
            else:
                print("[refresh_values] Sex is mixed — setting to '— Mixed —'")
                self.sex.setCurrentIndex(0)  # '— Mixed —'
            # Only enable if there's at least one valid individual
            non_null_iids = self.data["individual_id"].dropna()
            self.sex.setDisabled(non_null_iids.empty)
            self.sex.blockSignals(False)
        



        # --- Viewpoint ---
        if not self.fields_changed["viewpoint"]:
            unique_viewpoints = self.data["viewpoint"].dropna().unique()
            print(f"[refresh_values] Unique viewpoints: {unique_viewpoints}")
            self.viewpoint.blockSignals(True)
            if len(unique_viewpoints) == 1:
                vp_text = self.VIEWPOINTS[str(unique_viewpoints[0])]
                index = self.viewpoint.findText(vp_text)
                print(f"[refresh_values] Setting viewpoint to {vp_text}")
                self.viewpoint.setCurrentIndex(index)
            else:
                print("[refresh_values] Viewpoint is mixed, setting to '— Mixed —'")
                self.viewpoint.setCurrentIndex(0)  # '— Mixed —'
            self.viewpoint.blockSignals(False)
        # --- Favorite ---
        if not self.fields_changed["favorite"]:
            unique_fav = self.data["favorite"].dropna().unique()
            self.favorite.blockSignals(True)
            if len(unique_fav) == 1:
                index = 2 if unique_fav[0] == 1 else 1  # 1 = Not Favorite, 2 = Favorite
                self.favorite.setCurrentIndex(index)
            else:
                self.favorite.setCurrentIndex(0)  # '— Mixed —'
            self.favorite.blockSignals(False)

        


    def load_selected_media(self):
        """
        Fetch all columns from both `roi` and `media` tables for the selected ROI IDs.
        """
        ids_str = ', '.join(map(str, self.ids))
        print(f"Selected ROI IDs: {ids_str}")
    
        # Use all_media to get a complete view of each ROI
        data, col_names = self.mpDB.all_media(row_cond=f"roi.id IN ({ids_str})")

        # Create DataFrame
        df = pd.DataFrame(data, columns=col_names)
        df = df.replace({float('nan'): None}).reset_index(drop=True)

        # Debug prints
        print("=== Loaded ROI + MEDIA + SPECIES + INDIVIDUAL Info ===")
        print(df.head(10).to_string())
        print("Columns:", list(df.columns))

        return df

    def load_individuals(self):
        print("[load_individuals] Loading individual list...")
        individuals = self.mpDB.select("individual", "id, name, sex")
        
        # Prepend special entries
        self.individuals = [(-1, '— Mixed —', 'Unknown'), (0, 'Unknown', 'Unknown')] + individuals

        self.name.blockSignals(True)
        self.name.clear()
        self.name.addItems([ind[1] for ind in self.individuals])
        self.name.blockSignals(False)


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
            # Just refresh favorite (and other) dropdowns based on loaded data
            #self.refresh_values()


                
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
    def mark_field_changed(self, field):
        if field == "viewpoint" and self.viewpoint.currentIndex() == 0:
            print(f"[mark_field_changed] Viewpoint still mixed — not marking as changed.")
            return
        if field == "name" and self.name.currentIndex() == 0:
            print(f"[mark_field_changed] Name still mixed — not marking as changed.")
            return
        if field == "sex" and self.sex.currentIndex() == 0:
            print(f"[mark_field_changed] Sex still mixed — not marking as changed.")
            return
        if field == "favorite" and self.favorite.currentIndex() == 0:
            print(f"[mark_field_changed] Favorite still mixed — not marking as changed.")
            return

        print(f"[mark_field_changed] {field} is marked as changed.")
    
        self.fields_changed[field] = True

    #Viewpoint

    def apply_viewpoint(self):
        """
        Update `viewpoint` for all selected ROIs.
        """
        viewpoint_keys = list(self.VIEWPOINTS.keys())
        if self.viewpoint.currentIndex() <= 0:  # 0 = '— Mixed —'
            print("[apply_viewpoint] Skipping update — still mixed or invalid.")
            return
        selected_viewpoint_key = viewpoint_keys[self.viewpoint.currentIndex()]  # Adjust for 'any' skipping
        print(f"[apply_viewpoint] Applying viewpoint: {selected_viewpoint_key}")
        for _, row in self.data.iterrows():
            roi_id = row["id"]
            if selected_viewpoint_key == 'None':
                self.mpDB.edit_row('roi', roi_id, {"viewpoint": "NULL"}, quiet=False)
            else:
                self.mpDB.edit_row('roi', roi_id, {"viewpoint": int(selected_viewpoint_key)}, quiet=False)
        self.refresh_values()




    #name
    def apply_name(self):
        if self.name.currentIndex() == 0:
            print("[apply_name] Still showing '— Mixed —', skipping.")
            return

        selected_individual = self.individuals[self.name.currentIndex()]
        print(f"[apply_name] Applying individual_id = {selected_individual[0]}")
        for i, row in self.data.iterrows():
            roi_id = row["id"]
            if selected_individual[0] > 0:
                self.mpDB.edit_row('roi', roi_id, {"individual_id": selected_individual[0]}, quiet=False)
                self.data.at[i, "individual_id"] = selected_individual[0]
            else:
                self.mpDB.edit_row('roi', roi_id, {"individual_id": "NULL"}, quiet=False)
                self.data.at[i, "individual_id"] = None

            

    #sex
    
    def apply_sex(self):
        if self.sex.currentIndex() == 0:
            print("[apply_sex] Still showing '— Mixed —', skipping.")
            return

        selected_sex = self.sex.currentText()
        print(f"[apply_sex] Applying sex: {selected_sex}")
        for i, row in self.data.iterrows():
            iid = row["individual_id"]
            if iid:
                self.mpDB.edit_row('individual', iid, {"sex": f"'{selected_sex}'"}, quiet=False)
                self.data.at[i, "sex"] = selected_sex
 

    def apply_favorite(self):
        if self.favorite.currentIndex() == 0:
            print("[apply_favorite] Still showing '— Mixed —', skipping.")
            return

        new_val = 1 if self.favorite.currentIndex() == 2 else 0
        print(f"[apply_favorite] Setting favorite = {new_val}")

        updated_media_ids = set()

        for idx, row in self.data.iterrows():
            media_id = row["media_id"]
            if media_id not in updated_media_ids:
                self.mpDB.edit_row("media", media_id, {"favorite": new_val}, quiet=False)
                updated_media_ids.add(media_id)
            self.data.loc[idx, "favorite"] = new_val

        self.parent.media_table.refresh_table()



    def accept(self):
        print("\n=== ACCEPTING CHANGES ===")
        for key, changed in self.fields_changed.items():
            print(f"[accept] {key} changed? {changed}")

        if self.fields_changed["viewpoint"]:
            self.apply_viewpoint()
        if self.fields_changed["name"]:
            self.apply_name()
        if self.fields_changed["sex"]:
            self.apply_sex()
        if self.fields_changed["favorite"]:
            self.apply_favorite()

        super().accept()


#TO DO: favorite 