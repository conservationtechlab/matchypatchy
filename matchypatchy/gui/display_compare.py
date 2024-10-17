"""
GUI Window for Match Comparisons



"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from ..database.roi import fetch_roi_media, match, rank, get_bbox, get_info
from .widget_image import ImageWidget
from .popup_alert import AlertPopup

class DisplayCompare(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB

        self.current_query_id = 0
        self.current_match_id = 0

        self.current_query = 0
        self.current_match = 0
        self.current_query_seq = 0
        self.current_match_seq = 0
        
        layout = QVBoxLayout()

        self.label = QLabel("Compare Images")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(20)
        layout.addWidget(self.label)
        first_layer = QHBoxLayout()

        # FILTERS
        survey_label = QLabel("Filter:")
        survey_label.setFixedWidth(50)
        first_layer.addWidget(survey_label, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # SURVEY 
        self.survey_select = QComboBox()
        self.survey_select.setFixedWidth(200)
        first_layer.addWidget(self.survey_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        # SITE
        self.site_select = QComboBox()
        self.site_select.setFixedWidth(200)
        first_layer.addWidget(self.site_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)


        # SPECIES 
        self.species_select = QComboBox()
        self.species_select.setFixedWidth(200)
        first_layer.addWidget(self.species_select, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        first_layer.addStretch()
        layout.addLayout(first_layer)

        # Control Panel
        control_panel = QVBoxLayout()
        layer_one = QHBoxLayout()
        layer_one.addWidget(QPushButton("Button 1"))
        layer_one.addWidget(QPushButton("Button 2"))
        layer_two = QHBoxLayout()
        layer_two.addWidget(QLabel("Label 1"))
        layer_two.addWidget(QLabel("Label 2"))
        control_panel.addLayout(layer_one)
        layout.addLayout(control_panel)

        layout.addSpacing(20)

        # Image Comparison
        image_layout = QHBoxLayout()
        
        # QUERY
        query_layout = QVBoxLayout()
        query_label = QLabel("Query")
        query_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        query_layout.addWidget(query_label)
        # Options
        query_options = QHBoxLayout()
        # # Query Number
        query_options.addWidget(QLabel("Query Image:"))
        self.button_previous_query = QPushButton("<<")
        self.button_previous_query.setMaximumWidth(40)
        self.button_previous_query.clicked.connect(lambda: self.set_query(self.current_query - 1))
        query_options.addWidget(self.button_previous_query)
        self.query_number = QLineEdit(str(self.current_query + 1))
        self.query_number.setMaximumWidth(100)
        query_options.addWidget(self.query_number)
        self.query_n = QLabel("/9")
        query_options.addWidget(self.query_n)
        self.button_next_query = QPushButton(">>")
        self.button_next_query.setMaximumWidth(40)
        self.button_next_query.clicked.connect(lambda: self.set_query(self.current_query + 1))
        query_options.addWidget(self.button_next_query)
        query_options.addStretch()  # stretch the gap
        # # Sequence Number
        query_options.addWidget(QLabel("Sequence:"))
        self.button_previous_query_seq = QPushButton("<<")
        self.button_previous_query_seq.setMaximumWidth(40)
        self.button_previous_query_seq.clicked.connect(lambda: self.set_query_sequence(self.current_query_seq - 1))
        query_options.addWidget(self.button_previous_query_seq)
        self.query_seq_number = QLineEdit(str(self.current_query_seq + 1))
        self.query_seq_number.setMaximumWidth(100)
        query_options.addWidget(self.query_seq_number)
        self.query_sequence_n = QLabel("/3")
        query_options.addWidget(self.query_sequence_n)
        self.button_next_query_seq = QPushButton(">>")
        self.button_next_query_seq.setMaximumWidth(40)
        self.button_next_query_seq.clicked.connect(lambda: self.set_query_sequence(self.current_query_seq + 1))
        query_options.addWidget(self.button_next_query_seq)
        query_options.addStretch()
        query_layout.addLayout(query_options)

        # Image
        self.query_image = ImageWidget()
        self.query_image.setStyleSheet("border: 1px solid black;")
        self.query_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        query_layout.addWidget(self.query_image,1)
        # Image Tools

        image_buttons = QHBoxLayout()
        placeholder = QLabel("Brightness, Contrast, zoom? ")
        image_buttons.addWidget(placeholder)
        query_layout.addLayout(image_buttons)

        # MetaData
        self.query_info = QLabel("Image Metadata")
        self.query_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.query_info.setContentsMargins(10, 20, 10, 20)
        self.query_info.setMaximumHeight(200)
        self.query_info.setStyleSheet("border: 1px solid black;")
        query_layout.addWidget(self.query_info,1)
        image_layout.addLayout(query_layout)


        # MIDDLE COLUMN
        middle_column = QVBoxLayout()
        # Viewpoint Toggle In Middle
        self.button_viewpoint = QPushButton("L/R")
        self.button_viewpoint.clicked.connect(self.toggle_viewpoint)
        self.button_viewpoint.setMaximumWidth(50)
        middle_column.addWidget(self.button_viewpoint, alignment=Qt.AlignmentFlag.AlignTop)
        middle_column.addSpacing(200)


        self.button_match = QPushButton("Match")
        self.button_match.setCheckable(True)
        self.button_match.clicked.connect(self.toggle_match)
        self.button_match.setMaximumWidth(50)
        middle_column.addWidget(self.button_match, alignment=Qt.AlignmentFlag.AlignTop)
        middle_column.addStretch()
        image_layout.addLayout(middle_column)

         # match
        match_layout = QVBoxLayout()
        match_label = QLabel("Match")
        match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        match_layout.addWidget(match_label)
        # Options
        match_options = QHBoxLayout()
        # # Match Number
        match_options.addWidget(QLabel("Match Image:"))
        self.button_previous_match = QPushButton("<<")
        self.button_previous_match.setMaximumWidth(40)
        self.button_previous_match.clicked.connect(lambda: self.set_match(self.current_match - 1))
        match_options.addWidget(self.button_previous_match)
        self.match_number = QLineEdit(str(self.current_match + 1))
        self.match_number.setMaximumWidth(100)
        match_options.addWidget(self.match_number)
        self.match_n = QLabel("/9")
        match_options.addWidget(self.match_n)
        self.button_next_match = QPushButton(">>")
        self.button_next_match.setMaximumWidth(40)
        self.button_next_match.clicked.connect(lambda: self.set_match(self.current_match + 1))
        match_options.addWidget(self.button_next_match)
        match_options.addStretch()  # stretch the gap
        # # Sequence Number
        match_options.addWidget(QLabel("Sequence:"))
        self.button_previous_match_seq = QPushButton("<<")
        self.button_previous_match_seq.setMaximumWidth(40)
        self.button_previous_match_seq.clicked.connect(lambda: self.set_match_sequence(self.current_match_seq - 1))
        match_options.addWidget(self.button_previous_match_seq)
        self.match_seq_number = QLineEdit(str(self.current_match_seq + 1))
        self.match_seq_number.setMaximumWidth(100)
        match_options.addWidget(self.match_seq_number)
        self.match_sequence_n = QLabel("/3")
        match_options.addWidget(self.match_sequence_n)
        self.button_next_match_seq = QPushButton(">>")
        self.button_next_match_seq.setMaximumWidth(40)
        self.button_next_match_seq.clicked.connect(lambda: self.set_match_sequence(self.current_match_seq + 1))
        match_options.addWidget(self.button_next_match_seq)
        match_options.addStretch()
        match_layout.addLayout(match_options)

        # Image
        self.match_image = ImageWidget()
        self.match_image.setStyleSheet("border: 1px solid black;")
        self.match_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        match_layout.addWidget(self.match_image,1)
        # Image Tools

        image_buttons = QHBoxLayout()
        placeholder = QLabel("Brightness, Contrast, zoom? ")
        image_buttons.addWidget(placeholder)
        match_layout.addLayout(image_buttons)
        
        # Add buttons to the layout


        # MetaData
        self.match_info = QLabel("Image Metadata")
        self.match_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.match_info.setContentsMargins(10, 20, 10, 20)
        self.match_info.setMaximumHeight(200)
        self.match_info.setStyleSheet("border: 1px solid black;")

        match_layout.addWidget(self.match_info,1)
        image_layout.addLayout(match_layout)
        # Add image block to layout
        layout.addLayout(image_layout)

        # Buttons
        bottom_layer = QHBoxLayout()
        button_home = QPushButton("Home")
        button_home.clicked.connect(self.home)
        button_load = QPushButton("Load Data")
        
        # Add buttons to the layout
        bottom_layer.addWidget(button_home)
        bottom_layer.addWidget(button_load)
        layout.addLayout(bottom_layer)
        
        self.setLayout(layout)
        
    def home(self):
        self.parent._set_base_view()

    def set_query(self, n):
        # wrap around
        if n < 0: n = self.n_queries - 1
        if n > self.n_queries - 1: n = 0

        # set current query
        self.current_query = n
        self.current_query_id = self.ranked_queries[self.current_query][0]
        self.query_number.setText(str(self.current_query + 1))

        # get query sequences

        # update matches
        self.update_matches()

        # load new images
        self.load_images()
        self.load_data()


    def set_query_sequence(self, n):
        pass


    def update_matches(self):
        """
        Update images if current_query, sequence changes
        """
        # get all matches for query
        self.current_query_matches = self.neighbor_dict[self.current_query_id]
        self.match_n.setText("/" + str(len(self.current_query_matches)))
        # set to top of matches
        self.set_match(0)
        
    
    def set_match(self, n):
        """
        Set the curent match index and id 
        """
        if n < 0: n = len(self.current_query_matches) - 1
        if n > len(self.current_query_matches) - 1: n = 0

        self.current_match = n
        self.current_match_id = self.current_query_matches[self.current_match][0]
        self.match_number.setText(str(self.current_match + 1))

        # get match sequences

        # load new images
        self.load_images(match_only=True)
        self.load_data(match_only=True)


    def set_match_sequence(self, n):
        pass

    def toggle_viewpoint(self):
        pass

    def toggle_match(self):
        # Check if the button is checked (pushed in)
        if self.button_match.isChecked():
            self.button_match.setStyleSheet("""
            QPushButton {
                background-color: #2e7031;  /* Green background */
                color: white;              /* White text */
            }
        """)
            print("Button is pressed in.")
        else:
            self.button_match.setStyleSheet("")
            print("Button is released.")

    def load_images(self, match_only=False):
       """
       Load Images for Current Query and Match
       """
       if not match_only: # dont update query if only updating match
           self.query_image.display_image(self.rois.loc[self.current_query_id,"filepath"],
                                        bbox=get_bbox(self.rois.loc[self.current_query_id]))
       self.match_image.display_image(self.rois.loc[self.current_match_id,"filepath"],
                                      bbox=get_bbox(self.rois.loc[self.current_match_id]))

    def load_data(self, match_only=False):
        """
        Load MetaData for Current Query and Match
        """
        if not match_only: # dont update query if only updating match
            self.query_info.setText(get_info(self.rois.loc[self.current_query_id]))
        self.match_info.setText(get_info(self.rois.loc[self.current_match_id]))

    # run on entry
    def calculate_neighbors(self):
        """
        Calculates knn for all unvalidated images, ranks by smallest distance to nn
        """
        self.rois = fetch_roi_media(self.mpDB)

        # must have embeddings to continue
        if not (self.rois["emb_id"] == 0).all():
            self.neighbor_dict, self.nearest_dict = match(self.mpDB)
            self.ranked_queries = rank(self.nearest_dict)

            # set number of queries to validate
            self.n_queries = len(self.neighbor_dict)
            self.query_n.setText("/" + str(self.n_queries))

            # set first query to highest rank 
            self.set_query(0)
        else:
            dialog = AlertPopup(self, prompt="No data to match, process images first.")
            if dialog.exec():
                del dialog
            self.parent._set_base_view()
        

        # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()

        # Right Arrow
        if key == 16777236:
            self.set_query(self.current_query + 1)
        # Left Arrow
        elif key == 16777234:
            self.set_query(self.current_query - 1)
        # Up Arrow
        elif key == 16777235:
            self.set_match(self.current_match - 1)
        # Down Arrow
        elif key == 16777237:
            self.set_match(self.current_match + 1)

        else:
            print(f"Key pressed: {key_text} (Qt key code: {key})")


