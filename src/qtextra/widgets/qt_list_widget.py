"""Common widget list interface."""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager

from koyo.timer import MeasureTimer
from loguru import logger
from qtpy.QtCore import Signal, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFrame, QListWidget, QListWidgetItem, QSizePolicy, QWidget

import qtextra.helpers as hp

_W = ty.TypeVar("_W")  # Widget
_M = ty.TypeVar("_M")  # Model


class QtListItem(QFrame):
    """List item that is shown inside the QtListWidget."""

    # event triggered whenever an item is checked
    _evt_checked = Signal(QListWidgetItem, bool)
    # event triggered whenever an item is removed
    evt_remove = Signal(QListWidgetItem)
    # event triggered when double click occurred
    evt_double_clicked = Signal(QListWidgetItem, bool)
    # event triggered whenever the item is active
    evt_active = Signal(QListWidgetItem)

    # Attributes
    item: QListWidgetItem = None
    _is_checked: bool = False
    _mode: bool = False

    def _set_from_model(self, _=None):
        """Update UI elements."""
        raise NotImplementedError("Must implement method")

    @property
    def item_model(self) -> _M:
        """Get item model."""
        return self.item.item_model

    @item_model.setter
    def item_model(self, item_model: _M):
        """Update item model."""
        self.item.item_model = item_model
        self._set_from_model()

    @property
    def is_checked(self) -> bool:
        """Get check state."""
        return self._is_checked

    @property
    def name(self):
        """Get heatmap name."""
        return self.name_label.text()

    @property
    def hash_id(self):
        """Get hash id information the selected item."""
        return self.item_model.name

    @property
    def mode(self):
        """Setup mode."""
        return self._mode

    @mode.setter
    def mode(self, value: bool):
        self._mode = value
        self.setProperty("mode", str(value))
        hp.polish_widget(self)
        self.evt_active.emit(self.item)

    def set_state(self, state: bool):
        """Check."""
        state = bool(state)
        self._is_checked = state
        if hasattr(self, "check_label"):
            self.check_label.setVisible(state)
        elif hasattr(self, "checkbox"):
            with hp.qt_signals_blocked(self.checkbox):
                self.checkbox.setChecked(state)
        self.mode = str(state)
        self._evt_checked.emit(self.item, self._is_checked)

    def mouseDoubleClickEvent(self, event):
        """Detect double-click event."""
        self.evt_double_clicked.emit(self.item, self._is_checked)

    def refresh(self):
        """Refresh values in the widget."""
        self._set_from_model()
        self.parent().update()


class QtListWidget(QListWidget):
    """List of notifications."""

    evt_updated = Signal(int)
    evt_added = Signal(object)
    evt_pre_remove = Signal(object)
    evt_remove = Signal(object)
    evt_cleared = Signal()

    _is_setup = False

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSpacing(1)
        self.setMinimumHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setUniformItemSizes(True)

    def closeEvent(self, event):
        """Close event."""
        self.teardown()
        return super().closeEvent(event)

    def teardown(self) -> None:
        """Teardown method."""

    def refresh_list(self):
        """Refresh list of items. This method should be re-implemented by subclasses."""

    def _get_menu(self):
        menu = hp.make_menu(self, "Actions")
        menu_remove = hp.make_menu_item(self, "Refresh list...", menu=menu, icon="refresh")
        menu_remove.triggered.connect(self.refresh_list)

    def _get_check_state(self, state: bool, attr: str = "is_checked"):
        items = []
        for widget in self.widget_iter():
            if hasattr(widget, attr) and getattr(widget, attr) == state:
                items.append((widget.hash_id, state))
        return items

    def _make_widget(self, item: QListWidgetItem):
        raise NotImplementedError("Must implement method")

    def _check_existing(self, item_model: _M) -> bool:
        """This method should be modified actually implement checking functionality."""
        return False

    @property
    def n_rows(self) -> int:
        """Return the current number of rows in the widget."""
        return self.count()

    def widget_iter(self) -> ty.Iterator[_W]:
        """Iterate through list of widgets."""
        for index in range(self.count()):
            yield self.itemWidget(self.item(index))

    def item_iter(self, indices: ty.Sequence[int] | None = None, reverse: bool = False) -> ty.Iterator[_W]:
        """Iterate through list of widgets."""
        if indices is None:
            indices = range(self.count())

        iterator = indices if not reverse else reversed(indices)
        for index in iterator:
            yield self.item(index)  # type: ignore[misc]

    def item_model_widget_iter(self) -> ty.Iterator[tuple[QListWidgetItem, _M, _W]]:
        """Iterate through list of widgets."""
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            yield item, item.item_model, widget  # type: ignore[misc,union-attr]

    def model_iter(self, indices: ty.Sequence[int] | None = None) -> ty.Iterator[_M]:
        """Iterate through list of ions."""
        if indices is None:
            indices = range(self.count())
        for index in indices:
            item = self.item(index)
            if item:
                yield item.item_model

    def get_all_checked(self, *, reverse: bool = False) -> list[int]:
        """Get list of checked items."""
        checked = []
        for index, widget in enumerate(self.widget_iter()):  # type: ignore[var-annotated]
            if widget.is_checked:
                checked.append(index)
        if reverse:
            return list(reversed(checked))
        return checked

    def get_all_unchecked(self) -> list[int]:
        """Get list of checked items."""
        checked = []
        for index, widget in enumerate(self.widget_iter()):  # type: ignore[var-annotated]
            if not widget.is_checked:
                checked.append(index)
        return checked

    def get_hash_ids(self, indices: ty.Iterator[int]) -> list[str]:
        """Get list of names."""
        hash_ids = []
        for item_id in indices:
            item = self.item(item_id)
            hash_ids.append(item.item_model.name)  # type: ignore[union-attr]
        return hash_ids

    def get_attr(self, indices: ty.Iterator[int], attr: str, default: ty.Any = None) -> list[ty.Any]:
        """Get a list of attributes."""
        values = []
        for item_id in indices:
            item = self.item(item_id)
            item_model = item.item_model  # type: ignore[union-attr]
            if hasattr(item_model, attr):
                values.append(getattr(item_model, attr))
            elif hasattr(item, attr):
                values.append(getattr(item, attr))
            else:
                values.append(default)
        return values

    def get_item_widget_for_index(self, index: int) -> tuple[QListWidgetItem, _W]:
        """Get widget for specified item."""
        item = self.item(index)
        return item, self.itemWidget(item)

    def get_index_for_hash_id(self, hash_id: str) -> int:
        """Get index of the item."""
        for index, widget in enumerate(self.widget_iter()):  # type: ignore[var-annotated]
            if widget.hash_id == hash_id:
                return index
        return -1

    def get_item_model_for_index(self, index: int) -> _M:
        """Get item's model."""
        item = self.item(index)
        return item.item_model

    def get_item_for_item_model(self, item_model: _M) -> ty.Optional[QListWidgetItem]:
        """Get item by its model."""
        for item, _item_model, _ in self.item_model_widget_iter():  # type: ignore[var-annotated]
            if _item_model is item_model or _item_model == item_model:
                return item
        return None

    def get_widget_for_hash_id(self, hash_id: str) -> _W:
        """Return item's widget."""
        index = self.get_index_for_hash_id(hash_id)
        if index == -1:
            return None
        return self.get_item_widget_for_index(index)[1]

    def get_widget_for_item_model(self, item_model: _M) -> ty.Optional[_W]:
        """Get widget by its model."""
        for _, _item_model, widget in self.item_model_widget_iter():  # type: ignore[var-annotated]
            if _item_model is item_model or _item_model == item_model:
                return widget
        return None

    def get_hash_id_for_index(self, index: int) -> str:
        """Get item's hash id."""
        item = self.get_item_model_for_index(index)
        return item.name

    @Slot(QListWidgetItem)
    @Slot(QListWidgetItem, bool)
    def remove_item(self, item: QListWidgetItem, force: bool = False):
        """Remove item from the list."""
        self.evt_pre_remove.emit(item)
        self.takeItem(self.indexFromItem(item).row())
        self.evt_remove.emit(item.item_model)
        super().removeItemWidget(item)
        self.evt_updated.emit(self.count())

    def remove_by_index(self, index: int, force: bool = False):
        """Remove item from the list based on row id."""
        item = self.item(index)
        self.remove_item(item, force)

    def remove_by_item_model(self, item_model: _M, force: bool = False, **kwargs):
        """Remove item from the list based on the item model."""
        item = self.get_item_for_item_model(item_model)
        if item:
            self.remove_item(item, force, **kwargs)

    def move_item(self, index: int, new_index: int, item_model: _M = None):
        """Move item from one index to another."""
        item = self.takeItem(index)
        self.insertItem(new_index, item)

    def select_by_index(self, index: int):
        """Select item."""
        self.setCurrentIndex(index)

    def select_by_item_model(self, item_model):
        """Find by item model."""
        item = self.get_item_for_item_model(item_model)
        if item:
            self.select_by_item(item)

    def select_by_item(self, item: QListWidgetItem):
        """Select item."""
        self.setCurrentIndex(self.indexFromItem(item))

    def refresh(self) -> None:
        """Refresh widget UI."""
        for index in range(self.count()):
            widget = self.itemWidget(self.item(index))
            widget.refresh()

    def reset_data(self) -> None:
        """Reset data."""
        self.clear()
        self.evt_cleared.emit()

    def append_item(self, item_model: _M) -> tuple[ty.Optional[QListWidgetItem], ty.Optional[QWidget]]:
        """Append item."""
        if self._check_existing(item_model):
            return None, None
        try:
            item = QListWidgetItem(parent=self)
        except AttributeError:
            item = QListWidgetItem()
        item.item_model = item_model
        widget = self._make_widget(item)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.evt_added.emit(item_model)
        self.evt_updated.emit(self.count())
        return item, widget

    def insert_item(self, item_model: _M, index: int = 0) -> tuple[ty.Optional[QListWidgetItem], ty.Optional[QWidget]]:
        """Insert item in the list."""
        if self._check_existing(item_model):
            return None, None
        item = QListWidgetItem(parent=self)
        item.item_model = item_model
        self.insertItem(index, item)
        widget = self._make_widget(item)
        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)
        self.evt_updated.emit(self.count())
        return item, widget

    def _clear(self, _):
        self.clear()
        self.evt_updated.emit(self.count())

    @contextmanager
    def disable_updates(self):
        """Temporarily disable updates."""
        self.setUpdatesEnabled(False)
        yield
        self.setUpdatesEnabled(True)

    @contextmanager
    def measure_time(self, message: str = "Task took", print_: bool = False):
        """Measure time."""
        with MeasureTimer() as timer:
            yield
        msg = f"{message} {timer()}"
        logger.debug(msg)
        if print_:
            print(msg)
