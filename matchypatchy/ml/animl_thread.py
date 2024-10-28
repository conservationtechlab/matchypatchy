"""
Thread Class for Processing BBox and Species Classification

"""
import os
import pandas as pd
import logging
from animl import matchypatchy as animl_mp

from PyQt6.QtCore import QThread, pyqtSignal

from ..database.roi import (fetch_roi, match)

FRAME_DIR = os.path.join(os.getcwd(), "Frames")
logging.debug('FRAME_DIR: ' + FRAME_DIR)


class AnimlThread(QThread):
    progress_update = pyqtSignal(str)  # Signal to update the progress bar

    def __init__(self, mpDB):
        super().__init__()
        self.mpDB = mpDB

        # select media that do not have rois
        media = self.mpDB._fetch("""SELECT * FROM media WHERE NOT EXISTS 
                                 (SELECT 1 FROM roi WHERE roi.media_id = media.id);""")
        

        self.media = pd.DataFrame(media, columns=["id", "filepath", "ext", "timestamp", "site", 
                                                  "sequence_id", "capture_id", "comment", "favorite"])
        self.image_paths = pd.Series(self.media["filepath"].values,index=self.media["id"]).to_dict() 

        self.md_filepath = os.path.join(os.getcwd(), "viewpoint_jaguar.pt")
        self.classifier_filepath = os.path.join(os.getcwd(), "miewid.bin")
        self.classifier_classlist = os.path.join(os.getcwd(), "miewid.bin")
    
    def run(self):
        self.progress_update.emit("Extracting frames from videos...")
        self.get_frames()
        self.progress_update.emit("Calculating bounding box...")
        self.get_bbox()
        self.progress_update.emit("Predicting species...")
        #self.get_species()

    def get_frames(self):
        self.media = animl_mp.extract_frames(self.media, FRAME_DIR)

    def get_bbox(self):
        # 1 RUN MED
        detections = animl_mp.detect(self.md_filepath, self.media)
        
        for i, roi in detections.iterrows():
            print(i,roi)

            media_id = roi['id']

            # 2. ADD ROI
            frame = roi['FrameNumber'] if 'FrameNumber' in roi.names else 1
 
            bbox_x = roi['bbox1']
            bbox_y = roi['bbox2']
            bbox_w = roi['bbox3']
            bbox_h = roi['bbox4']

            # species, viewpoint, individual TBD
            species_id = -1
            viewpoint = None
            individual_id = None

                # do not add emb_id, to be determined later
            self.mpDB.add_roi(frame, bbox_x, bbox_y, bbox_w, bbox_h,
                              media_id, species_id, viewpoint=viewpoint,
                              reviewed=0, individual_id=individual_id, emb_id=0)
    
    def get_species(self):
        # TODO: Utilize probability for captures/sequences
        self.rois = fetch_roi(self.mpDB)
