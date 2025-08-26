from __future__ import annotations

import os
import unittest

from typing import cast
from PySide6.QtWidgets import QApplication  # type: ignore[reportMissingImports]
from PySide6.QtCore import QCoreApplication, QSettings  # type: ignore[reportMissingImports]
from PySide6.QtGui import QPalette  # type: ignore[reportMissingImports]

from metaedit.style import apply_app_style, read_theme_from_settings, write_theme_to_settings


class TestStyle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Use offscreen platform for headless CI
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    def test_apply_app_style_is_idempotent_and_sets_stylesheet(self) -> None:
        app = cast(QApplication, QApplication.instance() or QApplication([]))
        # First application
        apply_app_style(app)  # should not raise
        ss1 = app.styleSheet()
        self.assertTrue(isinstance(ss1, str))
        self.assertGreater(len(ss1), 10)

        # Second application (idempotent)
        apply_app_style(app)
        ss2 = app.styleSheet()
        self.assertEqual(ss1, ss2)

    def test_theme_settings_persist_and_switch(self) -> None:
        # Use test-specific settings scope
        QCoreApplication.setOrganizationName("SpinoramaTest")
        QCoreApplication.setApplicationName("MetadataQtTest")
        settings = QSettings()
        settings.remove("ui/theme")

        app = cast(QApplication, QApplication.instance() or QApplication([]))

        # Persist dark theme and apply
        write_theme_to_settings("dark")
        self.assertEqual(read_theme_from_settings(), "dark")
        apply_app_style(app, "dark")
        dark_win = app.palette().color(QPalette.ColorRole.Window)

        # Switch to light and verify palette changes
        write_theme_to_settings("light")
        self.assertEqual(read_theme_from_settings(), "light")
        apply_app_style(app, "light")
        light_win = app.palette().color(QPalette.ColorRole.Window)

        # Ensure colors are different between dark and light applications
        self.assertNotEqual(dark_win, light_win)

    def test_default_theme_is_light(self) -> None:
        # Use a fresh QSettings scope and ensure key is removed
        QCoreApplication.setOrganizationName("SpinoramaTestDefault")
        QCoreApplication.setApplicationName("MetadataQtTestDefault")
        settings = QSettings()
        settings.remove("ui/theme")

        # When no theme is saved, default should be light
        self.assertEqual(read_theme_from_settings(), "light")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
