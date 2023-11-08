from collections import OrderedDict
from enum import Enum


class Symbol(str, Enum):
    """Symbol: Valid symbol/marker types for the Points layer.
    The string method returns the valid vispy string.

    """

    ARROW = "arrow"
    CLOBBER = "clobber"
    CROSS = "cross"
    DIAMOND = "diamond"
    DISC = "disc"
    HBAR = "hbar"
    RING = "ring"
    SQUARE = "square"
    STAR = "star"
    TAILED_ARROW = "tailed_arrow"
    TRIANGLE_DOWN = "triangle_down"
    TRIANGLE_UP = "triangle_up"
    VBAR = "vbar"
    X = "x"

    def __str__(self):
        """String representation: The string method returns the
        valid vispy symbol string for the Markers visual.
        """
        return self.value


# Mapping of symbol alias names to the deduplicated name
SYMBOL_ALIAS = {
    "o": Symbol.DISC,
    "*": Symbol.STAR,
    "+": Symbol.CROSS,
    "-": Symbol.HBAR,
    "->": Symbol.TAILED_ARROW,
    ">": Symbol.ARROW,
    "^": Symbol.TRIANGLE_UP,
    "v": Symbol.TRIANGLE_DOWN,
    "s": Symbol.SQUARE,
    "|": Symbol.VBAR,
}


SYMBOL_TRANSLATION = OrderedDict(
    [
        (Symbol.ARROW, "arrow"),
        (Symbol.CLOBBER, "clobber"),
        (Symbol.CROSS, "cross"),
        (Symbol.DIAMOND, "diamond"),
        (Symbol.DISC, "disc"),
        (Symbol.HBAR, "hbar"),
        (Symbol.RING, "ring"),
        (Symbol.SQUARE, "square"),
        (Symbol.STAR, "star"),
        (Symbol.TAILED_ARROW, "tailed arrow"),
        (Symbol.TRIANGLE_DOWN, "triangle down"),
        (Symbol.TRIANGLE_UP, "triangle up"),
        (Symbol.VBAR, "vbar"),
        (Symbol.X, "x"),
    ]
)
