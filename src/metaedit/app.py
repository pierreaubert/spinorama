from __future__ import annotations

from typing import Any, Optional, get_args, cast

import argparse
import sys
import os
import shutil
import json

from PySide6 import QtWidgets  # type: ignore[reportMissingImports]
from PySide6.QtCore import Qt, QSize, QCoreApplication  # type: ignore[reportMissingImports]
from PySide6.QtGui import QPixmap, QIcon, QFont, QTextOption  # type: ignore[reportMissingImports]
from PySide6.QtWidgets import (  # type: ignore[reportMissingImports]
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from metaedit import api
from metaedit.models import SpeakerMetadata, Measurement, export_speaker_metadata
from metaedit.merger import apply_merge
from metaedit.style import (
    apply_app_style,
    install_theme_menu,
    read_theme_from_settings,
)
from metaedit.gitops import create_metadata_pr, preflight_repo

# Image directories (can be monkeypatched in tests)
ICONS_DIR = os.path.join("datas", "icons")
PICTURES_DIR = os.path.join("datas", "pictures")


class SelectSpeakerPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Step 1: Select or Create Speaker")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Existing vs New (at top but will be moved to bottom visually)
        self.opt_group = QButtonGroup(self)
        opt_row = QHBoxLayout()
        opt_row.addStretch(1)  # Add stretch to center the buttons
        self.rb_existing = QRadioButton("Existing")
        self.rb_new = QRadioButton("New")
        # Make the primary choice controls visually prominent
        for rb in (self.rb_existing, self.rb_new):
            rb.setStyleSheet("font-size: 16px; font-weight: 600; padding: 6px 10px;")
            rb.setMinimumHeight(32)
        self.rb_existing.setChecked(True)
        self.opt_group.addButton(self.rb_existing)
        self.opt_group.addButton(self.rb_new)
        opt_row.addWidget(self.rb_existing)
        opt_row.addWidget(self.rb_new)
        opt_row.addStretch(1)  # Add stretch to center the buttons
        # Add a spacer widget to push the radio buttons to the bottom later
        layout.addLayout(opt_row)

        # Existing speaker selection with search (grouped so we can hide/show cleanly)
        self.speakers_cb = QComboBox()
        self.speakers_cb.setObjectName("cb_speakers")
        self.speakers_search = QLineEdit()
        self.speakers_search.setPlaceholderText("Search speakers...")
        self.speakers_search.setObjectName("le_speakers_search")
        self.existing_group = QWidget()
        existing_form = QFormLayout(self.existing_group)
        existing_form.addRow("Search:", self.speakers_search)
        existing_form.addRow("Speaker:", self.speakers_cb)
        layout.addWidget(self.existing_group)

        # New speaker inputs (grouped so we can hide/show cleanly)
        self.brands_cb = QComboBox()
        self.new_brand = QLineEdit()
        self.new_brand.setMinimumWidth(260)
        self.new_speaker_model = QLineEdit()
        self.new_speaker_model.setMinimumWidth(260)
        self.new_group = QWidget()
        new_form = QFormLayout(self.new_group)
        new_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        new_form.addRow("Brand (select):", self.brands_cb)
        new_form.addRow("Brand (new):", self.new_brand)
        new_form.addRow("Model:", self.new_speaker_model)

        # Toggle visibility on radio change
        def _toggle():
            is_existing = self.rb_existing.isChecked()
            # Hide irrelevant controls for a cleaner UI
            self.existing_group.setVisible(is_existing)
            self.new_group.setVisible(not is_existing)
            # Force update
            QApplication.processEvents()

        self.rb_existing.toggled.connect(_toggle)  # type: ignore[arg-type]
        self.rb_new.toggled.connect(_toggle)  # type: ignore[arg-type]
        layout.addWidget(self.existing_group)
        layout.addWidget(self.new_group)

        # Move the radio buttons row to the bottom by adding a stretch
        layout.addStretch(1)
        # Add the radio buttons at the bottom
        layout.addLayout(opt_row)

        # Set initial state after widgets are added to layout
        # Show existing speaker options by default since it's the default selection
        self.existing_group.setVisible(True)
        self.new_group.setVisible(False)
        # Force layout update
        self.existing_group.adjustSize()
        self.new_group.adjustSize()

        # Navigation
        nav = QHBoxLayout()
        nav.addStretch(1)
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("btn_next_select")
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        # Cached for client-side filtering; populated via ``set_speakers``.
        self._all_speakers: list[str] = []

    def set_speakers(self, speakers: list[str]) -> None:
        """Replace the speaker combobox contents and remember the full list."""
        self._all_speakers = list(speakers)
        self.speakers_cb.clear()
        self.speakers_cb.addItems([""] + self._all_speakers)

    def set_brands(self, brands: list[str]) -> None:
        self.brands_cb.clear()
        self.brands_cb.addItems([""] + list(brands))

    def filter_speakers(self, search_text: str) -> None:
        """Filter the speaker combobox by substring match (case-insensitive)."""
        self.speakers_cb.clear()
        if not search_text.strip():
            self.speakers_cb.addItems([""] + self._all_speakers)
            return

        needle = search_text.lower()
        matches = [s for s in self._all_speakers if needle in s.lower()]
        self.speakers_cb.addItems([""] + matches)

        # Auto-select if there's exactly one exact-text match.
        if len(matches) == 1 and matches[0].lower() == needle:
            index = self.speakers_cb.findText(matches[0])
            if index >= 0:
                self.speakers_cb.setCurrentIndex(index)


class EditMetadataPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Step 2: Edit Metadata")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        # Top area: 3 columns (two form columns + picture as last column)
        self.form_brand = QLineEdit()
        self.form_brand.setMinimumWidth(260)
        self.form_model = QLineEdit()
        self.form_model.setMinimumWidth(260)
        self.form_type_cb = QComboBox()
        self.form_shape_cb = QComboBox()
        self.form_price = QLineEdit()
        self.form_amount = QComboBox()
        self.form_amount.setObjectName("form_amount")
        self.form_amount.addItems(["each", "pair"])

        # Create a container with visual separation for the top area
        top_container = QFrame()
        top_container.setFrameShape(QFrame.Shape.StyledPanel)
        top_container.setFrameShadow(QFrame.Shadow.Raised)
        top_container_layout = QVBoxLayout(top_container)
        top_container_layout.setContentsMargins(10, 10, 10, 10)

        top_grid = QtWidgets.QGridLayout()
        # Two form columns
        form_col1 = QFormLayout()
        form_col1.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_col2 = QFormLayout()
        form_col2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_col1.addRow("Brand:", self.form_brand)
        form_col1.addRow("Model:", self.form_model)
        form_col1.addRow("Type:", self.form_type_cb)
        form_col2.addRow("Shape:", self.form_shape_cb)
        form_col2.addRow("Price:", self.form_price)
        form_col2.addRow("Amount:", self.form_amount)
        col1_host = QWidget()
        col1_host.setLayout(form_col1)
        col2_host = QWidget()
        col2_host.setLayout(form_col2)
        top_grid.addWidget(col1_host, 0, 0)
        top_grid.addWidget(col2_host, 0, 1)

        # Picture as third column with 2:3 vertical ratio + choose button
        pic_frame = QFrame()
        pic_frame.setObjectName("picture_frame")
        pic_col = QVBoxLayout(pic_frame)
        pic_col.setContentsMargins(8, 8, 8, 8)
        pic_col.setSpacing(8)
        self.picture_label = QLabel()
        self.picture_label.setObjectName("speaker_picture")
        self.picture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Enforce a vertical 2:3 aspect label size
        self.picture_label.setFixedSize(200, 300)
        self.picture_label.setText("No image")
        self.picture_label.setScaledContents(False)
        pic_col.addWidget(self.picture_label)
        self.choose_picture_btn = QPushButton("Choose Picture…")
        self.choose_picture_btn.setObjectName("btn_choose_picture")
        pic_col.addWidget(self.choose_picture_btn)
        top_grid.addWidget(pic_frame, 0, 2)
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(2, 0)
        top_container_layout.addLayout(top_grid)
        outer.addWidget(top_container)

        # Measurements area: default selector at top + tabs
        # Create a container with visual separation for the measurements area
        meas_container = QFrame()
        meas_container.setFrameShape(QFrame.Shape.StyledPanel)
        meas_container.setFrameShadow(QFrame.Shadow.Raised)
        meas_container_layout = QVBoxLayout(meas_container)
        meas_container_layout.setContentsMargins(10, 10, 10, 10)

        # Default measurement selector (now at top of measurements area) with inline Add button
        self.default_meas_cb = QComboBox()
        self.default_meas_cb.setEditable(False)
        self.default_meas_cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.add_meas_btn = QPushButton("Add Measurement")
        dm_form = QFormLayout()
        dm_row = QWidget()
        dm_row_lay = QHBoxLayout(dm_row)
        dm_row_lay.setContentsMargins(0, 0, 0, 0)
        dm_row_lay.addWidget(self.default_meas_cb)
        dm_row_lay.addWidget(self.add_meas_btn)
        dm_row_lay.addStretch(1)
        dm_form.addRow("Default measurement:", dm_row)
        meas_container_layout.addLayout(dm_form)

        # Tabs for measurements (centered with enhanced visibility for selected tab)
        from PySide6.QtWidgets import QTabWidget  # type: ignore[reportMissingImports]

        self.measurements_tabs = QTabWidget()
        self.measurements_tabs.setObjectName("meas_tabs")
        # Center the tab bar
        self.measurements_tabs.tabBar().setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
                margin: 2px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f0f0f0;
            }
            QTabBar::tab:selected {
                background: #007acc;
                color: white;
                font-weight: bold;
                border-color: #005a9e;
            }
            QTabBar::tab:hover:!selected {
                background: #d0d0d0;
            }
        """)
        meas_container_layout.addWidget(self.measurements_tabs, 1)
        outer.addWidget(meas_container, 1)

        # Navigation buttons
        btns = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("btn_back_edit")
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("btn_next_edit")
        btns.addWidget(self.back_btn)
        btns.addStretch(1)
        btns.addWidget(self.next_btn)
        outer.addLayout(btns)

        # Model + per-session state. The controller calls ``set_current`` when
        # entering this step; the page reads back from ``current`` (e.g. to
        # decide which picture to show, or to store one chosen via the dialog).
        self.current: Optional[SpeakerMetadata] = None
        self._custom_picture_path: str | None = None

    def set_current(self, model: Optional[SpeakerMetadata]) -> None:
        """Bind a speaker metadata model to the page (called on entry)."""
        self.current = model
        self._custom_picture_path = None

    # ------------------------------------------------------------------
    # Page-internal widget helpers (used by the controller and by the
    # form-collection routines on the main window).
    # ------------------------------------------------------------------

    def init_type_shape_options(self) -> None:
        """Populate the Type/Shape combos with the allowed values."""
        types = ["passive", "active"]
        try:
            from datas import SpeakerShape  # type: ignore

            shapes = list(get_args(SpeakerShape))
        except Exception:
            shapes = [
                "floorstanders",
                "bookshelves",
                "center",
                "surround",
                "omnidirectional",
                "columns",
                "cbt",
                "outdoor",
                "panel",
                "inwall",
                "soundbar",
                "liveportable",
                "toursound",
                "cinema",
            ]
        self.form_type_cb.clear()
        self.form_type_cb.addItems(types)
        self.form_shape_cb.clear()
        # No open choice for shape -> no empty entry
        self.form_shape_cb.addItems(shapes)

    def apply_type_rules_to_panels(self) -> None:
        """Disable per-measurement sensitivity/impedance when type is ``active``."""
        is_active = self.form_type_cb.currentText().strip().lower() == "active"
        for i in range(self.measurements_tabs.count()):
            panel = self.measurements_tabs.widget(i)
            sp_sens: QLineEdit | None = panel.findChild(QLineEdit, "sp_sens")  # type: ignore[assignment]
            sp_imp: QLineEdit | None = panel.findChild(QLineEdit, "sp_imp")  # type: ignore[assignment]
            if sp_sens is not None:
                sp_sens.setDisabled(is_active)
            if sp_imp is not None:
                sp_imp.setDisabled(is_active)

    def format_changed_set_quality(self, fmt: str, quality_cb: QComboBox) -> None:
        """Klippel measurements are always ``high`` quality — auto-set it."""
        if fmt.strip().lower() == "klippel":
            idx = quality_cb.findText("high")
            if idx >= 0:
                quality_cb.setCurrentIndex(idx)

    def collect_current_measurement_keys(self) -> list[str]:
        """Return the non-empty key strings from every measurement-panel tab."""
        keys: list[str] = []
        for i in range(self.measurements_tabs.count()):
            panel = self.measurements_tabs.widget(i)
            le: QLineEdit | None = panel.findChild(QLineEdit, "meas_key")  # type: ignore[assignment]
            key = le.text().strip() if le else ""
            if key:
                keys.append(key)
        return keys

    def sync_default_measurements(self) -> None:
        """Refresh the ``default measurement`` combo from current panel keys."""
        keys = self.collect_current_measurement_keys()
        current = self.default_meas_cb.currentText()
        self.default_meas_cb.blockSignals(True)
        self.default_meas_cb.clear()
        self.default_meas_cb.addItems([""] + keys)
        if current in keys:
            idx = self.default_meas_cb.findText(current)
            if idx >= 0:
                self.default_meas_cb.setCurrentIndex(idx)
        self.default_meas_cb.blockSignals(False)

    def add_measurement_panel(self, key: str | None = None, meas: object | None = None) -> None:
        # Build a small panel for measurement editing (to be placed in a tab)
        panel = QWidget()
        lay = QVBoxLayout(panel)

        # Top row
        row1 = QHBoxLayout()
        le_key = QLineEdit()
        le_key.setObjectName("meas_key")
        if isinstance(key, str):
            le_key.setText(key)
        row1.addWidget(QLabel("Key:"))
        row1.addWidget(le_key)
        le_origin = QLineEdit()
        le_origin.setObjectName("meas_origin")
        if isinstance(meas, dict) and "origin" in meas and isinstance(meas["origin"], str):
            le_origin.setText(meas["origin"])  # type: ignore[arg-type]
        row1.addWidget(QLabel("Origin:"))
        row1.addWidget(le_origin)
        btn_remove = QPushButton("Remove")
        row1.addWidget(btn_remove)
        lay.addLayout(row1)

        # Row 2: combos
        row2 = QHBoxLayout()
        cb_format = QComboBox()
        cb_format.setObjectName("meas_format")
        # Populate from datas.MeasurementFormat when available
        try:
            from datas import MeasurementFormat  # type: ignore

            formats = list(get_args(MeasurementFormat))
        except Exception:
            formats = [
                "klippel",
                "webplotdigitizer",
                "spl_hv_txt",
                "gll_hv_txt",
                "princeton",
                "rew_text_dump",
            ]
        cb_format.addItems([""] + formats)
        if isinstance(meas, dict) and isinstance(meas.get("format"), str):
            idx = cb_format.findText(meas.get("format") or "")
            cb_format.setCurrentIndex(idx if idx >= 0 else 0)
        row2.addWidget(QLabel("Format:"))
        row2.addWidget(cb_format)
        cb_quality = QComboBox()
        cb_quality.setObjectName("meas_quality")
        # Populate from datas.MeasurementQuality when available
        try:
            from datas import MeasurementQuality  # type: ignore

            qualities = list(get_args(MeasurementQuality))
        except Exception:
            qualities = ["low", "medium", "high", "unknown"]
        cb_quality.addItems([""] + qualities)
        if isinstance(meas, dict) and isinstance(meas.get("quality"), str):
            idx = cb_quality.findText(meas.get("quality") or "")
            cb_quality.setCurrentIndex(idx if idx >= 0 else 0)
        # Initial auto: if format is already klippel and no quality set, set to high
        if (
            cb_format.currentText().strip().lower() == "klippel"
            and not cb_quality.currentText().strip()
        ):
            idx_high = cb_quality.findText("high")
            if idx_high >= 0:
                cb_quality.setCurrentIndex(idx_high)
        # Auto: when format == klippel, set quality to high
        cb_format.currentTextChanged.connect(
            lambda txt: self.format_changed_set_quality(txt, cb_quality)
        )  # type: ignore[arg-type]
        row2.addWidget(QLabel("Quality:"))
        row2.addWidget(cb_quality)
        cb_sym = QComboBox()
        cb_sym.setObjectName("meas_symmetry")
        # Populate from datas.Symmetry when available
        try:
            from datas import Symmetry  # type: ignore

            syms = list(get_args(Symmetry))
        except Exception:
            syms = ["none", "coaxial", "vertical", "horizontal"]
        # Ensure 'none' is present and first
        if "none" not in syms:
            syms = ["none"] + syms
        else:
            syms = ["none"] + [s for s in syms if s != "none"]
        cb_sym.addItems(syms)
        sym_val = None
        if isinstance(meas, dict):
            sym_val = meas.get("symmetry")
        else:
            sym_val = getattr(meas, "symmetry", None)
        if isinstance(sym_val, str) and sym_val:
            idx = cb_sym.findText(sym_val)
            cb_sym.setCurrentIndex(idx if idx >= 0 else cb_sym.findText("none"))
        else:
            idx = cb_sym.findText("none")
            cb_sym.setCurrentIndex(idx if idx >= 0 else 0)
        row2.addWidget(QLabel("Symmetry:"))
        row2.addWidget(cb_sym)
        lay.addLayout(row2)

        # Review published date (kept close to Reviews area)
        row_date = QHBoxLayout()
        row_date.setContentsMargins(0, 0, 0, 0)
        row_date.setSpacing(6)
        row_date.addWidget(QLabel("Review published:"))
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setObjectName("meas_review_date")
        rp_val = None
        if isinstance(meas, dict):
            rp_val = meas.get("review_published")
        else:
            rp_val = getattr(meas, "review_published", None)
        if isinstance(rp_val, str) and len(rp_val) == 8:
            try:
                y, m, d = int(rp_val[0:4]), int(rp_val[4:6]), int(rp_val[6:8])
                from PySide6.QtCore import QDate  # type: ignore[reportMissingImports]

                de.setDate(QDate(y, m, d))
                de.setProperty("has_value", True)
            except Exception:
                de.setProperty("has_value", False)
        else:
            # no date provided in metadata; mark as not set
            de.setProperty("has_value", False)
        # If the user changes the date, mark as set so it will be exported
        de.dateChanged.connect(lambda *_: de.setProperty("has_value", True))  # type: ignore[arg-type]
        row_date.addWidget(de)
        # Reviews simple list (right after the date to keep them close together)
        reviews_group = QVBoxLayout()
        reviews_group.setContentsMargins(0, 0, 0, 0)
        reviews_group.setSpacing(6)
        reviews_group.addLayout(row_date)
        reviews_group.addWidget(QLabel("Reviews:"))
        reviews_container = QVBoxLayout()

        def add_review_row(k: str = "", u: str = "") -> None:
            row = QWidget()
            row.setObjectName("review_row")
            rlay = QHBoxLayout(row)
            rk = QLineEdit(k)
            rk.setObjectName("review_key")
            rk.setMaximumWidth(140)  # keys are short; keep the field compact
            ru = QLineEdit(u)
            ru.setObjectName("review_url")
            btn_del = QPushButton("✕")
            rlay.addWidget(QLabel("Key:"))
            rlay.addWidget(rk)
            rlay.addWidget(QLabel("URL:"))
            rlay.addWidget(ru)
            rlay.addWidget(btn_del)
            reviews_container.addWidget(row)

            def _del() -> None:
                row.setParent(None)

            btn_del.clicked.connect(_del)  # type: ignore[arg-type]

        # seed from model
        reviews_map = None
        if isinstance(meas, dict):
            reviews_map = meas.get("reviews")
        else:
            reviews_map = getattr(meas, "reviews", None)
        if isinstance(reviews_map, dict) and reviews_map:
            for rk, ru in reviews_map.items():
                add_review_row(str(rk), str(ru))
        else:
            add_review_row()

        reviews_group.addLayout(reviews_container)
        btn_add_review = QPushButton("Add Review")
        reviews_group.addWidget(btn_add_review, alignment=Qt.AlignmentFlag.AlignLeft)
        btn_add_review.clicked.connect(lambda: add_review_row())  # type: ignore[arg-type]
        # Wrap Reviews in a framed box with a larger header label
        rev_box = QFrame()
        rev_box.setObjectName("reviews_box")
        rev_box.setFrameShape(QFrame.Shape.StyledPanel)
        rev_lay = QVBoxLayout(rev_box)
        rev_header = QLabel("Reviews")
        rev_header.setStyleSheet("font-weight:600; font-size:13px;")
        rev_lay.addWidget(rev_header)
        rev_lay.addLayout(reviews_group)
        lay.addWidget(rev_box)

        # Data Acquisition section (collapsible, hidden by default), 3 columns inside
        da_toggle = QToolButton()
        da_toggle.setText("")
        da_toggle.setObjectName("toggle_da")
        da_toggle.setCheckable(True)
        da_toggle.setChecked(False)
        da_toggle.setArrowType(Qt.ArrowType.RightArrow)
        # Wrap DA in framed box with legend next to toggle
        da_box = QFrame()
        da_box.setObjectName("da_box")
        da_box.setFrameShape(QFrame.Shape.StyledPanel)
        da_box_v = QVBoxLayout(da_box)
        da_box_v.setContentsMargins(6, 2, 6, 2)
        da_box_v.setSpacing(2)
        da_header = QHBoxLayout()
        da_header.setContentsMargins(0, 0, 0, 0)
        da_header.setSpacing(4)
        da_header.addWidget(da_toggle)
        da_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        da_toggle.setIconSize(QSize(12, 12))
        da_toggle.setStyleSheet("QToolButton { padding: 0px; margin: 0px; }")
        da_legend = QLabel("Data Acquisition")
        da_legend.setStyleSheet("font-weight:600; font-size:13px;")
        da_header.addWidget(da_legend)
        da_header.addStretch(1)
        da_box_v.addLayout(da_header)
        da_container = QWidget()
        da_container.setObjectName("da_container")
        da_container.setVisible(False)
        da_container_v = QVBoxLayout(da_container)
        da_cols = QHBoxLayout()
        da_col1 = QFormLayout()
        da_col2 = QFormLayout()
        da_col3 = QFormLayout()
        # Via becomes an editable combo with presets (e.g., GLL) and open edit
        cb_da_via = QComboBox()
        cb_da_via.setObjectName("da_via")
        cb_da_via.setEditable(True)
        # Provide a small set of suggestions; keep editable for free text
        cb_da_via.addItems(["", "GLL"])
        le_da_dist = QLineEdit()
        le_da_dist.setObjectName("da_distance")
        le_da_signal = QLineEdit()
        le_da_signal.setObjectName("da_signal")
        le_da_res = QLineEdit()
        le_da_res.setObjectName("da_resolution")
        le_da_min = QLineEdit()
        le_da_min.setObjectName("da_min")
        le_da_max = QLineEdit()
        le_da_max.setObjectName("da_max")
        cb_da_air = QCheckBox("Air absorption correction")
        cb_da_air.setObjectName("da_air")
        te_da_notes = QTextEdit()
        te_da_notes.setObjectName("da_notes")
        da = None
        if isinstance(meas, dict):
            da = meas.get("data_acquisition")
        else:
            da = getattr(meas, "data_acquisition", None)
        if isinstance(da, dict):
            cb_da_via.setCurrentText(str(da.get("via") or ""))
            le_da_dist.setText(str(da.get("distance") or ""))
            le_da_signal.setText(str(da.get("signal") or ""))
            le_da_res.setText(str(da.get("resolution") or ""))
            le_da_min.setText(str(da.get("min_valid_freq") or ""))
            le_da_max.setText(str(da.get("max_valid_freq") or ""))
            cb_da_air.setChecked(bool(da.get("air_absorbtion") or False))
            te_da_notes.setPlainText(str(da.get("notes") or ""))
        elif da is not None:
            cb_da_via.setCurrentText(str(getattr(da, "via", "") or ""))
            le_da_dist.setText(str(getattr(da, "distance", "") or ""))
            le_da_signal.setText(str(getattr(da, "signal", "") or ""))
            le_da_res.setText(str(getattr(da, "resolution", "") or ""))
            le_da_min.setText(str(getattr(da, "min_valid_freq", "") or ""))
            le_da_max.setText(str(getattr(da, "max_valid_freq", "") or ""))
            cb_da_air.setChecked(bool(getattr(da, "air_absorbtion", False)))
            te_da_notes.setPlainText(str(getattr(da, "notes", "") or ""))
        da_col1.addRow("Via:", cb_da_via)
        da_col1.addRow("Distance (m):", le_da_dist)
        da_col2.addRow("Signal:", le_da_signal)
        da_col2.addRow("Resolution (deg):", le_da_res)
        da_col3.addRow("Min valid freq (Hz):", le_da_min)
        da_col3.addRow("Max valid freq (Hz):", le_da_max)
        da_cols.addLayout(da_col1)
        da_cols.addLayout(da_col2)
        da_cols.addLayout(da_col3)
        da_container_v.addLayout(da_cols)
        da_container_v.addWidget(cb_da_air)
        da_container_v.addWidget(QLabel("Notes:"))
        da_container_v.addWidget(te_da_notes)
        da_box_v.addWidget(da_container)

        # When Via == GLL, prefill defaults if fields are empty
        def _via_changed(txt: str) -> None:
            if txt.strip().lower() == "gll":
                if not le_da_dist.text().strip():
                    le_da_dist.setText("10")
                if not le_da_signal.text().strip():
                    le_da_signal.setText("aes 20Hz-20kHz")
                if not le_da_min.text().strip():
                    le_da_min.setText("20")
                if not le_da_max.text().strip():
                    le_da_max.setText("20000")

        cb_da_via.currentTextChanged.connect(_via_changed)  # type: ignore[arg-type]

        def _toggle_da(checked: bool) -> None:
            da_container.setVisible(checked)
            da_toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

        da_toggle.toggled.connect(_toggle_da)  # type: ignore[arg-type]
        # Ensure container is hidden by default
        da_container.setVisible(False)

        # Extras section (collapsible, hidden by default), 2 columns
        ex_toggle = QToolButton()
        ex_toggle.setText("")
        ex_toggle.setObjectName("toggle_ex")
        ex_toggle.setCheckable(True)
        ex_toggle.setChecked(False)
        ex_toggle.setArrowType(Qt.ArrowType.RightArrow)
        # Wrap Extras in framed box with legend next to toggle
        ex_box = QFrame()
        ex_box.setObjectName("ex_box")
        ex_box.setFrameShape(QFrame.Shape.StyledPanel)
        ex_box_lay = QVBoxLayout(ex_box)
        ex_box_lay.setContentsMargins(6, 2, 6, 2)
        ex_box_lay.setSpacing(2)
        ex_header = QHBoxLayout()
        ex_header.setContentsMargins(0, 0, 0, 0)
        ex_header.setSpacing(4)
        ex_header.addWidget(ex_toggle)
        ex_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        ex_toggle.setIconSize(QSize(12, 12))
        ex_toggle.setStyleSheet("QToolButton { padding: 0px; margin: 0px; }")
        ex_legend = QLabel("Extras")
        ex_legend.setStyleSheet("font-weight:600; font-size:13px;")
        ex_header.addWidget(ex_legend)
        ex_header.addStretch(1)
        ex_box_lay.addLayout(ex_header)
        ex_container = QWidget()
        ex_container.setObjectName("ex_container")
        ex_container.setVisible(False)
        ex_container_lay = QVBoxLayout(ex_container)
        ex_cols = QHBoxLayout()
        ex_form1 = QFormLayout()
        ex_form2 = QFormLayout()
        cb_ex_equed = QCheckBox("Is EQ'd")
        cb_ex_equed.setObjectName("ex_equed")
        le_ex_penalty = QLineEdit()
        le_ex_penalty.setObjectName("ex_penalty")
        ex = None
        if isinstance(meas, dict):
            ex = meas.get("extras")
        else:
            ex = getattr(meas, "extras", None)
        if isinstance(ex, dict):
            cb_ex_equed.setChecked(bool(ex.get("is_equed") or False))
            le_ex_penalty.setText(str(ex.get("score_penalty") or ""))
        elif ex is not None:
            cb_ex_equed.setChecked(bool(getattr(ex, "is_equed", False)))
            le_ex_penalty.setText(str(getattr(ex, "score_penalty", "") or ""))
        ex_form1.addRow(cb_ex_equed)
        ex_form2.addRow("Score penalty:", le_ex_penalty)
        ex_cols.addLayout(ex_form1)
        ex_cols.addLayout(ex_form2)
        ex_container_lay.addLayout(ex_cols)
        ex_box_lay.addWidget(ex_container)

        # Defer adding ex_box to main layout; will be added after specs for ordering
        def _toggle_ex(checked: bool) -> None:
            ex_container.setVisible(checked)
            ex_toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

        ex_toggle.toggled.connect(_toggle_ex)  # type: ignore[arg-type]
        # Ensure container is hidden by default
        ex_container.setVisible(False)

        # Specifications section on 3 columns (expanded fields)
        sp_box = QFrame()
        sp_box.setObjectName("specs_box")
        sp_box.setFrameShape(QFrame.Shape.StyledPanel)
        sp_box_lay = QVBoxLayout(sp_box)
        sp_header = QLabel("Specifications")
        sp_header.setStyleSheet("font-weight:600; font-size:13px;")
        sp_box_lay.addWidget(sp_header)
        sp_cols = QHBoxLayout()
        sp_col1 = QFormLayout()
        sp_col2 = QFormLayout()
        sp_col3 = QFormLayout()
        le_sp_sens = QLineEdit()
        le_sp_sens.setObjectName("sp_sens")
        le_sp_imp = QLineEdit()
        le_sp_imp.setObjectName("sp_imp")
        le_sp_weight = QLineEdit()
        le_sp_weight.setObjectName("sp_weight")
        # Dispersion
        le_sp_disp_h = QLineEdit()
        le_sp_disp_h.setObjectName("sp_disp_h")
        le_sp_disp_v = QLineEdit()
        le_sp_disp_v.setObjectName("sp_disp_v")
        le_sp_h = QLineEdit()
        le_sp_h.setObjectName("sp_h")
        le_sp_w = QLineEdit()
        le_sp_w.setObjectName("sp_w")
        le_sp_d = QLineEdit()
        le_sp_d.setObjectName("sp_d")
        le_sp_spl_peak = QLineEdit()
        le_sp_spl_peak.setObjectName("sp_spl_peak")
        le_sp_spl_long = QLineEdit()
        le_sp_spl_long.setObjectName("sp_spl_long")
        le_sp_spl_max = QLineEdit()
        le_sp_spl_max.setObjectName("sp_spl_max")
        le_sp_spl_mn = QLineEdit()
        le_sp_spl_mn.setObjectName("sp_spl_m_noise")
        le_sp_spl_bn = QLineEdit()
        le_sp_spl_bn.setObjectName("sp_spl_b_noise")
        le_sp_spl_pn = QLineEdit()
        le_sp_spl_pn.setObjectName("sp_spl_pink_noise")
        sp = None
        if isinstance(meas, dict):
            sp = meas.get("specifications")
        else:
            sp = getattr(meas, "specifications", None)
        if isinstance(sp, dict):
            le_sp_sens.setText(str(sp.get("sensitivity") or ""))
            le_sp_imp.setText(str(sp.get("impedance") or ""))
            le_sp_weight.setText(str(sp.get("weight") or ""))
            disp = sp.get("dispersion") if isinstance(sp.get("dispersion"), dict) else None
            if disp is not None:
                le_sp_disp_h.setText(str(disp.get("horizontal") or ""))
                le_sp_disp_v.setText(str(disp.get("vertical") or ""))
            size = sp.get("size") if isinstance(sp.get("size"), dict) else {}
            le_sp_h.setText(str((size or {}).get("height") or ""))
            le_sp_w.setText(str((size or {}).get("width") or ""))
            le_sp_d.setText(str((size or {}).get("depth") or ""))
            # Support both our flat fields and the datas Specifications.SPL structure
            peak_val = sp.get("spl_peak")
            long_val = sp.get("spl_long_term")
            if (peak_val is None) or (long_val is None):
                spl = sp.get("SPL") if isinstance(sp.get("SPL"), dict) else None
                if spl is not None:
                    peak_val = peak_val if peak_val is not None else spl.get("peak")
                    long_val = long_val if long_val is not None else spl.get("continuous")
                    le_sp_spl_max.setText(str(spl.get("max") or ""))
                    le_sp_spl_mn.setText(str(spl.get("m_noise") or ""))
                    le_sp_spl_bn.setText(str(spl.get("b_noise") or ""))
                    le_sp_spl_pn.setText(str(spl.get("pink_noise") or ""))
            le_sp_spl_peak.setText(str(peak_val or ""))
            le_sp_spl_long.setText(str(long_val or ""))
        elif sp is not None:
            le_sp_sens.setText(str(getattr(sp, "sensitivity", "") or ""))
            le_sp_imp.setText(str(getattr(sp, "impedance", "") or ""))
            le_sp_weight.setText(str(getattr(sp, "weight", "") or ""))
            disp = getattr(sp, "dispersion", None)
            if disp is not None:
                le_sp_disp_h.setText(str(getattr(disp, "horizontal", "") or ""))
                le_sp_disp_v.setText(str(getattr(disp, "vertical", "") or ""))
            size = getattr(sp, "size", None)
            if size is not None:
                le_sp_h.setText(str(getattr(size, "height", "") or ""))
                le_sp_w.setText(str(getattr(size, "width", "") or ""))
                le_sp_d.setText(str(getattr(size, "depth", "") or ""))
            le_sp_spl_peak.setText(str(getattr(sp, "spl_peak", "") or ""))
            le_sp_spl_long.setText(str(getattr(sp, "spl_long_term", "") or ""))
            spl = getattr(sp, "spl", None)
            if spl is not None:
                le_sp_spl_max.setText(str(getattr(spl, "max", "") or ""))
                le_sp_spl_mn.setText(str(getattr(spl, "m_noise", "") or ""))
                le_sp_spl_bn.setText(str(getattr(spl, "b_noise", "") or ""))
                le_sp_spl_pn.setText(str(getattr(spl, "pink_noise", "") or ""))
        sp_col1.addRow("Sensitivity (dB):", le_sp_sens)
        sp_col1.addRow("Impedance (Ω):", le_sp_imp)
        # Dispersion grouped in col1
        disp_box = QVBoxLayout()
        disp_box.addWidget(QLabel("Dispersion (deg):"))
        disp_row1 = QHBoxLayout()
        disp_row1.addWidget(QLabel("H:"))
        disp_row1.addWidget(le_sp_disp_h)
        disp_row2 = QHBoxLayout()
        disp_row2.addWidget(QLabel("V:"))
        disp_row2.addWidget(le_sp_disp_v)
        disp_box.addLayout(disp_row1)
        disp_box.addLayout(disp_row2)
        disp_host = QWidget()
        disp_host.setLayout(disp_box)
        sp_col1.addRow(disp_host)
        sp_col2.addRow("Weight (kg):", le_sp_weight)
        # Size fields stacked vertically under a header
        size_box = QVBoxLayout()
        size_box.addWidget(QLabel("Size (mm):"))
        size_row1 = QHBoxLayout()
        size_row1.addWidget(QLabel("H:"))
        size_row1.addWidget(le_sp_h)
        size_row2 = QHBoxLayout()
        size_row2.addWidget(QLabel("W:"))
        size_row2.addWidget(le_sp_w)
        size_row3 = QHBoxLayout()
        size_row3.addWidget(QLabel("D:"))
        size_row3.addWidget(le_sp_d)
        size_box.addLayout(size_row1)
        size_box.addLayout(size_row2)
        size_box.addLayout(size_row3)
        size_host = QWidget()
        size_host.setLayout(size_box)
        sp_col2.addRow(size_host)
        sp_col3.addRow("SPL peak (dB):", le_sp_spl_peak)
        sp_col3.addRow("SPL continuous (dB):", le_sp_spl_long)
        # Extra SPL fields
        sp_col3.addRow("SPL max (dB):", le_sp_spl_max)
        sp_col3.addRow("SPL M-noise (dB):", le_sp_spl_mn)
        sp_col3.addRow("SPL B-noise (dB):", le_sp_spl_bn)
        sp_col3.addRow("SPL pink noise (dB):", le_sp_spl_pn)
        sp_cols.addLayout(sp_col1)
        sp_cols.addLayout(sp_col2)
        sp_cols.addLayout(sp_col3)
        sp_box_lay.addLayout(sp_cols)
        # Add sections to main layout in desired order: Specs, then DA, then Extras
        lay.addWidget(sp_box)
        lay.addWidget(da_box)
        lay.addWidget(ex_box)

        # Remove panel
        def _remove_panel() -> None:
            # Remove the tab containing this panel
            tabs = self.measurements_tabs
            for i in range(tabs.count()):
                if tabs.widget(i) is panel:
                    tabs.removeTab(i)
                    break
            self.sync_default_measurements()

        btn_remove.clicked.connect(_remove_panel)  # type: ignore[arg-type]

        # Keep default measurement options and tab title in sync with key
        def _key_changed() -> None:
            self.sync_default_measurements()
            tabs = self.measurements_tabs
            for i in range(tabs.count()):
                if tabs.widget(i) is panel:
                    tabs.setTabText(i, le_key.text().strip() or "(unnamed)")
                    break

        le_key.textChanged.connect(_key_changed)  # type: ignore[arg-type]

        # Add as a new tab
        self.measurements_tabs.addTab(panel, (key or "").strip() or "(unnamed)")
        # After adding a panel, re-apply rules and sync default selector
        self.apply_type_rules_to_panels()
        self.sync_default_measurements()

    def update_picture(self) -> None:
        """Refresh ``picture_label`` from the model's picture or a brand+model lookup."""
        if not self.current:
            return
        brand = (self.current.brand or "").strip()
        model = (self.current.model or "").strip()

        def _try_set(path: str) -> bool:
            if not path or not os.path.isfile(path):
                return False
            pix = QPixmap(path)
            if pix.isNull():
                return False
            scaled = pix.scaled(
                self.picture_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.picture_label.setPixmap(scaled)
            self.picture_label.setText("")
            return True

        # Prefer model.picture, then the in-session custom path, then a
        # convention-based lookup in datas/icons + datas/pictures.
        explicit = getattr(self.current, "picture", None)
        if isinstance(explicit, str) and _try_set(explicit):
            return
        if self._custom_picture_path and _try_set(self._custom_picture_path):
            return
        if brand and model:
            base_names = [f"{brand} {model}", f"{brand}_{model}"]
            for d in (ICONS_DIR, PICTURES_DIR):
                for bn in base_names:
                    for ext in (".png", ".jpg", ".jpeg", ".webp"):
                        if _try_set(os.path.join(d, bn + ext)):
                            return

        self.picture_label.setText("No image")
        # Empty QPixmap (not None) avoids TypeError downstream.
        self.picture_label.setPixmap(QPixmap())

    def choose_picture(self) -> None:
        """Open a file dialog; copy the chosen image into ``PICTURES_DIR``."""
        if not self.current:
            return
        brand = (self.form_brand.text() or "").strip()
        model = (self.form_model.text() or "").strip()
        if not brand or not model:
            QMessageBox.warning(
                self,
                "Missing fields",
                "Please fill Brand and Model before choosing a picture.",
            )
            return
        from PySide6.QtWidgets import QFileDialog  # type: ignore[reportMissingImports]

        fname, _ = QFileDialog.getOpenFileName(
            self, "Choose Picture", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not fname:
            return

        os.makedirs(PICTURES_DIR, exist_ok=True)

        def sanitize(x: str) -> str:
            return " ".join(x.split())

        base = f"{sanitize(brand)} {sanitize(model)}"
        _, ext = os.path.splitext(fname)
        ext = (ext or ".png").lower()
        dest_path = os.path.join(PICTURES_DIR, base + ext)
        try:
            shutil.copy2(fname, dest_path)
        except Exception as e:
            QMessageBox.critical(self, "Copy failed", f"Failed to copy image: {e}")
            return

        self._custom_picture_path = dest_path
        self.current.picture = dest_path
        self.update_picture()

    def populate_form(self, raw_loaded: dict[str, Any] | None = None) -> None:
        assert self.current is not None
        c = self.current
        p = self
        p.form_brand.setText(c.brand)
        p.form_model.setText(c.model)
        # Set type/shape combos
        if c.type:
            idx = p.form_type_cb.findText(c.type)
            p.form_type_cb.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            p.form_type_cb.setCurrentIndex(0)
        if c.shape:
            idxs = p.form_shape_cb.findText(c.shape)
            p.form_shape_cb.setCurrentIndex(idxs if idxs >= 0 else 0)
        else:
            p.form_shape_cb.setCurrentIndex(0)
        p.form_price.setText(c.price or "")
        # Set amount combobox selection
        if c.amount:
            idxa = p.form_amount.findText(c.amount)
            p.form_amount.setCurrentIndex(idxa if idxa >= 0 else 0)
        else:
            p.form_amount.setCurrentIndex(0)

        # Clear existing measurement tabs
        while p.measurements_tabs.count():
            p.measurements_tabs.removeTab(0)

        raw_meas_map = None
        if isinstance(raw_loaded, dict):
            raw_meas_map = raw_loaded.get("measurements")  # type: ignore[assignment]
        if c.measurements:
            for key, meas in c.measurements.items():
                raw_meas = raw_meas_map.get(key) if isinstance(raw_meas_map, dict) else None
                self.add_measurement_panel(key, raw_meas or meas)
        else:
            self.add_measurement_panel()

        # Populate default measurement options
        p.default_meas_cb.clear()
        keys = list(c.measurements.keys())
        p.default_meas_cb.addItems([""] + keys)
        if c.default_measurement:
            idx = p.default_meas_cb.findText(c.default_measurement)
            if idx >= 0:
                p.default_meas_cb.setCurrentIndex(idx)
        # Apply rules after population
        self.apply_type_rules_to_panels()
        self.sync_default_measurements()
        # Update picture when brand/model text changes
        p.form_brand.textChanged.connect(lambda *_: p.update_picture())  # type: ignore[arg-type]
        p.form_model.textChanged.connect(lambda *_: p.update_picture())  # type: ignore[arg-type]
        p.update_picture()

    def collect_form(self) -> bool:
        if not self.current:
            return False
        p = self
        c = self.current
        c.brand = p.form_brand.text().strip()
        c.model = p.form_model.text().strip()
        c.type = p.form_type_cb.currentText().strip() or None
        c.shape = p.form_shape_cb.currentText().strip() or None
        c.price = p.form_price.text().strip() or None
        c.amount = p.form_amount.currentText().strip() or None

        # Collect measurements from panels (now from tabs)
        new_meas: dict[str, Measurement] = {}
        for i in range(p.measurements_tabs.count()):
            panel = p.measurements_tabs.widget(i)
            key_le: QLineEdit = panel.findChild(QLineEdit, "meas_key")  # type: ignore[assignment]
            origin_le: QLineEdit = panel.findChild(QLineEdit, "meas_origin")  # type: ignore[assignment]
            format_cb: QComboBox = panel.findChild(QComboBox, "meas_format")  # type: ignore[assignment]
            quality_cb: QComboBox = panel.findChild(QComboBox, "meas_quality")  # type: ignore[assignment]
            symmetry_cb: QComboBox = panel.findChild(QComboBox, "meas_symmetry")  # type: ignore[assignment]
            # Review published date
            review_date: QDateEdit = panel.findChild(QDateEdit, "meas_review_date")  # type: ignore[assignment]
            # Data Acquisition fields
            # Via may be QComboBox (editable) or QLineEdit depending on version
            da_via_le: QLineEdit | None = panel.findChild(QLineEdit, "da_via")  # type: ignore[assignment]
            da_via_cb: QComboBox | None = panel.findChild(QComboBox, "da_via")  # type: ignore[assignment]
            da_distance: QLineEdit = panel.findChild(QLineEdit, "da_distance")  # type: ignore[assignment]
            da_signal: QLineEdit = panel.findChild(QLineEdit, "da_signal")  # type: ignore[assignment]
            da_resolution: QLineEdit = panel.findChild(QLineEdit, "da_resolution")  # type: ignore[assignment]
            da_min: QLineEdit = panel.findChild(QLineEdit, "da_min")  # type: ignore[assignment]
            da_max: QLineEdit = panel.findChild(QLineEdit, "da_max")  # type: ignore[assignment]
            da_air: QCheckBox = panel.findChild(QCheckBox, "da_air")  # type: ignore[assignment]
            da_notes: QTextEdit = panel.findChild(QTextEdit, "da_notes")  # type: ignore[assignment]
            # Extras
            ex_equed: QCheckBox = panel.findChild(QCheckBox, "ex_equed")  # type: ignore[assignment]
            ex_penalty: QLineEdit = panel.findChild(QLineEdit, "ex_penalty")  # type: ignore[assignment]
            # Specifications
            sp_sens: QLineEdit = panel.findChild(QLineEdit, "sp_sens")  # type: ignore[assignment]
            sp_imp: QLineEdit = panel.findChild(QLineEdit, "sp_imp")  # type: ignore[assignment]
            sp_weight: QLineEdit = panel.findChild(QLineEdit, "sp_weight")  # type: ignore[assignment]
            sp_disp_h: QLineEdit = panel.findChild(QLineEdit, "sp_disp_h")  # type: ignore[assignment]
            sp_disp_v: QLineEdit = panel.findChild(QLineEdit, "sp_disp_v")  # type: ignore[assignment]
            sp_h: QLineEdit = panel.findChild(QLineEdit, "sp_h")  # type: ignore[assignment]
            sp_w: QLineEdit = panel.findChild(QLineEdit, "sp_w")  # type: ignore[assignment]
            sp_d: QLineEdit = panel.findChild(QLineEdit, "sp_d")  # type: ignore[assignment]
            sp_spl_peak: QLineEdit = panel.findChild(QLineEdit, "sp_spl_peak")  # type: ignore[assignment]
            sp_spl_long: QLineEdit = panel.findChild(QLineEdit, "sp_spl_long")  # type: ignore[assignment]
            sp_spl_max: QLineEdit = panel.findChild(QLineEdit, "sp_spl_max")  # type: ignore[assignment]
            sp_spl_mn: QLineEdit = panel.findChild(QLineEdit, "sp_spl_m_noise")  # type: ignore[assignment]
            sp_spl_bn: QLineEdit = panel.findChild(QLineEdit, "sp_spl_b_noise")  # type: ignore[assignment]
            sp_spl_pn: QLineEdit = panel.findChild(QLineEdit, "sp_spl_pink_noise")  # type: ignore[assignment]
            # Reviews
            reviews: dict[str, str] = {}
            for row in panel.findChildren(QWidget, "review_row"):
                k: QLineEdit = row.findChild(QLineEdit, "review_key")  # type: ignore[assignment]
                u: QLineEdit = row.findChild(QLineEdit, "review_url")  # type: ignore[assignment]
                key = k.text().strip() if k else ""
                val = u.text().strip() if u else ""
                if key and val:
                    reviews[key] = val

            key = key_le.text().strip() if key_le else ""
            if not key:
                QMessageBox.warning(
                    self, "Missing measurement key", "Each measurement requires a key."
                )
                return False

            # helper to parse float
            def pf(x: QLineEdit | None) -> float | None:
                if x is None:
                    return None
                s = x.text().strip()
                if not s:
                    return None
                try:
                    return float(s)
                except Exception:
                    return None

            review_published = None
            if (
                review_date is not None
                and bool(review_date.property("has_value"))
                and review_date.date().isValid()
            ):
                y = review_date.date().year()
                m = review_date.date().month()
                d = review_date.date().day()
                review_published = f"{y:04d}{m:02d}{d:02d}"

            # Helper to get text from via widget
            def gtxt() -> str | None:
                if da_via_cb is not None:
                    return da_via_cb.currentText().strip() or None
                if da_via_le is not None:
                    return da_via_le.text().strip() or None
                return None

            # Build DA and extras first so we can drop blocks that are fully empty
            _da_block = {
                "via": gtxt(),
                "distance": pf(da_distance),
                "signal": da_signal.text().strip() if da_signal else None,
                "resolution": pf(da_resolution),
                "min_valid_freq": pf(da_min),
                "max_valid_freq": pf(da_max),
                "air_absorbtion": bool(da_air.isChecked()) if da_air else None,
                "notes": da_notes.toPlainText().strip() if da_notes else None,
            }

            # Consider block empty when all values are None or False
            def _block_empty(d: dict[str, object | None]) -> bool:
                for _vk, _vv in d.items():
                    if _vv is None:
                        continue
                    if isinstance(_vv, bool) and _vv is False:
                        continue
                    if isinstance(_vv, str) and _vv.strip() == "":
                        continue
                    return False
                return True

            da_block = None if _block_empty(_da_block) else _da_block

            _ex_block = {
                "is_equed": bool(ex_equed.isChecked()) if ex_equed else None,
                "score_penalty": pf(ex_penalty),
            }
            ex_block = None if _block_empty(_ex_block) else _ex_block

            m_dict = {
                "origin": origin_le.text().strip() if origin_le else None,
                "format": format_cb.currentText() if format_cb else None,
                "quality": quality_cb.currentText() if quality_cb else None,
                "symmetry": symmetry_cb.currentText() if symmetry_cb else None,
                "reviews": reviews,
                "review_published": review_published,
                "data_acquisition": da_block,
                "extras": ex_block,
                "specifications": {
                    "sensitivity": pf(sp_sens),
                    "impedance": pf(sp_imp),
                    "weight": pf(sp_weight),
                    "size": {
                        "height": pf(sp_h),
                        "width": pf(sp_w),
                        "depth": pf(sp_d),
                    },
                    # Keep flat fields for backward compatibility
                    "spl_peak": pf(sp_spl_peak),
                    "spl_long_term": pf(sp_spl_long),
                    # Expanded
                    "dispersion": {
                        "horizontal": pf(sp_disp_h),
                        "vertical": pf(sp_disp_v),
                    },
                    # Use alias 'SPL' expected by datas.Specifications
                    "SPL": {
                        "peak": pf(sp_spl_peak),
                        "continuous": pf(sp_spl_long),
                        "max": pf(sp_spl_max),
                        "m_noise": pf(sp_spl_mn),
                        "b_noise": pf(sp_spl_bn),
                        "pink_noise": pf(sp_spl_pn),
                    },
                },
            }
            new_meas[key] = Measurement.model_validate(m_dict)

        c.measurements = new_meas
        # Default measurement
        c.default_measurement = p.default_meas_cb.currentText().strip() or None
        return True


class ReviewExportPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Step 3: Review & Export")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)
        btns = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("btn_back_review")
        self.diff_btn = QPushButton("Show Diff")
        self.diff_btn.setObjectName("btn_diff_review")
        self.diff_btn.setVisible(False)
        self.export_btn = QPushButton("Copy JSON to Clipboard")
        self.apply_btn = QPushButton("Apply to repository")
        self.start_over_btn = QPushButton("Start Over")
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("btn_exit_review")
        btns.addWidget(self.back_btn)
        btns.addStretch(1)
        btns.addWidget(self.diff_btn)
        btns.addWidget(self.export_btn)
        btns.addWidget(self.apply_btn)
        btns.addWidget(self.start_over_btn)
        btns.addWidget(self.exit_btn)
        layout.addLayout(btns)


class MetadataMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spinorama Metadata Manager (Qt)")
        self.resize(1000, 700)
        # Set a window icon if available
        try:
            icon_path = os.path.join(ICONS_DIR, "3d3a.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        self.stack = QStackedWidget()
        self.page_select = SelectSpeakerPage()
        self.page_edit = EditMetadataPage()
        self.page_review = ReviewExportPage()
        self.stack.addWidget(self.page_select)
        self.stack.addWidget(self.page_edit)
        self.stack.addWidget(self.page_review)
        self.setCentralWidget(self.stack)

        # Menus (theme toggle)
        install_theme_menu(self)

        # Wire navigation
        self.page_select.next_btn.clicked.connect(self._to_edit)  # type: ignore[arg-type]
        self.page_edit.back_btn.clicked.connect(self._to_select)  # type: ignore[arg-type]
        self.page_edit.next_btn.clicked.connect(self._to_review)  # type: ignore[arg-type]
        self.page_review.back_btn.clicked.connect(self._back_to_edit)  # type: ignore[arg-type]
        self.page_review.export_btn.clicked.connect(self._copy_export)  # type: ignore[arg-type]
        self.page_review.diff_btn.clicked.connect(self._show_diff)  # type: ignore[arg-type]
        self.page_review.apply_btn.clicked.connect(self._apply_merge)  # type: ignore[arg-type]
        self.page_review.exit_btn.clicked.connect(self.close)  # type: ignore[arg-type]
        # Wire search functionality (delegated to the page)
        self.page_select.speakers_search.textChanged.connect(
            self.page_select.filter_speakers
        )  # type: ignore[arg-type]
        self.page_edit.add_meas_btn.clicked.connect(self._add_measurement_panel)  # type: ignore[arg-type]
        self.page_review.start_over_btn.clicked.connect(self._start_over)  # type: ignore[arg-type]
        # Picture choose handler
        self.page_edit.choose_picture_btn.clicked.connect(self.page_edit.choose_picture)  # type: ignore[arg-type]

        # Load initial data. The page now owns its own picture/session state.
        self._raw_loaded = None
        self._baseline_export: dict[str, Any] | None = None
        self._load_initial()

        # Initialize type/shape options and rules
        self.page_edit.init_type_shape_options()
        self.page_edit.form_type_cb.currentTextChanged.connect(
            lambda _: self.page_edit.apply_type_rules_to_panels()
        )  # type: ignore[arg-type]

    # Data state
    speakers: list[str] = []
    brands: list[str] = []
    current: Optional[SpeakerMetadata] = None

    def _load_initial(self) -> None:
        # Simple blocking load to keep it minimal; could be threaded.
        self.speakers = api.get_speakers()
        self.brands = api.get_brands()
        self.page_select.set_speakers(self.speakers)
        self.page_select.set_brands(self.brands)

    # Navigation slots
    def _to_select(self) -> None:
        self.stack.setCurrentWidget(self.page_select)

    def _back_to_edit(self) -> None:
        # From Step 3 back to Step 2 without reloading/asking selection again
        # Preserve the current context and edits already present in the form
        self.stack.setCurrentWidget(self.page_edit)

    def _to_edit(self) -> None:
        # Decide existing vs new
        if self.page_select.rb_existing.isChecked():
            name = self.page_select.speakers_cb.currentText().strip()
            if not name:
                QMessageBox.warning(self, "Missing selection", "Please select a speaker.")
                return
            data = api.get_speaker_metadata(name)
            if not data:
                QMessageBox.critical(self, "Load failed", f"Failed to load metadata for '{name}'.")
                return
            data = SpeakerMetadata.convert_legacy_reviews(data)
            # Keep a copy of the raw dict to allow richer prefill (e.g., Specifications.SPL)
            self._raw_loaded = data
            self.current = SpeakerMetadata(**data)
            # Establish baseline (pruned) for diff in review
            try:
                self._baseline_export = export_speaker_metadata(SpeakerMetadata(**data))
            except Exception:
                self._baseline_export = None
        else:
            brand = (
                self.page_select.brands_cb.currentText().strip()
                or self.page_select.new_brand.text().strip()
            )
            model = self.page_select.new_speaker_model.text().strip()
            if not brand or not model:
                QMessageBox.warning(self, "Missing fields", "Please provide both brand and model.")
                return
            self.current = SpeakerMetadata(brand=brand, model=model)
            self._baseline_export = None

        # Bind the model to the page (also resets any in-session custom picture).
        self.page_edit.set_current(self.current)
        self._populate_form()
        self.stack.setCurrentWidget(self.page_edit)

    def _to_review(self) -> None:
        # Collect form data to current model
        if not self._collect_form():
            return
        # Summarize and go to review
        import json

        if not self.current:
            return
        # Build pruned export JSON so empty fields/blocks are omitted
        export_dict = export_speaker_metadata(self.current)
        self.page_review.summary.setPlainText(json.dumps(export_dict, indent=2, sort_keys=True))
        # Toggle diff button: show only for existing speakers when there are changes
        show_diff = False
        if isinstance(self._baseline_export, dict):
            try:
                show_diff = self._baseline_export != export_dict
            except Exception:
                show_diff = True
        self.page_review.diff_btn.setVisible(show_diff)
        self.stack.setCurrentWidget(self.page_review)

    def _copy_export(self) -> None:
        # Copy pruned JSON to clipboard
        import json

        if not self.current:
            return
        data = export_speaker_metadata(self.current)
        QApplication.clipboard().setText(json.dumps(data, indent=2, sort_keys=True))
        QMessageBox.information(self, "Copied", "Metadata JSON copied to clipboard.")

    def _apply_merge(self) -> None:
        # Apply current export into datas/metadata_*.py via merger
        try:
            if not self.current:
                QMessageBox.warning(self, "No data", "No current speaker to apply.")
                return
            # Preflight: ensure repo is on 'develop' and up-to-date before writing any file
            ok_repo, msg_repo = preflight_repo(required_branch="develop")
            if not ok_repo:
                QMessageBox.warning(
                    self,
                    "Repository not ready",
                    f"Cannot apply changes because repository is not ready:\n{msg_repo}",
                )
                return
            # Ensure form is collected so Step 2 changes are included if user navigated back
            self._collect_form()
            export_dict = export_speaker_metadata(self.current)
            file_path, key = apply_merge(export_dict)
            # Reload in-memory DB and refresh step 1 lists
            try:
                api.reload_metadata()  # type: ignore[attr-defined]
                self._load_initial()
            except Exception:
                pass
            # Attempt to create a PR with metadata and picture
            changed: list[str] = [file_path]
            try:
                pic_path = cast(str, getattr(self.current, "picture", "") or "")
                if pic_path and os.path.isfile(pic_path):
                    changed.append(pic_path)
            except Exception:
                pass

            ok, msg = create_metadata_pr(changed, key)
            if ok:
                QMessageBox.information(
                    self,
                    "Applied & Git actions",
                    f"Merged entry for '{key}'.\n{msg}",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Applied but PR not created",
                    f"Merged entry for '{key}' into:\n{file_path}\n\nGit/PR step failed: {msg}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Apply failed", f"Failed to apply: {e}")

    def _show_diff(self) -> None:
        # Show unified diff between baseline (loaded) and current export
        if not self.current or not isinstance(self._baseline_export, dict):
            return
        import json
        import difflib

        current = export_speaker_metadata(self.current)
        baseline_text = json.dumps(self._baseline_export, indent=2, sort_keys=True)
        current_text = json.dumps(current, indent=2, sort_keys=True)
        diff_lines = difflib.unified_diff(
            baseline_text.splitlines(),
            current_text.splitlines(),
            fromfile="original",
            tofile="current",
            lineterm="",
        )
        diff_text = "\n".join(diff_lines) or "No changes."

        dlg = QDialog(self)
        dlg.setWindowTitle("Metadata Diff")
        vbox = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(diff_text)
        vbox.addWidget(te)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)  # type: ignore[arg-type]
        vbox.addWidget(btn_close)
        dlg.resize(800, 600)
        dlg.exec()

    # Form helpers
    def _populate_form(self) -> None:
        """Forwarder: page owns the form widgets and (de)serialisation."""
        self.page_edit.populate_form(self._raw_loaded)

    def _collect_form(self) -> bool:
        """Forwarder: page owns the form widgets and (de)serialisation."""
        return self.page_edit.collect_form()

    def _add_measurement_panel(self, key: str | None = None, meas: object | None = None) -> None:
        """Forwarder kept for tests that drive panel creation through the window."""
        self.page_edit.add_measurement_panel(key, meas)

    def _start_over(self) -> None:
        # Reset state and go back to select page
        self.current = None
        self._raw_loaded = None
        # Reset page-owned per-session state.
        self.page_edit.set_current(None)
        # Clear edit page fields
        p = self.page_edit
        p.form_brand.clear()
        p.form_model.clear()
        # Reset combos
        if hasattr(p, "form_type_cb"):
            p.form_type_cb.setCurrentIndex(0)
        if hasattr(p, "form_shape_cb"):
            p.form_shape_cb.setCurrentIndex(0)
        p.form_price.clear()
        # Reset amount to first option (e.g., 'each') without clearing items
        if (
            hasattr(p, "form_amount")
            and isinstance(p.form_amount, QComboBox)
            and p.form_amount.count() > 0
        ):
            p.form_amount.setCurrentIndex(0)
        p.default_meas_cb.clear()
        # Clear measurement tabs
        while p.measurements_tabs.count():
            p.measurements_tabs.removeTab(0)
        self.stack.setCurrentWidget(self.page_select)


def main() -> None:
    parser = argparse.ArgumentParser(description="Spinorama Metadata Manager (Qt)")
    parser.add_argument(
        "-s",
        "--speaker",
        type=str,
        default=None,
        help="Speaker key to open directly in Step 2 (Edit)",
    )
    args = parser.parse_args()

    app = cast(QApplication, QApplication.instance() or QApplication([]))
    # Ensure QSettings works with stable identifiers
    QCoreApplication.setOrganizationName("Spinorama")
    QCoreApplication.setApplicationName("MetadataQt")
    # Apply theme from settings (defaults to light)
    apply_app_style(app, read_theme_from_settings())
    win = MetadataMainWindow()

    # If a specific speaker is requested, try to load it and jump to Step 2
    if args.speaker:
        data = api.get_speaker_metadata(args.speaker)
        if not data:
            print(f"Warning: speaker '{args.speaker}' not found.", file=sys.stderr)
            sys.exit(1)
        # Prefer reusing existing flow: set selection and navigate
        try:
            idx = win.page_select.speakers_cb.findText(args.speaker)
            if idx >= 0:
                win.page_select.speakers_cb.setCurrentIndex(idx)
            win.page_select.rb_existing.setChecked(True)
            win._to_edit()
        except Exception:
            # Fallback: populate directly
            data = SpeakerMetadata.convert_legacy_reviews(data)
            win._raw_loaded = data
            win.current = SpeakerMetadata(**data)
            win._populate_form()
            win.stack.setCurrentWidget(win.page_edit)

    win.show()
    app.exec()


if __name__ == "__main__":
    main()
