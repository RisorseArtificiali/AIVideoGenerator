"""Fixtures of all the tests."""

from __future__ import annotations

import manim
import pytest


@pytest.fixture(scope="session", autouse=True)
def media_folder(tmp_path_factory):
    manim.config.media_dir = str(tmp_path_factory.mktemp("media"))   # the LaTeX files stay out of the repository
