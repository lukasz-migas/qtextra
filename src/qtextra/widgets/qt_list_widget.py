"""List widgets that host custom Qt widgets for each row."""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager

from qtpy.QtCore import Qt, Signal, Slot  # type: ignore[attr-defined]
from qtpy.QtGui import QCloseEvent, QMouseEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

import qtextra.helpers as hp

_W = ty.TypeVar("_W")  # Widget
_M = ty.TypeVar("_M")  # Model


class QListWidgetItemWithModel(QListWidgetItem):
    """Typed ``QListWidgetItem`` carrying an attached ``item_model``."""

    item_model: _M


class QtListItem(QFrame):
    """Base class for widgets rendered inside :class:`QtListWidget`."""

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

    def _set_from_model(self, _: ty.Any = None) -> None:
        """Synchronise the widget state from ``item_model``."""
        raise NotImplementedError("Must implement method")

    @property
    def item_model(self) -> _M:
        """Return the bound model for this row widget."""
        try:
            return self.item.item_model
        except (AttributeError, ValueError):
            return self.item

    @item_model.setter
    def item_model(self, item_model: _M) -> None:
        """Attach a new model and refresh the widget contents."""
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
    def name(self) -> str:
        """Return the current display label text."""
        return self.name_label.text()

    @property
    def hash_id(self) -> str:
        """Return the model identifier used by list lookup helpers."""
        return self.item_model.name

    @property
    def mode(self) -> bool:
        """Return the current active/checked visual mode."""
        return self._mode

    @mode.setter
    def mode(self, value: bool) -> None:
        self._mode = bool(value)
        self.setProperty("mode", str(value))
        hp.polish_widget(self)
        self.evt_active.emit(self.item)

    def set_state(self, state: bool) -> None:
        """Update the checked state and the matching visual affordance."""
        state = bool(state)
        self._is_checked = state
        if hasattr(self, "check_label"):
            self.check_label.setVisible(state)
        elif hasattr(self, "checkbox"):
            with hp.qt_signals_blocked(self.checkbox):
                self.checkbox.setChecked(state)
        self.mode = state
        self._evt_checked.emit(self.item, self._is_checked)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Emit the row double-click signal and preserve base handling."""
        self.evt_double_clicked.emit(self.item, self._is_checked)
        super().mouseDoubleClickEvent(event)

    def refresh(self) -> None:
        """Refresh the widget from its bound model."""
        self._set_from_model()
        parent = self.parentWidget()
        if parent is not None:
            parent.update()

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
    """Shared helpers for the list-widget variants in this module."""

    # Current filter text; empty string means no filter is active.
    _filter_text: str = ""

    def teardown(self) -> None:
        """Release subclass resources before the widget closes."""

    def refresh_list(self) -> None:
        """Refresh the list contents.

        Subclasses are expected to reimplement this hook.
        """

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    @staticmethod
    def _get_search_terms(item_model: _M) -> list[str]:
        """Return the list of strings used when filtering this row.

        Override in subclasses to expose the attributes that should be
        matched against the filter text.  The default returns an empty
        list, which means no row will be shown when a filter is active
        unless the method is overridden.
        """
        return []

    def set_filter_text(self, text: str) -> None:
        """Set the active filter text and immediately apply the filter."""
        self._filter_text = text
        self.apply_filter()

    def apply_filter(self) -> int:
        """Show or hide rows based on :attr:`_filter_text`.

        If ``_filter_text`` is empty every row is shown.  Otherwise a row
        is shown only when at least one of its :meth:`_get_search_terms`
        values contains the filter text as a case-insensitive substring.

        Returns the number of visible rows after filtering.
        """
        if not self._filter_text:
            return self.filter_items(lambda _: True)
        needle = self._filter_text.lower()

        def _predicate(widget: _W) -> bool:
            terms = self._get_search_terms(widget.item_model)
            return any(needle in term.lower() for term in terms)

        return self.filter_items(_predicate)

    def filter_items(self, predicate: ty.Callable[[_W], bool]) -> int:
        """Show or hide each row widget based on ``predicate``.

        Returns the number of visible items after filtering.
        Subclasses must override this to apply visibility changes.
        """
        raise NotImplementedError("Must implement method")

    def filter_by_text(
        self,
        text: str,
        *,
        attr: str = "name",
        case_sensitive: bool = False,
    ) -> int:
        """Show only rows whose ``attr`` value contains ``text``.

        An empty ``text`` restores all rows. Returns the number of visible items.
        """
        if not text:
            return self.filter_items(lambda _: True)
        needle = text if case_sensitive else text.lower()

        def _predicate(widget: _W) -> bool:
            value = getattr(widget, attr, None)
            if value is None:
                try:
                    value = getattr(widget.item_model, attr, "")
                except Exception:  # noqa: BLE001
                    value = ""
            haystack = str(value) if case_sensitive else str(value).lower()
            return needle in haystack

        return self.filter_items(_predicate)

    # ------------------------------------------------------------------
    # Iterators (all items, ignoring visibility)
    # ------------------------------------------------------------------

    def all_widget_iter(self) -> ty.Iterator[_W]:
        """Yield every row widget regardless of visibility."""
        raise NotImplementedError("Must implement method")

    # ------------------------------------------------------------------
    # Close / size helpers
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Call :meth:`teardown` before forwarding the close event."""
        self.teardown()
        QWidget.closeEvent(self, event)

    @property
    def n_rows(self) -> int:
        """Return the current number of rows in the widget."""
        return self.count()

    # ------------------------------------------------------------------
    # Check-state helpers (operate on visible rows only)
    # ------------------------------------------------------------------

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
        """Get the absolute index of the item (searches all rows)."""
        for index, widget in enumerate(self.all_widget_iter()):  # type: ignore[var-annotated]
            if widget.hash_id == hash_id:
                return index
        return -1


class QtListWidget(QListWidget, ListMixin):
    """`QListWidget` specialisation for rows backed by custom widgets."""

    evt_updated = Signal(int)
    evt_added = Signal(object)
    evt_pre_remove = Signal(object)
    evt_remove = Signal(object)
    evt_cleared = Signal()

    _is_setup: bool = False

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSpacing(1)
        self.setMinimumHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def _get_menu(self) -> None:
        """Build the standard context menu for list actions."""
        menu = hp.make_menu(self, "Actions")
        menu_remove = hp.make_menu_item(self, "Refresh list...", menu=menu, icon="refresh")
        menu_remove.triggered.connect(self.refresh_list)

    def _get_check_state(self, state: bool, attr: str = "is_checked") -> list[tuple[str, bool]]:
        """Return ``(hash_id, state)`` pairs for matching row widgets."""
        items: list[tuple[str, bool]] = []
        for widget in self.widget_iter():
            if hasattr(widget, attr) and getattr(widget, attr) == state:
                items.append((widget.hash_id, state))
        return items

    def _check_existing(self, item_model: _M) -> bool:
        """Method should be modified actually implement checking functionality."""
        return False

    def _make_widget(self, item: QListWidgetItemWithModel) -> _W:
        """Create the widget used to render ``item``."""
        raise NotImplementedError("Must implement method")

    # ------------------------------------------------------------------
    # Visibility-aware iterators (skip hidden rows)
    # ------------------------------------------------------------------

    def widget_iter(self) -> ty.Iterator[_W]:
        """Yield visible row widgets in visual order."""
        for index in range(self.count()):
            item = self.item(index)
            if item is not None and not item.isHidden():
                widget = self.itemWidget(item)
                if widget is not None:
                    yield widget  # type: ignore[misc]

    def item_iter(
        self,
        indices: ty.Iterable[int] | None = None,
        reverse: bool = False,
    ) -> ty.Iterator[QListWidgetItemWithModel]:
        """Yield visible list items (or items at explicit ``indices``)."""
        if indices is None:
            indices = [i for i in range(self.count()) if not self.item(i).isHidden()]

        iterator: ty.Iterable[int]
        iterator = reversed(tuple(indices)) if reverse else tuple(indices)
        for index in iterator:
            item = self.item(index)
            if item is not None:
                yield item  # type: ignore[misc]

    def item_model_widget_iter(self) -> ty.Iterator[tuple[QListWidgetItemWithModel, _M, _W]]:
        """Yield ``(item, model, widget)`` triples for visible rows."""
        for index in range(self.count()):
            item = self.item(index)
            if item is None or item.isHidden():
                continue
            widget = self.itemWidget(item)
            if widget is not None:
                yield item, item.item_model, widget  # type: ignore[misc,union-attr]

    def model_iter(self, indices: ty.Iterable[int] | None = None) -> ty.Iterator[_M]:
        """Yield item models for visible rows (or rows at explicit ``indices``)."""
        if indices is None:
            indices = [i for i in range(self.count()) if not self.item(i).isHidden()]
        for index in indices:
            item: QListWidgetItemWithModel = self.item(index)
            if item:
                yield item.item_model

    # ------------------------------------------------------------------
    # All-items iterators (ignore visibility)
    # ------------------------------------------------------------------

    def all_widget_iter(self) -> ty.Iterator[_W]:
        """Yield every row widget regardless of visibility."""
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget is not None:
                yield widget  # type: ignore[misc]

    def all_item_iter(
        self,
        indices: ty.Iterable[int] | None = None,
        reverse: bool = False,
    ) -> ty.Iterator[QListWidgetItemWithModel]:
        """Yield all list items regardless of visibility."""
        if indices is None:
            indices = range(self.count())

        iterator: ty.Iterable[int]
        iterator = reversed(tuple(indices)) if reverse else tuple(indices)
        for index in iterator:
            item = self.item(index)
            if item is not None:
                yield item  # type: ignore[misc]

    def all_item_model_widget_iter(self) -> ty.Iterator[tuple[QListWidgetItemWithModel, _M, _W]]:
        """Yield ``(item, model, widget)`` triples for every row regardless of visibility."""
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if item is not None and widget is not None:
                yield item, item.item_model, widget  # type: ignore[misc,union-attr]

    def all_model_iter(self, indices: ty.Iterable[int] | None = None) -> ty.Iterator[_M]:
        """Yield item models for every row regardless of visibility."""
        if indices is None:
            indices = range(self.count())
        for index in indices:
            item: QListWidgetItemWithModel = self.item(index)
            if item:
                yield item.item_model

    # ------------------------------------------------------------------
    # Lookup helpers (search all rows regardless of visibility)
    # ------------------------------------------------------------------

    def get_hash_ids(self, indices: ty.Iterable[int]) -> list[str]:
        """Return model ``name`` values for the provided item indices."""
        hash_ids: list[str] = []
        for item_id in indices:
            item = self.item(item_id)
            if item is not None:
                hash_ids.append(item.item_model.name)  # type: ignore[union-attr]
        return hash_ids

    def get_attr(self, indices: ty.Iterable[int], attr: str, default: ty.Any = None) -> list[ty.Any]:
        """Return an attribute for each indexed item or model."""
        values: list[ty.Any] = []
        for item_id in indices:
            item = self.item(item_id)
            if item is None:
                values.append(default)
                continue
            item_model = item.item_model  # type: ignore[union-attr]
            if hasattr(item_model, attr):
                values.append(getattr(item_model, attr))
            elif hasattr(item, attr):
                values.append(getattr(item, attr))
            else:
                values.append(default)
        return values

    def get_item_widget_for_index(self, index: int) -> tuple[QListWidgetItemWithModel, _W]:
        """Return the item and widget at ``index``."""
        item = self.item(index)
        widget = self.itemWidget(item)
        if item is None or widget is None:
            raise IndexError(f"No list widget item at index {index}")
        return item, widget  # type: ignore[misc]

    def get_item_model_for_index(self, index: int) -> _M:
        """Get item's model."""
        item: QListWidgetItemWithModel = self.item(index)
        return item.item_model

    def get_widget_for_hash_id(self, hash_id: str) -> _W | None:
        """Return the widget matching ``hash_id``, if present."""
        index = self.get_index_for_hash_id(hash_id)
        if index == -1:
            return None
        return self.get_item_widget_for_index(index)[1]

    def get_item_for_item_model(self, item_model: _M) -> QListWidgetItem | None:
        """Get the item by its model (searches all rows)."""
        for item, _item_model, _ in self.all_item_model_widget_iter():  # type: ignore[var-annotated]
            if _item_model is item_model or _item_model == item_model:
                return item
        return None

    def get_widget_for_item_model(self, item_model: _M) -> _W | None:
        """Get the widget by its model (searches all rows)."""
        for _, _item_model, widget in self.all_item_model_widget_iter():  # type: ignore[var-annotated]
            if _item_model is item_model or _item_model == item_model:
                return widget
        return None

    def get_hash_id_for_index(self, index: int) -> str:
        """Get item's hash id."""
        item = self.get_item_model_for_index(index)
        return item.name

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    @Slot(QListWidgetItem)
    @Slot(QListWidgetItem, bool)
    def remove_item(self, item: QListWidgetItemWithModel, force: bool = False) -> None:
        """Remove ``item`` from the widget and emit lifecycle signals."""
        if item is None:
            return
        row = self.row(item)
        if row < 0:
            return

        widget = self.itemWidget(item)
        self.evt_pre_remove.emit(item)
        if widget is not None:
            self.removeItemWidget(item)
        self.takeItem(row)
        if widget is not None:
            widget.deleteLater()
        self.evt_remove.emit(item.item_model)
        self.evt_updated.emit(self.count())

    def remove_by_index(self, index: int, force: bool = False) -> None:
        """Remove the item at ``index`` if it exists."""
        item = self.item(index)
        if item is not None:
            self.remove_item(item, force)

    def remove_by_item_model(self, item_model: _M, force: bool = False, **_kwargs: ty.Any) -> None:
        """Remove the item matching ``item_model`` if it exists."""
        item = self.get_item_for_item_model(item_model)
        if item:
            self.remove_item(item, force)

    def move_item(self, index: int, new_index: int, item_model: _M | None = None) -> None:
        """Move an existing row while preserving its attached widget."""
        if index == new_index:
            return
        item = self.item(index)
        if item is None:
            return
        widget = self.itemWidget(item)
        item = self.takeItem(index)
        self.insertItem(new_index, item)
        if widget is not None:
            self.setItemWidget(item, widget)
        if item_model is not None:
            item.item_model = item_model

    def select_by_index(self, index: int) -> None:
        """Select the row at ``index``."""
        self.setCurrentRow(index)

    def select_by_item_model(self, item_model: _M) -> None:
        """Select the row matching ``item_model``."""
        item = self.get_item_for_item_model(item_model)
        if item:
            self.select_by_item(item)

    def select_by_item(self, item: QListWidgetItem) -> None:
        """Select ``item`` if it is currently in the list."""
        if item is not None:
            self.setCurrentItem(item)

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

    def append_item(self, item_model: _M) -> tuple[QListWidgetItemWithModel, _W] | tuple[None, None]:
        """Append ``item_model`` and return the created ``(item, widget)``."""
        if self._check_existing(item_model):
            return None, None
        item = QListWidgetItem()
        item.item_model = item_model
        self.addItem(item)
        widget = self._make_widget(item)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)
        self.evt_added.emit(item_model)
        self.evt_updated.emit(self.count())
        return item, widget  # type: ignore[return-value]

    def insert_item(self, item_model: _M, index: int = 0) -> tuple[QListWidgetItemWithModel, _W] | tuple[None, None]:
        """Insert ``item_model`` at ``index`` and return ``(item, widget)``."""
        if self._check_existing(item_model):
            return None, None
        item = QListWidgetItem()
        item.item_model = item_model
        self.insertItem(index, item)
        widget = self._make_widget(item)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)
        self.evt_added.emit(item_model)
        self.evt_updated.emit(self.count())
        return item, widget  # type: ignore[return-value]

    def _clear(self, _: ty.Any) -> None:
        """Clear all rows and emit an updated count."""
        self.clear()
        self.evt_updated.emit(self.count())

    def filter_items(self, predicate: ty.Callable[[_W], bool]) -> int:
        """Show or hide each row based on ``predicate``. Returns visible count."""
        visible = 0
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget is not None:
                show = predicate(widget)
                item.setHidden(not show)
                if show:
                    visible += 1
        return visible

    @contextmanager
    def disable_updates(self) -> ty.Iterator[None]:
        """Temporarily disable repaint/update processing."""
        self.setUpdatesEnabled(False)
        try:
            yield
        finally:
            self.setUpdatesEnabled(True)


class QtListScrollWidget(QScrollArea, ListMixin):
    """Scroll-area variant for custom row widgets not backed by `QListWidgetItem`."""

    evt_updated = Signal(int)
    evt_added = Signal(object)
    evt_pre_remove = Signal(object)
    evt_remove = Signal(object)
    evt_cleared = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.widgets: dict[str, QtListItem] = {}

        # setup UI
        scroll_widget = QWidget()
        self.setWidget(scroll_widget)
        self._layout = hp.make_v_layout(parent=scroll_widget, spacing=2, margin=1, stretch_after=True)

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _make_widget(self, item_model: _M) -> _W:
        """Create the widget used to render ``item_model``."""
        raise NotImplementedError("Must implement method")

    def count(self) -> int:
        """Return the total number of rows (visible and hidden)."""
        return len(self.widgets)

    @property
    def n_visible(self) -> int:
        """Return the number of currently visible rows."""
        return sum(1 for w in self.widgets.values() if not w.isHidden())

    # ------------------------------------------------------------------
    # Visibility-aware iterators (skip hidden rows)
    # ------------------------------------------------------------------

    def widget_iter(self) -> ty.Iterator[_W]:
        """Yield visible child widgets in visual order."""
        for widget in self.widgets.values():
            if not widget.isHidden():
                yield widget  # type: ignore[misc]

    def model_iter(self, indices: ty.Sequence[int] | None = None, reverse: bool = False) -> ty.Iterator[_M]:
        """Yield item models for visible rows (or rows at explicit ``indices``)."""
        if indices is None:
            widgets = [w for w in self.widgets.values() if not w.isHidden()]
            if reverse:
                widgets.reverse()
            for w in widgets:
                yield w.item_model  # type: ignore[union-attr]
        else:
            keys = list(self.widgets.keys())
            selected = [keys[i] for i in indices if i < len(keys)]
            if reverse and selected:
                selected.reverse()
            for key in selected:
                yield self.widgets[key].item_model

    # ------------------------------------------------------------------
    # All-items iterators (ignore visibility)
    # ------------------------------------------------------------------

    def all_widget_iter(self) -> ty.Iterator[_W]:
        """Yield every child widget regardless of visibility."""
        yield from self.widgets.values()  # type: ignore[misc]

    def all_model_iter(self, indices: ty.Sequence[int] | None = None, reverse: bool = False) -> ty.Iterator[_M]:
        """Yield item models for every row regardless of visibility."""
        if indices is None:
            indices = range(self.count())
        keys = list(self.widgets.keys())
        selected = [keys[i] for i in indices if i < len(keys)]
        if reverse and selected:
            selected.reverse()
        for key in selected:
            yield self.widgets[key].item_model

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def _check_existing(self, item_model: _M) -> bool:
        """Check if item with the same model already exists."""
        raise NotImplementedError("Must implement method")

    def append_item(self, item_model: _M) -> _W | None:
        """Append ``item_model`` and return its widget."""
        if self._check_existing(item_model):
            return None
        widget = self._make_widget(item_model)
        widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.widgets = {item_model.unique_id: widget, **self.widgets}
        self._layout.insertWidget(0, widget)
        self.evt_added.emit(item_model)
        self.evt_updated.emit(self.count())
        return widget

    def get_widget_for_item_model(self, item_model: _M) -> _W | None:
        """Get the widget by its model."""
        return self.widgets.get(item_model.unique_id)

    def remove_item(self, item_model: _M, force: bool = False) -> None:
        """Remove the row associated with ``item_model``."""
        self.evt_pre_remove.emit(item_model)
        widget = self.widgets.get(item_model.unique_id)
        if widget:
            self._layout.removeWidget(widget)
            widget.deleteLater()
        self.widgets.pop(item_model.unique_id, None)
        self.evt_remove.emit(item_model)
        self.evt_updated.emit(self.count())

    def remove_by_item_model(self, item_model: _M, force: bool = False, **_kwargs: ty.Any):
        """Remove item from the list based on the item model."""
        self.remove_item(item_model, force=force)

    def get_item_widget_for_index(self, index: int) -> tuple[_M, _W]:
        """Return the model and widget stored at ``index``."""
        keys = list(self.widgets.keys())
        if index < 0 or index >= len(keys):
            raise IndexError("Index out of range")
        key = keys[index]
        widget = self.widgets[key]
        return widget.item_model, widget

    def get_widget_for_hash_id(self, hash_id: str) -> _W | None:
        """Return the widget matching ``hash_id``, if present."""
        index = self.get_index_for_hash_id(hash_id)
        if index == -1:
            return None
        return self.get_item_widget_for_index(index)[1]

    def get_item_for_index(self, index: int) -> _M:
        """Return the model stored at ``index``."""
        return self.get_item_widget_for_index(index)[0]

    def get_widget_for_index(self, index: int) -> _W:
        """Return the widget stored at ``index``."""
        return self.get_item_widget_for_index(index)[1]

    def filter_items(self, predicate: ty.Callable[[_W], bool]) -> int:
        """Show or hide each row based on ``predicate``. Returns visible count."""
        visible = 0
        for widget in self.widgets.values():
            show = predicate(widget)
            widget._toggle_visibility(show)
            if show:
                visible += 1
        return visible

    def reset_data(self) -> None:
        """Remove all rows and emit lifecycle signals."""
        for widget in list(self.widgets.values()):
            self._layout.removeWidget(widget)
            widget.deleteLater()
        self.widgets.clear()
        self.evt_cleared.emit()
        self.evt_updated.emit(0)

    def refresh(self) -> None:
        """Refresh all row widgets from their bound models."""
        for widget in self.widgets.values():
            if hasattr(widget, "refresh"):
                widget.refresh()
