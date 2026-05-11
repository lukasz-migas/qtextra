"""Minimal Pac-Man-like game dialog."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, replace
from enum import Enum

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import QHBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config.theme import THEMES
from qtextra.games._base import GameBoardWidget, GameDialogMixin
from qtextra.widgets.qt_dialog import QtDialog

# ── layout constants ──────────────────────────────────────────────────────────
COLS = 21
ROWS = 21
TICK_INTERVAL_MS = 150
PLAYER_LIVES = 3
FRIGHTENED_TICKS = 40  # ~6 s at 150 ms per tick

# ── scoring ───────────────────────────────────────────────────────────────────
DOT_SCORE = 10
PELLET_SCORE = 50
GHOST_BASE_SCORE = 200

# ── key positions ─────────────────────────────────────────────────────────────
GHOST_DOOR_COL = 10
GHOST_DOOR_ROW = 9  # row in MAZE that holds '='
GHOST_HOUSE_COL = 10
GHOST_HOUSE_ROW = 10  # interior respawn target
PLAYER_START_COL = 10
PLAYER_START_ROW = 15

# ── ghost release: dots eaten before ghost leaves the house ───────────────────
_RELEASE_DOTS: dict[str, int] = {
    "BLINKY": 0,  # starts outside; only matters if eaten and respawned
    "PINKY": 0,
    "INKY": 30,
    "CLYDE": 60,
}
# Ticks a ghost stays in the house after being eaten before re-entering play.
_RESPAWN_TICKS = 20  # 20 * 150 ms ≈ 3 seconds

# ── global mode schedule: (ticks, mode_name); -1 ticks = indefinite ──────────
_MODE_SCHEDULE: tuple[tuple[int, str], ...] = (
    (47, "SCATTER"),
    (133, "CHASE"),
    (47, "SCATTER"),
    (133, "CHASE"),
    (33, "SCATTER"),
    (-1, "CHASE"),
)

# ── maze ──────────────────────────────────────────────────────────────────────
#   '#' wall   '.' dot   'o' power pellet   ' ' ghost-house interior   '=' door
MAZE: tuple[str, ...] = (
    "#####################",  # 0
    "#...................#",  # 1
    "#.###.####.####.###.#",  # 2
    "#o.................o#",  # 3  power pellets at col 1 and 19
    "#.###.####.####.###.#",  # 4
    "#...................#",  # 5
    "#.###.####.####.###.#",  # 6
    "#.###...........###.#",  # 7  open centre
    "#.###.####.####.###.#",  # 8
    "#.###.####=####.###.#",  # 9  ghost door at col 10
    "#.###.###   ###.###.#",  # 10 ghost house interior
    "#.###.###   ###.###.#",  # 11 ghost house interior
    "#.###.#########.###.#",  # 12 ghost house bottom wall
    "#.###...........###.#",  # 13 open centre
    "#.###.####.####.###.#",  # 14
    "#...................#",  # 15
    "#.###.####.####.###.#",  # 16
    "#o.................o#",  # 17 power pellets at col 1 and 19
    "#.###.####.####.###.#",  # 18
    "#...................#",  # 19
    "#####################",  # 20
)

assert all(len(row) == COLS for row in MAZE), "MAZE row length mismatch"
assert len(MAZE) == ROWS, "MAZE row count mismatch"


# ── enums ─────────────────────────────────────────────────────────────────────


class Direction(Enum):
    """Cardinal movement direction."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self) -> tuple[int, int]:
        """Return the (dcol, drow) step for this direction."""
        return self.value  # type: ignore[return-value]

    @property
    def opposite(self) -> Direction:
        """Return the 180-degree opposite direction."""
        dc, dr = self.value
        return Direction((-dc, -dr))


class GhostMode(Enum):
    """Ghost behaviour mode."""

    SCATTER = "SCATTER"
    CHASE = "CHASE"
    FRIGHTENED = "FRIGHTENED"
    EATEN = "EATEN"


class GhostName(Enum):
    """Ghost identity with start position and scatter corner."""

    BLINKY = "BLINKY"
    PINKY = "PINKY"
    INKY = "INKY"
    CLYDE = "CLYDE"

    @property
    def scatter_target(self) -> tuple[int, int]:
        """Return the (col, row) scatter corner for this ghost."""
        corners: dict[GhostName, tuple[int, int]] = {
            GhostName.BLINKY: (COLS - 2, 1),
            GhostName.PINKY: (1, 1),
            GhostName.INKY: (COLS - 2, ROWS - 2),
            GhostName.CLYDE: (1, ROWS - 2),
        }
        return corners[self]

    @property
    def start_col(self) -> int:
        """Starting column in the maze."""
        cols: dict[GhostName, int] = {
            GhostName.BLINKY: 10,
            GhostName.PINKY: 9,
            GhostName.INKY: 10,
            GhostName.CLYDE: 11,
        }
        return cols[self]

    @property
    def start_row(self) -> int:
        """Starting row in the maze."""
        rows: dict[GhostName, int] = {
            GhostName.BLINKY: 8,
            GhostName.PINKY: 10,
            GhostName.INKY: 10,
            GhostName.CLYDE: 10,
        }
        return rows[self]

    @property
    def color(self) -> QColor:
        """Characteristic display colour."""
        colors: dict[GhostName, QColor] = {
            GhostName.BLINKY: QColor(231, 76, 60),
            GhostName.PINKY: QColor(255, 105, 180),
            GhostName.INKY: QColor(0, 206, 209),
            GhostName.CLYDE: QColor(255, 165, 0),
        }
        return colors[self]


# ── dataclasses ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Ghost:
    """Immutable state for one ghost."""

    name: GhostName
    col: int
    row: int
    direction: Direction
    mode: GhostMode
    in_house: bool
    been_released: bool  # has ever left the ghost house
    frightened_ticks: int  # remaining ticks in FRIGHTENED mode
    respawn_ticks: int = 0  # countdown after being eaten; held in house while > 0


@dataclass(frozen=True, slots=True)
class PacmanGameState:
    """Immutable full Pac-Man game state."""

    dots: frozenset[tuple[int, int]]
    power_pellets: frozenset[tuple[int, int]]
    player_col: int
    player_row: int
    player_dir: Direction
    player_queued_dir: Direction | None
    ghosts: tuple[Ghost, ...]
    score: int
    lives: int
    global_mode: GhostMode
    mode_ticks: int
    mode_phase: int
    dots_eaten: int
    ghost_eat_streak: int
    is_game_over: bool
    level_complete: bool
    has_started: bool
    maze: tuple[str, ...]


# ── maze helpers ──────────────────────────────────────────────────────────────


def _cell(col: int, row: int, maze: tuple[str, ...]) -> str:
    """Return the maze character at (col, row), or '#' if out of bounds."""
    if 0 <= row < ROWS and 0 <= col < COLS:
        return maze[row][col]
    return "#"


def _passable(col: int, row: int, *, can_use_door: bool, maze: tuple[str, ...]) -> bool:
    """Return True if an entity can move to (col, row).

    Normal entities (player and ghosts in the maze) use can_use_door=False.
    Ghosts entering/exiting the house use can_use_door=True.
    """
    ch = _cell(col, row, maze)
    if ch == "#":
        return False
    if ch in (" ", "="):
        return can_use_door
    return True  # '.', 'o'


def _is_house_interior(col: int, row: int, maze: tuple[str, ...]) -> bool:
    """Return True only for ghost-house interior cells (' ')."""
    return _cell(col, row, maze) == " "


# ── BFS pathfinding ───────────────────────────────────────────────────────────


def _bfs_next_dir(
    from_col: int,
    from_row: int,
    target_col: int,
    target_row: int,
    *,
    can_use_door: bool,
    forbidden_dir: Direction | None,
    maze: tuple[str, ...],
) -> Direction | None:
    """Return the first direction to take on the shortest path to the target.

    Returns None when already at the target or no path exists.
    """
    if from_col == target_col and from_row == target_row:
        return None

    visited: set[tuple[int, int]] = {(from_col, from_row)}
    queue: deque[tuple[int, int, Direction]] = deque()

    for direction in Direction:
        if forbidden_dir is not None and direction == forbidden_dir:
            continue
        dc, dr = direction.delta
        nc, nr = from_col + dc, from_row + dr
        if _passable(nc, nr, can_use_door=can_use_door, maze=maze) and (nc, nr) not in visited:
            visited.add((nc, nr))
            queue.append((nc, nr, direction))

    while queue:
        col, row, first_dir = queue.popleft()
        if col == target_col and row == target_row:
            return first_dir
        for direction in Direction:
            dc, dr = direction.delta
            nc, nr = col + dc, row + dr
            if _passable(nc, nr, can_use_door=can_use_door, maze=maze) and (nc, nr) not in visited:
                visited.add((nc, nr))
                queue.append((nc, nr, first_dir))

    # No path found with the forbidden direction constraint — retry without it.
    if forbidden_dir is not None:
        return _bfs_next_dir(
            from_col,
            from_row,
            target_col,
            target_row,
            can_use_door=can_use_door,
            forbidden_dir=None,
            maze=maze,
        )
    return None


def _valid_dirs(
    col: int,
    row: int,
    *,
    can_use_door: bool,
    forbidden_dir: Direction | None,
    maze: tuple[str, ...],
) -> list[Direction]:
    """Return all passable directions from (col, row), excluding forbidden_dir."""
    result = []
    for direction in Direction:
        if forbidden_dir is not None and direction == forbidden_dir:
            continue
        dc, dr = direction.delta
        if _passable(col + dc, row + dr, can_use_door=can_use_door, maze=maze):
            result.append(direction)
    return result


# ── ghost targeting ───────────────────────────────────────────────────────────


def _ghost_chase_target(ghost: Ghost, state: PacmanGameState) -> tuple[int, int]:
    """Return the (col, row) chase target for a ghost."""
    pc, pr = state.player_col, state.player_row

    if ghost.name == GhostName.BLINKY:
        return pc, pr

    if ghost.name == GhostName.PINKY:
        dc, dr = state.player_dir.delta
        return pc + dc * 4, pr + dr * 4

    if ghost.name == GhostName.INKY:
        dc, dr = state.player_dir.delta
        mid_c, mid_r = pc + dc * 2, pr + dr * 2
        blinky = next((g for g in state.ghosts if g.name == GhostName.BLINKY), None)
        if blinky is not None:
            return 2 * mid_c - blinky.col, 2 * mid_r - blinky.row
        return pc, pr

    # Clyde: chase if far, scatter if close (> 8 tiles away).
    dist_sq = (ghost.col - pc) ** 2 + (ghost.row - pr) ** 2
    if dist_sq > 64:
        return pc, pr
    return ghost.name.scatter_target


# ── ghost movement ────────────────────────────────────────────────────────────


def _move_ghost(ghost: Ghost, state: PacmanGameState, rng: random.Random) -> Ghost:
    """Advance a ghost by one step and return the updated ghost."""
    maze = state.maze

    # ── inside the ghost house ─────────────────────────────────────────────
    if ghost.in_house:
        threshold = _RELEASE_DOTS.get(ghost.name.value, 0)
        should_release = ghost.been_released or (state.dots_eaten >= threshold)

        if not should_release or ghost.respawn_ticks > 0:
            # Bounce up-down using only house interior cells.
            new_respawn = max(0, ghost.respawn_ticks - 1)
            dc, dr = ghost.direction.delta
            nc, nr = ghost.col + dc, ghost.row + dr
            if _is_house_interior(nc, nr, maze):
                return replace(ghost, col=nc, row=nr, respawn_ticks=new_respawn)
            new_dir = ghost.direction.opposite
            dc, dr = new_dir.delta
            nc, nr = ghost.col + dc, ghost.row + dr
            if _is_house_interior(nc, nr, maze):
                return replace(ghost, col=nc, row=nr, direction=new_dir, respawn_ticks=new_respawn)
            return replace(ghost, respawn_ticks=new_respawn)  # nowhere to bounce (shouldn't occur)

        # Move toward the exit cell above the door.
        exit_col, exit_row = GHOST_DOOR_COL, GHOST_DOOR_ROW - 1
        next_dir = _bfs_next_dir(
            ghost.col,
            ghost.row,
            exit_col,
            exit_row,
            can_use_door=True,
            forbidden_dir=None,
            maze=maze,
        )
        if next_dir is None:
            # Already at exit — mark as released and face left.
            return replace(ghost, in_house=False, been_released=True, direction=Direction.LEFT)
        dc, dr = next_dir.delta
        nc, nr = ghost.col + dc, ghost.row + dr
        exited = nr < GHOST_DOOR_ROW
        return replace(
            ghost,
            col=nc,
            row=nr,
            direction=next_dir,
            in_house=not exited,
            been_released=ghost.been_released or exited,
        )

    # ── returning to house (EATEN) ─────────────────────────────────────────
    # Note: ghosts are normally teleported instantly on collision, so this path
    # is rarely reached. Keep it consistent with the teleport behaviour.
    if ghost.mode == GhostMode.EATEN:
        next_dir = _bfs_next_dir(
            ghost.col,
            ghost.row,
            GHOST_HOUSE_COL,
            GHOST_HOUSE_ROW,
            can_use_door=True,
            forbidden_dir=None,
            maze=maze,
        )
        if next_dir is None:
            # Arrived — respawn inside the house with a cooldown before re-exit.
            return replace(
                ghost,
                in_house=True,
                mode=state.global_mode,
                direction=Direction.DOWN,
                frightened_ticks=0,
                been_released=True,
                respawn_ticks=_RESPAWN_TICKS,
            )
        dc, dr = next_dir.delta
        nc, nr = ghost.col + dc, ghost.row + dr
        if nc == GHOST_HOUSE_COL and nr == GHOST_HOUSE_ROW:
            return replace(
                ghost,
                col=nc,
                row=nr,
                direction=next_dir,
                in_house=True,
                mode=state.global_mode,
                frightened_ticks=0,
                been_released=True,
                respawn_ticks=_RESPAWN_TICKS,
            )
        return replace(ghost, col=nc, row=nr, direction=next_dir)

    # ── frightened: move randomly, no reversing ────────────────────────────
    if ghost.mode == GhostMode.FRIGHTENED:
        valid = _valid_dirs(ghost.col, ghost.row, can_use_door=False, forbidden_dir=ghost.direction.opposite, maze=maze)
        if not valid:
            valid = _valid_dirs(ghost.col, ghost.row, can_use_door=False, forbidden_dir=None, maze=maze)
        if not valid:
            return ghost
        chosen = rng.choice(valid)
        dc, dr = chosen.delta
        return replace(ghost, col=ghost.col + dc, row=ghost.row + dr, direction=chosen)

    # ── scatter / chase: BFS toward target ────────────────────────────────
    if ghost.mode == GhostMode.SCATTER:
        tc, tr = ghost.name.scatter_target
    else:
        tc, tr = _ghost_chase_target(ghost, state)

    tc = max(0, min(COLS - 1, tc))
    tr = max(0, min(ROWS - 1, tr))

    next_dir = _bfs_next_dir(
        ghost.col,
        ghost.row,
        tc,
        tr,
        can_use_door=False,
        forbidden_dir=ghost.direction.opposite,
        maze=maze,
    )
    if next_dir is None:
        valid = _valid_dirs(ghost.col, ghost.row, can_use_door=False, forbidden_dir=ghost.direction.opposite, maze=maze)
        if not valid:
            valid = _valid_dirs(ghost.col, ghost.row, can_use_door=False, forbidden_dir=None, maze=maze)
        if not valid:
            return ghost
        next_dir = valid[0]

    dc, dr = next_dir.delta
    return replace(ghost, col=ghost.col + dc, row=ghost.row + dr, direction=next_dir)


# ── state factories ───────────────────────────────────────────────────────────


def _initial_dots(maze: tuple[str, ...]) -> frozenset[tuple[int, int]]:
    """Extract all dot positions from the maze."""
    return frozenset((col, row) for row in range(ROWS) for col in range(COLS) if maze[row][col] == ".")


def _initial_pellets(maze: tuple[str, ...]) -> frozenset[tuple[int, int]]:
    """Extract all power-pellet positions from the maze."""
    return frozenset((col, row) for row in range(ROWS) for col in range(COLS) if maze[row][col] == "o")


def _is_fully_connected(grid: list[list[str]]) -> bool:
    """Return True if all dot/pellet cells are reachable from the player start via walkable cells."""
    walkable = {(row, col) for row in range(ROWS) for col in range(COLS) if grid[row][col] in (".", "o")}
    if not walkable:
        return False
    start = (PLAYER_START_ROW, PLAYER_START_COL)
    if start not in walkable:
        return False

    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque([start])
    visited.add(start)
    while queue:
        row, col = queue.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nb = (row + dr, col + dc)
            if nb in walkable and nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited == walkable


def generate_maze(rng: random.Random) -> tuple[str, ...]:
    """Generate a random Pac-Man maze with mirrored wall pillars.

    The ghost house, outer border, power pellets and player area are fixed.
    Random wall clusters are placed in the left half and mirrored to the right.
    Connectivity is verified after each placement; invalid placements are reverted.
    """
    grid: list[list[str]] = [["." for _ in range(COLS)] for _ in range(ROWS)]

    # Outer border walls.
    for c in range(COLS):
        grid[0][c] = "#"
        grid[ROWS - 1][c] = "#"
    for r in range(ROWS):
        grid[r][0] = "#"
        grid[r][COLS - 1] = "#"

    # Power pellets at the four inner corners.
    grid[3][1] = "o"
    grid[3][COLS - 2] = "o"
    grid[ROWS - 4][1] = "o"
    grid[ROWS - 4][COLS - 2] = "o"

    # Ghost house: outer walls, interior, and door.
    house_r0, house_r1 = 8, 12
    house_c0, house_c1 = 5, 15
    for c in range(house_c0, house_c1 + 1):
        grid[house_r0][c] = "#"
        grid[house_r1][c] = "#"
    for r in range(house_r0, house_r1 + 1):
        grid[r][house_c0] = "#"
        grid[r][house_c1] = "#"
    for r in range(house_r0 + 1, house_r1):
        for c in range(house_c0 + 1, house_c1):
            grid[r][c] = " "
    grid[GHOST_DOOR_ROW][GHOST_DOOR_COL] = "="

    # Protected cells that must never become walls.
    protected: set[tuple[int, int]] = set()
    # Outer border.
    for c in range(COLS):
        protected.add((0, c))
        protected.add((ROWS - 1, c))
    for r in range(ROWS):
        protected.add((r, 0))
        protected.add((r, COLS - 1))
    # Ghost house zone (generous margin).
    for r in range(house_r0 - 1, house_r1 + 2):
        for c in range(house_c0 - 1, house_c1 + 2):
            protected.add((r, c))
    # Power pellet corners.
    protected.update({(3, 1), (3, COLS - 2), (ROWS - 4, 1), (ROWS - 4, COLS - 2)})
    # Player starting area.
    for r in range(PLAYER_START_ROW - 1, PLAYER_START_ROW + 2):
        for c in range(PLAYER_START_COL - 1, PLAYER_START_COL + 2):
            protected.add((r, c))
    # Blinky start (just above door).
    protected.add((GHOST_DOOR_ROW - 1, GHOST_DOOR_COL))

    # Wall pillar shapes (as (row_offset, col_offset) tuples).
    pillar_shapes: list[list[tuple[int, int]]] = [
        [(0, 0), (0, 1)],  # 1x2 horizontal
        [(0, 0), (1, 0)],  # 2x1 vertical
        [(0, 0), (0, 1), (0, 2)],  # 1x3 horizontal
        [(0, 0), (1, 0), (2, 0)],  # 3x1 vertical
        [(0, 0), (0, 1), (1, 0), (1, 1)],  # 2x2 block
        [(0, 0), (0, 1)],  # 1x2 (weighted duplicate)
        [(0, 0), (1, 0)],  # 2x1 (weighted duplicate)
    ]

    target_walls = rng.randint(10, 18)
    walls_placed = 0
    attempts = 0
    max_attempts = 400

    while walls_placed < target_walls and attempts < max_attempts:
        attempts += 1
        shape = rng.choice(pillar_shapes)
        anchor_r = rng.randint(1, ROWS - 2)
        # Restrict left-half anchor so mirrored cells stay in bounds.
        anchor_c = rng.randint(1, COLS // 2 - 1)

        cells_left = [(anchor_r + dr, anchor_c + dc) for dr, dc in shape]
        cells_right = [(r, COLS - 1 - c) for r, c in cells_left]
        all_cells = list(dict.fromkeys(cells_left + cells_right))  # deduplicate

        if any(r < 1 or r >= ROWS - 1 or c < 1 or c >= COLS - 1 for r, c in all_cells):
            continue
        if any((r, c) in protected for r, c in all_cells):
            continue
        if any(grid[r][c] == "#" for r, c in all_cells):
            continue

        for r, c in all_cells:
            grid[r][c] = "#"

        if not _is_fully_connected(grid):
            for r, c in all_cells:
                grid[r][c] = "."
            continue

        walls_placed += 1

    # Ensure pellets are not accidentally overwritten.
    grid[3][1] = "o"
    grid[3][COLS - 2] = "o"
    grid[ROWS - 4][1] = "o"
    grid[ROWS - 4][COLS - 2] = "o"

    return tuple("".join(row) for row in grid)


def _make_ghosts(global_mode: GhostMode) -> tuple[Ghost, ...]:
    """Create the four ghosts in their starting configuration."""
    return (
        Ghost(
            name=GhostName.BLINKY,
            col=GhostName.BLINKY.start_col,
            row=GhostName.BLINKY.start_row,
            direction=Direction.LEFT,
            mode=global_mode,
            in_house=False,
            been_released=True,
            frightened_ticks=0,
        ),
        Ghost(
            name=GhostName.PINKY,
            col=GhostName.PINKY.start_col,
            row=GhostName.PINKY.start_row,
            direction=Direction.DOWN,
            mode=global_mode,
            in_house=True,
            been_released=False,
            frightened_ticks=0,
        ),
        Ghost(
            name=GhostName.INKY,
            col=GhostName.INKY.start_col,
            row=GhostName.INKY.start_row,
            direction=Direction.DOWN,
            mode=global_mode,
            in_house=True,
            been_released=False,
            frightened_ticks=0,
        ),
        Ghost(
            name=GhostName.CLYDE,
            col=GhostName.CLYDE.start_col,
            row=GhostName.CLYDE.start_row,
            direction=Direction.DOWN,
            mode=global_mode,
            in_house=True,
            been_released=False,
            frightened_ticks=0,
        ),
    )


def create_initial_state(rng: random.Random | None = None) -> PacmanGameState:
    """Create a fresh Pac-Man game state.

    If ``rng`` is provided a random maze is generated; otherwise the fixed
    default ``MAZE`` is used.
    """
    maze = generate_maze(rng) if rng is not None else MAZE
    phase_ticks, phase_mode_str = _MODE_SCHEDULE[0]
    global_mode = GhostMode[phase_mode_str]
    return PacmanGameState(
        dots=_initial_dots(maze),
        power_pellets=_initial_pellets(maze),
        player_col=PLAYER_START_COL,
        player_row=PLAYER_START_ROW,
        player_dir=Direction.LEFT,
        player_queued_dir=None,
        ghosts=_make_ghosts(global_mode),
        score=0,
        lives=PLAYER_LIVES,
        global_mode=global_mode,
        mode_ticks=phase_ticks,
        mode_phase=0,
        dots_eaten=0,
        ghost_eat_streak=0,
        is_game_over=False,
        level_complete=False,
        has_started=False,
        maze=maze,
    )


def queue_direction(state: PacmanGameState, direction: Direction) -> PacmanGameState:
    """Queue the player's next turn direction."""
    if state.is_game_over or state.level_complete:
        return state
    return replace(state, player_queued_dir=direction, has_started=True)


# ── main game logic ───────────────────────────────────────────────────────────


def advance_state(state: PacmanGameState, rng: random.Random) -> PacmanGameState:
    """Advance the game by one tick and return the new state."""
    if state.is_game_over or state.level_complete:
        return state

    # ── 1. Update global mode timer ────────────────────────────────────────
    mode_ticks = state.mode_ticks
    mode_phase = state.mode_phase
    global_mode = state.global_mode
    maze = state.maze

    if mode_ticks > 0:
        mode_ticks -= 1
    if mode_ticks == 0 and mode_phase < len(_MODE_SCHEDULE) - 1:
        mode_phase += 1
        new_ticks, new_mode_str = _MODE_SCHEDULE[mode_phase]
        global_mode = GhostMode[new_mode_str]
        mode_ticks = new_ticks

    # ── 2. Move player ─────────────────────────────────────────────────────
    player_col = state.player_col
    player_row = state.player_row
    player_dir = state.player_dir
    player_queued_dir = state.player_queued_dir

    # Try queued direction first; keep it queued if blocked.
    if player_queued_dir is not None:
        qdc, qdr = player_queued_dir.delta
        if _passable(player_col + qdc, player_row + qdr, can_use_door=False, maze=maze):
            player_dir = player_queued_dir
            player_queued_dir = None

    dc, dr = player_dir.delta
    nc, nr = player_col + dc, player_row + dr
    if _passable(nc, nr, can_use_door=False, maze=maze):
        player_col, player_row = nc, nr

    # ── 3. Eat dots and pellets ────────────────────────────────────────────
    pos = (player_col, player_row)
    score = state.score
    dots = state.dots
    pellets = state.power_pellets
    dots_eaten = state.dots_eaten
    ghost_eat_streak = state.ghost_eat_streak
    activated_frightened = False

    if pos in dots:
        dots = dots - {pos}
        score += DOT_SCORE
        dots_eaten += 1
    elif pos in pellets:
        pellets = pellets - {pos}
        score += PELLET_SCORE
        dots_eaten += 1
        activated_frightened = True
        ghost_eat_streak = 0

    # ── 4. Update ghost modes ──────────────────────────────────────────────
    updated_ghosts: list[Ghost] = []
    for ghost in state.ghosts:
        if ghost.mode == GhostMode.EATEN:
            # Returning ghosts keep their state unchanged.
            updated_ghosts.append(ghost)
        elif activated_frightened:
            # All non-EATEN ghosts (including those still in the house) become frightened.
            updated_ghosts.append(replace(ghost, mode=GhostMode.FRIGHTENED, frightened_ticks=FRIGHTENED_TICKS))
        elif ghost.mode == GhostMode.FRIGHTENED:
            # Countdown applies to both in-house and out-of-house frightened ghosts.
            ticks_left = ghost.frightened_ticks - 1
            if ticks_left <= 0:
                updated_ghosts.append(replace(ghost, mode=global_mode, frightened_ticks=0))
            else:
                updated_ghosts.append(replace(ghost, frightened_ticks=ticks_left))
        elif ghost.in_house:
            # Non-frightened, non-EATEN in-house ghosts keep their state.
            updated_ghosts.append(ghost)
        else:
            updated_ghosts.append(replace(ghost, mode=global_mode))

    # ── 5. Move ghosts ─────────────────────────────────────────────────────
    # Build a temporary state with current player position and updated ghost
    # modes so targeting functions read a consistent snapshot.
    temp_state = replace(
        state,
        player_col=player_col,
        player_row=player_row,
        player_dir=player_dir,
        global_mode=global_mode,
        dots_eaten=dots_eaten,
        ghost_eat_streak=ghost_eat_streak,
        ghosts=tuple(updated_ghosts),
    )
    moved_ghosts = [_move_ghost(g, temp_state, rng) for g in updated_ghosts]

    # ── 6. Player-ghost collisions ─────────────────────────────────────────
    lives = state.lives
    died = False
    final_ghosts: list[Ghost] = []

    for ghost in moved_ghosts:
        if ghost.col == player_col and ghost.row == player_row:
            if ghost.mode == GhostMode.FRIGHTENED:
                eat_score = GHOST_BASE_SCORE * (2**ghost_eat_streak)
                score += eat_score
                ghost_eat_streak += 1
                # Teleport the eaten ghost to the house; it stays there for
                # _RESPAWN_TICKS before re-entering play.
                final_ghosts.append(
                    replace(
                        ghost,
                        col=GHOST_HOUSE_COL,
                        row=GHOST_HOUSE_ROW,
                        in_house=True,
                        mode=global_mode,
                        frightened_ticks=0,
                        been_released=True,
                        direction=Direction.DOWN,
                        respawn_ticks=_RESPAWN_TICKS,
                    )
                )
            elif ghost.mode != GhostMode.EATEN:
                died = True
                final_ghosts.append(ghost)
            else:
                final_ghosts.append(ghost)
        else:
            final_ghosts.append(ghost)

    # ── 7. Handle player death ─────────────────────────────────────────────
    if died:
        lives -= 1
        if lives <= 0:
            return replace(
                state,
                score=score,
                lives=0,
                dots=dots,
                power_pellets=pellets,
                ghosts=tuple(final_ghosts),
                is_game_over=True,
                has_started=True,
                global_mode=global_mode,
                mode_ticks=mode_ticks,
                mode_phase=mode_phase,
                dots_eaten=dots_eaten,
                ghost_eat_streak=0,
            )
        # Reset positions; keep score, dots eaten, and mode schedule.
        init_ticks, init_mode_str = _MODE_SCHEDULE[0]
        init_mode = GhostMode[init_mode_str]
        return replace(
            state,
            score=score,
            lives=lives,
            player_col=PLAYER_START_COL,
            player_row=PLAYER_START_ROW,
            player_dir=Direction.LEFT,
            player_queued_dir=None,
            ghosts=_make_ghosts(init_mode),
            dots=dots,
            power_pellets=pellets,
            dots_eaten=dots_eaten,
            ghost_eat_streak=0,
            global_mode=init_mode,
            mode_ticks=init_ticks,
            mode_phase=0,
            has_started=True,
        )

    # ── 8. Win condition ───────────────────────────────────────────────────
    level_complete = len(dots) == 0 and len(pellets) == 0

    return PacmanGameState(
        dots=dots,
        power_pellets=pellets,
        player_col=player_col,
        player_row=player_row,
        player_dir=player_dir,
        player_queued_dir=player_queued_dir,
        ghosts=tuple(final_ghosts),
        score=score,
        lives=lives,
        global_mode=global_mode,
        mode_ticks=mode_ticks,
        mode_phase=mode_phase,
        dots_eaten=dots_eaten,
        ghost_eat_streak=ghost_eat_streak,
        is_game_over=False,
        level_complete=level_complete,
        has_started=True,
        maze=maze,
    )


# ── board widget ──────────────────────────────────────────────────────────────

_FRIGHTENED_COLOR = QColor(65, 105, 225)
_EATEN_PEN_COLOR = QColor(180, 180, 180)


class PacmanBoardWidget(GameBoardWidget):
    """Paint the Pac-Man game board."""

    _state: PacmanGameState | None  # narrowed from GameBoardWidget

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self.setMinimumSize(380, 380)

    def sizeHint(self) -> QSize:
        """Return the preferred board size."""
        return QSize(480, 480)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the current board state."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        background = self.palette().color(self.backgroundRole())
        board_bg = background.darker(112) if THEMES.is_dark else background.lighter(104)
        wall_color = QColor(THEMES.get_hex_color("primary")).darker(160)
        dot_color = QColor(200, 165, 50)
        pellet_color = QColor(THEMES.get_hex_color("warning"))
        player_color = QColor(THEMES.get_hex_color("success"))
        win_overlay = QColor(THEMES.get_hex_color("success"))
        win_overlay.setAlpha(80)

        painter.fillRect(self.rect(), board_bg)

        if self._state is None:
            return

        cw = self.width() / COLS
        ch = self.height() / ROWS

        # Draw walls.
        maze = self._state.maze
        for row in range(ROWS):
            for col in range(COLS):
                if maze[row][col] == "#":
                    painter.fillRect(round(col * cw), round(row * ch), max(1, round(cw)), max(1, round(ch)), wall_color)

        # Draw remaining dots.
        dot_size = max(3, round(cw * 0.28))
        for col, row in self._state.dots:
            dot_x = round(col * cw + (cw - dot_size) / 2)
            dot_y = round(row * ch + (ch - dot_size) / 2)
            painter.fillRect(dot_x, dot_y, dot_size, dot_size, dot_color)

        # Draw remaining power pellets.
        p_size = max(4, round(cw * 0.5))
        for col, row in self._state.power_pellets:
            p_x = round(col * cw + (cw - p_size) / 2)
            p_y = round(row * ch + (ch - p_size) / 2)
            painter.fillRect(p_x, p_y, p_size, p_size, pellet_color)

        # Draw ghosts.
        ghost_w = max(1, round(cw) - 1)
        ghost_h = max(1, round(ch) - 1)
        for ghost in self._state.ghosts:
            gx = round(ghost.col * cw)
            gy = round(ghost.row * ch)
            if ghost.mode == GhostMode.EATEN:
                painter.save()
                painter.setPen(QPen(_EATEN_PEN_COLOR, 1))
                painter.drawRect(gx + 2, gy + 2, ghost_w - 4, ghost_h - 4)
                painter.restore()
            elif ghost.mode == GhostMode.FRIGHTENED:
                painter.fillRect(gx, gy, ghost_w, ghost_h, _FRIGHTENED_COLOR)
            else:
                painter.fillRect(gx, gy, ghost_w, ghost_h, ghost.name.color)

        # Draw player.
        px = round(self._state.player_col * cw)
        py = round(self._state.player_row * ch)
        pw = max(1, round(cw) - 1)
        ph = max(1, round(ch) - 1)
        painter.fillRect(px, py, pw, ph, player_color)

        # Overlay for end states.
        if self._state.is_game_over:
            painter.fillRect(self.rect(), self._game_over_overlay(80))
        elif self._state.level_complete:
            painter.fillRect(self.rect(), win_overlay)


# ── dialog ────────────────────────────────────────────────────────────────────


class PacmanDialog(GameDialogMixin, QtDialog):
    """Standalone dialog that hosts the Pac-Man game."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        rng: random.Random | None = None,
    ) -> None:
        """Initialize the Pac-Man dialog."""
        self._rng = rng if rng is not None else random.Random()
        self._first_game = True
        self._state = create_initial_state()
        self._is_paused = False
        super().__init__(parent, title="Pac-Man")
        self.setMinimumSize(480, 580)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_game_timer(TICK_INTERVAL_MS)
        self.restart_game()

    # ── GameDialogMixin interface ──────────────────────────────────────────────

    def _create_board_widget(self) -> PacmanBoardWidget:
        """Return the Pac-Man board widget."""
        return PacmanBoardWidget(self)

    def _instructions_text(self) -> str:
        """Return keyboard instructions."""
        return "Arrow keys or WASD to move. Space pauses. R restarts."

    def _do_restart(self) -> None:
        """Reset game state, using the fixed maze for the very first game."""
        if self._first_game:
            self._state = create_initial_state()
            self._first_game = False
        else:
            self._state = create_initial_state(self._rng)

    def _do_advance_state(self) -> None:
        """Advance the Pac-Man simulation by one tick."""
        self._state = advance_state(self._state, self._rng)

    def _is_terminal_state(self) -> bool:
        """Return True when the game has ended (game over or level complete)."""
        return self._state.is_game_over or self._state.level_complete

    def _status_text(self) -> str:
        """Return the full status string for the current Pac-Man state."""
        if self._state.is_game_over:
            return "Game over"
        if self._state.level_complete:
            return "You win!"
        if self._is_paused:
            return "Paused"
        if not self._state.has_started:
            return "Ready"
        return "Running"

    def _setup_extra_header_widgets(self, header_layout: QHBoxLayout) -> None:
        """Add the lives label between score and status."""
        self.lives_label = hp.make_label(self, "", alignment=Qt.AlignmentFlag.AlignHCenter)
        header_layout.addStretch(1)
        header_layout.addWidget(self.lives_label)

    def _refresh_extra_labels(self) -> None:
        """Update the lives label."""
        self.lives_label.setText(f"Lives: {self._state.lives}")

    # ── keyboard handling ──────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle keyboard controls."""
        if event is None:
            return

        key = event.key()
        direction_map = {
            Qt.Key.Key_Up: Direction.UP,
            Qt.Key.Key_W: Direction.UP,
            Qt.Key.Key_Down: Direction.DOWN,
            Qt.Key.Key_S: Direction.DOWN,
            Qt.Key.Key_Left: Direction.LEFT,
            Qt.Key.Key_A: Direction.LEFT,
            Qt.Key.Key_Right: Direction.RIGHT,
            Qt.Key.Key_D: Direction.RIGHT,
        }

        if key in direction_map:
            self._state = queue_direction(self._state, direction_map[key])
            self._refresh_ui()
            event.accept()
            return
        if key == Qt.Key.Key_Space:
            self.toggle_pause()
            event.accept()
            return
        if key == Qt.Key.Key_R:
            self.restart_game()
            event.accept()
            return

        super().keyPressEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore
    dlg = PacmanDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
