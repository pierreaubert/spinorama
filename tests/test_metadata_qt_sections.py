import json
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QFormLayout,
    QLineEdit,
    QToolButton,
    QWidget,
    QComboBox,
    QFrame,
    QLabel,
)

pytestmark = pytest.mark.qt


def _goto_step2(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Navigate to Step 2
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit
    return win


def test_collapsible_sections_default_and_toggle(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    assert tabs.count() >= 1
    panel: QWidget = tabs.widget(0)

    # Find toggles and containers
    da_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_da")
    ex_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_ex")
    da_container: QWidget | None = panel.findChild(QWidget, "da_container")
    ex_container: QWidget | None = panel.findChild(QWidget, "ex_container")

    assert da_toggle is not None and ex_toggle is not None
    assert da_container is not None and ex_container is not None

    # Hidden by default
    assert not da_container.isVisible()
    assert not ex_container.isVisible()

    # Toggle ON
    qtbot.mouseClick(da_toggle, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(ex_toggle, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: da_container.isVisible() and ex_container.isVisible())

    # Toggle OFF
    qtbot.mouseClick(da_toggle, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(ex_toggle, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: (not da_container.isVisible()) and (not ex_container.isVisible()))


def test_extras_two_columns_and_specs_fields_present(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Extras two columns (two QFormLayouts inside ex_container)
    ex_container: QWidget | None = panel.findChild(QWidget, "ex_container")
    assert ex_container is not None
    # The two columns are QFormLayouts; traverse layouts by counting children that are QFormLayout
    form_layouts = ex_container.findChildren(QFormLayout)
    assert len(form_layouts) >= 2

    # Specifications expanded fields present
    assert panel.findChild(QLineEdit, "sp_disp_h") is not None
    assert panel.findChild(QLineEdit, "sp_disp_v") is not None
    assert panel.findChild(QLineEdit, "sp_spl_max") is not None
    assert panel.findChild(QLineEdit, "sp_spl_m_noise") is not None
    assert panel.findChild(QLineEdit, "sp_spl_b_noise") is not None
    assert panel.findChild(QLineEdit, "sp_spl_pink_noise") is not None


def test_collect_form_exports_nested_spec_fields(qtbot):
    from metaedit.app import MetadataMainWindow

    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Fill required key
    le_key = panel.findChild(QLineEdit, "meas_key")
    assert isinstance(le_key, QLineEdit)
    le_key.setText("t1")

    # Fill some specifications fields
    for name, value in (
        ("sp_sens", "87.5"),
        ("sp_imp", "4"),
        ("sp_weight", "12.3"),
        ("sp_h", "300"),
        ("sp_w", "180"),
        ("sp_d", "250"),
    ):
        w = panel.findChild(QLineEdit, name)
        assert isinstance(w, QLineEdit)
        w.setText(value)

    # Dispersion
    w = panel.findChild(QLineEdit, "sp_disp_h")
    assert isinstance(w, QLineEdit)
    w.setText("90")
    w = panel.findChild(QLineEdit, "sp_disp_v")
    assert isinstance(w, QLineEdit)
    w.setText("40")

    # SPL
    for name, value in (
        ("sp_spl_peak", "110"),
        ("sp_spl_long", "98"),
        ("sp_spl_max", "112"),
        ("sp_spl_m_noise", "101"),
        ("sp_spl_b_noise", "99"),
        ("sp_spl_pink_noise", "100"),
    ):
        w = panel.findChild(QLineEdit, name)
        assert isinstance(w, QLineEdit)
        w.setText(value)

    # Proceed to review to trigger _collect_form
    qtbot.mouseClick(win.page_edit.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_review

    # Grab JSON summary
    txt = win.page_review.summary.toPlainText().strip()
    assert txt
    data = json.loads(txt)

    meas = data["measurements"]["t1"]
    specs = meas["specifications"]

    # Flat fields
    assert specs["spl_peak"] == 110.0
    assert specs["spl_long_term"] == 98.0

    # Nested dispersion
    assert specs["dispersion"]["horizontal"] == 90.0
    assert specs["dispersion"]["vertical"] == 40.0

    # Nested SPL alias
    assert "SPL" in specs
    spl = specs["SPL"]
    assert spl["peak"] == 110.0
    assert spl["continuous"] == 98.0
    assert spl["max"] == 112.0
    assert spl["m_noise"] == 101.0
    assert spl["b_noise"] == 99.0
    assert spl["pink_noise"] == 100.0


def test_default_symmetry_and_group_boxes_present(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Default symmetry is 'none'
    cb: QComboBox | None = panel.findChild(QComboBox, "meas_symmetry")
    assert cb is not None
    assert cb.currentText().strip().lower() == "none"

    # Group frames exist with headers
    for obj, header in (
        ("reviews_box", "Reviews"),
        ("specs_box", "Specifications"),
        ("da_box", "Data Acquisition"),
        ("ex_box", "Extras"),
    ):
        box: QFrame | None = panel.findChild(QFrame, obj)
        assert box is not None
        # A QLabel child with the expected header text exists inside the box
        labels = box.findChildren(QLabel)
        assert any(l.text() == header for l in labels)


def test_amount_combobox_and_shape_no_empty(qtbot):
    win = _goto_step2(qtbot)

    # Amount is a combobox with fixed options
    amt = win.page_edit.form_amount
    assert isinstance(amt, QComboBox)
    items = [amt.itemText(i) for i in range(amt.count())]
    assert items == ["each", "pair"]

    # Shape has no empty option
    shp = win.page_edit.form_shape_cb
    assert isinstance(shp, QComboBox)
    shp_items = [shp.itemText(i) for i in range(shp.count())]
    assert "" not in shp_items
    assert shp_items[0] != ""


def test_specs_before_da_and_extras_and_brand_model_wider(qtbot):
    from typing import cast

    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Ordering: Specifications comes before DA and Extras in the main panel layout
    layout = panel.layout()
    assert layout is not None
    specs_box = panel.findChild(QFrame, "specs_box")
    da_box = panel.findChild(QFrame, "da_box")
    ex_box = panel.findChild(QFrame, "ex_box")
    assert specs_box and da_box and ex_box
    idx_specs = layout.indexOf(specs_box)
    idx_da = layout.indexOf(da_box)
    idx_ex = layout.indexOf(ex_box)
    assert 0 <= idx_specs < idx_da
    assert 0 <= idx_specs < idx_ex

    # Brand/Model fields are wider (min width >= 260)
    assert win.page_edit.form_brand.minimumWidth() >= 260
    assert win.page_edit.form_model.minimumWidth() >= 260


def test_collapsed_headers_compact(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # DA toggle icon size small and margins reduced
    da_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_da")
    assert da_toggle is not None
    icon_sz: QSize = da_toggle.iconSize()
    assert icon_sz.width() <= 12 and icon_sz.height() <= 12

    # Layout margins on DA box are compact
    da_box: QFrame | None = panel.findChild(QFrame, "da_box")
    assert da_box is not None
    lay = da_box.layout()
    assert lay is not None
    m = lay.contentsMargins()
    assert m.left() <= 6 and m.top() <= 4 and m.right() <= 6 and m.bottom() <= 4


def test_extras_header_compact(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Extras toggle icon size small and margins reduced
    ex_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_ex")
    assert ex_toggle is not None
    icon_sz: QSize = ex_toggle.iconSize()
    assert icon_sz.width() <= 12 and icon_sz.height() <= 12

    # Layout margins on Extras box are compact
    ex_box: QFrame | None = panel.findChild(QFrame, "ex_box")
    assert ex_box is not None
    lay = ex_box.layout()
    assert lay is not None
    m = lay.contentsMargins()
    assert m.left() <= 6 and m.top() <= 4 and m.right() <= 6 and m.bottom() <= 4
