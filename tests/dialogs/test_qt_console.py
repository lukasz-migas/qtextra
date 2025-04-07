import pytest

try:
    from qtextra.dialogs.qt_console import QtConsole
except ImportError:
    QtConsole = None


@pytest.mark.skipif(QtConsole is None, reason="IPython not installed")
def test_console(qtbot):
    """Test creating the console."""
    console = QtConsole()
    qtbot.addWidget(console)

    assert console.kernel_client is not None


@pytest.mark.skipif(QtConsole is None, reason="IPython not installed")
def test_console_user_variables(qtbot):
    """Test creating the console with user variables."""
    console = QtConsole({"var": 3})
    qtbot.addWidget(console)

    assert console.kernel_client is not None
    assert "var" in console.shell.user_ns
    assert console.shell.user_ns["var"] == 3


@pytest.mark.skipif(QtConsole is None, reason="IPython not installed")
def test_multiple_consoles(qtbot):
    """Test creating multiple consoles."""
    console_a = QtConsole({"var_a": 3})
    qtbot.addWidget(console_a)
    console_b = QtConsole({"var_b": 4})
    qtbot.addWidget(console_b)

    assert console_a.kernel_client is not None
    assert console_b.kernel_client is not None
    assert "var_a" in console_a.shell.user_ns
    assert "var_b" in console_a.shell.user_ns
