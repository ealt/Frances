from puzzle_pb2 import Puzzle


class Space:
    def __init__(self, room_id):
        self.room_id = room_id


class Board:
    def __init__(self, n, crime_scene):
        self._n = n
        self._crime_scene = crime_scene
        self._init_spaces()

    def _init_spaces(self):
        self._spaces = [[
            Space(self._get_room_id(row, column))
            for column in range(self._n)]
            for row in range(self._n)]

    def _get_room_id(self, row, column):
        index = (self._n * row) + column
        return self._crime_scene.floor_plan[index]


class PuzzleSolver:
    def __init__(self, puzzle):   
        self._puzzle = puzzle
        n = len(self._puzzle.people)
        self._board = Board(n, self._puzzle.crime_scene)