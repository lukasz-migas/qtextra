"""Table configuration class."""
import typing as ty

from koyo.utilities import is_valid_python_name


class TableConfig(dict):
    """Table configuration object."""

    def __init__(self):
        super().__init__()
        self.last_idx = -1
        self.color_column = -1
        self._no_sort_columns: ty.List[int] = []
        self._icon_columns: ty.List[int] = []

    def __getitem__(self, tag: ty.Union[int, str]) -> ty.Any:
        """Get item id."""
        if isinstance(tag, int):
            val = self[tag]
        else:
            val = self.find_col_id(tag)
        if val == -1:
            raise KeyError("Could not retrieve value")
        return val

    def __dir__(self) -> ty.List[str]:
        # noinspection PyUnresolvedReferences
        base = super().__dir__()
        keys = sorted(set(base + list(self) + list(self.keys())))  # type: ignore[operator]
        keys = [k for k in keys if is_valid_python_name(k)]
        return keys

    def _ipython_key_completions_(self) -> ty.List[str]:
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
    def header(self) -> ty.List[str]:
        """Return header."""
        return [v["name"] for v in self.values()]

    @property
    def hidden_columns(self) -> ty.List[int]:
        """Returns list of hidden columns."""
        return [value["order"] for value in self.values() if value["hidden"]]

    @property
    def icon_columns(self) -> ty.List[int]:
        """Returns list of hidden columns."""
        return self._icon_columns

    @property
    def no_sort_columns(self) -> ty.List[int]:
        """Returns list of."""
        return self._no_sort_columns

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
    ) -> "TableConfig":
        """Add an item to the configuration."""
        self.last_idx += 1
        self[self.last_idx] = {
            "name": name,
            "tag": tag,
            "type": dtype,
            "show": show,
            "width": width,
            "order": self.last_idx,
            "hidden": hidden,
            "tooltip": tooltip,
        }
        if is_color:
            self.color_column = self.last_idx
        if no_sort:
            self._no_sort_columns.append(self.last_idx)
        if dtype == "icon":
            self._icon_columns.append(self.last_idx)
        return self

    def find_col_id(self, tag: str) -> int:
        """Find column id by the tag."""
        for col_id, col_info in self.items():
            if col_info["tag"] == tag:
                return col_id  # type: ignore
        return -1
