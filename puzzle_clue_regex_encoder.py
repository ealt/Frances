from collections import namedtuple
import re
from typing import Dict, List

from puzzle_clue_encoder import PuzzleClueEncoder
from puzzle_utils import GENDER_DICT, ROLE_DICT, FEATURE_DATA_DICT, NUMBERS_NAMES, get_number_value
from puzzle_pb2 import Clue, Preposition, SubjectSelector
from google.protobuf.pyext._message import RepeatedCompositeContainer


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


class PuzzleClueRegexEncoder(PuzzleClueEncoder):

    def encode_clue(
        self,
        raw_clue: str,
        room_ids: Dict[str, int],
        people_ids: Dict[str, int],
    ) -> List[Clue]:
        self._room_ids = room_ids
        self._people_ids = people_ids
        if re.match('^There was no empty room\.?$', raw_clue, re.IGNORECASE):
            return self._encode_no_empty_room()
        parsed_person_clue = self._parse_person_clue(raw_clue)
        if parsed_person_clue.exclusive:
            return self._encode_exclusive_person_clue(parsed_person_clue)
        return self._encode_person_clue(parsed_person_clue)

    def _encode_no_empty_room(self) -> List[Clue]:
        clues = []
        for room_id in self._room_ids.values():
            clue = Clue()
            clue.subject_selectors.add()
            clue.position_selectors.add(preposition=Preposition.IN,
                                        room_id=room_id)
            clue.min_count = 1
            clues.append(clue)
        return clues

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
        n = len(self._people_ids)
        return PERSON_CLUE_PATTERN.format(
            people='|'.join(self._people_ids.keys()),
            feature=stringify(FEATURE_DATA_DICT.values()),
            rooms='|'.join(self._room_ids.keys()),
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

    def _encode_exclusive_person_clue(
            self, parsed_person_clue: ParsedPersonClue) -> List[Clue]:
        person_id = self._people_ids[parsed_person_clue.subject]
        subject_clue = Clue()
        subject_clue.subject_selectors.add(person_id=person_id)
        subject_clue.exact_count = 1
        self._add_prepositional_phrase(subject_clue, parsed_person_clue)
        others_clue = Clue()
        others_clue.subject_selectors.add(person_id=person_id, negate=True)
        others_clue.exact_count = 0
        self._add_prepositional_phrase(others_clue, parsed_person_clue)
        return [subject_clue, others_clue]

    def _encode_person_clue(self,
                            parsed_person_clue: ParsedPersonClue) -> List[Clue]:
        person_id = self._people_ids[parsed_person_clue.subject]
        clue = Clue()
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
        return [clue]

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
