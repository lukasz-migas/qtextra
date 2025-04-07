import pytest
from loguru import logger

from qtextra.dialogs.qt_logger import QtLoggerDialog


@pytest.fixture
def qt_logger(qtbot):
    widget = QtLoggerDialog(None)
    qtbot.addWidget(widget)
    return widget


def test_qt_logger_01(qtbot):
    widget = QtLoggerDialog(None)
    qtbot.addWidget(widget)


def test_qt_logger_02(qt_logger, qtbot):
    logger.debug("debug")
    logger.info("INFO")
    logger.warning("warning")
    logger.error("error")
    logger.critical("critical")

    expected = "light"
    qt_logger.logger.set_theme(expected)
    assert qt_logger.logger.THEME == expected

    expected = "dark"
    qt_logger.logger.set_theme(expected)
    assert qt_logger.logger.THEME == expected


def test_qt_logger_03(qt_logger, qtbot):
    expected = "other"
    with pytest.raises(ValueError) as __:
        qt_logger.logger.set_theme(expected)


if __name__ == "__main__":
    pytest.main()
