import json
import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

pytestmark = pytest.mark.qt


def test_choose_picture_copies_and_exports(qtbot, tmp_path, monkeypatch):
    # Prepare a tiny valid PNG using QPixmap
    src_img = tmp_path / "src.png"
    pm = QPixmap(1, 1)
    pm.fill(QColor("white"))
    assert pm.save(str(src_img), "PNG")

    # Patch QFileDialog.getOpenFileName to return our image
    from metaedit import app as app_mod

    def fake_get_open_file_name(parent=None, caption="", directory="", filter_str=""):
        return str(src_img), "Images (*.png *.jpg *.jpeg *.webp)"

    monkeypatch.setattr(
        app_mod,
        "QFileDialog",
        type("_QFD", (), {"getOpenFileName": staticmethod(fake_get_open_file_name)}),
    )

    # Patch pictures destination directory to be tmp_path
    monkeypatch.setattr(app_mod, "PICTURES_DIR", str(tmp_path))

    # Create window
    win = app_mod.MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Step 1: New speaker
    win.page_select.rb_new.setChecked(True)
    win.page_select.new_brand.setText("TestBrandX")
    win.page_select.new_speaker_model.setText("ModelY 123")

    # Next to edit
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit

    # Click choose picture -> should copy to PICTURES_DIR/TestBrandX ModelY 123.png
    qtbot.mouseClick(win.page_edit.choose_picture_btn, Qt.MouseButton.LeftButton)

    dest_path = os.path.join(str(tmp_path), "TestBrandX ModelY 123.png")
    assert os.path.isfile(dest_path)

    # The model should record the picture path
    assert win.current is not None
    assert win.current.picture == dest_path

    # The UI label should now have a pixmap (and no placeholder text)
    lbl = win.page_edit.picture_label
    assert lbl.pixmap() is not None
    assert lbl.text() in (None, "")

    # Proceed to review and validate export contains picture
    qtbot.mouseClick(win.page_edit.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_review
    data = json.loads(win.page_review.summary.toPlainText())
    assert data["brand"] == "TestBrandX"
    assert data["model"] == "ModelY 123"
    assert data.get("picture") == dest_path
