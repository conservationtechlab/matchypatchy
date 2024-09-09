import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QProgressBar, QLabel, QDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import time



class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def run(self):
        for i in range(101):
            time.sleep(0.1)  # Simulate a long-running task
            self.progress.emit(i)
        self.finished.emit()

class ProgressPopup(QDialog):
    def __init__(self, prompt):
        super().__init__()
        self.setWindowTitle("Progress")
        self.setGeometry(100, 100, 300, 100)
        self.layout = QVBoxLayout()

        self.label = QLabel(prompt)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)

        self.worker_thread = WorkerThread()
        self.worker_thread.progress.connect(self.update_progress)
        self.worker_thread.finished.connect(self.close)
        self.worker_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)


class ProgressBar(QWidget):
    """
    Progress bar widget in place on window
    """
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("Progress")
        self.setGeometry(100, 100, 300, 100)
        self.layout = QVBoxLayout()

        self.label = QLabel(prompt)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)

        self.worker_thread = WorkerThread()
        self.worker_thread.progress.connect(self.update_progress)
        self.worker_thread.finished.connect(self.close)
        self.worker_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)