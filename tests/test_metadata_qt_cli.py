import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.qt


def test_cli_missing_speaker_exits_with_warning():
    # Run the module with a clearly missing speaker key
    cmd = [sys.executable, "-m", "metaedit.app", "--speaker", "__nonexistent__"]
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)

    assert res.returncode == 1
    assert "Warning: speaker '__nonexistent__' not found." in (res.stderr or "")
