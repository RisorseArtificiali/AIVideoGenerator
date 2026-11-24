"""The full pipeline on the demo video. It is slow, and it needs the network for the voice:
start it with AIVIDEOGEN_SELFTEST=1, or use the command `videogen selftest`."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.pipeline, pytest.mark.skipif(
    not os.environ.get("AIVIDEOGEN_SELFTEST"), reason="Set AIVIDEOGEN_SELFTEST=1 to start the full pipeline.",
)]


def test_selftest():
    done = subprocess.run([sys.executable, "-m", "videogen.cli", "selftest"], capture_output=True, text=True)
    print(done.stdout, done.stderr)
    assert done.returncode == 0
