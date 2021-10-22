import logging

from dataclasses import dataclass, field
from itertools import product, repeat
from ortools.sat.python.cp_model import CpModel, IntVar

from puzzle_pb2 import Clue, Coordinate, CrimeSceneFeature, CrimeSceneFeatureType, Gender, PositionType, Puzzle, Role, SubjectSelector
from typing import Callable, List, Optional, Set, Tuple

EXACT_COUNT = lambda count: lambda total_occupancy: total_occupancy == count
MIN_COUNT = lambda count: lambda total_occupancy: total_occupancy >= count


@dataclass
class Space:

    room_id: int
    on: Optional[int] = None
    beside: Set[int] = field(default_factory=set)

    def __repr__(self) -> str:
        on = CrimeSceneFeatureType.Name(
            self.on).capitalize() if self.on is not None else 'None'
        beside = '[' + ', '.join([
            CrimeSceneFeatureType.Name(feature).capitalize()
            for feature in self.beside
        ]) + ']'
        return f'{{room_id: {self.room_id}, on: {on}, beside: {beside}}}'


class PuzzleModeler:

    def __init__(self, puzzle: Puzzle, debug: bool = False) -> None:
        self._puzzle = puzzle
        self._debug = debug
        self._n = len(self._puzzle.people)
        self._init_board()
        self._create_model()

    @property
    def model(self) -> CpModel:
        return self._model

    @property
    def occupancies(self) -> List[List[List[IntVar]]]:
        return self._occupancies

    def get_room_of_coordinate(self, coordinate: Coordinate) -> int:
        return self._spaces[coordinate.row][coordinate.column].room_id

    def _init_board(self):
        self._get_room_coordinates()
        self._init_spaces()
        self._add_walls_and_corners()
        self._add_features()
        if self._debug:
            self._log_board_debug()

    def _get_room_coordinates(self) -> None:
        self._room_coordinates = [
            [] for _ in range(len(self._puzzle.crime_scene.rooms) + 1)
        ]
        for r, row in enumerate(self._puzzle.crime_scene.floor_plan):
            for c, room_id in enumerate(row.values):
                self._room_coordinates[room_id].append((r, c))

    def _init_spaces(self) -> None:
        self._spaces = [[
            Space(self._get_room_id(row, column)) for column in range(self._n)
        ] for row in range(self._n)]
        self._roomwise_features = [
            set() for _ in range(len(self._puzzle.crime_scene.rooms) + 1)
        ]
        self._rowwise_features = [set() for _ in range(self._n)]
        self._columwise_features = [set() for _ in range(self._n)]

    def _get_room_id(self, row: int, column: int) -> int:
        return self._puzzle.crime_scene.floor_plan[row].values[column]

    def _add_walls_and_corners(self) -> None:
        for r, row in enumerate(self._spaces):
            for c, space in enumerate(row):
                is_different_room = lambda room_id: room_id != space.room_id
                neighbor_room_ids = self._get_neighbor_room_ids(r, c)
                N, S, W, E = tuple(map(is_different_room, neighbor_room_ids))
                if N or S or E or W:
                    space.beside.add(CrimeSceneFeatureType.WALL)
                    if (N or S) and (E or W):
                        space.beside.add(CrimeSceneFeatureType.CORNER)

    def _get_neighbor_room_ids(self, r, c):
        north_room_id = self._spaces[r - 1][c].room_id if r > 0 else -1
        south_room_id = self._spaces[r +
                                     1][c].room_id if r < self._n - 1 else -1
        west_room_id = self._spaces[r][c - 1].room_id if c > 0 else -1
        east_room_id = self._spaces[r][c + 1].room_id if c < self._n - 1 else -1
        return (north_room_id, south_room_id, west_room_id, east_room_id)

    def _add_features(self) -> None:
        self._blocked_coordinates = []
        for feature in self._puzzle.crime_scene.features:
            if feature.position_type == PositionType.OCCUPIABLE_SPACE:
                self._add_space_feature(feature)
            elif feature.position_type == PositionType.BLOCKED_SPACE:
                self._add_space_feature(feature)
                self._blocked_coordinates.extend([
                    (coordinate.row, coordinate.column)
                    for coordinate in feature.coordinates
                ])
            elif feature.position_type == PositionType.VERTICAL_BOUNDARY:
                self._add_vertical_feature(feature)
            elif feature.position_type == PositionType.HORIZONTAL_BOUNDARY:
                self._add_horizontal_feature(feature)

    def _add_space_feature(self, feature: CrimeSceneFeature) -> None:
        coordinates = [(coordinate.row, coordinate.column)
                       for coordinate in feature.coordinates]
        for row, column in coordinates:
            self._spaces[row][column].on = feature.type
            self._rowwise_features[row].add(feature.type)
            self._columwise_features[column].add(feature.type)
            room_id = self._get_room_id(row, column)
            self._roomwise_features[room_id].add(feature.type)
            for n_row, n_col in self._get_neighbor_coordinates(row, column):
                if (n_row, n_col) not in coordinates:
                    self._spaces[n_row][n_col].beside.add(feature.type)

    def _get_neighbor_coordinates(self, row: int,
                                  column: int) -> List[Tuple[int, int]]:
        room_id = self._get_room_id(row, column)
        neighbor_coordinates = []
        if row > 0 and self._get_room_id(row - 1, column) == room_id:
            neighbor_coordinates.append((row - 1, column))
        if column > 0 and self._get_room_id(row, column - 1) == room_id:
            neighbor_coordinates.append((row, column - 1))
        if row < self._n - 1 and self._get_room_id(row + 1, column) == room_id:
            neighbor_coordinates.append((row + 1, column))
        if column < self._n - 1 and self._get_room_id(row,
                                                      column + 1) == room_id:
            neighbor_coordinates.append((row, column + 1))
        return neighbor_coordinates

    def _add_vertical_feature(self, feature: CrimeSceneFeature) -> None:
        for coordinate in feature.coordinates:
            row = coordinate.row
            self._rowwise_features[row].add(feature.type)
            if coordinate.column > 0:
                column = coordinate.column - 1
                room_id = self._get_room_id(row, column)
                self._roomwise_features[room_id].add(feature.type)
                self._spaces[row][column].beside.add(feature.type)
            if coordinate.column < self._n:
                column = coordinate.column
                room_id = self._get_room_id(row, column)
                self._roomwise_features[room_id].add(feature.type)
                self._spaces[row][column].beside.add(feature.type)

    def _add_horizontal_feature(self, feature: CrimeSceneFeature) -> None:
        for coordinate in feature.coordinates:
            column = coordinate.column
            self._columwise_features[column].add(feature.type)
            if coordinate.row > 0:
                row = coordinate.row - 1
                room_id = self._get_room_id(row, column)
                self._roomwise_features[room_id].add(feature.type)
                self._spaces[row][column].beside.add(feature.type)
            if coordinate.row < self._n:
                row = coordinate.row
                room_id = self._get_room_id(row, column)
                self._roomwise_features[room_id].add(feature.type)
                self._spaces[row][column].beside.add(feature.type)

    def _log_board_debug(self) -> None:
        logging.debug('spaces: {\n' + '\n'.join([
            '\n'.join([
                f'\t({r}, {c}): ' + repr(space) + ','
                for c, space in enumerate(row)
            ])
            for r, row in enumerate(self._spaces)
        ]) + '\n}')
        logging.debug('Roomwise features: ' + self._feature_sets_repr(
            self._roomwise_features, ['Unspecified'] +
            [room.name for room in self._puzzle.crime_scene.rooms]))
        logging.debug('Rowwise features: ' +
                      self._feature_sets_repr(self._rowwise_features))
        logging.debug('Columnwise features: ' +
                      self._feature_sets_repr(self._columwise_features))

    def _feature_sets_repr(self,
                           features_sets: List[Set[int]],
                           labels: Optional[List[str]] = None) -> str:
        if labels is None:
            labels = range(len(features_sets))
        return '{\n' + '\n'.join([
            f'\t{label}: [' + ', '.join([
                CrimeSceneFeatureType.Name(feature).capitalize()
                for feature in features
            ]) + '],'
            for label, features in zip(labels, features_sets)
        ]) + '\n}'

    def _create_model(self) -> None:
        self._model = CpModel()
        unavailable = set(self._blocked_coordinates)
        self._occupancies = [[[
            self._model.NewConstant(0) if (row, col) in unavailable else
            self._model.NewBoolVar(f'({person_id}, {row}, {col})')
            for col in range(self._n)
        ]
                              for row in range(self._n)]
                             for person_id in range(1, self._n + 1)]
        self._row_indexes = lambda row: list(
            zip(repeat(row, self._n), range(self._n)))
        self._col_indexes = lambda col: list(
            zip(range(self._n), repeat(col, self._n)))
        self._set_uniqueness_constraints()
        self._set_clues()

    def _get_coordinates_of_room(self, room_id: int) -> List[Tuple[int, int]]:
        return self._room_coordinates[room_id]

    def _add_constraint(self, constraint_function: Callable[[int], bool],
                        people_ids: List[int],
                        space_indexes: List[Tuple[int, int]]) -> None:
        if self._debug:
            logging.debug('Constraint:\n' + self._constraint_repr(
                constraint_function, people_ids, space_indexes))
        self._model.Add(
            constraint_function(
                sum([
                    self._occupancies[person_id - 1][row][col]
                    for person_id in people_ids
                    for row, col in space_indexes
                ])))

    def _constraint_repr(self, constraint_function: Callable[[int], bool],
                         people_ids: List[int],
                         space_indexes: List[Tuple[int, int]]) -> str:
        for i in range(self._n + 1):
            if constraint_function(i):
                if constraint_function(i + 1):
                    constraint_repr = f'MIN_COUNT({i})'
                else:
                    constraint_repr = f'EXACT_COUNT({i})'
                break
        people_repr = '[' + ', '.join(
            [str(person_id) for person_id in people_ids]) + ']'
        spaces_repr = '[' + ', '.join([f'({r}, {c})' for r, c in space_indexes
                                      ]) + ']'
        return f'constraint: {constraint_repr}\npeople: {people_repr}\nspaces: {spaces_repr}'

    def _set_uniqueness_constraints(self) -> None:
        for person_id in range(1, self._n + 1):
            people_ids = [person_id]
            space_indexes = list(product(range(self._n), repeat=2))
            self._add_constraint(EXACT_COUNT(1), people_ids, space_indexes)
        for row in range(self._n):
            people_ids = list(range(1, self._n + 1))
            space_indexes = self._row_indexes(row)
            self._add_constraint(EXACT_COUNT(1), people_ids, space_indexes)
        for col in range(self._n):
            people_ids = list(range(1, self._n + 1))
            space_indexes = self._col_indexes(col)
            self._add_constraint(EXACT_COUNT(1), people_ids, space_indexes)

    def _set_clues(self) -> None:
        for clue in self._puzzle.clues:
            self._set_clue(clue)

    def _set_clue(self, clue: Clue) -> None:
        people_ids = self._get_subject_ids(clue)
        if clue.HasField('same_row'):
            for row, furnuture in enumerate(self._rowwise_features):
                if clue.same_row not in furnuture:
                    space_indexes = self._row_indexes(row)
                    self._add_constraint(EXACT_COUNT(0), people_ids,
                                         space_indexes)
        elif clue.HasField('same_column'):
            for column, furnuture in enumerate(self._columnwise_features):
                if clue.same_column not in furnuture:
                    space_indexes = self._col_indexes(column)
                    self._add_constraint(EXACT_COUNT(0), people_ids,
                                         space_indexes)
        elif clue.HasField('same_room'):
            for room_id, furnuture in enumerate(self._roomwise_features):
                if clue.same_room not in furnuture:
                    space_indexes = self._room_coordinates[room_id]
                    self._add_constraint(EXACT_COUNT(0), people_ids,
                                         space_indexes)
        else:
            constraint_function = EXACT_COUNT(
                clue.exact_count) if clue.HasField(
                    'exact_count') else MIN_COUNT(clue.min_count)
            space_indexes = self._get_person_clue_coordinates(clue)
            self._add_constraint(constraint_function, people_ids, space_indexes)

    def _get_subject_ids(self, clue: Clue) -> List[int]:
        subject_ids = set()
        for subject_selector in clue.subject_selectors:
            selected_subject_ids = self._get_selected_subject_ids(
                subject_selector)
            subject_ids.update(selected_subject_ids)
        return sorted(list(subject_ids))

    def _get_selected_subject_ids(
            self, subject_selector: SubjectSelector) -> List[int]:
        if subject_selector.person_id == 0:
            person_id_filter = lambda person: True
        else:
            person_id_filter = lambda person: person.id == subject_selector.person_id
        if subject_selector.role == Role.UNSPECIFIED_ROLE:
            role_filter = lambda person: True
        else:
            role_filter = lambda person: person.role == subject_selector.role
        if subject_selector.gender == Gender.UNSPECIFIED_GENDER:
            gender_filter = lambda person: True
        else:
            gender_filter = lambda person: person.gender == subject_selector.gender
        passes_filters = lambda person: person_id_filter(
            person) and role_filter(person) and gender_filter(person)
        return [
            person.id
            for person in self._puzzle.people
            if passes_filters(person) != subject_selector.negate
        ]

    def _get_person_clue_coordinates(self, clue: Clue) -> List[Tuple[int, int]]:
        if clue.HasField('room_id'):
            return self._get_coordinates_of_room(clue.room_id)
        else:
            coordinates = []
            for row, row_spaces in enumerate(self._spaces):
                for column, space in enumerate(row_spaces):
                    if self._evaluate_space_for_clue(space, clue):
                        coordinates.append((row, column))
            return coordinates

    def _evaluate_space_for_clue(self, space: Space, clue: Clue) -> bool:
        if clue.HasField('beside'):
            return clue.beside in space.beside
        elif clue.HasField('on'):
            return clue.on == space.on
        raise AttributeError
