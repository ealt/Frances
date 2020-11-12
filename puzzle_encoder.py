from puzzle_pb2 import Puzzle


class PuzzleEncoder:
    def __init__(self, name=''):
        self._puzzle = Puzzle(name=name)

    def get_puzzle(self):
        return self._puzzle