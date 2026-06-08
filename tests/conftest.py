from unittest.mock import MagicMock

import pytest

from wol_app.storage import get_storage, set_data_dir

_ORIGINAL_DIR = "."


def _make_mock_page():
    page = MagicMock()
    page.overlay = []
    page.padding = None
    page.scroll = None
    page.theme_mode = None
    page.appbar = None
    page.theme = None
    page.dark_theme = None
    return page


def _patch_storage(tmp_path):
    set_data_dir(str(tmp_path))
    return get_storage()


def _unpatch_storage():
    set_data_dir(_ORIGINAL_DIR)


@pytest.fixture
def mock_page():
    return _make_mock_page()


@pytest.fixture
def patched_storage(tmp_path):
    old_storage = get_storage()
    _patch_storage(tmp_path)
    yield
    old_dir = old_storage.data_dir if old_storage and old_storage.data_dir != "." else _ORIGINAL_DIR
    set_data_dir(old_dir)
