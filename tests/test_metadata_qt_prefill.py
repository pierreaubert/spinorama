import pytest
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QComboBox, QLineEdit, QDateEdit

pytestmark = pytest.mark.qt


def _pick_sample_speaker():
    from datas.metadata import speakers_info

    for key, val in speakers_info.items():
        if not isinstance(val, dict):
            continue
        if not val.get("brand") or not val.get("model"):
            continue
        measurements = val.get("measurements")
        if isinstance(measurements, dict) and measurements:
            return key, val
    pytest.skip("No suitable speaker found in local metadata DB")


def test_prefill_existing_speaker(qtbot):
    from metaedit.app import MetadataMainWindow

    name, meta = _pick_sample_speaker()

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Ensure we're in Existing mode
    win.page_select.rb_existing.setChecked(True)

    # Select the sample speaker in the combobox
    cb = win.page_select.speakers_cb
    idx = cb.findText(name)
    assert idx >= 0, "Sample speaker not listed in combobox"
    cb.setCurrentIndex(idx)

    # Proceed to Step 2
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit

    # Basic fields
    assert win.page_edit.form_brand.text() == meta.get("brand")
    assert win.page_edit.form_model.text() == meta.get("model")
    assert win.page_edit.form_type.text() == (meta.get("type") or "")
    assert win.page_edit.form_shape.text() == (meta.get("shape") or "")
    assert win.page_edit.form_price.text() == (meta.get("price") or "")
    assert win.page_edit.form_amount.text() == (meta.get("amount") or "")

    # Default measurement selector
    dm = meta.get("default_measurement")
    if isinstance(dm, str):
        assert win.page_edit.default_meas_cb.currentText() == dm

    # Measurement panels count must match
    measurements = meta.get("measurements", {})
    expected_count = len(measurements)
    # layout has a trailing stretch
    actual_count = win.page_edit.measurements_layout.count() - 1
    assert actual_count == expected_count

    # Validate a sample measurement prefill (first one)
    # Access the first panel widget
    if expected_count:
        panel = win.page_edit.measurements_layout.itemAt(0).widget()
        assert panel is not None
        # Check a few representative fields
        first_key = next(iter(measurements))
        first_meas = measurements[first_key]
        fmt = first_meas.get("format") if isinstance(first_meas, dict) else None
        origin = first_meas.get("origin") if isinstance(first_meas, dict) else None
        de_str = first_meas.get("review_published") if isinstance(first_meas, dict) else None

        cb_format: QComboBox | None = panel.findChild(QComboBox, "meas_format")
        le_origin: QLineEdit | None = panel.findChild(QLineEdit, "meas_origin")
        de: QDateEdit | None = panel.findChild(QDateEdit, "meas_review_date")

        if fmt:
            assert cb_format is not None
            assert cb_format.currentText() == fmt
        if origin:
            assert le_origin is not None
            assert le_origin.text() == origin
        if isinstance(de_str, str) and len(de_str) == 8:
            assert de is not None
            qd = QDate.fromString(de_str, "yyyyMMdd")
            assert qd.isValid()
            assert de.date() == qd
