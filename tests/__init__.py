"""Path pytest-qt"""

import logging

import pytest
from koyo.system import IS_MAC
from loguru import logger

# os.environ["QTEXTRA_PYTEST"] = "1"
logger.enable("qtextra")
logger.remove()


class PropagateHandler(logging.Handler):
    def emit(self, record):
        logger = logging.getLogger(record.name)
        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


@pytest.fixture(autouse=True, scope="session")
def cleanup_loguru():
    # Remove all handlers to make sure we don't interfere with tests.
    logger.remove()


@pytest.fixture(autouse=True, scope="session")
def propagate_loguru(cleanup_loguru):
    handler_id = logger.add(PropagateHandler(), format="{message}")
    yield
    logger.remove(handler_id)


if IS_MAC:
    # See: https://github.com/pytest-dev/pytest-qt/issues/521
    import pytestqt.plugin
    from pytestqt.plugin import qt_api

    def _process_events():
        """Calls app.processEvents() while taking care of capturing exceptions
        or not based on the given item's configuration.
        """
        app = qt_api.QtWidgets.QApplication.instance()
        if app is not None:
            # app.processEvents()
            pass

    pytestqt.plugin._process_events = _process_events
