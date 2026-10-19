"""
Thread processing media in one pass: detection, viewpoint and re-id embeddings

Each media file (an image, or the frames of a video that are needed) is read
once. Detection runs on that image, and every roi is cropped from it for its
thumbnail, viewpoint and embedding, so files aren't re-read per model or per roi.
Results are written to the roi they were computed for.
"""
import logging

import animl
import numpy as np
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from matchypatchy.database.media import fetch_roi_media
from matchypatchy.database.thumbnails import save_roi_thumbnail_from_image
from matchypatchy.threads import image_pipeline as ip
from matchypatchy.threads.model_download_thread import get_path

logger = logging.getLogger(__name__)

FULL_FRAME = {"bbox_x": 0, "bbox_y": 0, "bbox_w": 1, "bbox_h": 1}


class ProcessThread(QThread):
    """Detect animals, then compute viewpoints and embeddings, one media file at a time"""
    prompt_update = pyqtSignal(str)  # Signal to update the alert prompt
    progress_update = pyqtSignal(int)  # Signal to update the progress bar
    done = pyqtSignal()

    def __init__(self, mpDB, cfg, mloptions):
        super().__init__()
        self.mpDB = mpDB
        self.thumbnail_dir = cfg.THUMBNAIL_DIR
        self.device = cfg.DEVICE
        self.smart_frames = cfg.SMART_FRAMES
        self.fps = cfg.VIDEO_FPS
        self.n_frames = max(1, int(cfg.N_FRAMES))  # extract at least 1 frame
        self.confidence_threshold = 0.1
        # model keys chosen in the options (None = not used) and their files (None = not downloaded)
        self.keys = {name: mloptions.get(key) for name, key in
                     (("detector", "DETECTOR_KEY"), ("viewpoint", "VIEWPOINT_KEY"), ("reid", "REID_KEY"))}
        self.paths = {name: get_path(cfg.ML_DIR, key) for name, key in self.keys.items()}
        self.detector = None
        self.viewpoint_model = None
        self.miew = None
        self.failed = []

    def run(self):
        # an unhandled exception in a QThread aborts the app
        try:
            self._run()
        except Exception:
            logger.exception("Processing failed")
            self.prompt_update.emit("Processing failed, see the log for details.")

    def _run(self):
        missing = [self.keys[name] for name in self.keys if self.keys[name] and self.paths[name] is None]
        if missing:
            self.prompt_update.emit(f"Model(s) not downloaded: {', '.join(missing)}")
            return

        self.prompt_update.emit("Loading models...")
        self._load_models()
        work = self._collect_work()
        if not work:
            self.prompt_update.emit("Nothing new to process.")
            self.done.emit()
            return

        self.prompt_update.emit(f"Processing {len(work)} file(s)...")
        for i, (media_id, item) in enumerate(work.items()):
            if self.isInterruptionRequested():
                return
            # one unreadable or broken file must not stop the others
            try:
                self._process_media(media_id, item)
            except Exception:
                logger.exception(f"Could not process {item['filepath']}")
                self.failed.append(item["filepath"])
            self.progress_update.emit(round(100 * (i + 1) / len(work)))

        if self.failed:
            # leave the progress popup open with the result
            self.prompt_update.emit(f"Processing finished, {len(self.failed)} file(s) could not be "
                                    "processed. See the log for details.")
            return
        self.prompt_update.emit("Processing complete!")
        self.done.emit()

    # SETUP --------------------------------------------------------------------
    def _load_models(self):
        """Load the selected models once for the whole run"""
        if self.paths["detector"]:
            self.detector = animl.load_detector(str(self.paths["detector"]), device=self.device)
        if self.paths["viewpoint"]:
            self.viewpoint_model, _ = animl.load_classifier(str(self.paths["viewpoint"]), device=self.device)
        if self.paths["reid"]:
            self.miew = animl.load_miew(str(self.paths["reid"]), device=self.device)
        self.detector_prep = ip.detector_preprocessor()
        self.viewpoint_prep = ip.viewpoint_preprocessor()
        self.miew_prep = ip.miewid_preprocessor()

    def _collect_work(self):
        """
        {media_id: {"filepath", "detect", "rois"}} for media that need any processing

        detect: the media has no rois yet
        rois: existing rois needing a bbox (with a detector), a viewpoint or an embedding
        """
        work = {}
        media, columns = self.mpDB.get_media_with_filepath(
            row_cond="NOT EXISTS (SELECT 1 FROM roi WHERE roi.media_id = m.id)")
        if media:
            for row in pd.DataFrame(media, columns=columns).to_dict("records"):
                work[int(row["id"])] = {"filepath": row["filepath"], "detect": True, "rois": []}

        rois = fetch_roi_media(self.mpDB, reset_index=False)
        if rois.empty:
            return work
        needs = pd.Series(False, index=rois.index)
        if self.detector is not None:
            needs |= rois["bbox_x"] == -1
        if self.viewpoint_model is not None:
            needs |= rois["viewpoint"].isna()
        if self.miew is not None:
            needs |= rois["emb"] == 0
        for roi in rois[needs].to_dict("records"):
            item = work.setdefault(int(roi["media_id"]), {"filepath": roi["filepath"], "detect": False, "rois": []})
            item["rois"].append(roi)
        return work

    # PER MEDIA ----------------------------------------------------------------
    def _process_media(self, media_id, item):
        """Read the media once, detect if needed, then viewpoint / embed each roi"""
        filepath = item["filepath"]
        video = ip.is_video(filepath)

        frames = {int(roi["frame"]) for roi in item["rois"]}
        candidates = []
        if item["detect"]:
            if video and self.detector is not None:
                candidates = self._candidate_frames(filepath)
                frames |= set(candidates)
            else:
                frames.add(0)
        images = ip.load_frames(filepath, frames)
        if not images:
            raise OSError(f"Could not read {filepath}")

        new_rois = self._detect(media_id, filepath, images, candidates, video) if item["detect"] else []

        for roi in item["rois"]:
            if not ip.has_bbox(roi) and int(roi["frame"]) in images:
                self._find_bbox(roi, filepath, images[int(roi["frame"])])

        for roi in item["rois"] + new_rois:
            if self.isInterruptionRequested():
                return
            image = images.get(int(roi["frame"]))
            if image is not None and ip.has_bbox(roi):
                self._viewpoint_and_embedding(roi, image)

    def _candidate_frames(self, filepath):
        """Video frames to run the detector on: at VIDEO_FPS, or N_FRAMES spread over the video"""
        video = pd.DataFrame([{"filepath": str(filepath)}])
        if self.smart_frames:
            frames = animl.extract_frames(video, fps=self.fps, parallel=False)
        else:
            frames = animl.extract_frames(video, frames=self.n_frames, parallel=False)
        return [int(f) for f in frames["frame"]] if "frame" in frames.columns else []

    def _detect(self, media_id, filepath, images, candidates, video):
        """Add rois for media without any, return them as roi dicts"""
        if self.detector is None:
            # no detector: the whole image (first frame of a video) is the roi
            detections = [dict(FULL_FRAME, frame=0)] if 0 in images else []
        elif not video:
            detections = [dict(d, frame=0) for d in
                          ip.detect_animals(self.detector, self.detector_prep, images[0], filepath,
                                            confidence_threshold=self.confidence_threshold)]
        else:
            found = []
            for frame in candidates:
                if frame in images:
                    found += [dict(d, frame=frame) for d in
                              ip.detect_animals(self.detector, self.detector_prep, images[frame], filepath,
                                                frame=frame, confidence_threshold=self.confidence_threshold,
                                                calculate_clarity=True)]
            # the best detections across the video, up to N_FRAMES
            detections = sorted(found, key=lambda d: d["score"], reverse=True)[:self.n_frames]

        rois = []
        for det in detections:
            frame = int(det["frame"])
            bbox = ip.bbox_of(det)
            roi_id = self.mpDB.add_roi(media_id, frame, *bbox.values(),
                                       viewpoint=None, individual_id=None, emb=0)
            if roi_id is None:
                continue
            thumbnail = save_roi_thumbnail_from_image(self.thumbnail_dir, filepath, images[frame], *bbox.values())
            self.mpDB.add_thumbnail("roi", roi_id, thumbnail)
            rois.append(dict(bbox, id=roi_id, frame=frame, viewpoint=None, emb=0))
        return rois

    def _find_bbox(self, roi, filepath, image):
        """Box for an imported roi without one: the most confident animal detection"""
        detections = ip.detect_animals(self.detector, self.detector_prep, image, filepath,
                                       frame=int(roi["frame"]), confidence_threshold=self.confidence_threshold)
        if not detections:
            return
        bbox = ip.bbox_of(max(detections, key=lambda d: d["conf"]))
        if not self.mpDB.edit_row("roi", int(roi["id"]), bbox):
            return
        roi.update(bbox)
        thumbnail = save_roi_thumbnail_from_image(self.thumbnail_dir, filepath, image, *bbox.values())
        self.mpDB.batch_update_thumbnails("roi_thumbnails", "fid", {int(roi["id"]): {"filepath": thumbnail}})

    def _viewpoint_and_embedding(self, roi, image):
        """Crop the roi from the image in memory and run the viewpoint / re-id models it still needs"""
        roi_id = int(roi["id"])
        bbox = ip.bbox_of(roi)
        if self.viewpoint_model is not None and (roi["viewpoint"] is None or pd.isna(roi["viewpoint"])):
            arr, _ = self.viewpoint_prep(image, bbox)
            output = ip.run_model(self.viewpoint_model, arr)
            value = int(np.argmax(animl.softmax(output), axis=1)[0])
            self.mpDB.edit_row("roi", roi_id, {"viewpoint": value})
        if self.miew is not None and roi["emb"] == 0:
            arr, _ = self.miew_prep(image, bbox)
            embedding = ip.run_model(self.miew, arr)[0]
            self.mpDB.add_emb(roi_id, embedding)
            self.mpDB.edit_row("roi", roi_id, {"emb": 1})
