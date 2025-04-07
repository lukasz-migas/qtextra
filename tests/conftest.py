"""Configuration for pytest."""

import pytest

try:
    from PIL import Image
except ImportError:
    Image = None


@pytest.fixture(scope="session", autouse=False)
def get_icon_path(tmpdir_factory):
    """Get icon path."""
    if Image is None:
        return None
    else:
        icon = Image.new("RGB", (16, 16), color="red")
        path = str(tmpdir_factory.mktemp("data").join("img.png"))
        icon.save(path)
        return path
