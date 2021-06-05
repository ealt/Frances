from dataclasses import dataclass, field
from itertools import chain, product, repeat
from ortools.sat.python import cp_model

from puzzle_pb2 import Coordinate, HorizontalBorder, VerticalBorder, Puzzle
from typing import Callable, List, Optional, Set, Tuple, Union
from ortools.sat.python.cp_model import IntVar

OCCUPIED = lambda total_occupancy: total_occupancy >= 1
UNOCCUPIED = lambda total_occupancy: total_occupancy == 0
UNIQUELY_OCCUPIED = lambda total_occupancy: total_occupancy == 1

CORNER = set(['vertical_wall', 'horizontal_wall'])


@dataclass
class Space:

    room_id: int
    on: Optional[Union[int, str]] = None
    beside: Set[Union[int, str]] = field(default_factory=set)


class PuzzleModeler:

    def __init__(self, puzzle: Puzzle) -> None:
        self._puzzle = puzzle
        self._n = len(self._puzzle.people)
        self._init_board()
        self._create_model()

    @property
    def model(self) -> cp_model.CpModel:
        return self._model

    @property
    def occupancies(self) -> List[List[List[IntVar]]]:
        return self._occupancies

    def get_room_of_coordinate(self, coordinate: Coordinate) -> int:
        return self._spaces[coordinate.row][coordinate.column].room_id

    def _init_board(self):
        self._get_room_coordinates()
        self._init_spaces()
        self._add_walls()
        self._add_windows()
        self._add_furniture()

    def _get_room_coordinates(self) -> None:
        self._room_coordinates = [
            [] for _ in range(len(self._puzzle.crime_scene.rooms))
        ]
        for index, room_id in enumerate(self._puzzle.crime_scene.floor_plan):
            row = index // self._n
            col = index % self._n
            self._room_coordinates[room_id].append((row, col))

    def _init_spaces(self) -> None:
        self._spaces = [[
            Space(self._get_room_id(row, column)) for column in range(self._n)
        ] for row in range(self._n)]
        self._roomwise_furniture = [
            set() for _ in range(len(self._puzzle.crime_scene.rooms))
        ]
        self._rowwise_furniture = [set() for _ in range(self._n)]
        self._columwise_furniture = [set() for _ in range(self._n)]

    def _get_room_id(self, row: int, column: int) -> int:
        index = (self._n * row) + column
        return self._puzzle.crime_scene.floor_plan[index]

    def _add_walls(self) -> None:
        self._add_vertical_walls()
        self._add_horizontal_walls()

    def _add_vertical_walls(self) -> None:
        for spaces_row in self._spaces:
            spaces_row[0].beside.add('vertical_wall')
            spaces_row[-1].beside.add('vertical_wall')
            for left, right in zip(spaces_row, spaces_row[1:]):
                if left.room_id != right.room_id:
                    left.beside.add('vertical_wall')
                    right.beside.add('vertical_wall')

    def _add_horizontal_walls(self) -> None:
        for space in chain(self._spaces[0], self._spaces[-1]):
            space.beside.add('horizontal_wall')
        for row in range(1, self._n):
            for top, bottom in zip(self._spaces[row - 1], self._spaces[row]):
                if top.room_id != bottom.room_id:
                    top.beside.add('horizontal_wall')
                    bottom.beside.add('horizontal_wall')

    def _add_windows(self) -> None:
        for window in self._puzzle.crime_scene.windows:
            if window.HasField('vertical_border'):
                self._add_vertical_window(window.vertical_border)
            if window.HasField('horizontal_border'):
                self._add_horizontal_window(window.horizontal_border)

    def _add_vertical_window(self, vertical_border: VerticalBorder) -> None:
        row = vertical_border.row
        self._rowwise_furniture[row].add('window')
        if vertical_border.right > 0:
            column = vertical_border.right - 1
            room_id = self._get_room_id(row, column)
            self._roomwise_furniture[room_id].add('window')
            self._spaces[row][column].beside.add('window')
        if vertical_border.right < self._n:
            column = vertical_border.right
            room_id = self._get_room_id(row, column)
            self._roomwise_furniture[room_id].add('window')
            self._spaces[row][column].beside.add('window')

    def _add_horizontal_window(self,
                               horizontal_border: HorizontalBorder) -> None:
        column = horizontal_border.column
        self._columwise_furniture[column].add('window')
        if horizontal_border.bottom > 0:
            row = horizontal_border.bottom - 1
            room_id = self._get_room_id(row, column)
            self._roomwise_furniture[room_id].add('window')
            self._spaces[row][column].beside.add('window')
        if horizontal_border.bottom < self._n:
            row = horizontal_border.bottom
            room_id = self._get_room_id(row, column)
            self._roomwise_furniture[room_id].add('window')
            self._spaces[row][column].beside.add('window')

    def _add_furniture(self) -> None:
        self._blocked_coordinates = []
        for furniture in self._puzzle.crime_scene.furniture:
            coordinates = [(coordinate.row, coordinate.column)
                           for coordinate in furniture.coordinates]
            for row, column in coordinates:
                self._spaces[row][column].on = furniture.type
                self._rowwise_furniture[row].add(furniture.type)
                self._columwise_furniture[column].add(furniture.type)
                room_id = self._get_room_id(row, column)
                self._roomwise_furniture[room_id].add(furniture.type)
                for n_row, n_col in self._get_neighbors(row, column):
                    if (n_row, n_col) not in coordinates:
                        self._spaces[n_row][n_col].beside.add(furniture.type)
            if not furniture.occupiable:
                self._blocked_coordinates.extend(coordinates)

    def _get_neighbors(self, row: int, column: int) -> List[Tuple[int, int]]:
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

    def _create_model(self) -> None:
        self._model = cp_model.CpModel()
        unavailable = set(self._blocked_coordinates +
                          self._get_unoccupied_room_coordinates())
        self._occupancies = [[[
            self._model.NewConstant(0) if (row, col) in unavailable else
            self._model.NewBoolVar(f'({person_id}, {row}, {col})')
            for col in range(self._n)
        ]
                              for row in range(self._n)]
                             for person_id in range(self._n)]
        self._row_indexes = lambda row: list(
            zip(repeat(row, self._n), range(self._n)))
        self._col_indexes = lambda col: list(
            zip(range(self._n), repeat(col, self._n)))
        self._set_uniqueness_constraints()
        self._set_clues()

    def _get_unoccupied_room_coordinates(self) -> List[Tuple[int, int]]:
        unoccupied_room_coordinates = []
        for clue in self._puzzle.clues:
            if clue.HasField('room_clue') and not clue.room_clue.is_occupied:
                unoccupied_room_coordinates.extend(
                    self._get_coordinates_of_room(clue.room_clue.room_id))
        return unoccupied_room_coordinates

    def _get_coordinates_of_room(self, room_id: int) -> List[Tuple[int, int]]:
        return self._room_coordinates[room_id]

    def _add_constraint(self, constraint_function: Callable[[int], bool],
                        people_ids: List[int],
                        space_indexes: List[Tuple[int, int]]) -> None:
        self._model.Add(
            constraint_function(
                sum([
                    self._occupancies[person_id][row][col]
                    for person_id in people_ids
                    for row, col in space_indexes
                ])))

    def _set_uniqueness_constraints(self) -> None:
        for person_id in range(self._n):
            people_ids = [person_id]
            space_indexes = list(product(range(self._n), repeat=2))
            self._add_constraint(UNIQUELY_OCCUPIED, people_ids, space_indexes)
        for row in range(self._n):
            people_ids = list(range(self._n))
            space_indexes = self._row_indexes(row)
            self._add_constraint(UNIQUELY_OCCUPIED, people_ids, space_indexes)
        for col in range(self._n):
            people_ids = list(range(self._n))
            space_indexes = self._col_indexes(col)
            self._add_constraint(UNIQUELY_OCCUPIED, people_ids, space_indexes)

    def _set_clues(self) -> None:
        for clue in self._puzzle.clues:
            if clue.HasField('room_clue'):
                self._set_room_clue(clue.room_clue)
            elif clue.HasField('person_clue'):
                self._set_person_clue(clue.person_clue)

    def _set_room_clue(self, room_clue: Puzzle.Clue.RoomClue) -> None:
        if room_clue.is_occupied:
            people_ids = list(range(self._n))
            space_indexes = self._get_coordinates_of_room(room_clue.room_id)
            self._add_constraint(OCCUPIED, people_ids, space_indexes)

    def _set_person_clue(self, person_clue: Puzzle.Clue.PersonClue) -> None:
        people_ids = [person_clue.person_id]
        if person_clue.HasField('same_row'):
            for row, furnuture in enumerate(self._rowwise_furniture):
                if person_clue.same_row not in furnuture:
                    space_indexes = self._row_indexes(row)
                    self._add_constraint(UNOCCUPIED, people_ids, space_indexes)
        elif person_clue.HasField('same_column'):
            for column, furnuture in enumerate(self._columnwise_furniture):
                if person_clue.same_column not in furnuture:
                    space_indexes = self._col_indexes(column)
                    self._add_constraint(UNOCCUPIED, people_ids, space_indexes)
        elif person_clue.HasField('same_room'):
            for room_id, furnuture in enumerate(self._roomwise_furniture):
                if person_clue.same_room not in furnuture:
                    space_indexes = self._room_coordinates[room_id]
                    self._add_constraint(UNOCCUPIED, people_ids, space_indexes)
        else:
            constraint_function = UNOCCUPIED if person_clue.negate else UNIQUELY_OCCUPIED
            space_indexes = self._get_person_clue_coordinates(person_clue)
            self._add_constraint(constraint_function, people_ids, space_indexes)

    def _get_person_clue_coordinates(
            self, person_clue: Puzzle.Clue.PersonClue) -> List[Tuple[int, int]]:
        if person_clue.HasField('room_id'):
            return self._get_coordinates_of_room(person_clue.room_id)
        else:
            coordinates = []
            for row, row_spaces in enumerate(self._spaces):
                for column, space in enumerate(row_spaces):
                    if self._evaluate_space_for_clue(space, person_clue):
                        coordinates.append((row, column))
            return coordinates

    def _evaluate_space_for_clue(self, space: Space, clue: Puzzle.Clue) -> bool:
        if clue.HasField('beside_window'):
            return clue.beside_window == ('window' in space.beside)
        elif clue.HasField('beside'):
            return clue.beside in space.beside
        elif clue.HasField('on'):
            return clue.on == space.on
        elif clue.HasField('in_corner'):
            return clue.in_corner == space.beside.issuperset(CORNER)
        raise AttributeError
