import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt6.QtCore import QSize, Qt



class MainWindow(QMainWindow):
    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB
        self.setWindowTitle("MatchyPatchy")
        self.setFixedSize(QSize(1200, 800))
        
        button = QPushButton("Validate db")
        button.clicked.connect(self.get_tables)
        # Set the central widget of the Window.
        self.setCentralWidget(button)
        
    def get_tables(self):
        print("Clicked!")


def main(mpDB):
    app = QApplication(sys.argv)

    window = MainWindow(mpDB)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()