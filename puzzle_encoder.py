from collections import namedtuple
import re

from puzzle_pb2 import Clue, Coordinate, CrimeSceneFeature, Gender, IntArray, Role, Puzzle
from google.protobuf.pyext._message import RepeatedCompositeContainer
from typing import List, Tuple

GENDER_DICT = {
    'female': Gender.FEMALE,
    'male': Gender.MALE,
}

FeatureData = namedtuple('FeatureData', ['name', 'type', 'occupiable'])

FEATURE_DATA_DICT = {
    'wall': FeatureData('wall', CrimeSceneFeature.WALL, False),
    'corner': FeatureData('corner', CrimeSceneFeature.CORNER, False),
    'window': FeatureData('window', CrimeSceneFeature.WINDOW, False),
    'chair': FeatureData('chair', CrimeSceneFeature.CHAIR, True),
    'bed': FeatureData('bed', CrimeSceneFeature.BED, True),
    'carpet': FeatureData('carpet', CrimeSceneFeature.CARPET, True),
    'plant': FeatureData('plant', CrimeSceneFeature.PLANT, False),
    'tv': FeatureData('tv', CrimeSceneFeature.TV, False),
    'table': FeatureData('table', CrimeSceneFeature.TABLE, False),
}

ParsedPersonClue = namedtuple('ParsedPersonClue',
                              ['subject', 'exclusive', 'preposition', 'object'])

PERSON_CLUE_PATTERN = (
    '^(?P<subject>{people}) (is |was )?'
    '(?P<exclusive>the only person (in the house )?|alone )?'
    '(that was )?(standing |sitting )?'
    '(?P<preposition>on|beside|next to|in'
    '( the (same (row|column|room) as|corner of))?) (a |the )?'
    '(?P<object>{furniture}|window|{rooms}|room)\.?$')


def stringify(messages: RepeatedCompositeContainer) -> str:
    return '|'.join([message.name.lower() for message in messages])


class PuzzleEncoder:

    def __init__(self, name: str = '') -> None:
        self._puzzle = Puzzle(name=name)

    @property
    def puzzle(self) -> Puzzle:
        return self._puzzle

    def set_rooms(self, room_names: List[str]) -> None:
        del self._puzzle.crime_scene.rooms[:]
        for room_id, room_name in enumerate(room_names):
            _ = self._puzzle.crime_scene.rooms.add(id=room_id, name=room_name)
        self._room_ids = {
            room_name.lower(): room_id
            for room_id, room_name in enumerate(room_names)
        }

    def set_floor_plan(self, floor_plan: List[List[int]]) -> None:
        del self._puzzle.crime_scene.floor_plan[:]
        for row_values in floor_plan:
            row = IntArray()
            row.values.extend(row_values)
            self._puzzle.crime_scene.floor_plan.append(row)

    def add_vertical_window(self, row: int, right: int) -> None:
        window = self._puzzle.crime_scene.windows.add(vertical=True)
        window.coordinate.row = row
        window.coordinate.column = right

    def add_horizontal_window(self, bottom: int, column: int) -> None:
        window = self._puzzle.crime_scene.windows.add(vertical=False)
        window.coordinate.column = column
        window.coordinate.row = bottom

    def add_furniture(self, name: str, coordinates: List[Tuple[int,
                                                               int]]) -> None:
        furniture_data = FEATURE_DATA_DICT[name.lower()]
        furniture = self._puzzle.crime_scene.furniture.add(
            type=furniture_data.type, occupiable=furniture_data.occupiable)
        furniture.coordinates.extend(
            [Coordinate(row=row, column=column) for row, column in coordinates])

    def set_people(self, suspects: List[Tuple[str, str]],
                   victim: Tuple[str, str]) -> None:
        del self._puzzle.people[:]
        for suspect_id, suspect in enumerate(suspects):
            suspect_name, suspect_gender = suspect
            _ = self._puzzle.people.add(id=suspect_id,
                                        name=suspect_name,
                                        gender=GENDER_DICT.get(
                                            suspect_gender.lower(),
                                            Gender.UNSPECIFIED_GENDER),
                                        role=Role.SUSPECT)
        victim_name, victim_gender = victim
        _ = self._puzzle.people.add(id=len(suspects),
                                    name=victim_name,
                                    gender=GENDER_DICT.get(
                                        victim_gender.lower(),
                                        Gender.UNSPECIFIED_GENDER),
                                    role=Role.VICTIM)
        self._people_ids = {
            person[0].lower(): person_id
            for person_id, person in enumerate(suspects + [victim])
        }

    def add_clue(self, raw_clue: str) -> None:
        if re.match('^There was no empty room\.?$', raw_clue, re.IGNORECASE):
            self._add_no_empty_room()
        else:
            parsed_person_clue = self._parse_person_clue(raw_clue)
            if parsed_person_clue.exclusive:
                self._add_exclusive_person_clue(parsed_person_clue)
            else:
                self._add_person_clue(parsed_person_clue)

    def _add_no_empty_room(self) -> None:
        for room in self._puzzle.crime_scene.rooms:
            clue = self._puzzle.clues.add()
            clue.room_clue.room_id = room.id
            clue.room_clue.is_occupied = True

    def _parse_person_clue(self, raw_clue: str) -> ParsedPersonClue:
        person_clue_pattern = self._generate_person_clue_pattern()
        match = re.match(person_clue_pattern, raw_clue, re.IGNORECASE)
        return ParsedPersonClue(subject=match.group('subject').lower(),
                                exclusive=match.group('exclusive') != None,
                                preposition=match.group('preposition').lower(),
                                object=match.group('object').lower())

    def _generate_person_clue_pattern(self) -> str:
        return PERSON_CLUE_PATTERN.format(
            people=stringify(self._puzzle.people),
            furniture=stringify(FEATURE_DATA_DICT.values()),
            rooms=stringify(self._puzzle.crime_scene.rooms))

    def _add_exclusive_person_clue(
            self, parsed_person_clue: ParsedPersonClue) -> None:
        for person in self._puzzle.people:
            clue = self._puzzle.clues.add()
            clue.person_clue.person_id = person.id
            self._add_prepositional_phrase(clue, parsed_person_clue)
            clue.person_clue.negate = person.name.lower(
            ) != parsed_person_clue.subject

    def _add_person_clue(self, parsed_person_clue: ParsedPersonClue) -> None:
        clue = self._puzzle.clues.add()
        clue.person_clue.person_id = self._people_ids[
            parsed_person_clue.subject]
        self._add_prepositional_phrase(clue, parsed_person_clue)

    def _add_prepositional_phrase(self, clue: Clue,
                                  parsed_person_clue: ParsedPersonClue) -> None:
        if parsed_person_clue.preposition == 'on':
            clue.person_clue.on = FEATURE_DATA_DICT[
                parsed_person_clue.object].type
        elif parsed_person_clue.preposition in ('beside', 'next to'):
            if parsed_person_clue.object in FEATURE_DATA_DICT.keys():
                object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
                clue.person_clue.beside = object_type
        elif parsed_person_clue.preposition == 'in the same row as':
            object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
            clue.person_clue.same_row = object_type
        elif parsed_person_clue.preposition == 'in the same column as':
            object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
            clue.person_clue.same_column = object_type
        elif parsed_person_clue.preposition == 'in the same room as':
            object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
            clue.person_clue.same_room = object_type
        elif parsed_person_clue.preposition == 'in the corner of':
            corner = FEATURE_DATA_DICT['corner'].type
            clue.person_clue.beside = corner
        elif parsed_person_clue.preposition == 'in':
            clue.person_clue.room_id = self._room_ids[parsed_person_clue.object]
