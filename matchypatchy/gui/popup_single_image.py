"""
Edit A Single Image


"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QListWidget,
                             QLabel, QLineEdit, QDialogButtonBox, QPushButton)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from matchypatchy.gui.widget_image import ImageWidget

class ImagePopup(QDialog):
    def __init__(self, parent, rid):
        super().__init__(parent)
        self.setWindowTitle("View Image")
        self.mpDB = parent.mpDB
        self.rid = rid
        print(self.rid)

        self.roi_data = self.mpDB.select("roi", row_cond=f"id={self.rid}")
        print(self.roi_data)

        layout = QVBoxLayout()
        # Title
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)


        # Options
        query_options = QHBoxLayout()
        query_options.addStretch()
        # # Query Number
        query_options.addWidget(QLabel("Query Image:"))
        self.button_previous_query = QPushButton("<<")
        self.button_previous_query.setMaximumWidth(40)
        self.button_previous_query.clicked.connect(lambda: self.change_query(self.QueryContainer.current_query - 1))
        query_options.addWidget(self.button_previous_query)

        # Image
        self.image = ImageWidget()
        self.image.setStyleSheet("border: 1px solid black;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.image, 1)


        # Query Image Tools
        query_image_buttons = QHBoxLayout()
        # Reset
        button_query_image_reset = QPushButton("Reset") 
        button_query_image_reset.clicked.connect(self.query_image_reset)
        query_image_buttons.addWidget(button_query_image_reset, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # View Image
        button_query_image_view = QPushButton("View Image") 
        button_query_image_view.clicked.connect(lambda: self.view_image(self.QueryContainer.current_query_rid))
        query_image_buttons.addWidget(button_query_image_view, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Open Image
        button_query_image_open = QPushButton("Open Image") 
        button_query_image_open.clicked.connect(lambda: self.open_image(self.QueryContainer.current_query_rid))
        query_image_buttons.addWidget(button_query_image_open, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        query_image_buttons.addStretch()
        layout.addLayout(query_image_buttons)

        # MetaData
        self.query_info = QLabel("Image Metadata")
        self.query_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.query_info.setContentsMargins(10, 20, 10, 20)
        self.query_info.setMaximumHeight(200)
        self.query_info.setStyleSheet("border: 1px solid black;")
        query_layout.addWidget(self.query_info, 1)
        image_layout.addLayout(query_layout)


        # OK/Cancel Buttons
        button_layout = QHBoxLayout()
                # Ok/Cancel Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)

        self.setLayout(layout)
