from puzzle_pb2 import Puzzle


class Space:
    def __init__(self, room_id):
        self.room_id = room_id
        self.beside = set()


class Board:
    def __init__(self, n, crime_scene):
        self._n = n
        self._crime_scene = crime_scene
        self._init_spaces()
        self._add_windows()

    def _init_spaces(self):
        self._spaces = [[
            Space(self._get_room_id(row, column))
            for column in range(self._n)]
            for row in range(self._n)]

    def _get_room_id(self, row, column):
        index = (self._n * row) + column
        return self._crime_scene.floor_plan[index]

    def _add_windows(self):
        for window in self._crime_scene.windows:
            if window.HasField('vertical_border'):
                self._add_vertical_window(window.vertical_border)
            if window.HasField('horizontal_border'):
                self._add_horizontal_window(window.horizontal_border)

    def _add_vertical_window(self, vertical_border):
        row = vertical_border.row
        if vertical_border.left is not None:
            column = vertical_border.left
            self._spaces[row][column].beside.add('window')
        if vertical_border.right is not None:
            column = vertical_border.right
            self._spaces[row][column].beside.add('window')
            
    def _add_horizontal_window(self, horizontal_border):
        column = horizontal_border.column
        if horizontal_border.top is not None:
            row = horizontal_border.top
            self._spaces[row][column].beside.add('window')
        if horizontal_border.bottom is not None:
            row = horizontal_border.bottom
            self._spaces[row][column].beside.add('window')


class PuzzleSolver:
    def __init__(self, puzzle):   
        self._puzzle = puzzle
        n = len(self._puzzle.people)
        self._board = Board(n, self._puzzle.crime_scene)