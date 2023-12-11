"""Table configuration class."""
from __future__ import annotations

import typing as ty

from koyo.utilities import is_valid_python_name


class TableConfig(ty.MutableMapping[int, dict[str, ty.Any]]):
    """Table configuration object."""

    def __init__(self):
        self._dict = {}
        self.last_index = -1
        self.color_columns = []
        self.no_sort_columns: list[int] = []
        self.checkable_columns: list[int] = []
        self.html_columns: list[int] = []
        self.icon_columns: list[int] = []

    def __getitem__(self, tag: ty.Union[int, str]) -> ty.Any:
        """Get item id."""
        if isinstance(tag, int):
            val = self._dict[tag]
        else:
            val = self.find_col_id(tag)
        if val == -1:
            raise KeyError("Could not retrieve value")
        return val

    def __dir__(self) -> list[str]:
        # noinspection PyUnresolvedReferences
        base = super().__dir__()
        keys = sorted(set(base + list(self) + list(self._dict.keys())))  # type: ignore[operator]
        keys = [k for k in keys if is_valid_python_name(k)]
        return keys

    def __setitem__(self, __key, __value):
        self._dict[__key] = __value

    def __delitem__(self, __key):
        del self._dict[__key]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def _ipython_key_completions_(self) -> list[str]:
        return sorted(self)

    def __getattr__(self, item: ty.Union[int, str]) -> ty.Any:
        # allow access to group members via dot notation
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError from None

    @property
    def n_columns(self) -> int:
        """Return number of columns."""
        return len(self)

    @property
    def header(self) -> list[str]:
        """Return header."""
        return [v["name"] for v in self.values()]

    @property
    def hidden_columns(self) -> list[int]:
        """Returns list of hidden columns."""
        return [value["order"] for value in self.values() if value["hidden"]]

    def update_attribute(self, name: str, attr: str, value: ty.Any) -> None:
        """Update attribute value."""
        for _name, _meta in self.items():
            if _name == name:
                _meta[attr] = value

    def add(
        self,
        name: str,
        tag: str,
        dtype: str,
        width: int,
        show: bool = True,
        hidden: bool = False,
        is_color: bool = False,
        no_sort: bool = False,
        tooltip: str = "",
        sizing: str = "stretch",
        checkable: bool = False,
    ) -> TableConfig:
        """Add an item to the configuration."""
        self.last_index += 1
        self[self.last_index] = {
            "name": name,
            "tag": tag,
            "type": dtype,
            "show": show,
            "width": width,
            "order": self.last_index,
            "hidden": hidden,
            "tooltip": tooltip,
            "sizing": sizing,
        }
        if is_color:
            self.color_columns.append(self.last_index)
        if checkable or dtype == "bool":
            self.checkable_columns.append(self.last_index)
        if no_sort:
            self.no_sort_columns.append(self.last_index)
        if dtype == "icon":
            self.icon_columns.append(self.last_index)
        return self

    def find_col_id(self, tag: str) -> int:
        """Find column id by the tag."""
        for col_id, col_info in self.items():
            if col_info["tag"] == tag:
                return col_id
        return -1

    def get_width(self, column_id: int) -> int:
        """Get the width of column."""
        data = self.get(column_id, {})
        if data:
            return data["width"]
        return 100
