"""
Thread Class for Processing BBox and Species Classification

"""
import os
import pandas as pd
import animl

from PyQt6.QtCore import QThread, pyqtSignal

from ..database.roi import (fetch_roi, match)



class AnimlThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB

        # select media that do not have rois
        media = self.mpDB._fetch("""SELECT * FROM media WHERE NOT EXISTS 
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")
        print(media)

        self.media = pd.DataFrame(media, columns=["id", "filepath", "capture_id", "sequence_id"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 

        self.md_filepath = os.path.join(os.getcwd(), "viewpoint_jaguar.pt")
        self.classifier_filepath = os.path.join(os.getcwd(), "miewid.bin")
        self.classifier_classlist = os.path.join(os.getcwd(), "miewid.bin")
    
    def run(self):
        self.progress_update.emit("Calculating bounding box...")
        self.get_bbox()
        self.progress_update.emit("Predicting species...")
        self.get_species()


    def get_bbox(self):
        # 1 RUN MED

        # 2. ADD ROI
        pass

    def get_species(self):
        # TODO: Utilize probability for captures/sequences
        self.rois = fetch_roi(self.mpDB)



class ManifestThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, directory):
        super().__init__()