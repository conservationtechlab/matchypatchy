import sys
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from PyQt6.QtGui import QPixmap, QIcon

class MediaTable(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.mpDB = parent.mpDB
        
        # Set up layout
        layout = QVBoxLayout()

        # Create QTableWidget
        self.table = QTableWidget()
        self.table.setRowCount(4)  # Number of rows
        self.table.setColumnCount(3)  # Columns: Thumbnail, Name, and Description
        self.table.setHorizontalHeaderLabels(["Thumbnail", "Name", "Description"])

        # Sample data with images, names, and descriptions
        data = [
            {"image": "path_to_image_1.jpg", "name": "Item 1", "description": "Description for Item 1"},
            {"image": "path_to_image_2.jpg", "name": "Item 2", "description": "Description for Item 2"},
            {"image": "path_to_image_3.jpg", "name": "Item 3", "description": "Description for Item 3"},
            {"image": "path_to_image_4.jpg", "name": "Item 4", "description": "Description for Item 4"},
        ]

        # Populate the table with data
        for row, item in enumerate(data):
            # Load and set the thumbnail
            pixmap = QPixmap(item["image"]).scaled(50, 50)  # Scale the image to thumbnail size
            icon = QIcon(pixmap)
            thumbnail_item = QTableWidgetItem()
            thumbnail_item.setIcon(icon)

            # Set the name
            name_item = QTableWidgetItem(item["name"])

            # Set the description
            description_item = QTableWidgetItem(item["description"])

            # Add items to the table
            self.table.setItem(row, 0, thumbnail_item)  # Thumbnail column
            self.table.setItem(row, 1, name_item)  # Name column
            self.table.setItem(row, 2, description_item)  # Description column

        # Add table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThumbnailTableWidget()
    window.show()
    sys.exit(app.exec())
