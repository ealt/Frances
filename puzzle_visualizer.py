import re

from collections import namedtuple

from puzzle_pb2 import Coordinate, CrimeSceneFeatureType, Puzzle

WallIntersection = namedtuple('WallIntersection',
                              ['up', 'down', 'left', 'right'],
                              defaults=[False, False, False, False])

# https://www.unicode.org/charts/PDF/U2500.pdf
WALL_INTERSECTION_VALUES = {
    WallIntersection(): ' ',
    WallIntersection(left=True, right=True): '\u2500',
    WallIntersection(up=True, down=True): '\u2502',
    WallIntersection(down=True, right=True): '\u250C',
    WallIntersection(down=True, left=True): '\u2510',
    WallIntersection(up=True, right=True): '\u2514',
    WallIntersection(up=True, left=True): '\u2518',
    WallIntersection(up=True, down=True, right=True): '\u251C',
    WallIntersection(up=True, down=True, left=True): '\u2524',
    WallIntersection(down=True, left=True, right=True): '\u252C',
    WallIntersection(up=True, left=True, right=True): '\u2534',
    WallIntersection(up=True, down=True, left=True, right=True): '\u253C',
    WallIntersection(left=True): '\u2574',
    WallIntersection(up=True): '\u2575',
    WallIntersection(right=True): '\u2576',
    WallIntersection(down=True): '\u2577',
}

ROW = lambda n, value: [value if c % 2 == 1 else ' ' for c in range(2 * n + 1)]

BACKGROUND_COLOR_IDS = {
    'black': 40,
    'red': 41,
    'green': 42,
    'yellow': 43,
    'blue': 44,
    'magenta': 45,
    'cyan': 46,
    'grey': 47,
}


# https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
def add_background_color(text, color):
    if color in BACKGROUND_COLOR_IDS.keys():
        background_color_id = BACKGROUND_COLOR_IDS[color]
        return f'\x1b[{background_color_id}m{text}\x1b[0m'
    else:
        return text


FURNITURE_COLORS = {
    CrimeSceneFeatureType.CHAIR: 'red',
    CrimeSceneFeatureType.BED: 'magenta',
    CrimeSceneFeatureType.CARPET: 'blue',
    CrimeSceneFeatureType.PLANT: 'green',
    CrimeSceneFeatureType.TV: 'grey',
    CrimeSceneFeatureType.TABLE: 'yellow',
}

LEGEND = ' '.join([
    add_background_color(CrimeSceneFeatureType.Name(type).capitalize(), color)
    for type, color in FURNITURE_COLORS.items()
])


class PuzzleVisualizer:

    def __init__(self, puzzle: Puzzle, w: int = 3) -> None:
        self._board = []
        if puzzle.HasField('crime_scene'):
            self._crime_scene = puzzle.crime_scene
            self._people = puzzle.people
            self._w = w
            self._n = len(self._crime_scene.floor_plan)
            self._add_crime_scene()
            self._add_people()
        self._set_visulization()

    @property
    def visualization(self) -> str:
        return self._visualization

    def _add_crime_scene(self):
        self._add_walls()
        self._add_windows()
        self._add_furniture()

    def _add_walls(self):
        self._vertical_wall_value = WALL_INTERSECTION_VALUES[WallIntersection(
            up=True, down=True)]
        self._horizontal_wall_value = self._w * WALL_INTERSECTION_VALUES[
            WallIntersection(left=True, right=True)]
        self._horizontal_empty_value = self._w * WALL_INTERSECTION_VALUES[
            WallIntersection()]
        self._add_exterior_walls()
        self._add_interior_walls()
        self._add_wall_intersections()

    def _add_exterior_walls(self) -> None:
        self._board.append(ROW(self._n, self._horizontal_wall_value))
        for r in range(1, 2 * self._n):
            self._board.append(ROW(self._n, self._horizontal_empty_value))
            if r % 2 == 1:
                self._board[-1][0] = self._vertical_wall_value
                self._board[-1][-1] = self._vertical_wall_value
        self._board.append(ROW(self._n, self._horizontal_wall_value))

    def _add_interior_walls(self) -> None:
        self._add_vertical_interior_walls()
        self._add_horizontal_interior_walls()

    def _add_vertical_interior_walls(self) -> None:
        for r, row in enumerate(self._crime_scene.floor_plan):
            for c, left, right in zip(range(1, self._n), row.values[:-1],
                                      row.values[1:]):
                if left != right:
                    self._set_vertical_boundary_value(r, c,
                                                      self._vertical_wall_value)

    def _add_horizontal_interior_walls(self) -> None:
        for r, top_row, bottom_row in zip(range(1, self._n),
                                          self._crime_scene.floor_plan[:-1],
                                          self._crime_scene.floor_plan[1:]):
            for c, top, bottom in zip(range(self._n), top_row.values,
                                      bottom_row.values):
                if top != bottom:
                    self._set_horizontal_boundary_value(
                        r, c, self._horizontal_wall_value)

    def _add_wall_intersections(self) -> None:
        for bottom in range(self._n + 1):
            for right in range(self._n + 1):
                wall_intersection = self._get_wall_intersection(bottom, right)
                value = WALL_INTERSECTION_VALUES[wall_intersection]
                self._set_boundary_intersection_value(bottom, right, value)

    def _get_wall_intersection(self, bottom: int,
                               right: int) -> WallIntersection:
        top = bottom - 1
        left = right - 1
        up_wall = False if bottom == 0 else self._get_vertical_boundary_value(
            top, right) == self._vertical_wall_value
        down_wall = False if bottom == self._n else self._get_vertical_boundary_value(
            bottom, right) == self._vertical_wall_value
        left_wall = False if right == 0 else self._get_horizontal_boundary_value(
            bottom, left) == self._horizontal_wall_value
        right_wall = False if right == self._n else self._get_horizontal_boundary_value(
            bottom, right) == self._horizontal_wall_value
        return WallIntersection(up=up_wall,
                                down=down_wall,
                                left=left_wall,
                                right=right_wall)

    def _add_windows(self) -> None:
        self._vertical_window_value = '\u2551'
        self._horizontal_window_value = self._w * '\u2550'
        for window in self._crime_scene.windows:
            if window.vertical:
                self._set_vertical_boundary_value(window.coordinate.row,
                                                  window.coordinate.column,
                                                  self._vertical_window_value)
            else:
                self._set_horizontal_boundary_value(
                    window.coordinate.row, window.coordinate.column,
                    self._horizontal_window_value)

    def _add_furniture(self) -> None:
        self._add_funiture_spaces()
        self._add_funiture_boundaries()

    def _add_funiture_spaces(self) -> None:
        self._furniture_text_value = self._w * ' '
        for furniture in self._crime_scene.furniture:
            furniture_color = FURNITURE_COLORS[furniture.type]
            furniture_value = add_background_color(self._furniture_text_value,
                                                   furniture_color)
            for coordinate in furniture.coordinates:
                self._set_space_value(coordinate.row, coordinate.column,
                                      furniture_value)

    def _add_funiture_boundaries(self) -> None:
        self._vertical_furniture_boundary_text_value = ' '
        self._horizontal_furniture_boundary_text_value = self._w * ' '
        for furniture in self._crime_scene.furniture:
            furniture_color = FURNITURE_COLORS[furniture.type]
            for coordinate_1, coordinate_2 in zip(furniture.coordinates[:-1],
                                                  furniture.coordinates[1:]):
                self._add_funiture_boundary(coordinate_1, coordinate_2,
                                            furniture_color)

    def _add_funiture_boundary(self, coordinate_1: Coordinate,
                               coordinate_2: Coordinate, furniture_color: str):
        row_diff = abs(coordinate_2.row - coordinate_1.row)
        column_diff = abs(coordinate_2.column - coordinate_1.column)
        if row_diff == 0 and column_diff == 1:
            row = coordinate_1.row
            right = max(coordinate_2.column, coordinate_1.column)
            value = add_background_color(
                self._vertical_furniture_boundary_text_value, furniture_color)
            self._set_vertical_boundary_value(row, right, value)
        elif row_diff == 1 and column_diff == 0:
            bottom = max(coordinate_2.row, coordinate_1.row)
            column = coordinate_1.column
            value = add_background_color(
                self._horizontal_furniture_boundary_text_value, furniture_color)
            self._set_horizontal_boundary_value(bottom, column, value)

    def _add_people(self) -> None:
        for person in self._people:
            person_initial = person.name[0]
            person_value = self._get_padded_value(person_initial)
            space_value = self._get_space_value(person.coordinate.row,
                                                person.coordinate.column)
            value = re.sub(f'\ {{{self._w}}}', person_value, space_value)
            self._set_space_value(person.coordinate.row,
                                  person.coordinate.column, value)

    def _get_padded_value(self, value: str) -> str:
        left_pad = ' ' * ((self._w - len(value)) // 2)
        right_pad = ' ' * (self._w - len(value) - len(left_pad))
        return left_pad + value + right_pad

    def _get_space_value(self, row: int, column: int) -> str:
        return self._board[2 * row + 1][2 * column + 1]

    def _set_space_value(self, row: int, column: int, value: str) -> None:
        self._board[2 * row + 1][2 * column + 1] = value

    def _get_vertical_boundary_value(self, row: int, right: int) -> str:
        return self._board[2 * row + 1][2 * right]

    def _set_vertical_boundary_value(self, row: int, right: int,
                                     value: str) -> None:
        self._board[2 * row + 1][2 * right] = value

    def _get_horizontal_boundary_value(self, bottom: int, column: int) -> str:
        return self._board[2 * bottom][2 * column + 1]

    def _set_horizontal_boundary_value(self, bottom: int, column: int,
                                       value: str) -> None:
        self._board[2 * bottom][2 * column + 1] = value

    def _set_boundary_intersection_value(self, bottom: int, right: int,
                                         value: str) -> None:
        self._board[2 * bottom][2 * right] = value

    def _set_visulization(self):
        column_labels = ' '.join(
            [self._get_padded_value(str(c)) for c in range(self._n)])
        board = [
            f'{r // 2} ' + ''.join(row) if r % 2 == 1 else '  ' + ''.join(row)
            for r, row in enumerate(self._board)
        ]
        self._visualization = '\n'.join(['   ' + column_labels] + board +
                                        ['   ' + LEGEND])
