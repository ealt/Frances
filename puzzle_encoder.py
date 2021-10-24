from puzzle_clue_encoder import PuzzleClueEncoder
from puzzle_clue_regex_encoder import PuzzleClueRegexEncoder
from puzzle_pb2 import Coordinate, CrimeSceneFeatureType, Gender, IntArray, PositionType, Role, Puzzle
from puzzle_utils import FEATURE_DATA_DICT, GENDER_DICT
from typing import List, Tuple


class PuzzleEncoder:

    def __init__(self,
                 name: str = '',
                 clue_encoder: PuzzleClueEncoder = PuzzleClueRegexEncoder,
                 **kwargs) -> None:
        self._puzzle = Puzzle(name=name)
        self._clue_encoder = clue_encoder()

    @property
    def puzzle(self) -> Puzzle:
        return self._puzzle

    def set_rooms(self, room_names: List[str]) -> None:
        del self._puzzle.crime_scene.rooms[:]
        for room_id, room_name in enumerate(room_names, start=1):
            _ = self._puzzle.crime_scene.rooms.add(id=room_id, name=room_name)
        self._room_ids = {
            room_name.lower(): room_id
            for room_id, room_name in enumerate(room_names, start=1)
        }

    def set_floor_plan(self, floor_plan: List[List[int]]) -> None:
        del self._puzzle.crime_scene.floor_plan[:]
        for row_values in floor_plan:
            row = IntArray()
            row.values.extend(row_values)
            self._puzzle.crime_scene.floor_plan.append(row)

    def add_vertical_window(self, row: int, right: int) -> None:
        window = self._puzzle.crime_scene.features.add(
            type=CrimeSceneFeatureType.WINDOW,
            position_type=PositionType.VERTICAL_BOUNDARY)
        window.coordinates.append(Coordinate(row=row, column=right))

    def add_horizontal_window(self, bottom: int, column: int) -> None:
        window = self._puzzle.crime_scene.features.add(
            type=CrimeSceneFeatureType.WINDOW,
            position_type=PositionType.HORIZONTAL_BOUNDARY)
        window.coordinates.append(Coordinate(row=bottom, column=column))

    def add_feature(self, name: str, coordinates: List[Tuple[int,
                                                             int]]) -> None:
        feature_data = FEATURE_DATA_DICT[name.lower()]
        feature = self._puzzle.crime_scene.features.add(
            type=feature_data.type, position_type=feature_data.position_type)
        feature.coordinates.extend(
            [Coordinate(row=row, column=column) for row, column in coordinates])

    def set_people(self, suspects: List[Tuple[str, str]],
                   victim: Tuple[str, str]) -> None:
        del self._puzzle.people[:]
        for suspect_id, suspect in enumerate(suspects, start=1):
            suspect_name, suspect_gender = suspect
            _ = self._puzzle.people.add(id=suspect_id,
                                        name=suspect_name,
                                        gender=GENDER_DICT.get(
                                            suspect_gender.lower(),
                                            Gender.UNSPECIFIED_GENDER),
                                        role=Role.SUSPECT)
        victim_name, victim_gender = victim
        _ = self._puzzle.people.add(id=len(suspects) + 1,
                                    name=victim_name,
                                    gender=GENDER_DICT.get(
                                        victim_gender.lower(),
                                        Gender.UNSPECIFIED_GENDER),
                                    role=Role.VICTIM)
        self._people_ids = {
            person[0].lower(): person_id
            for person_id, person in enumerate(suspects + [victim], start=1)
        }

    def add_clue(self, raw_clue: str) -> None:
        clues = self._clue_encoder.encode_clue(
            raw_clue,
            self._room_ids,
            self._people_ids,
        )
        self._puzzle.clues.extend(clues)
