from puzzle_pb2 import Puzzle


class PuzzleVisualizer:

    def __init__(self, puzzle: Puzzle) -> None:
        self._puzzle = puzzle
        self._board = []
        self._set_visulization()

    @property
    def visualization(self) -> str:
        return self._visualization

    def _set_visulization(self):
        self._visualization = '\n'.join([''.join(row) for row in self._board])
