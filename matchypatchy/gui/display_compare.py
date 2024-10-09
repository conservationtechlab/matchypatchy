"""
GUI Window for Match Comparisons



"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent


from .widget_image import ImageWidget

class DisplayCompare(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.mpDB = parent.mpDB
        
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
        query_image_label = QLabel("Query Image:")
        query_options.addWidget(query_image_label,1)
        self.button_previous_query = QPushButton("<<")
        self.button_previous_query.setMaximumWidth(40)
        query_options.addWidget(self.button_previous_query)
        self.query_number = QLineEdit()
        query_options.addWidget(self.query_number)
        query_n = QLabel("/9")
        query_options.addWidget(query_n)
        self.query_number = QLabel()
        query_options.addWidget(self.query_number)
        self.button_next_query = QPushButton(">>")
        query_options.addWidget(self.button_next_query)
        self.button_next_query.setMaximumWidth(40)
        # # Sequence Number
        sequence_label = QLabel("Sequence:")
        query_options.addWidget(sequence_label)
        self.button_previous_sequence = QPushButton("<<")
        self.button_previous_sequence.setMaximumWidth(40)
        query_options.addWidget(self.button_previous_sequence, 0)
        self.sequence_number = QLineEdit()
        query_options.addWidget(self.sequence_number, 0)
        query_sequence_n = QLabel("/3")
        query_options.addWidget(query_sequence_n, 0)
        self.sequence_number = QLabel()
        query_options.addWidget(self.sequence_number, 0)
        self.button_next_sequence = QPushButton(">>")
        self.button_next_sequence.setMaximumWidth(40)
        query_options.addWidget(self.button_next_sequence)
        # # Viewpoint Toggle
        self.button_viewpoint = QPushButton("Left/Right")
        query_options.addWidget(self.button_viewpoint)
        query_layout.addLayout(query_options)
        # Image
        self.query_image = ImageWidget("IMAG0104.JPG")
        self.query_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        query_layout.addWidget(self.query_image,1)
        # MetaData
        self.query_info = QLabel("Image Metadata")
        self.query_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.query_info.setMaximumHeight(200)
        query_layout.addWidget(self.query_info,1)
        image_layout.addLayout(query_layout)
        image_layout.addSpacing(50)

         # match
        match_layout = QVBoxLayout()
        match_label = QLabel("Match")
        match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        match_layout.addWidget(match_label)
        # Options
        match_options = QHBoxLayout()
        # # match Number
        match_image_label = QLabel("Match Image:")
        match_options.addWidget(match_image_label,1)
        self.button_previous_match = QPushButton("<<")
        self.button_previous_match.setMaximumWidth(40)
        match_options.addWidget(self.button_previous_match)
        self.match_number = QLineEdit()
        match_options.addWidget(self.match_number)
        match_n = QLabel("/9")
        match_options.addWidget(match_n)
        self.match_number = QLabel()
        match_options.addWidget(self.match_number)
        self.button_next_match = QPushButton(">>")
        match_options.addWidget(self.button_next_match)
        self.button_next_match.setMaximumWidth(40)
        # # Sequence Number
        sequence_label = QLabel("Sequence:")
        match_options.addWidget(sequence_label)
        self.button_previous_sequence = QPushButton("<<")
        self.button_previous_sequence.setMaximumWidth(40)
        match_options.addWidget(self.button_previous_sequence, 0)
        self.sequence_number = QLineEdit()
        match_options.addWidget(self.sequence_number, 0)
        match_sequence_n = QLabel("/3")
        match_options.addWidget(match_sequence_n, 0)
        self.sequence_number = QLabel()
        match_options.addWidget(self.sequence_number, 0)
        self.button_next_sequence = QPushButton(">>")
        self.button_next_sequence.setMaximumWidth(40)
        match_options.addWidget(self.button_next_sequence, 0)
        # # Viewpoint Toggle
        self.button_viewpoint = QPushButton("Left/Right")
        match_options.addWidget(self.button_viewpoint, 0)
        match_layout.addLayout(match_options)
        # Image
        self.match_image = ImageWidget("IMAG0104.JPG")
        self.match_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        match_layout.addWidget(self.match_image,1)
        # MetaData
        self.match_info = QLabel("Image Metadata")
        self.match_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.match_info.setMaximumHeight(200)
        match_layout.addWidget(self.match_info,1)

        image_layout.addLayout(match_layout)
        # Add image block to layout
        layout.addLayout(image_layout)

        # Buttons
        bottom_layer = QHBoxLayout()
        button_home = QPushButton("Home")
        button_home.clicked.connect(self.home)
        button_load = QPushButton("Load Data")
        button_match = QPushButton("Match")

        # Add buttons to the layout
        bottom_layer.addWidget(button_home)
        bottom_layer.addWidget(button_load)
        bottom_layer.addWidget(button_match)
        layout.addLayout(bottom_layer)
        
        self.setLayout(layout)
        
    def home(self):
        self.parent._set_base_view()

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")
