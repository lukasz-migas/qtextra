"""Module responsible for handling user interaction with the image."""

from dataclasses import dataclass
from typing import Union

import numpy as np

# from imspy_core.reader import SingleReader
from koyo.utilities import check_value_order
from qtpy.QtCore import QObject, QPointF, Signal


class Polygon(QObject):
    """Class responsible for collecting points."""

    evt_n_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.points = []
        self._last_idx = -1

    @property
    def n_points(self) -> int:
        """Return the number of points in the container."""
        return len(self.points)

    def reset(self):
        """Reset polygon."""
        self.points.clear()
        self._last_idx = -1
        self.evt_n_changed.emit(0)

    def add_point(self, x: Union[int, float], y: Union[int, float]):
        """Add point to the polygon container."""
        if [x, y] in self.points:
            return
        self.points.append([x, y])
        self._last_idx += 1
        self.evt_n_changed.emit(self.n_points)

    def remove_point(self, x: Union[int, float], y: Union[int, float]):
        """Remove point (x, y) from the list."""
        remove_id = -1
        for i, (_x, _y) in enumerate(self.points):
            if _x == x and _y == y:
                remove_id = i
                break
        if remove_id != -1:
            del self.points[remove_id]
            self.evt_n_changed.emit(self.n_points)

    def remove_last(self):
        """Remove last point from polygon."""
        if self._last_idx != -1:
            del self.points[self._last_idx]
            self._last_idx -= 1
            self.evt_n_changed.emit(self.n_points)

    def get_polygon(self, ax, dpi_ratio: float, height: float) -> list[QPointF]:
        """Render currently present points as polygon."""
        points = []
        for x, y in self.points:
            (_x, _y) = ax.transData.transform([x, y])
            _y = height - _y
            points.append(QPointF(_x / dpi_ratio, _y / dpi_ratio))
        return points

    def get_polygon_mpl(self) -> np.ndarray:
        """Get polygon data."""
        return np.asarray([[y, x] for (x, y) in self.points])

    def get_polygon_vispy(self) -> np.ndarray:
        """Get polygon data."""
        return np.asarray([[x, y] for (x, y) in self.points])

    def get_zoom_rect(self) -> tuple:
        """Get zoom-in rectangle."""
        points = self.get_polygon_mpl()
        y_min, y_max = points[:, 0].min(), points[:, 0].max()
        x_min, x_max = points[:, 1].min(), points[:, 1].max()
        return x_min, x_max, y_min, y_max


@dataclass
class ExtractEvent:
    """Data object to ensure all necessary data extraction is provided."""

    roi_shape: str
    xmin: Union[int, float]
    xmax: Union[int, float]
    ymin: Union[int, float]
    ymax: Union[int, float]
    polygon: Polygon = None
    x_labels: list[str] = None
    y_labels: list[str] = None

    # cacheable properties
    _mask: np.ndarray = None
    _framelist: np.ndarray = None

    @property
    def width(self) -> float:
        """Get width of the bounding box."""
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        """Get height of the bounding box."""
        return self.ymax - self.ymin

    def get_x_range(self) -> tuple[float, float]:
        """Get the x-axis extraction range."""
        return self.xmin, self.xmax

    def get_y_range(self) -> tuple[float, float]:
        """Get the x-axis extraction range."""
        return self.ymin, self.ymax

    def get_rect(self) -> tuple[float, float, float, float]:
        """Get rect parameters."""
        return self.xmin, self.ymin, self.width, self.height

    def get_x_with_width_label(self, n_dim: int = 0) -> str:
        """Get the mean value of x with +/- window around it."""
        x = get_center(self.xmin, self.xmax)
        width = abs(self.width) / 2
        if n_dim == 0:
            return f"{int(np.round(x, n_dim))} ± {int(np.round(width, n_dim))}"
        return f"{np.round(x, n_dim)} ± {np.round(width, n_dim)}"

    def unpack(self, as_int: bool = False):
        """Unpack values to give the usual xmin, xmax, ymin, ymax."""
        if as_int:
            return [round(v) for v in [self.xmin, self.xmax, self.ymin, self.ymax]]
        return self.xmin, self.xmax, self.ymin, self.ymax

    def unpack_rect(self, as_int: bool = False):
        """Unpack values to give the xmin, ymin, xmax, ymax."""
        if as_int:
            return [round(v) for v in [self.xmin, self.ymin, self.xmax, self.ymax]]
        return self.xmin, self.ymin, self.xmax, self.ymax

    def is_point(self) -> bool:
        """Checks whether it was a point."""
        if abs(self.xmax - self.xmin) < 0.0001 and abs(self.ymax - self.ymin) < 0.0001:
            return True
        return False

    def round_point(self):
        """Slightly modify values to enable extraction."""
        self.xmin -= 0.5
        self.ymin -= 0.5
        self.xmax += 0.5
        self.ymax += 0.5

    def get_rect_1d(self) -> tuple:
        """Get rectangle parameters compatible with matplotlib."""
        return self.xmin, 0, self.width, None

    def get_window(self, as_int: bool = False) -> tuple:
        """Get window."""
        xmin, xmax, _, _ = self.unpack(as_int)
        return xmin, xmax

    def get_ellipse(self) -> tuple[tuple[float, float], float, float]:
        """Get ellipse parameters."""
        assert self.roi_shape == "circle", "The ROI should be a circle"
        x_center, y_center = get_center(self.xmin, self.xmax), get_center(self.ymin, self.ymax)
        x_center, y_center = x_center - 0.5, y_center - 0.5
        x_radius, y_radius = self.xmax - x_center, self.ymax - y_center
        r, c = y_center, x_center
        r_radius, c_radius = y_radius, x_radius
        return (r, c), r_radius, c_radius

    def get_ellipse_mpl(self) -> tuple[tuple[float, float], float, float]:
        """Get ellipse parameters compatible with matplotlib."""
        assert self.roi_shape == "circle", "The ROI should be a circle"
        center, height, width = self.get_ellipse()
        center = list(center)
        center = (center[1] + 0.5, center[0] + 0.5)
        return center, width, height

    def get_zoom_rect(self, pad: float = 5, as_int: bool = True) -> tuple:
        """Get x- and y-axis zoom window.

        Parameters
        ----------
        pad : float
            amount of padding around each of the values
        as_int : bool
            if ``True``, return all values as integers
        """
        if self.roi_shape == "poly":
            assert self.polygon is not None, "Missing polygon data"
            xmin, xmax, ymin, ymax = self.polygon.get_zoom_rect()
        else:
            xmin, xmax, ymin, ymax = self.unpack(as_int)
        return xmin - pad, xmax + pad, ymin - pad, ymax + pad

    # def get_framelist(self, m_obj: SingleReader, flipud: bool = False) -> np.ndarray:
    #     """Get list of frames based on the extraction parameters.
    #
    #     Parameters
    #     ----------
    #     m_obj : SingleReader
    #         SingleReader object
    #     flipud : bool
    #         if ``True``, the original mask will be flipped
    #
    #     Returns
    #     -------
    #     framelist : np.ndarray
    #         array of sorted frames that should be consumed by some extraction function
    #     """
    #     if self.is_point():
    #         self.round_point()
    #     if self._framelist is not None:
    #         return self._framelist
    #     if self.roi_shape == "rect":
    #         framelist = m_obj.get_framelist_from_rect(*self.unpack(True), flipud=flipud)
    #     elif self.roi_shape == "circle":
    #         center, r_radius, c_radius = self.get_ellipse()
    #         framelist = m_obj.get_framelist_from_circle(center, r_radius, c_radius, flipud=flipud)
    #     elif self.roi_shape == "poly":
    #         assert self.polygon is not None, "Missing polygon data"
    #         polygons = self.polygon.get_polygon_mpl()
    #         framelist = m_obj.get_framelist_from_poly(polygons, flipud=flipud)
    #     else:
    #         raise ValueError("Cannot parse this type of ROI yet")
    #
    #     self._framelist = np.sort(framelist)  # cache in cased its needed again
    #     return self._framelist
    #
    # def get_mask(self, m_obj: SingleReader, flipud: bool = False) -> np.ndarray:
    #     """Get mask of the same shape as the default image.
    #
    #     Parameters
    #     ----------
    #     m_obj : SingleReader
    #         SingleReader object
    #     flipud : bool
    #         if ``True``, the original mask will be flipped
    #
    #     Returns
    #     -------
    #     mask : np.ndarray
    #         2d image mask for this particular event / roi
    #     """
    #     if self._mask is not None:
    #         return self._mask
    #     if self.roi_shape == "rect":
    #         mask = m_obj.get_mask_from_rect(*self.unpack(True), flipud=flipud)
    #     elif self.roi_shape == "circle":
    #         center, r_radius, c_radius = self.get_ellipse()
    #         mask = m_obj.get_mask_from_circle(center, r_radius, c_radius, flipud=flipud)
    #     elif self.roi_shape == "poly":
    #         assert self.polygon is not None, "Missing polygon data"
    #         polygons = self.polygon.get_polygon_mpl()
    #         mask = m_obj.get_mask_from_poly(polygons, flipud=flipud)
    #     else:
    #         raise ValueError("Cannot parse this type of ROI yet")
    #     self._mask = mask
    #     return mask

    def get_line_mask(self, as_int: bool = True):
        """Get 1d mask that can be used to extract part of the data."""
        xmin, xmax, _, _ = self.unpack(as_int)
        return np.arange(xmin, xmax)


def get_center(x1: float, x2: float) -> float:
    """Get center."""
    mod = abs(x1 - x2) / 2
    x1, x2 = check_value_order(x1, x2)
    return x1 + mod
