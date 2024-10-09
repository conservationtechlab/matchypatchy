"""
GUI Window for Match Comparisons



"""
from PyQt6.QtWidgets import (QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox)
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
        
        # IMAGES
        image_layout = QHBoxLayout()
        
        left_side = QVBoxLayout()
        left_label = QLabel("Query")
        left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_side.addWidget(left_label,0)
        self.left_box = ImageWidget()
        left_side.addWidget(self.left_box)
        image_layout.addLayout(left_side)
        
        right_side = QVBoxLayout()
        right_label = QLabel("Match")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_side.addWidget(right_label,0)
        self.right_box = ImageWidget()
        right_side.addWidget(self.right_box)
        image_layout.addLayout(right_side)
        
        layout.addLayout(image_layout)

        # Image Options
        image_options = QHBoxLayout()
        
        query_options = QHBoxLayout()
        query_label = QLabel("Query:")
        query_options.addWidget(query_label, 1)
        self.button_previous_query = QPushButton("<<")
        query_options.addWidget(self.button_previous_query, 0)
        self.query_number = QLabel()
        query_options.addWidget(self.query_number, 0)
        self.button_next_query = QPushButton(">>")
        query_options.addWidget(self.button_next_query, 0)
        sequence_label = QLabel("Sequence:")
        query_options.addWidget(sequence_label, 1)
        self.button_previous_sequence = QPushButton("<<")
        query_options.addWidget(self.button_previous_sequence, 0)
        self.sequence_number = QLabel()
        query_options.addWidget(self.sequence_number, 0)
        self.button_next_sequence = QPushButton(">>")
        query_options.addWidget(self.button_next_sequence, 0)

        image_options.addLayout(query_options)
        
        # MATCH OPTIONS
        match_options = QHBoxLayout()
        match_label = QLabel("Match:")
        match_options.addWidget(match_label, 1)
        self.button_previous_match = QPushButton("<<")
        match_options.addWidget(self.button_previous_match, 0)
        self.match_number = QLabel()
        match_options.addWidget(self.match_number, 0)
        self.button_next_match = QPushButton(">>")
        match_options.addWidget(self.button_next_match, 0)
        sequence_label = QLabel("Sequence:")
        match_options.addWidget(sequence_label, 1)
        self.button_previous_sequence = QPushButton("<<")
        match_options.addWidget(self.button_previous_sequence, 0)
        self.sequence_number = QLabel()
        match_options.addWidget(self.sequence_number, 0)
        self.button_next_sequence = QPushButton(">>")
        match_options.addWidget(self.button_next_sequence, 0)

        image_options.addLayout(match_options)
        layout.addLayout(image_options)

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
        
        # self.left_box.display_image_padded('/home/kyra/animl-py/examples/Southwest/2021-06-30_SYFR0218.JPG')
        # self.right_box.display_image_padded('/home/kyra/animl-py/examples/Southwest/2021-08-08_RCNX0063.JPG')

        self.left_box.display_image_padded("C:/Users/tswanson/animl-py/examples/Southwest/2021-06-30_SYFR0218.JPG")
        self.right_box.display_image_padded('C:/Users/tswanson/animl-py/examples/Southwest/2021-08-08_RCNX0063.JPG')

        self.setLayout(layout)
        
    def home(self):
        self.parent._set_base_view()

    # Keyboard Handler
    def keyPressEvent(self, event):
        key = event.key()
        key_text = event.text()
        print(f"Key pressed: {key_text} (Qt key code: {key})")
