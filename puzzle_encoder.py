from collections import namedtuple
import re

from puzzle_pb2 import Clue, Coordinate, CrimeSceneFeatureType, Gender, IntArray, PositionType, Preposition, Role, Puzzle, SubjectSelector
from puzzle_utils import GENDER_DICT, ROLE_DICT, FEATURE_DATA_DICT, NUMBERS_NAMES, get_number_value
from google.protobuf.pyext._message import RepeatedCompositeContainer
from typing import List, Tuple


def update_subject_selector(selector: SubjectSelector, key: str) -> None:
    if key in ROLE_DICT:
        selector.role = ROLE_DICT[key]
    if key in GENDER_DICT:
        selector.gender = GENDER_DICT[key]


ParsedPersonClue = namedtuple(
    'ParsedPersonClue',
    ['subject', 'exclusive', 'preposition', 'object', 'subj_phrase'])

PasrsedSubjPhrase = namedtuple('PasrsedSubjPhrase', ['number', 'selector'])

PERSON_CLUE_PATTERN = (
    '^(?P<subject>{people}) (is |was )?'
    '(?P<exclusive>the only person (in the house )?|alone )?'
    '(that was )?(standing |sitting )?'
    '(?P<preposition>on|beside|next to|in'
    '( the (same (row|column|room) as|corner of))?) (a |the )?'
    '(?P<object>{feature}|window|{rooms}|room)'
    '(?P<subj_phrase> with (?P<subj_num>a|an|another|{numbers}) (other )?'
    '((?P<subj_adj>suspect) )?'
    '(?P<subj_noun>man|men|woman|women|person|people|suspect|suspects))?\.?$')


def stringify(messages: RepeatedCompositeContainer) -> str:
    return '|'.join([message.name.lower() for message in messages])


def stringify_numbers(n: int = 9) -> str:
    return '|'.join([str(i) + '|' + NUMBERS_NAMES[i] for i in range(n + 1)])


class PuzzleEncoder:

    def __init__(self, name: str = '') -> None:
        self._puzzle = Puzzle(name=name)

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
            clue.subject_selectors.add()
            clue.position_selectors.add(preposition=Preposition.IN,
                                        room_id=room.id)
            clue.min_count = 1

    def _parse_person_clue(self, raw_clue: str) -> ParsedPersonClue:
        person_clue_pattern = self._generate_person_clue_pattern()
        match = re.match(person_clue_pattern, raw_clue, re.IGNORECASE)
        parsed_subj_phrase = None if match.group(
            'subj_phrase') is None else self._parse_subj_phrase(match)
        return ParsedPersonClue(subject=match.group('subject').lower(),
                                exclusive=match.group('exclusive') != None,
                                preposition=match.group('preposition').lower(),
                                object=match.group('object').lower(),
                                subj_phrase=parsed_subj_phrase)

    def _generate_person_clue_pattern(self) -> str:
        n = len(self._puzzle.people)
        return PERSON_CLUE_PATTERN.format(
            people=stringify(self._puzzle.people),
            feature=stringify(FEATURE_DATA_DICT.values()),
            rooms=stringify(self._puzzle.crime_scene.rooms),
            numbers=stringify_numbers(n))

    def _parse_subj_phrase(self, match) -> PasrsedSubjPhrase:
        number = get_number_value(match.group('subj_num'))
        selector = SubjectSelector()
        update_subject_selector(selector, match.group('subj_adj'))
        subj_noun = match.group('subj_noun')
        if subj_noun[-1] == 's':
            subj_noun = subj_noun[:-1]
        update_subject_selector(selector, subj_noun)
        return PasrsedSubjPhrase(number=number, selector=selector)

    def _add_exclusive_person_clue(
            self, parsed_person_clue: ParsedPersonClue) -> None:
        person_id = self._people_ids[parsed_person_clue.subject]
        subject_clue = self._puzzle.clues.add()
        subject_clue.subject_selectors.add(person_id=person_id)
        subject_clue.exact_count = 1
        self._add_prepositional_phrase(subject_clue, parsed_person_clue)
        others_clue = self._puzzle.clues.add()
        others_clue.subject_selectors.add(person_id=person_id, negate=True)
        others_clue.exact_count = 0
        self._add_prepositional_phrase(others_clue, parsed_person_clue)

    def _add_person_clue(self, parsed_person_clue: ParsedPersonClue) -> None:
        person_id = self._people_ids[parsed_person_clue.subject]
        clue = self._puzzle.clues.add()
        clue.subject_selectors.add(person_id=person_id)
        if parsed_person_clue.subj_phrase is None:
            clue.exact_count = 1
        else:
            clue.subject_selectors.append(
                parsed_person_clue.subj_phrase.selector)
            if parsed_person_clue.subj_phrase.number is None:
                clue.min_count = 1
            else:
                clue.exact_count = 1 + parsed_person_clue.subj_phrase.number
        self._add_prepositional_phrase(clue, parsed_person_clue)

    def _add_prepositional_phrase(self, clue: Clue,
                                  parsed_person_clue: ParsedPersonClue) -> None:
        if parsed_person_clue.preposition == 'on':
            clue.position_selectors.add(
                preposition=Preposition.ON,
                feature=FEATURE_DATA_DICT[parsed_person_clue.object].type)
        elif parsed_person_clue.preposition in ('beside', 'next to'):
            if parsed_person_clue.object in FEATURE_DATA_DICT.keys():
                object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
                clue.position_selectors.add(preposition=Preposition.BESIDE,
                                            feature=object_type)
        elif parsed_person_clue.preposition == 'in the same row as':
            object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
            clue.position_selectors.add(preposition=Preposition.IN_SAME_ROW_AS,
                                        feature=object_type)
        elif parsed_person_clue.preposition == 'in the same column as':
            object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
            clue.position_selectors.add(
                preposition=Preposition.IN_SAME_COLUMN_AS, feature=object_type)
        elif parsed_person_clue.preposition == 'in the same room as':
            object_type = FEATURE_DATA_DICT[parsed_person_clue.object].type
            clue.position_selectors.add(preposition=Preposition.IN_SAME_ROOM_AS,
                                        feature=object_type)
        elif parsed_person_clue.preposition == 'in the corner of':
            corner = FEATURE_DATA_DICT['corner'].type
            clue.position_selectors.add(preposition=Preposition.BESIDE,
                                        feature=corner)
        elif parsed_person_clue.preposition == 'in':
            clue.position_selectors.add(
                preposition=Preposition.IN,
                room_id=self._room_ids[parsed_person_clue.object])
