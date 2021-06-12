from puzzle_pb2 import Puzzle

ROW = lambda n, value: [value if c % 2 == 1 else ' ' for c in range(2 * n + 1)]


class PuzzleVisualizer:

    def __init__(self, puzzle: Puzzle, w: int = 3) -> None:
        self._puzzle = puzzle
        self._w = w
        self._n = len(self._puzzle.people)
        self._board = []
        self._add_exterior_walls()
        self._add_interior_walls()
        self._set_visulization()

    @property
    def visualization(self) -> str:
        return self._visualization

    def _add_exterior_walls(self) -> None:
        vertical_wall_value = '\u2502'
        horizontal_wall_value = self._w * '\u2500'
        horizontal_empty_value = self._w * ' '
        self._board.append(ROW(self._n, horizontal_wall_value))
        for r in range(1, 2 * self._n):
            self._board.append(ROW(self._n, horizontal_empty_value))
            if r % 2 == 1:
                self._board[-1][0] = vertical_wall_value
                self._board[-1][-1] = vertical_wall_value
        self._board.append(ROW(self._n, horizontal_wall_value))

    def _add_interior_walls(self) -> None:
        self._add_vertical_interior_walls()
        self._add_horizontal_interior_walls()

    def _add_vertical_interior_walls(self) -> None:
        vertical_wall_value = '\u2502'
        for r, row in enumerate(self._puzzle.crime_scene.floor_plan):
            for c, left, right in zip(range(1, self._n), row.values[:-1],
                                      row.values[1:]):
                if left != right:
                    self._set_vertical_boundary_value(r, c, vertical_wall_value)

    def _add_horizontal_interior_walls(self) -> None:
        horizontal_wall_value = self._w * '\u2500'
        for r, top_row, bottom_row in zip(
                range(1, self._n), self._puzzle.crime_scene.floor_plan[:-1],
                self._puzzle.crime_scene.floor_plan[1:]):
            for c, top, bottom in zip(range(self._n), top_row.values,
                                      bottom_row.values):
                if top != bottom:
                    self._set_horizontal_boundary_value(r, c,
                                                        horizontal_wall_value)

    def _set_vertical_boundary_value(self, row: int, right: int,
                                     value: str) -> None:
        self._board[2 * row + 1][2 * right] = value

    def _set_horizontal_boundary_value(self, bottom: int, column: int,
                                       value: str) -> None:
        self._board[2 * bottom][2 * column + 1] = value

    def _set_visulization(self):
        self._visualization = '\n'.join([''.join(row) for row in self._board])
