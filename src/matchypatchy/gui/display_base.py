"""
Overview page (the home view)

Shows the active survey, the next workflow step to take and the five steps
(import, process, validate, match, export) with how much each has left to do.

Also owns the survey selector, which the main window places in the sidebar,
and the survey, station and individual management popups.
"""
import logging
import os

from PyQt6.QtWidgets import (QPushButton, QWidget, QFileDialog, QDialog, QFrame, QMenu,
                             QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSizePolicy)
from PyQt6.QtCore import Qt

from matchypatchy.database.location import survey_names
from matchypatchy.database.media import clear_project_data, rois_without_embeddings, workflow_counts
from matchypatchy.gui.dialogs.popup_survey import SurveyPopup
from matchypatchy.gui.dialogs.popup_station import StationPopup
from matchypatchy.gui.dialogs.popup_individual import IndividualPopup
from matchypatchy.gui.dialogs.popup_alert import AlertPopup
from matchypatchy.gui.dialogs.popup_import_csv import ImportCSVPopup
from matchypatchy.gui.dialogs.popup_import_folder import ImportFolderPopup
from matchypatchy.gui.widgets.styles import label, set_variant, ACCENT, ACCENT_SOFT, ACCENT_INK

from matchypatchy.project import UsesProject


logger = logging.getLogger(__name__)

# workflow steps: key, button text, description of what the count means
STEPS = [("import", "Import", "media from {stations} stations"),
         ("process", "Process", "new ROIs need embeddings"),
         ("validate", "Validate", "ROIs missing a viewpoint"),
         ("match", "Match", "unidentified ROIs"),
         ("export", "Export", "individuals ready to export as CSV")]


def next_step(counts):
    """
    The first workflow step that still has work, as a key of STEPS

    Import when the survey is empty, then process (detection or embeddings),
    validate (missing viewpoints), match (unidentified rois), else export.
    """
    if counts.media == 0:
        return "import"
    if counts.undetected or counts.unembedded:
        return "process"
    if counts.missing_viewpoint:
        return "validate"
    if counts.unidentified:
        return "match"
    return "export"


class StepRow(QWidget):
    """One workflow step: status dot, step button, count and what it counts"""
    def __init__(self, number, text):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(20)
        self.number = number
        self.dot = QLabel(str(number))
        self.dot.setFixedSize(34, 34)
        self.dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.dot)
        self.button = QPushButton(text)
        self.button.setFixedSize(140, 46)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(self.button)
        self.count = QLabel("")
        self.count.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(self.count)
        self.status = label("", "muted")
        self.status.setStyleSheet("font-size: 17px;")
        layout.addWidget(self.status, 1)

    def set_state(self, count, status, done, current):
        """Show the count and status; a check when done, filled when it is the next step"""
        self.count.setText(f"{count:,}" if count is not None else "")
        self.status.setText(status)
        base = "border-radius: 17px; font-weight: 700; font-size: 14px;"
        if current:
            self.dot.setText(str(self.number))
            self.dot.setStyleSheet(base + f"background: {ACCENT}; color: white;")
        elif done:
            self.dot.setText("✓")
            self.dot.setStyleSheet(base + f"background: {ACCENT_SOFT}; color: {ACCENT_INK};")
        else:
            self.dot.setText(str(self.number))
            self.dot.setStyleSheet(base + "background: palette(midlight); color: palette(text);")
        set_variant(self.button, "primary" if current else "")


class DisplayBase(UsesProject, QWidget):
    """Overview page of the MatchyPatchy GUI."""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.project = parent.project
        self.active_survey = None
        self.counts = None

        # survey selector, placed in the sidebar by the main window
        self.survey_select = QComboBox()
        self.survey_select.currentIndexChanged.connect(self.select_survey)
        self.survey_select.currentIndexChanged.connect(lambda _i: self.refresh())

        outer = QHBoxLayout(self)
        outer.setContentsMargins(40, 48, 40, 40)
        outer.addStretch(1)
        column = QVBoxLayout()
        column.setSpacing(28)
        outer.addLayout(column, 12)
        outer.addStretch(1)

        # HEADER
        header = QVBoxLayout()
        header.setSpacing(4)
        self.title = label("", "title")
        header.addWidget(self.title)
        self.subtitle = label("", "muted")
        self.subtitle.setStyleSheet("font-size: 14px;")
        header.addWidget(self.subtitle)
        column.addLayout(header)

        # NEXT STEP
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(20)
        card_text = QVBoxLayout()
        card_text.setSpacing(4)
        card_text.addWidget(label("NEXT STEP", "eyebrow"))
        self.next_title = QLabel("")
        self.next_title.setStyleSheet("font-size: 21px; font-weight: 600;")
        card_text.addWidget(self.next_title)
        self.next_text = label("", "muted")
        self.next_text.setWordWrap(True)
        card_text.addWidget(self.next_text)
        card_layout.addLayout(card_text, 1)
        self.next_button = QPushButton("")
        self.next_button.setMinimumSize(170, 46)
        self.next_button.setStyleSheet("font-size: 15px;")
        set_variant(self.next_button, "primary")
        self.next_button.clicked.connect(lambda: self.run_step(self._next))
        card_layout.addWidget(self.next_button, 0, Qt.AlignmentFlag.AlignVCenter)
        column.addWidget(card)

        # WORKFLOW
        workflow = QFrame()
        workflow.setObjectName("Card")
        workflow.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        workflow_layout = QVBoxLayout(workflow)
        workflow_layout.setContentsMargins(0, 6, 0, 6)
        workflow_layout.setSpacing(0)
        self.rows = {}
        for i, (key, text, _status) in enumerate(STEPS, start=1):
            if i > 1:
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet("background: palette(midlight);")
                workflow_layout.addWidget(line)
            row = StepRow(i, text)
            row.button.clicked.connect(lambda _c=False, k=key: self.run_step(k))
            workflow_layout.addWidget(row, 1)
            self.rows[key] = row
        column.addWidget(workflow, 1)

        # Import offers a folder or a csv manifest
        self.import_menu = QMenu(self)
        self.import_menu.addAction("From a folder…", self.import_folder)
        self.import_menu.addAction("From a CSV manifest…", self.import_csv)

        self._next = "import"
        self.update_survey()
        # the survey list belongs to the open project, start from its first survey
        self.project.changed.connect(lambda: self.update_survey(keep_selection=False))
        self.project.data_changed.connect(self.surveys_written)

    def showEvent(self, event):
        """Recount on every visit, imports and matching change the numbers elsewhere"""
        self.refresh()
        super().showEvent(event)

    # ==========================================================================
    # Overview
    # ==========================================================================
    def refresh(self):
        """Recount the active survey and update the header, next step and workflow rows"""
        if self.mpDB is None:
            return
        survey_id, survey_name = self.active_survey or (0, None)
        counts = workflow_counts(self.mpDB, survey_id)
        self.counts = counts

        self.title.setText(survey_name or "No survey")
        details = self.survey_details(survey_id)
        details += [f"{counts.media:,} media", f"{counts.individuals:,} individuals"]
        self.subtitle.setText(" · ".join(details))

        self._next = next_step(counts)
        pending = {"import": counts.media,
                   "process": counts.unembedded + counts.undetected,
                   "validate": counts.missing_viewpoint,
                   "match": counts.unidentified,
                   "export": counts.individuals}
        order = [key for key, _t, _s in STEPS]
        for key, _text, status in STEPS:
            if key == "process" and counts.undetected:
                status = "media and ROIs still to process"
            self.rows[key].set_state(pending[key], status.format(stations=counts.stations),
                                     done=order.index(key) < order.index(self._next),
                                     current=key == self._next)

        titles = {"import": ("Import media", "Add a folder of images or a CSV manifest to this survey.", "Import media"),
                  "process": (f"Process {pending['process']:,} new items",
                              "Run detection and re-identification so new ROIs can be matched.", "Process"),
                  "validate": (f"Check {counts.missing_viewpoint:,} ROIs missing a viewpoint",
                               "Fix viewpoints and boxes before matching.", "Review media"),
                  "match": (f"Match {counts.unidentified:,} unidentified ROIs",
                            "Review ranked candidates and link each ROI to an individual.", "Start matching"),
                  "export": ("Export results", "Every ROI has an individual. Save the survey as a CSV.", "Export CSV")}
        title, text, button = titles[self._next]
        self.next_title.setText(title)
        self.next_text.setText(text)
        self.next_button.setText(button)

    def survey_details(self, survey_id):
        """Region and years of the survey, for the header"""
        rows = self.mpDB.query("""SELECT region.name, survey.year_start, survey.year_end FROM survey
                                  LEFT JOIN region ON region.id = survey.region_id
                                  WHERE survey.id = ?;""", (survey_id,))
        if not rows:
            return []
        region, start, end = rows[0]
        details = [region] if region else []
        if start and end and start != end:
            details.append(f"{start}–{end}")
        elif start or end:
            details.append(str(start or end))
        return details

    def run_step(self, key):
        """Do what a workflow step's button says"""
        if key == "import":
            button = self.rows["import"].button
            self.import_menu.popup(button.mapToGlobal(button.rect().bottomLeft()))
        elif key == "process":
            self.select_models()
        elif key == "validate":
            self.validate()
        elif key == "match":
            self.match()
        elif key == "export":
            self.export()

    # ==========================================================================
    # Database Management Functions
    # ==========================================================================
    def update_survey(self, keep_selection=True):
        """Update survey dropdown list, keeping the selected survey unless it was deleted"""
        selected = self.active_survey[0] if keep_selection and self.active_survey else None
        self.survey_select.blockSignals(True)
        self.survey_select.clear()
        surveys = survey_names(self.mpDB)
        self.survey_list = dict(surveys)
        self.survey_list_ordered = list(surveys)
        if self.survey_list_ordered:
            self.survey_select.addItems([el[1] for el in surveys])
        position = next((i for i, (sid, _) in enumerate(self.survey_list_ordered) if sid == selected), 0)
        self.survey_select.setCurrentIndex(position)
        self.survey_select.blockSignals(False)
        self.select_survey()
        self.refresh()

    def surveys_written(self, table):
        """
        Reload the survey list after a write to the survey table

        Connected to project.data_changed in __init__, so surveys added by an
        import or edited in Manage Surveys show up without the caller refreshing.
        """
        if table == "survey":
            self.update_survey()

    def manage_survey(self):
        """Launch Survey Management Popup"""
        dialog = SurveyPopup(self)
        # the survey list refreshes itself as surveys are written
        dialog.exec()
        del dialog

    def select_survey(self):
        """Set active survey based on dropdown selection"""
        try:
            self.active_survey = self.survey_list_ordered[self.survey_select.currentIndex()]
            return True
        except IndexError:
            self.active_survey = (0, None)
            return False

    def manage_station(self):
        """Launch Station Management Popup"""
        self.select_survey()
        dialog = StationPopup(self, self.active_survey)
        if dialog.exec():
            del dialog

    def manage_individual(self):
        """Launch Individual Management Popup"""
        dialog = IndividualPopup(self)
        if dialog.exec():
            del dialog

    def set_filtered_view(self, filters):
        """Set media view with filters applied, called from IndividualPopup"""
        self.parent._set_media_view(filters=filters)

    # ==========================================================================
    # MAIN PROCESS
    # ==========================================================================
    # STEP 1: Import from CSV
    def import_csv(self):
        """Add media from a CSV manifest"""
        survey_selected = self.select_survey()
        if not survey_selected:
            dialog = AlertPopup(self, "Please select a survey before importing.")
            dialog.exec()
            del dialog
            return
        else:
            manifest = QFileDialog.getOpenFileName(self, "Open File",
                                                   os.path.expanduser('~'),
                                                   ("CSV Files (*.csv)"))[0]
            if manifest:
                logger.info(f"Importing from manifest: {manifest}")
                dialog = ImportCSVPopup(self, manifest)
                dialog.exec()
                del dialog
                self.refresh()

    # STEP 1: Import from FOLDER
    def import_folder(self):
        """Add media from a folder"""
        survey_selected = self.select_survey()
        if not survey_selected:
            dialog = AlertPopup(self, "Please select a survey before importing.")
            dialog.exec()
            del dialog
            return
        else:
            directory = QFileDialog.getExistingDirectory(self, "Open File",
                                                         os.path.expanduser('~'),
                                                         QFileDialog.Option.ShowDirsOnly)
            if directory:
                dialog = ImportFolderPopup(self, directory)
                logger.info(f"Importing from directory: {directory}")
                dialog.exec()
                # ask for another directory only if this one had no images, not on Cancel
                no_images = dialog.no_images
                del dialog
                if no_images:
                    self.import_folder()
                self.refresh()

    # STEP 2: Process
    def select_models(self):
        """Open the process page, which chooses models and runs them"""
        self.parent._set_process_view()

    # STEP 3: Validate/Manage Media Button
    def validate(self):
        """Open media view to validate/manage media"""
        self.parent._set_media_view()

    # STEP 4: Match Button
    def match(self):
        """Open compare view to match ROIs"""
        # check that the user has processed the images first
        if len(rois_without_embeddings(self.mpDB)) > 0:
            dialog = AlertPopup(self, "There are rois without embeddings. They will be ignored until processed.")
            if dialog.exec() == QDialog.DialogCode.Rejected:
                return
            del dialog

        self.parent._set_compare_view()

    # STEP 5: Export Button
    def export(self):
        """Export database to CSV"""
        data = self.mpDB.export_data()
        if data is not None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
            if file_path:
                # add csv if user didnt enter
                if not file_path.endswith(".csv"):
                    file_path += ".csv"

                # without the index, so the file can be imported (migrated) again; pandas
                # handles line endings (text mode on Windows added blank lines)
                data.to_csv(file_path, index=False, encoding="utf-8")
                logger.info(f"Data exported to: {file_path}")
        else:
            dialog = AlertPopup(self, prompt="No data to export.")
            if dialog.exec():
                del dialog

    # ==========================================================================
    # OTHER OPTIONS
    # ==========================================================================
    def clear_data(self):
        """
        Clear all media and ROIs from the database
        USED FOR DEBUGGING PURPOSES ONLY
        """
        dialog = AlertPopup(self, "This will delete all media and ROIs. Are you sure you want continue?")
        if dialog.exec():
            self.mpDB.info()
            logger.warning("DELETING DATA")
            clear_project_data(self.mpDB)
        del dialog
