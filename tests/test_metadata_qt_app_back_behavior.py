import pytest
from PySide6.QtCore import Qt

pytestmark = pytest.mark.qt


def test_step3_back_does_not_invoke_to_edit(qtbot, monkeypatch):
    # Ensure that pressing Back on Step 3 doesn't call _to_edit (which reloads from Step 1)
    from metaedit.app import MetadataMainWindow

    # Spy on _to_edit to track calls
    orig_to_edit = MetadataMainWindow._to_edit
    calls = {"count": 0}

    def spy(self):  # type: ignore[no-redef]
        calls["count"] += 1
        return orig_to_edit(self)

    # Patch before window instantiation so Step 1 -> Step 2 goes through spy
    monkeypatch.setattr(MetadataMainWindow, "_to_edit", spy, raising=True)

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Step 1 -> Step 2 via Next (this will call _to_edit once)
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit
    called_before = calls["count"]
    assert called_before >= 1  # sanity: we did go through _to_edit once

    # Step 2 -> Step 3
    qtbot.mouseClick(win.page_edit.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_review

    # Step 3 -> Step 2 (Back) should NOT call _to_edit again
    qtbot.mouseClick(win.page_review.back_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit
    assert calls["count"] == called_before
