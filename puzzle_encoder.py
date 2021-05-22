from collections import namedtuple
import re

from puzzle_pb2 import Coordinate, Puzzle

FurnitureData = namedtuple('FurnitureData', ['name', 'type', 'occupiable'])

FURNITURE_DATA_DICT = {
    'chair': FurnitureData('chair', Puzzle.CrimeScene.Furniture.CHAIR, True),
    'bed': FurnitureData('bed', Puzzle.CrimeScene.Furniture.BED, True),
    'carpet': FurnitureData('carpet', Puzzle.CrimeScene.Furniture.CARPET, True),
    'plant': FurnitureData('plant', Puzzle.CrimeScene.Furniture.PLANT, False),
    'tv': FurnitureData('tv', Puzzle.CrimeScene.Furniture.TV, False),
    'table': FurnitureData('table', Puzzle.CrimeScene.Furniture.TABLE, False)
}

ParsedPersonClue = namedtuple('ParsedPersonClue',
                              ['subject', 'exclusive', 'preposition', 'object'])

PERSON_CLUE_PATTERN = ('^(?P<subject>{people}) (is |was )?'
                       '(?P<exclusive>the only person (in the house )?|alone )?'
                       '(that was )?(standing )?'
                       '(?P<preposition>on|beside|next to|in) (a |the )?'
                       '(?P<object>{furniture}|window|{rooms})\.?$')


def stringify(messages):
    return '|'.join([message.name.lower() for message in messages])


class PuzzleEncoder:

    def __init__(self, name=''):
        self._puzzle = Puzzle(name=name)

    def set_rooms(self, room_names):
        del self._puzzle.crime_scene.rooms[:]
        for room_id, room_name in enumerate(room_names):
            _ = self._puzzle.crime_scene.rooms.add(id=room_id, name=room_name)
        self._room_ids = {
            room_name.lower(): room_id
            for room_id, room_name in enumerate(room_names)
        }

    def set_floor_plan(self, floor_plan):
        self._puzzle.crime_scene.floor_plan[:] = floor_plan

    def add_window(self,
                   row=None,
                   column=None,
                   top=None,
                   bottom=None,
                   left=None,
                   right=None,
                   **kwargs):
        window = self._puzzle.crime_scene.windows.add()
        if row is not None:
            window.vertical_border.row = row
            if left is not None:
                window.vertical_border.left = left
            if right is not None:
                window.vertical_border.right = right
        if column is not None:
            window.horizontal_border.column = column
            if top is not None:
                window.horizontal_border.top = top
            if bottom is not None:
                window.horizontal_border.bottom = bottom

    def add_furniture(self, name, coordinates):
        furniture_data = FURNITURE_DATA_DICT[name.lower()]
        furniture = self._puzzle.crime_scene.furniture.add(
            type=furniture_data.type, occupiable=furniture_data.occupiable)
        furniture.coordinates.extend(
            [Coordinate(row=row, column=column) for row, column in coordinates])

    def set_people(self, suspect_names, victim_name):
        del self._puzzle.people[:]
        for suspect_id, suspect_name in enumerate(suspect_names):
            _ = self._puzzle.people.add(id=suspect_id,
                                        name=suspect_name,
                                        type=Puzzle.Person.SUSPECT)
        _ = self._puzzle.people.add(id=len(suspect_names),
                                    name=victim_name,
                                    type=Puzzle.Person.VICTIM)
        self._people_ids = {
            person_name.lower(): person_id
            for person_id, person_name in enumerate(suspect_names +
                                                    [victim_name])
        }

    def add_clue(self, raw_clue):
        if re.match('^There was no empty room\.?$', raw_clue, re.IGNORECASE):
            self._add_no_empty_room()
        else:
            parsed_person_clue = self._parse_person_clue(raw_clue)
            if parsed_person_clue.exclusive:
                self._add_exclusive_person_clue(parsed_person_clue)
            else:
                self._add_person_clue(parsed_person_clue)

    def _add_no_empty_room(self):
        for room in self._puzzle.crime_scene.rooms:
            clue = self._puzzle.clues.add()
            clue.room_clue.room_id = room.id
            clue.room_clue.is_occupied = True

    def _parse_person_clue(self, raw_clue):
        person_clue_pattern = self._generate_person_clue_pattern()
        match = re.match(person_clue_pattern, raw_clue, re.IGNORECASE)
        return ParsedPersonClue(subject=match.group('subject').lower(),
                                exclusive=match.group('exclusive') != None,
                                preposition=match.group('preposition').lower(),
                                object=match.group('object').lower())

    def _generate_person_clue_pattern(self):
        return PERSON_CLUE_PATTERN.format(
            people=stringify(self._puzzle.people),
            furniture=stringify(FURNITURE_DATA_DICT.values()),
            rooms=stringify(self._puzzle.crime_scene.rooms))

    def _add_exclusive_person_clue(self, parsed_person_clue):
        for person in self._puzzle.people:
            clue = self._puzzle.clues.add()
            clue.person_clue.person_id = person.id
            self._add_prepositional_phrase(clue, parsed_person_clue)
            clue.person_clue.negate = person.name.lower(
            ) != parsed_person_clue.subject

    def _add_person_clue(self, parsed_person_clue):
        clue = self._puzzle.clues.add()
        clue.person_clue.person_id = self._people_ids[
            parsed_person_clue.subject]
        self._add_prepositional_phrase(clue, parsed_person_clue)

    def _add_prepositional_phrase(self, clue, parsed_person_clue):
        if parsed_person_clue.preposition == 'on':
            clue.person_clue.on = FURNITURE_DATA_DICT[
                parsed_person_clue.object].type
        elif parsed_person_clue.preposition in ('beside', 'next to'):
            if parsed_person_clue.object == 'window':
                clue.person_clue.beside_window = True
            elif parsed_person_clue.object in FURNITURE_DATA_DICT.keys():
                object_type = FURNITURE_DATA_DICT[
                    parsed_person_clue.object].type
                clue.person_clue.beside = object_type
        elif parsed_person_clue.preposition == 'in':
            clue.person_clue.room_id = self._room_ids[parsed_person_clue.object]

    def get_puzzle(self):
        return self._puzzle