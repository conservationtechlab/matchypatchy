"""
Process page

Chooses the models for each pipeline step (sequence, detection, re-id,
viewpoint), shows whether they are downloaded, and runs the pipeline with its
progress on the page instead of in a modal popup, so the user can keep working
in the media view while it runs.

Replaces the Model Options popup and the processing progress popup that
DisplayBase used to show.
"""
import logging

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
                             QComboBox, QCheckBox, QFrame, QProgressBar)
from PyQt6.QtCore import Qt

from matchypatchy.database.media import workflow_counts
from matchypatchy.gui.widgets.styles import label, set_role, set_variant
from matchypatchy.threads import model_download_thread
from matchypatchy.threads.model_download_thread import get_path
from matchypatchy.threads.sequence_thread import SequenceThread
from matchypatchy.threads.animl_thread import AnimlThread
from matchypatchy.threads.reid_thread import ReIDThread
from matchypatchy.project import UsesProject

logger = logging.getLogger(__name__)

# key in the models yml, label, required, description
MODEL_STEPS = [("DETECTOR_MODELS", "Detector", True, "Finds animals and draws ROIs."),
               ("REID_MODELS", "Re-identification", True, "Embeds each ROI to rank candidate matches."),
               ("VIEWPOINT_MODELS", "Viewpoint", False, "Limits matches to the same side of the animal.")]
# cfg attribute each step's choice is saved under
CFG_KEYS = {"DETECTOR_MODELS": "DETECTOR_KEY", "REID_MODELS": "REID_KEY", "VIEWPOINT_MODELS": "VIEWPOINT_KEY"}


def card(title):
    """Rounded panel with a title, returns the frame and its layout"""
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(10)
    heading = QLabel(title)
    heading.setStyleSheet("font-size: 16px; font-weight: 600;")
    layout.addWidget(heading)
    return frame, layout


class DisplayProcess(UsesProject, QWidget):
    """Pipeline settings and the current processing run"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.project = parent.project
        self.sequence_thread = None
        self.animl_thread = None
        self.miew_thread = None
        self.running = False
        self._process_cancelled = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 28, 36, 32)
        outer.setSpacing(18)

        title = QLabel("Process media")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        outer.addWidget(title)
        self.subtitle = label("", "muted")
        outer.addWidget(self.subtitle)

        columns = QHBoxLayout()
        columns.setSpacing(20)
        outer.addLayout(columns)
        outer.addStretch()

        # PIPELINE -------------------------------------------------------------
        pipeline, pipeline_layout = card("Pipeline")
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(1, 1)
        pipeline_layout.addLayout(grid)

        # sequence has no model, only on/off
        self.sequence = QCheckBox("Calculate sequence")
        self._add_step(grid, 0, 1, "Sequence", False,
                       "Groups bursts and video frames; faster, better matches.", self.sequence, None)

        self.selectors = {}
        self.status_labels = {}
        for row, (key, name, required, description) in enumerate(MODEL_STEPS, start=1):
            combo = QComboBox()
            combo.setMinimumWidth(220)
            status = QLabel("")
            self.selectors[key] = combo
            self.status_labels[key] = status
            combo.currentIndexChanged.connect(lambda _i, k=key: self._update_status(k))
            self._add_step(grid, row, row + 1, name, required, description, combo, status)

        footer = QHBoxLayout()
        self.model_note = label("", "muted")
        self.model_note.setWordWrap(True)
        footer.addWidget(self.model_note, 1)
        button_download = QPushButton("Download models…")
        button_download.clicked.connect(self.download_models)
        footer.addWidget(button_download)
        self.button_run = QPushButton("Run")
        self.button_run.setMinimumHeight(40)
        set_variant(self.button_run, "primary")
        self.button_run.clicked.connect(self.run)
        footer.addWidget(self.button_run)
        pipeline_layout.addSpacing(6)
        pipeline_layout.addLayout(footer)
        columns.addWidget(pipeline, 3)

        # CURRENT RUN ----------------------------------------------------------
        run_card, run_layout = card("Current run")
        self.prompt = label("No run in progress.", "muted")
        self.prompt.setWordWrap(True)
        run_layout.addWidget(self.prompt)
        self.progress = {}
        for key, name in (("sequence", "Sequence"), ("detection", "Detection"), ("reid", "Re-ID embeddings")):
            row = QVBoxLayout()
            row.setSpacing(4)
            row.addWidget(QLabel(name))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFixedHeight(16)
            row.addWidget(bar)
            run_layout.addLayout(row)
            self.progress[key] = bar
        self.note = label("You can keep working in Media while this runs; "
                          "Match uses new ROIs once re-ID finishes.", "muted")
        self.note.setWordWrap(True)
        run_layout.addWidget(self.note)
        self.failed_notice = label("", "pill-warn")
        self.failed_notice.setWordWrap(True)
        self.failed_notice.setVisible(False)
        run_layout.addWidget(self.failed_notice)
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.setEnabled(False)
        self.button_cancel.clicked.connect(self.cancel)
        run_layout.addWidget(self.button_cancel, 0, Qt.AlignmentFlag.AlignRight)
        run_layout.addStretch()
        columns.addWidget(run_card, 2, Qt.AlignmentFlag.AlignTop)

        self.refresh_models()

    def _add_step(self, grid, row, number, name, required, description, control, status):
        """One pipeline row: number, name and description, model control, download status"""
        dot = QLabel(str(number))
        dot.setFixedSize(28, 28)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet("border-radius: 14px; background: palette(midlight); font-weight: 700;")
        grid.addWidget(dot, row, 0)
        text = QVBoxLayout()
        text.setSpacing(1)
        heading = QLabel(f"<b>{name}</b> <span style='font-weight: 400'>{'required' if required else 'optional'}</span>")
        text.addWidget(heading)
        text.addWidget(label(description, "muted"))
        grid.addLayout(text, row, 1)
        grid.addWidget(control, row, 2)
        if status is not None:
            status.setMinimumWidth(130)
            grid.addWidget(status, row, 3)

    def showEvent(self, event):
        """Models may have been downloaded and media imported since the last visit"""
        self.refresh_models()
        super().showEvent(event)

    # MODELS ===================================================================
    def available(self, subset):
        """Models of a subset (eg. REID_MODELS) whose files are all downloaded"""
        ml_cfg = model_download_thread.load_model()
        return [m for m in ml_cfg.get(subset, []) if get_path(self.cfg.ML_DIR, m) is not None]

    def refresh_models(self):
        """Refill the model choices, keeping the saved choice, and recount what needs processing"""
        if self.cfg is None:
            return
        ml_cfg = model_download_thread.load_model()
        for key, combo in self.selectors.items():
            saved = getattr(self.cfg, CFG_KEYS[key], None)
            current = combo.currentText() or saved
            combo.blockSignals(True)
            combo.clear()
            # every known model is listed, downloaded or not, so the status says what is missing
            options = ([] if key == "REID_MODELS" else ["None"]) + list(ml_cfg.get(key, []))
            combo.addItems(options)
            downloaded = self.available(key)
            preferred = current if current in options else (downloaded[0] if downloaded else options[0])
            combo.setCurrentIndex(options.index(preferred))
            combo.blockSignals(False)
            self._update_status(key)
        self.sequence.setChecked(bool(getattr(self.cfg, "sequence_checked", self.sequence.isChecked())))
        self._update_run_button()

    def _update_status(self, key):
        """Downloaded / Not downloaded / Skipped beside a model choice"""
        choice = self.selectors[key].currentText()
        status = self.status_labels[key]
        if choice in ("", "None"):
            status.setText("Skipped")
            set_role(status, "pill-muted")
        elif get_path(self.cfg.ML_DIR, choice) is not None:
            status.setText("Downloaded")
            set_role(status, "pill-ok")
        else:
            status.setText("Not downloaded")
            set_role(status, "pill-warn")
        self._update_run_button()

    def _update_run_button(self):
        missing = [self.selectors[k].currentText() for k in self.selectors
                   if self.status_labels[k].text() == "Not downloaded"]
        survey_id = (self.parent.Base.active_survey or (0, None))[0] if hasattr(self.parent, "Base") else 0
        counts = workflow_counts(self.mpDB, survey_id) if self.mpDB is not None else None
        if counts is not None:
            todo = counts.undetected + counts.unembedded
            self.subtitle.setText(f"Runs only on media that hasn't been processed yet. "
                                  f"{counts.undetected:,} media need detection and "
                                  f"{counts.unembedded:,} ROIs need embeddings in this survey.")
            self.button_run.setText(f"Process {todo:,} items" if todo else "Run")
        if missing:
            self.model_note.setText(f"Download {', '.join(missing)} before running, or choose None.")
        elif self.selectors["VIEWPOINT_MODELS"].currentText() == "None":
            self.model_note.setText("No viewpoint model: matching will search both sides.")
        else:
            self.model_note.setText("")
        self.button_run.setEnabled(not missing and not self.running)

    def download_models(self):
        """Open the download popup, then pick up what was downloaded"""
        self.parent.download_ml()
        self.refresh_models()

    def return_selections(self):
        """The chosen options, in the dict the processing threads expect"""
        def choice(key):
            text = self.selectors[key].currentText()
            return None if text in ("", "None") else text
        return {"sequence_checked": self.sequence.isChecked(),
                "DETECTOR_KEY": choice("DETECTOR_MODELS"),
                "REID_KEY": choice("REID_MODELS"),
                "VIEWPOINT_KEY": choice("VIEWPOINT_MODELS")}

    # RUN ======================================================================
    def run(self):
        """Run sequence, detection and re-id one after the other"""
        mloptions = self.return_selections()
        # a chosen model's files can be deleted after the page was shown
        missing = [key for key in (mloptions['DETECTOR_KEY'], mloptions['REID_KEY'], mloptions['VIEWPOINT_KEY'])
                   if key is not None and get_path(self.cfg.ML_DIR, key) is None]
        if missing:
            self.prompt.setText(f"Model(s) not downloaded: {', '.join(missing)}")
            return
        if self.mpDB.count("media") == 0:
            self.prompt.setText("No images to process. Import media first.")
            return
        self.cfg.update(mloptions)
        self.running = True
        self._process_cancelled = False
        self.button_cancel.setEnabled(True)
        self.failed_notice.setVisible(False)
        for bar in self.progress.values():
            bar.setRange(0, 100)
            bar.setValue(0)
        self._update_run_button()

        # 1. SEQUENCE, no progress of its own
        self.progress["sequence"].setRange(0, 0)
        self.sequence_thread = SequenceThread(self.mpDB, self.cfg, mloptions['sequence_checked'])
        self.sequence_thread.prompt_update.connect(self.prompt.setText)
        # 2. ANIML (BBOX)
        self.animl_thread = AnimlThread(self.mpDB, self.cfg, mloptions['DETECTOR_KEY'])
        self.animl_thread.prompt_update.connect(self.prompt.setText)
        self.animl_thread.progress_update.connect(self.progress["detection"].setValue)
        # 3. REID AND VIEWPOINT
        self.miew_thread = ReIDThread(self.mpDB, self.cfg, mloptions)
        self.miew_thread.prompt_update.connect(self.prompt.setText)
        self.miew_thread.progress_update.connect(self.progress["reid"].setValue)
        self.miew_thread.done.connect(self._finish_processing)
        # run one step after the other, so only one thread writes to the database at a time
        self.sequence_thread.finished.connect(self._start_animl)
        self.animl_thread.finished.connect(self._start_reid)
        self.miew_thread.finished.connect(self._stopped_if_cancelled)
        self.sequence_thread.start()

    def _start_animl(self):
        """Step 2 once sequencing is done, unless processing was cancelled"""
        self.progress["sequence"].setRange(0, 100)
        self.progress["sequence"].setValue(100)
        if self._stopped_if_cancelled():
            return
        self.animl_thread.start()

    def _start_reid(self):
        """Step 3 once detection is done, unless processing was cancelled"""
        # QThread.start() clears an earlier interruption request, so check before starting
        if self._stopped_if_cancelled():
            return
        self.progress["detection"].setValue(100)
        self.miew_thread.start()

    def _stopped_if_cancelled(self):
        """
        After a cancelled step's thread has finished, allow another run

        Called when each thread finishes, so a new run never starts while a
        cancelled thread is still writing to the database.
        """
        if not self._process_cancelled:
            return False
        self.running = False
        self.prompt.setText("Cancelled.")
        self._update_run_button()
        return True

    def _finish_processing(self):
        """Report files that couldn't be read, and let the other pages recount"""
        self.running = False
        self.button_cancel.setEnabled(False)
        failed = self.animl_thread.failed | self.miew_thread.failed
        if failed:
            self.failed_notice.setText(f"{len(failed)} file(s) could not be read. See the log for which.")
            self.failed_notice.setVisible(True)
        self.refresh_models()
        if hasattr(self.parent, "refresh_counts"):
            self.parent.refresh_counts()

    def cancel(self):
        """Stop the running step and don't start the ones after it"""
        self._process_cancelled = True
        for thread in (self.sequence_thread, self.animl_thread, self.miew_thread):
            if thread is not None:
                thread.requestInterruption()
        self.button_cancel.setEnabled(False)
        self.prompt.setText("Cancelling, waiting for the current step to stop…")
        self.progress["sequence"].setRange(0, 100)
