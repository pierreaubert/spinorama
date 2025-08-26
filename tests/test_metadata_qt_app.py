import pytest
from PySide6.QtCore import Qt

pytestmark = pytest.mark.qt


def test_window_creation(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    assert win.windowTitle().startswith("Spinorama Metadata Manager")
    # Starts at first page
    assert win.stack.currentWidget() is win.page_select


def test_navigation_flow(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Step 1 -> Step 2
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit

    # Step 2 -> Step 1 (Back)
    qtbot.mouseClick(win.page_edit.back_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_select

    # Step 1 -> Step 2 -> Step 3
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit
    qtbot.mouseClick(win.page_edit.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_review

    # Step 3 -> Step 2 (Back)
    qtbot.mouseClick(win.page_review.back_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit


def test_step2_dynamic_behaviors(qtbot):
    from typing import cast
    from metaedit.app import MetadataMainWindow
    from PySide6.QtWidgets import QComboBox, QLineEdit

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Navigate to Step 2
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit

    # There should be at least one measurement tab by default
    tabs = win.page_edit.measurements_tabs
    assert tabs.count() >= 1
    panel = tabs.widget(0)

    # 1) format "klippel" sets quality to "high"
    cb_format_opt = panel.findChild(QComboBox, "meas_format")
    cb_quality_opt = panel.findChild(QComboBox, "meas_quality")
    assert cb_format_opt is not None and cb_quality_opt is not None
    cb_format = cast(QComboBox, cb_format_opt)
    cb_quality = cast(QComboBox, cb_quality_opt)
    idx = cb_format.findText("klippel")
    assert idx >= 0
    cb_format.setCurrentIndex(idx)
    qtbot.waitUntil(lambda: cb_quality.currentText() == "high")

    # 2) type "active" disables sensitivity and impedance; switching back enables them
    type_cb: QComboBox = win.page_edit.form_type_cb
    idx_active = type_cb.findText("active")
    assert idx_active >= 0
    type_cb.setCurrentIndex(idx_active)
    le_sens_opt = panel.findChild(QLineEdit, "sp_sens")
    le_imp_opt = panel.findChild(QLineEdit, "sp_imp")
    assert le_sens_opt is not None and le_imp_opt is not None
    le_sens = cast(QLineEdit, le_sens_opt)
    le_imp = cast(QLineEdit, le_imp_opt)
    qtbot.waitUntil(lambda: not le_sens.isEnabled() and not le_imp.isEnabled())
    idx_passive = type_cb.findText("passive")
    assert idx_passive >= 0
    type_cb.setCurrentIndex(idx_passive)
    qtbot.waitUntil(lambda: le_sens.isEnabled() and le_imp.isEnabled())

    # 3) editing key updates default measurement selector
    le_key_opt = panel.findChild(QLineEdit, "meas_key")
    assert le_key_opt is not None
    le_key = cast(QLineEdit, le_key_opt)
    le_key.setText("my_meas")
    dm_cb: QComboBox = win.page_edit.default_meas_cb

    def _dm_has_key() -> bool:
        return any(dm_cb.itemText(i) == "my_meas" for i in range(dm_cb.count()))

    qtbot.waitUntil(_dm_has_key)

    # 4) initial populate: creating a panel with format pre-set to klippel sets quality to high
    # Use the internal method to simulate initial population with existing data
    win._add_measurement_panel("init", {"format": "klippel"})  # type: ignore[attr-defined]
    # Find the tab/panel with key == "init"
    found_quality_high = False
    for i in range(tabs.count()):
        p2 = tabs.widget(i)
        le_key2 = p2.findChild(QLineEdit, "meas_key")
        if le_key2 and le_key2.text() == "init":
            cb_quality2 = p2.findChild(QComboBox, "meas_quality")
            assert cb_quality2 is not None
            found_quality_high = cb_quality2.currentText() == "high"
            break
    assert found_quality_high


def test_step1_visibility_toggle_and_radio_prominence(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    sel = win.page_select
    # Initial: Existing selected -> existing group visible, new group hidden
    assert sel.rb_existing.isChecked()
    assert sel.existing_group.isVisible()
    assert not sel.new_group.isVisible()

    # Toggle to New
    sel.rb_new.setChecked(True)
    qtbot.waitUntil(lambda: sel.new_group.isVisible())
    assert not sel.existing_group.isVisible()

    # Back to Existing
    sel.rb_existing.setChecked(True)
    qtbot.waitUntil(lambda: sel.existing_group.isVisible())
    assert not sel.new_group.isVisible()

    # Radios should be visually larger (style/min height)
    assert sel.rb_existing.minimumHeight() >= 32
    assert "font-size: 16px" in sel.rb_existing.styleSheet()


def test_data_acq_via_gll_defaults(qtbot):
    from typing import cast
    from metaedit.app import MetadataMainWindow
    from PySide6.QtWidgets import QComboBox, QLineEdit

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Navigate to Step 2
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit

    # Use first measurement panel
    tabs = win.page_edit.measurements_tabs
    panel = tabs.widget(0)

    cb_via_opt = panel.findChild(QComboBox, "da_via")
    le_dist_opt = panel.findChild(QLineEdit, "da_distance")
    le_signal_opt = panel.findChild(QLineEdit, "da_signal")
    le_min_opt = panel.findChild(QLineEdit, "da_min")
    le_max_opt = panel.findChild(QLineEdit, "da_max")
    assert cb_via_opt and le_dist_opt and le_signal_opt and le_min_opt and le_max_opt
    cb_via = cast(QComboBox, cb_via_opt)
    le_dist = cast(QLineEdit, le_dist_opt)
    le_signal = cast(QLineEdit, le_signal_opt)
    le_min = cast(QLineEdit, le_min_opt)
    le_max = cast(QLineEdit, le_max_opt)

    # Ensure empty initial values
    assert le_dist.text().strip() == ""
    assert le_signal.text().strip() == ""
    assert le_min.text().strip() == ""
    assert le_max.text().strip() == ""

    # Selecting GLL should prefill defaults when fields are empty
    cb_via.setCurrentText("GLL")
    qtbot.waitUntil(lambda: le_dist.text() == "10")
    assert le_signal.text() == "aes 20Hz-20kHz"
    assert le_min.text() == "20"
    assert le_max.text() == "20000"
