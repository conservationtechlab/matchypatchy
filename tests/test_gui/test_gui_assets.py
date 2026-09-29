"""
Tests for matchypatchy.gui.widgets.gui_assets — custom Qt widget classes.

PyQt6 is stubbed out in conftest.py.  These tests verify that all widget
module files are importable and that the expected names are exported.
"""
import pytest

# All imports go through the already-stubbed sys.modules from conftest.py
from matchypatchy.gui.widgets import gui_assets
from matchypatchy.gui.widgets import widget_filterbar
from matchypatchy.gui.widgets import widget_media
from matchypatchy.gui.widgets import widget_image_adjustment


# ---------------------------------------------------------------------------
# Import sanity
# ---------------------------------------------------------------------------

class TestGuiModuleImports:
    """Verify that all GUI widget modules import without error."""

    def test_gui_assets_importable(self):
        assert gui_assets is not None

    def test_widget_filterbar_importable(self):
        assert widget_filterbar is not None

    def test_widget_media_importable(self):
        assert widget_media is not None

    def test_widget_image_adjustment_importable(self):
        assert widget_image_adjustment is not None


# ---------------------------------------------------------------------------
# Exported names in gui_assets
# ---------------------------------------------------------------------------

class TestGuiAssetsExports:
    """Verify that all expected names exist in the gui_assets module."""

    def test_vertical_separator_present(self):
        assert hasattr(gui_assets, "VerticalSeparator")

    def test_horizontal_separator_present(self):
        assert hasattr(gui_assets, "HorizontalSeparator")

    def test_standard_button_present(self):
        assert hasattr(gui_assets, "StandardButton")

    def test_combo_box_separator_present(self):
        assert hasattr(gui_assets, "ComboBoxSeparator")

    def test_combo_box_delegate_present(self):
        assert hasattr(gui_assets, "ComboBoxDelegate")

    def test_three_point_slider_present(self):
        assert hasattr(gui_assets, "ThreePointSlider")

    def test_clickable_slider_present(self):
        assert hasattr(gui_assets, "ClickableSlider")

    def test_text_edit_with_signal_present(self):
        assert hasattr(gui_assets, "TextEditWithSignal")


# ---------------------------------------------------------------------------
# Exported names in widget_filterbar
# ---------------------------------------------------------------------------

class TestFilterBarExports:
    def test_filter_bar_present(self):
        assert hasattr(widget_filterbar, "FilterBar")

    def test_filter_box_present(self):
        assert hasattr(widget_filterbar, "FilterBox")


# ---------------------------------------------------------------------------
# Exported names in widget_media
# ---------------------------------------------------------------------------

class TestMediaWidgetExports:
    def test_image_widget_present(self):
        assert hasattr(widget_media, "ImageWidget")

    def test_media_widget_present(self):
        assert hasattr(widget_media, "MediaWidget")

    def test_video_player_bar_present(self):
        assert hasattr(widget_media, "VideoPlayerBar")

    def test_video_widget_present(self):
        assert hasattr(widget_media, "VideoWidget")


# ---------------------------------------------------------------------------
# Exported names in widget_image_adjustment
# ---------------------------------------------------------------------------

class TestImageAdjustBarExports:
    def test_image_adjust_bar_present(self):
        assert hasattr(widget_image_adjustment, "ImageAdjustBar")


# ---------------------------------------------------------------------------
# Display page modules importable
# ---------------------------------------------------------------------------

class TestDisplayPageImports:
    def test_display_base_importable(self):
        from matchypatchy.gui import display_base
        assert display_base is not None

    def test_display_media_importable(self):
        from matchypatchy.gui import display_media
        assert display_media is not None

    def test_display_compare_importable(self):
        from matchypatchy.gui import display_compare
        assert display_compare is not None

    def test_display_base_has_class(self):
        from matchypatchy.gui import display_base
        assert hasattr(display_base, "DisplayBase")

    def test_display_media_has_class(self):
        from matchypatchy.gui import display_media
        assert hasattr(display_media, "DisplayMedia")

    def test_display_compare_has_class(self):
        from matchypatchy.gui import display_compare
        assert hasattr(display_compare, "DisplayCompare")


# ---------------------------------------------------------------------------
# Dialog modules importable
# ---------------------------------------------------------------------------

class TestDialogImports:
    def test_popup_alert_importable(self):
        from matchypatchy.gui.dialogs import popup_alert
        assert popup_alert is not None

    def test_popup_config_importable(self):
        from matchypatchy.gui.dialogs import popup_config
        assert popup_config is not None

    def test_popup_survey_importable(self):
        from matchypatchy.gui.dialogs import popup_survey
        assert popup_survey is not None

    def test_popup_station_importable(self):
        from matchypatchy.gui.dialogs import popup_station
        assert popup_station is not None

    def test_popup_individual_importable(self):
        from matchypatchy.gui.dialogs import popup_individual
        assert popup_individual is not None

    def test_popup_ml_importable(self):
        from matchypatchy.gui.dialogs import popup_ml
        assert popup_ml is not None

    def test_popup_alert_has_class(self):
        from matchypatchy.gui.dialogs.popup_alert import AlertPopup
        assert AlertPopup is not None

    def test_popup_config_has_class(self):
        from matchypatchy.gui.dialogs import popup_config
        assert hasattr(popup_config, "ConfigPopup")


