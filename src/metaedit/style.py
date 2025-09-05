from __future__ import annotations

from typing import Literal, cast

from PySide6.QtCore import Qt, QSettings  # type: ignore[reportMissingImports]
from PySide6.QtGui import QColor, QPalette  # type: ignore[reportMissingImports]
from PySide6.QtWidgets import QApplication  # type: ignore[reportMissingImports]


def _set_dark_palette(app: QApplication) -> None:
    pal = QPalette()
    # Base tones
    bg = QColor(30, 34, 39)
    base = QColor(36, 41, 46)
    alt_base = QColor(44, 49, 55)
    text = QColor(220, 223, 228)
    disabled_text = QColor(140, 145, 150)
    highlight = QColor(56, 132, 255)

    pal.setColor(QPalette.ColorRole.Window, bg)
    pal.setColor(QPalette.ColorRole.WindowText, text)
    pal.setColor(QPalette.ColorRole.Base, base)
    pal.setColor(QPalette.ColorRole.AlternateBase, alt_base)
    pal.setColor(QPalette.ColorRole.ToolTipBase, base)
    pal.setColor(QPalette.ColorRole.ToolTipText, text)
    pal.setColor(QPalette.ColorRole.Text, text)
    pal.setColor(QPalette.ColorRole.Button, alt_base)
    pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.BrightText, QColor(255, 72, 66))
    pal.setColor(QPalette.ColorRole.Highlight, highlight)
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Disabled
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text)

    app.setPalette(pal)


_QSS = """
QWidget {
  font-size: 12px;
}

QLabel#pageTitle {
  font-size: 18px;
  font-weight: 600;
  margin: 4px 0 10px 0;
}

QFrame, QGroupBox {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  padding: 6px;
}

QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 4px;
}

QLineEdit, QComboBox, QTextEdit {
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 4px;
  padding: 6px 8px;
  background: rgba(0,0,0,0.06);
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
  border: 1px solid #3884ff;
}

QPushButton {
  background: #2f81f7;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
}
QPushButton:hover { background: #1f6feb; }
QPushButton:pressed { background: #1a5fd0; }
QPushButton:disabled { background: #3b3f45; color: #9aa0a6; }

QToolButton {
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  padding: 4px 8px;
}

QTabBar::tab {
  padding: 6px 10px;
  border: 1px solid rgba(255,255,255,0.12);
  border-bottom: none;
  background: rgba(0,0,0,0.06);
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  margin-right: 4px;
}
QTabBar::tab:selected {
  background: rgba(255,255,255,0.06);
}
QTabWidget::pane {
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  top: -1px;
}

QScrollArea { border: none; }
"""


Theme = Literal["dark", "light", "auto"]


def read_theme_from_settings(default: Theme = "light") -> Theme:
    """Return saved theme from QSettings or the provided default.

    Uses the current QCoreApplication organization/application names.
    """
    settings = QSettings()
    val = cast(str | None, settings.value("ui/theme", None))
    if val in ("dark", "light", "auto"):
        return cast(Theme, val)
    return default


def write_theme_to_settings(theme: Theme) -> None:
    settings = QSettings()
    settings.setValue("ui/theme", theme)


def apply_app_style(app: QApplication, theme: Theme = "auto") -> None:
    """Apply a modern, professional look to the Qt application.

    - Forces Fusion style for cross-platform consistency
    - Installs a global stylesheet with refined controls
    - Palette selection:
      * "light" -> use platform standard light palette
      * "dark" or "auto" -> use our dark palette
    """
    # Consistent cross-platform base
    app.setStyle("Fusion")

    # Palette
    if theme == "light":
        app.setPalette(app.style().standardPalette())
    else:
        # auto or dark -> default to dark for professional tooling look
        _set_dark_palette(app)

    # Stylesheet
    app.setStyleSheet(_QSS)
