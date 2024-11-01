"""
Popup for Selection within a list, ie Survey selection
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QPushButton, QCheckBox, QLabel

class MLDownloadPopup(QDialog):
    def __init__(self, parent, table, column):
        super().__init__(parent)
        self.parent = parent
        self.table = table
        self.column = column
        self.selected_option = None

        self.setWindowTitle("Select Models")

        # Create layout for the checkboxes and add it to the dialog
        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()
        layout.addLayout(grid_layout)

        self.items = ["MegaDetector", "Southwest", "Andes", "Amazon"]

        # Add checkboxes to the grid layout in two columns
        for index, item in enumerate(self.items):
            checkbox = QCheckBox(item)
            row = index // 2  # Determine the row based on index
            col = index % 2   # Alternate between column 0 and column 1
            grid_layout.addWidget(checkbox, row, col)

        # Add OK and Cancel buttons
        button_ok = QPushButton("OK")
        button_ok.clicked.connect(self.accept)
        button_cancel = QPushButton("Cancel")
        button_cancel.clicked.connect(self.reject)

        layout.addWidget(button_ok)
        layout.addWidget(button_cancel)


    def select(self):
        try:
            self.selected_option = self.list[self.combo.currentIndex()]
            return True
        except IndexError:
            return False

    def get_options(self):
        options = self.parent.mpDB.select(self.table, columns = f"id, {self.column}")
        self.list = list(options)
        self.combo.addItems([el[1] for el in self.list])

    def get_selection(self):
        return self.selected_option
