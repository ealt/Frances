from collections import namedtuple

from puzzle_pb2 import Puzzle

WallIntersection = namedtuple('WallIntersection',
                              ['up', 'down', 'left', 'right'],
                              defaults=[False, False, False, False])

# https://www.unicode.org/charts/PDF/U2500.pdf
WALL_INTERSECTION_VALUES = {
    WallIntersection(): ' ',
    WallIntersection(left=True, right=True): '\u2500',
    WallIntersection(up=True, down=True): '\u2502',
    WallIntersection(down=True, right=True): '\u250C',
    WallIntersection(down=True, left=True): '\u2510',
    WallIntersection(up=True, right=True): '\u2514',
    WallIntersection(up=True, left=True): '\u2518',
    WallIntersection(up=True, down=True, right=True): '\u251C',
    WallIntersection(up=True, down=True, left=True): '\u2524',
    WallIntersection(down=True, left=True, right=True): '\u252C',
    WallIntersection(up=True, left=True, right=True): '\u2534',
    WallIntersection(up=True, down=True, left=True, right=True): '\u253C',
    WallIntersection(left=True): '\u2574',
    WallIntersection(up=True): '\u2575',
    WallIntersection(right=True): '\u2576',
    WallIntersection(down=True): '\u2577',
}

ROW = lambda n, value: [value if c % 2 == 1 else ' ' for c in range(2 * n + 1)]


class PuzzleVisualizer:

    def __init__(self, puzzle: Puzzle, w: int = 3) -> None:
        self._board = []
        if puzzle.HasField('crime_scene'):
            self._crime_scene = puzzle.crime_scene
            self._w = w
            self._n = len(self._crime_scene.floor_plan)
            self._add_walls()
            self._add_windows()
        self._set_visulization()

    @property
    def visualization(self) -> str:
        return self._visualization

    def _add_walls(self):
        self._vertical_wall_value = WALL_INTERSECTION_VALUES[WallIntersection(
            up=True, down=True)]
        self._horizontal_wall_value = self._w * WALL_INTERSECTION_VALUES[
            WallIntersection(left=True, right=True)]
        self._horizontal_empty_value = self._w * WALL_INTERSECTION_VALUES[
            WallIntersection()]
        self._add_exterior_walls()
        self._add_interior_walls()
        self._add_wall_intersections()

    def _add_exterior_walls(self) -> None:
        self._board.append(ROW(self._n, self._horizontal_wall_value))
        for r in range(1, 2 * self._n):
            self._board.append(ROW(self._n, self._horizontal_empty_value))
            if r % 2 == 1:
                self._board[-1][0] = self._vertical_wall_value
                self._board[-1][-1] = self._vertical_wall_value
        self._board.append(ROW(self._n, self._horizontal_wall_value))

    def _add_interior_walls(self) -> None:
        self._add_vertical_interior_walls()
        self._add_horizontal_interior_walls()

    def _add_vertical_interior_walls(self) -> None:
        for r, row in enumerate(self._crime_scene.floor_plan):
            for c, left, right in zip(range(1, self._n), row.values[:-1],
                                      row.values[1:]):
                if left != right:
                    self._set_vertical_boundary_value(r, c,
                                                      self._vertical_wall_value)

    def _add_horizontal_interior_walls(self) -> None:
        for r, top_row, bottom_row in zip(range(1, self._n),
                                          self._crime_scene.floor_plan[:-1],
                                          self._crime_scene.floor_plan[1:]):
            for c, top, bottom in zip(range(self._n), top_row.values,
                                      bottom_row.values):
                if top != bottom:
                    self._set_horizontal_boundary_value(
                        r, c, self._horizontal_wall_value)

    def _add_wall_intersections(self) -> None:
        for bottom in range(self._n + 1):
            for right in range(self._n + 1):
                wall_intersection = self._get_wall_intersection(bottom, right)
                value = WALL_INTERSECTION_VALUES[wall_intersection]
                self._set_boundary_intersection_value(bottom, right, value)

    def _get_wall_intersection(self, bottom: int,
                               right: int) -> WallIntersection:
        top = bottom - 1
        left = right - 1
        up_wall = False if bottom == 0 else self._get_vertical_boundary_value(
            top, right) == self._vertical_wall_value
        down_wall = False if bottom == self._n else self._get_vertical_boundary_value(
            bottom, right) == self._vertical_wall_value
        left_wall = False if right == 0 else self._get_horizontal_boundary_value(
            bottom, left) == self._horizontal_wall_value
        right_wall = False if right == self._n else self._get_horizontal_boundary_value(
            bottom, right) == self._horizontal_wall_value
        return WallIntersection(up=up_wall,
                                down=down_wall,
                                left=left_wall,
                                right=right_wall)

    def _add_windows(self) -> None:
        self._vertical_window_value = '\u2551'
        self._horizontal_window_value = self._w * '\u2550'
        for window in self._crime_scene.windows:
            if window.HasField('vertical_border'):
                self._set_vertical_boundary_value(window.vertical_border.row,
                                                  window.vertical_border.right,
                                                  self._vertical_window_value)
            if window.HasField('horizontal_border'):
                self._set_horizontal_boundary_value(
                    window.horizontal_border.bottom,
                    window.horizontal_border.column,
                    self._horizontal_window_value)

    def _get_vertical_boundary_value(self, row: int, right: int) -> str:
        return self._board[2 * row + 1][2 * right]

    def _set_vertical_boundary_value(self, row: int, right: int,
                                     value: str) -> None:
        self._board[2 * row + 1][2 * right] = value

    def _get_horizontal_boundary_value(self, bottom: int, column: int) -> str:
        return self._board[2 * bottom][2 * column + 1]

    def _set_horizontal_boundary_value(self, bottom: int, column: int,
                                       value: str) -> None:
        self._board[2 * bottom][2 * column + 1] = value

    def _set_boundary_intersection_value(self, bottom: int, right: int,
                                         value: str) -> None:
        self._board[2 * bottom][2 * right] = value

    def _set_visulization(self):
        self._visualization = '\n'.join([''.join(row) for row in self._board])
