from ortools.sat.python import cp_model

from puzzle_pb2 import Puzzle


class Space:
    def __init__(self, room_id):
        self.room_id = room_id
        self.on = None
        self.beside = set()


class Board:
    def __init__(self, n, crime_scene):
        self._n = n
        self._crime_scene = crime_scene
        self._blocked_coordinates = []
        self._init_spaces()
        self._add_windows()
        self._add_furniture()

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

    def _add_furniture(self):
        for furniture in self._crime_scene.furniture:
            coordinates = [
                (coordinate.row, coordinate.column)
                for coordinate in furniture.coordinates
            ]
            for row, column in coordinates:
                self._spaces[row][column].on = furniture.type
                for n_row, n_col in self._get_neighbors(row, column):
                    if (n_row, n_col) not in coordinates:
                        self._spaces[n_row][n_col].beside.add(furniture.type)
            if not furniture.occupiable:
                self._blocked_coordinates.extend(coordinates)

    def _get_neighbors(self, row, column):
        neighbors = []
        if row > 0:
            neighbors.append((row - 1, column))
        if column > 0:
            neighbors.append((row, column - 1))
        if row < self._n - 1:
            neighbors.append((row + 1, column))
        if column < self._n - 1:
            neighbors.append((row, column + 1))
        return neighbors


class PuzzleSolver:
    def __init__(self, puzzle):   
        self._puzzle = puzzle
        self._n = len(self._puzzle.people)
        self._board = Board(self._n, self._puzzle.crime_scene)
        self._create_model()

    def _create_model(self):
        self._model = cp_model.CpModel()
        self._rows = [
            self._model.NewIntVar(
                0, self._n-1, 'row_{person_id}'.format(person_id=person_id))
            for person_id in range(len(self._puzzle.people))
        ]
        self._columns = [
            self._model.NewIntVar(
                0, self._n-1, 'column_{person_id}'.format(person_id=person_id))
            for person_id in range(len(self._puzzle.people))
        ]
        self._set_unique_rows_and_columns()

    def _set_unique_rows_and_columns(self):
        self._model.AddAllDifferent(self._rows)
        self._model.AddAllDifferent(self._columns)