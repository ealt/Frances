from ortools.sat.python import cp_model

from puzzle_pb2 import Puzzle


def get_name(messages, message_id):
    for message in messages:
        if message.id == message_id:
            return message.name


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
            Space(self._get_room_id(row, column)) for column in range(self._n)
        ] for row in range(self._n)]

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
            coordinates = [(coordinate.row, coordinate.column)
                           for coordinate in furniture.coordinates]
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

    def get_blocked_coordinates(self):
        return self._blocked_coordinates

    def get_spaces(self):
        return self._spaces

    def get_room_of_coordinate(self, coordinate):
        return self._spaces[coordinate.row][coordinate.column].room_id


class PuzzleSolver:

    def __init__(self, puzzle):
        self._puzzle = puzzle
        self._n = len(self._puzzle.people)
        self._board = Board(self._n, self._puzzle.crime_scene)
        self._create_model()

    def _create_model(self):
        self._model = cp_model.CpModel()
        self._rows = [
            self._model.NewIntVar(0, self._n - 1,
                                  'row_{person_id}'.format(person_id=person_id))
            for person_id in range(len(self._puzzle.people))
        ]
        self._columns = [
            self._model.NewIntVar(
                0, self._n - 1,
                'column_{person_id}'.format(person_id=person_id))
            for person_id in range(len(self._puzzle.people))
        ]
        self._set_unique_rows_and_columns()
        self._set_occupiable_constraints()
        self._set_clues()

    def _set_unique_rows_and_columns(self):
        self._model.AddAllDifferent(self._rows)
        self._model.AddAllDifferent(self._columns)

    def _set_occupiable_constraints(self):
        for person_vars in self._get_people_vars():
            self._model.AddForbiddenAssignments(
                list(person_vars), self._board.get_blocked_coordinates())

    def _get_people_vars(self):
        return [(row, column) for row, column in zip(self._rows, self._columns)]

    def _set_clues(self):
        for clue in self._puzzle.clues:
            if clue.HasField('room_clue'):
                self._set_room_clue(clue.room_clue)
            elif clue.HasField('person_clue'):
                self._set_person_clue(clue.person_clue)

    def _set_room_clue(self, room_clue):
        people_vars = self._get_people_vars()
        room_coordinates = self._get_clue_coordinates(room_clue)
        if room_clue.is_occupied:
            self._model.AddBoolOr([
                person_vars in room_coordinates for person_vars in people_vars
            ])
        else:
            self._model.AddBoolAnd([
                person_vars not in room_coordinates
                for person_vars in people_vars
            ])

    def _set_person_clue(self, person_clue):
        person_vars = self._get_person_vars(person_clue.person_id)
        coordinates = self._get_clue_coordinates(person_clue)
        self._model.AddAllowedAssignments(list(person_vars), coordinates)

    def _get_person_vars(self, person_id):
        return (self._rows[person_id], self._columns[person_id])

    def _get_clue_coordinates(self, clue):
        coordinates = []
        for row, row_spaces in enumerate(self._board.get_spaces()):
            for column, space in enumerate(row_spaces):
                if self._evaluate_space_for_clue(space, clue):
                    coordinates.append((row, column))
        return coordinates

    def _evaluate_space_for_clue(self, space, clue):
        if type(clue) == Puzzle.Clue.RoomClue or clue.HasField('room_id'):
            return clue.room_id == space.room_id
        elif clue.HasField('beside_window'):
            return clue.beside_window == ('window' in space.beside)
        elif clue.HasField('beside'):
            return clue.beside in space.beside
        elif clue.HasField('on'):
            return clue.on == space.on

    def solve(self):
        self._solver = cp_model.CpSolver()
        self._status = self._solver.Solve(self._model)
        print('Solution status: {status}'.format(
            status=self._solver.StatusName(self._status)))
        if self._status == cp_model.OPTIMAL:
            self._set_solution()

    def _set_solution(self):
        self._set_positions()
        self._set_murderer()

    def _set_positions(self):
        del self._puzzle.solution.positions[:]
        for person_id, person_vals in enumerate(self._get_people_vars()):
            row, column = person_vals
            position = self._puzzle.solution.positions.add(person_id=person_id)
            position.coordinate.row = self._solver.Value(row)
            position.coordinate.column = self._solver.Value(column)

    def _set_murderer(self):
        victim_id = self._get_victim_id()
        murder_room_id = self._get_room_of_person(victim_id)
        for person in self._puzzle.people:
            if (person.type == Puzzle.Person.SUSPECT and
                    self._get_room_of_person(person.id) == murder_room_id):
                self._puzzle.solution.murderer_id = person.id
                break

    def _get_victim_id(self):
        for person in self._puzzle.people:
            if person.type == Puzzle.Person.VICTIM:
                return person.id

    def _get_room_of_person(self, person_id):
        coordinate = self._puzzle.solution.positions[person_id].coordinate
        room_id = self._board.get_room_of_coordinate(coordinate)
        return room_id

    def get_solution(self):
        return self._puzzle.solution

    def verdict(self):
        murderer_id = self._puzzle.solution.murderer_id
        victim_id = self._get_victim_id()
        room_id = self._get_room_of_person(victim_id)
        print('{murderer} murdered {victim} in the {room}!'.format(
            murderer=get_name(self._puzzle.people, murderer_id),
            victim=get_name(self._puzzle.people, victim_id),
            room=get_name(self._puzzle.crime_scene.rooms, room_id)))