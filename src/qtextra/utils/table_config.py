"""Table configuration class."""

from __future__ import annotations

import typing as ty

from koyo.containers import MutableMapping

ColumnSizing = ty.Literal["stretch", "fixed", "contents"]
Alignment = ty.Literal["left", "center", "right"]


class Column(ty.TypedDict):
    """Column data."""

    name: str
    tag: str
    type: str
    show: bool
    width: int
    order: int
    hidden: bool
    tooltip: str
    sizing: ColumnSizing


class TableConfig(MutableMapping[int, Column]):
    """Table configuration object."""

    def __init__(self, text_alignment: Alignment | str = "center") -> None:
        super().__init__()
        self._dict: dict[int, Column] = {}
        self.last_index = -1
        self.color_columns: list[int] = []
        self.no_sort_columns: list[int] = []
        self.checkable_columns: list[int] = []
        self.html_columns: list[int] = []
        self.icon_columns: list[int] = []
        self.text_alignment: Alignment = text_alignment

    def __getitem__(self, tag: ty.Union[int, str]) -> ty.Any:
        """Get item id."""
        if isinstance(tag, int):
            val = self._dict[tag]
        else:
            val = self.find_col_id(tag)
        if val == -1:
            raise KeyError("Could not retrieve value")
        return val

    def __iter__(self):
        return iter(self._dict)

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
        for name_, meta_ in self.items():
            if name == name_:
                meta_[attr] = value

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
        sizing: ColumnSizing | str = "stretch",
        checkable: bool = False,
    ) -> TableConfig:
        """Add an item to the configuration."""
        if dtype == "bool":
            sizing = "contents"
        self.last_index += 1
        if self.last_index == 0 and dtype == "bool":
            checkable = True

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
        if checkable and dtype == "bool":
            self.checkable_columns.append(self.last_index)
        if no_sort:
            self.no_sort_columns.append(self.last_index)
        if dtype == "icon":
            self.icon_columns.append(self.last_index)
        return self

    def get_column(self, tag: str) -> Column | None:
        """Get column by tag."""
        for _col_id, col_info in self.items():
            if col_info["tag"] == tag:
                return col_info
        return None

    def find_col_id(self, tag: str) -> int:
        """Find column id by the tag."""
        for col_id, col_info in self.items():
            if col_info["tag"] == tag:
                return col_id
        return -1

    def get_width(self, column_id: int) -> int:
        """Get the width of column."""
        data = self.get(column_id, {})
        width: int = data.get("width", 100)
        return width

    def to_columns(self, include_check: bool = True) -> list[str]:
        """Return columns."""
        if include_check:
            return [v["name"] for v in self.values()]
        return [v["name"] for v in self.values() if v["tag"] != "check"]

    def column_iter(self) -> ty.Iterator[tuple[int, Column]]:
        """Return column iterator."""
        for col_id in self:
            yield col_id, self[col_id]
