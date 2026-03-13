"""Common widget list interface."""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager

from qtpy.QtCore import Qt, Signal, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QScrollArea, QSizePolicy, QWidget

import qtextra.helpers as hp

_W = ty.TypeVar("_W")  # Widget
_M = ty.TypeVar("_M")  # Model


class QListWidgetItemWithModel(QListWidgetItem):
    """Type stub only — never instantiate directly."""

    item_model: _M


class QtListItem(QFrame):
    """List item that is shown inside the QtListWidget."""

    # event triggered whenever an item is checked
    _evt_checked = Signal(object, bool)
    # event triggered whenever an item is removed
    evt_remove = Signal(object)
    # event triggered when double click occurred
    evt_double_clicked = Signal(object, bool)
    # event triggered whenever the item is active
    evt_active = Signal(object)

    # Widgets
    name_label: QLabel

    # Attributes
    item: _M | QListWidgetItemWithModel | None = None
    _is_checked: bool = False
    _mode: bool = False

    def _set_from_model(self, _=None):
        """Update UI elements."""
        raise NotImplementedError("Must implement method")

    @property
    def item_model(self) -> _M:
        """Get item model."""
        try:
            return self.item.item_model
        except (AttributeError, ValueError):
            return self.item

    @item_model.setter
    def item_model(self, item_model: _M):
        """Update item model."""
        try:
            self.item.item_model = item_model
        except (AttributeError, ValueError):
            self.item = item_model
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

    def _toggle_visibility(self, visible: bool) -> None:
        """Toggle visibility."""
        self.setVisible(visible)
        if not visible:
            self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        else:
            self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.updateGeometry()

        if self.parent() and self.parent().layout():
            self.parent().layout().invalidate()
            self.parent().layout().activate()


class ListMixin:
    """Mixin class for list widgets."""

    def teardown(self) -> None:
        """Teardown method."""

    def refresh_list(self):
        """Refresh list of items. This method should be re-implemented by subclasses."""

    def closeEvent(self, event):
        """Close event."""
        self.teardown()
        return super().closeEvent(event)

    @property
    def n_rows(self) -> int:
        """Return the current number of rows in the widget."""
        return self.count()

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

    def get_index_for_hash_id(self, hash_id: str) -> int:
        """Get the index of the item."""
        for index, widget in enumerate(self.widget_iter()):  # type: ignore[var-annotated]
            if widget.hash_id == hash_id:
                return index
        return -1


class QtListWidget(QListWidget, ListMixin):
    """List of notifications."""

    evt_updated = Signal(int)
    evt_added = Signal(object)
    evt_pre_remove = Signal(object)
    evt_remove = Signal(object)
    evt_cleared = Signal()

    _is_setup: bool = False

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSpacing(1)
        self.setMinimumHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setUniformItemSizes(True)

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

    def _check_existing(self, item_model: _M) -> bool:
        """Method should be modified actually implement checking functionality."""
        return False

    def _make_widget(self, item: QListWidgetItem):
        raise NotImplementedError("Must implement method")

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
            item: QListWidgetItemWithModel = self.item(index)
            if item:
                yield item.item_model

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

    def get_item_model_for_index(self, index: int) -> _M:
        """Get item's model."""
        item: QListWidgetItemWithModel = self.item(index)
        return item.item_model

    def get_widget_for_hash_id(self, hash_id: str) -> _W:
        """Return item's widget."""
        index = self.get_index_for_hash_id(hash_id)
        if index == -1:
            return None
        return self.get_item_widget_for_index(index)[1]

    def get_item_for_item_model(self, item_model: _M) -> ty.Optional[QListWidgetItem]:
        """Get the item by its model."""
        for item, _item_model, _ in self.item_model_widget_iter():  # type: ignore[var-annotated]
            if _item_model is item_model or _item_model == item_model:
                return item
        return None

    def get_widget_for_item_model(self, item_model: _M) -> ty.Optional[_W]:
        """Get the widget by its model."""
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
    def remove_item(self, item: QListWidgetItemWithModel, force: bool = False):
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
            if hasattr(widget, "refresh"):
                widget.refresh()

    def reset_data(self) -> None:
        """Reset data."""
        self.clear()
        self.evt_cleared.emit()

    def append_item(self, item_model: _M) -> tuple[ty.Optional[QListWidgetItem], ty.Optional[QWidget]]:
        """Append an item."""
        if self._check_existing(item_model):
            return None, None
        try:
            item = QListWidgetItem(parent=self)
        except AttributeError:
            item = QListWidgetItem()
        item.item_model = item_model
        widget: QWidget = self._make_widget(item)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.evt_added.emit(item_model)
        self.evt_updated.emit(self.count())
        return item, widget

    def insert_item(self, item_model: _M, index: int = 0) -> tuple[ty.Optional[QListWidgetItem], ty.Optional[QWidget]]:
        """Insert an item in the list."""
        if self._check_existing(item_model):
            return None, None
        item = QListWidgetItem(parent=self)
        item.item_model = item_model
        self.insertItem(index, item)
        widget: QWidget = self._make_widget(item)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
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


class QtListScrollWidget(QScrollArea, ListMixin):
    """Widget with similar functionality as QtListWidget but with scroll area."""

    evt_updated = Signal(int)
    evt_added = Signal(object)
    evt_pre_remove = Signal(object)
    evt_remove = Signal(object)
    evt_cleared = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.widgets: dict[str, QtListItem] = {}

        # setup UI
        scroll_widget = QWidget()
        self.setWidget(scroll_widget)
        self._layout = hp.make_v_layout(parent=scroll_widget, spacing=2, margin=1, stretch_after=True)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore[attr-defined]
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # type: ignore[attr-defined]

    def _make_widget(self, item_model: _M) -> QWidget:
        raise NotImplementedError("Must implement method")

    def count(self) -> int:
        """Return the current number of rows in the widget."""
        return len(self.widgets)

    def widget_iter(self) -> ty.Iterable[QtListWidget]:
        """Iterate over widgets."""
        yield from self.widgets.values()

    def model_iter(self, indices: ty.Sequence[int] | None = None, reverse: bool = False) -> ty.Iterator[_M]:
        """Iterate through list of ions."""
        if indices is None:
            indices = range(self.count())
        keys = list(self.widgets.keys())
        keys = [keys[i] for i in indices if i < len(keys)]
        if reverse and keys:
            keys.reverse()
        for key in keys:
            yield self.widgets[key].item_model

    def _check_existing(self, item_model: _M) -> bool:
        """Check if item with the same model already exists."""
        raise NotImplementedError("Must implement method")

    def append_item(self, item_model: _M) -> ty.Optional[QWidget]:
        """Append an item."""
        if self._check_existing(item_model):
            return None
        widget = self._make_widget(item_model)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.widgets[item_model.unique_id] = widget
        self._layout.insertWidget(0, widget)
        self.evt_added.emit(item_model)
        self.evt_updated.emit(self.count())
        return widget

    def get_widget_for_item_model(self, item_model: _M) -> ty.Optional[_W]:
        """Get the widget by its model."""
        return self.widgets.get(item_model.unique_id)

    def remove_item(self, item_model: _M, force: bool = False):
        """Remove item from the list."""
        self.evt_pre_remove.emit(item_model)
        widget = self.widgets.get(item_model.unique_id)
        if widget:
            self._layout.removeWidget(widget)
            widget.deleteLater()
        self.widgets.pop(item_model.unique_id, None)
        del widget
        self.evt_remove.emit(item_model)
        self.evt_updated.emit(self.count())

    def remove_by_item_model(self, item_model: _M, force: bool = False, **_kwargs: ty.Any):
        """Remove item from the list based on the item model."""
        self.remove_item(item_model, force)

    def get_item_widget_for_index(self, index: int) -> tuple[_M, _W]:
        """GEt widget and item model for a specified index."""
        keys = list(self.widgets.keys())
        if index < 0 or index >= len(keys):
            raise IndexError("Index out of range")
        key = keys[index]
        widget = self.widgets[key]
        return widget.item_model, widget

    def get_widget_for_hash_id(self, hash_id: str) -> _W:
        """Return item's widget."""
        index = self.get_index_for_hash_id(hash_id)
        if index == -1:
            return None
        return self.get_item_widget_for_index(index)[1]

    def get_item_for_index(self, index: int) -> _W:
        """Return item's widget."""
        return self.get_item_widget_for_index(index)[0]

    def get_widget_for_index(self, index: int) -> _W:
        """Return item's widget."""
        return self.get_item_widget_for_index(index)[1]
