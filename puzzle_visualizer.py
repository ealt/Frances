from puzzle_pb2 import Puzzle

ROW = lambda n, value: [value if c % 2 == 1 else ' ' for c in range(2 * n + 1)]


class PuzzleVisualizer:

    def __init__(self, puzzle: Puzzle, w: int = 3) -> None:
        self._puzzle = puzzle
        self._w = w
        self._n = len(self._puzzle.people)
        self._board = []
        self._add_exterior_walls()
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

    def _set_visulization(self):
        self._visualization = '\n'.join([''.join(row) for row in self._board])
