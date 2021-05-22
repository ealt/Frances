from itertools import chain
from ortools.sat.python import cp_model

from puzzle_pb2 import Puzzle

CORNER = set(['vertical_wall', 'horizontal_wall'])


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
        self._add_walls()
        self._add_windows()
        self._add_furniture()

    def _init_spaces(self):
        self._spaces = [[
            Space(self._get_room_id(row, column)) for column in range(self._n)
        ] for row in range(self._n)]
        self._rowwise_furniture = [set() for _ in range(self._n)]
        self._columwise_furniture = [set() for _ in range(self._n)]

    def _get_room_id(self, row, column):
        index = (self._n * row) + column
        return self._crime_scene.floor_plan[index]

    def _add_walls(self):
        self._add_vertical_walls()
        self._add_horizontal_walls()

    def _add_vertical_walls(self):
        for spaces_row in self._spaces:
            spaces_row[0].beside.add('vertical_wall')
            spaces_row[-1].beside.add('vertical_wall')
            for left, right in zip(spaces_row, spaces_row[1:]):
                if left.room_id != right.room_id:
                    left.beside.add('vertical_wall')
                    right.beside.add('vertical_wall')

    def _add_horizontal_walls(self):
        for space in chain(self._spaces[0], self._spaces[-1]):
            space.beside.add('horizontal_wall')
        for row in range(1, self._n):
            for top, bottom in zip(self._spaces[row - 1], self._spaces[row]):
                if top.room_id != bottom.room_id:
                    top.beside.add('horizontal_wall')
                    bottom.beside.add('horizontal_wall')

    def _add_windows(self):
        for window in self._crime_scene.windows:
            if window.HasField('vertical_border'):
                self._add_vertical_window(window.vertical_border)
            if window.HasField('horizontal_border'):
                self._add_horizontal_window(window.horizontal_border)

    def _add_vertical_window(self, vertical_border):
        row = vertical_border.row
        self._rowwise_furniture[row].add('window')
        if vertical_border.left is not None:
            column = vertical_border.left
            self._spaces[row][column].beside.add('window')
        if vertical_border.right is not None:
            column = vertical_border.right
            self._spaces[row][column].beside.add('window')

    def _add_horizontal_window(self, horizontal_border):
        column = horizontal_border.column
        self._columwise_furniture[column].add('window')
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
                self._rowwise_furniture[row].add(furniture.type)
                self._columwise_furniture[column].add(furniture.type)
                for n_row, n_col in self._get_neighbors(row, column):
                    if (n_row, n_col) not in coordinates:
                        self._spaces[n_row][n_col].beside.add(furniture.type)
            if not furniture.occupiable:
                self._blocked_coordinates.extend(coordinates)

    def _get_neighbors(self, row, column):
        room_id = self._get_room_id(row, column)
        neighbors = []
        if row > 0 and self._get_room_id(row - 1, column) == room_id:
            neighbors.append((row - 1, column))
        if column > 0 and self._get_room_id(row, column - 1) == room_id:
            neighbors.append((row, column - 1))
        if row < self._n - 1 and self._get_room_id(row + 1, column) == room_id:
            neighbors.append((row + 1, column))
        if column < self._n - 1 and self._get_room_id(row,
                                                      column + 1) == room_id:
            neighbors.append((row, column + 1))
        return neighbors

    def get_blocked_coordinates(self):
        return self._blocked_coordinates

    def get_spaces(self):
        return self._spaces

    def get_rowwise_furniture(self):
        return self._rowwise_furniture

    def get_columnwise_furniture(self):
        return self._columwise_furniture

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
        unavailable = set(self._board.get_blocked_coordinates() +
                          self._get_unoccupied_room_coordinates())
        self._occupancies = [[[
            self._model.NewConstant(0) if (row, col) in unavailable else
            self._model.NewBoolVar(f'({person_id}, {row}, {col})')
            for col in range(self._n)
        ]
                              for row in range(self._n)]
                             for person_id in range(self._n)]
        self._set_uniqueness_constraints()
        self._set_clues()

    def _get_unoccupied_room_coordinates(self):
        unoccupied_room_coordinates = []
        for clue in self._puzzle.clues:
            if clue.HasField('room_clue') and not clue.room_clue.is_occupied:
                unoccupied_room_coordinates.extend(
                    self._get_clue_coordinates(clue))
        return unoccupied_room_coordinates

    def _set_uniqueness_constraints(self):
        for person_id in range(self._n):
            self._model.Add(
                sum([
                    self._occupancies[person_id][col][row]
                    for row in range(self._n)
                    for col in range(self._n)
                ]) == 1)
        for row in range(self._n):
            self._model.Add(
                sum([
                    self._occupancies[person_id][col][row]
                    for person_id in range(self._n)
                    for col in range(self._n)
                ]) == 1)
        for col in range(self._n):
            self._model.Add(
                sum([
                    self._occupancies[person_id][col][row]
                    for person_id in range(self._n)
                    for row in range(self._n)
                ]) == 1)

    def _set_clues(self):
        for clue in self._puzzle.clues:
            if clue.HasField('room_clue'):
                self._set_room_clue(clue.room_clue)
            elif clue.HasField('person_clue'):
                self._set_person_clue(clue.person_clue)

    def _set_room_clue(self, room_clue):
        if room_clue.is_occupied:
            room_coordinates = self._get_clue_coordinates(room_clue)
            self._model.Add(
                sum([
                    person_occupancy[row][col]
                    for person_occupancy in self._occupancies
                    for row, col in room_coordinates
                ]) >= 1)

    def _set_person_clue(self, person_clue):
        if person_clue.HasField('same_row'):
            for row, furnuture in enumerate(
                    self._board.get_rowwise_furniture()):
                if person_clue.same_row not in furnuture:
                    self._model.Add(
                        sum([
                            self._occupancies[person_clue.person_id][row]
                            [column] for column in range(self._n)
                        ]) == 0)
        elif person_clue.HasField('same_column'):
            for column, furnuture in enumerate(
                    self._board.get_columnwise_furniture()):
                if person_clue.same_column not in furnuture:
                    self._model.Add(
                        sum([
                            self._occupancies[person_clue.person_id][row]
                            [column] for row in range(self._n)
                        ]) == 0)
        else:
            coordinates = self._get_clue_coordinates(person_clue)
            value = 0 if person_clue.negate else 1
            self._model.Add(
                sum([
                    self._occupancies[person_clue.person_id][row][col]
                    for row, col in coordinates
                ]) == value)

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
        elif clue.HasField('in_corner'):
            return clue.in_corner == space.beside.issuperset(CORNER)

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
        for person_id in range(self._n):
            row, column = self._get_position(person_id)
            position = self._puzzle.solution.positions.add(person_id=person_id)
            position.coordinate.row = row
            position.coordinate.column = column

    def _get_position(self, person_id):
        for row in range(self._n):
            for col in range(self._n):
                if self._solver.Value(self._occupancies[person_id][row][col]):
                    return (row, col)
        return (-1, -1)

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