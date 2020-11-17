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

ParsedClue = namedtuple(
    'ParsedClue', ['subject', 'preposition', 'object'])

CLUE_PATTERN = ('^(?P<subject>{people}) (is |was )?'
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

    def add_window(self, row=None, column=None, top=None, bottom=None,
                   left=None, right=None, **kwargs):
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
        furniture.coordinates.extend([
            Coordinate(row=row, column=column)
            for row, column in coordinates
        ])

    def set_people(self, suspect_names, victim_name):
        del self._puzzle.people[:]
        for suspect_id, suspect_name in enumerate(suspect_names):
            _ = self._puzzle.people.add(
                id=suspect_id, name=suspect_name, type=Puzzle.Person.SUSPECT)
        _ = self._puzzle.people.add(
            id=len(suspect_names), name=victim_name, type=Puzzle.Person.VICTIM)
        self._people_ids = {
            person_name.lower(): person_id 
            for person_id, person_name in enumerate(suspect_names + [victim_name])
        }

    def add_clue(self, raw_clue):
        parsed_clue = self._parse_clue(raw_clue)
        self._add_clue(parsed_clue)

    def _parse_clue(self, raw_clue):
        clue_pattern = self._generate_clue_pattern()
        match = re.match(clue_pattern, raw_clue, re.IGNORECASE)
        return ParsedClue(
            subject=match.group('subject').lower(),
            preposition=match.group('preposition').lower(),
            object=match.group('object').lower())

    def _generate_clue_pattern(self):
        return CLUE_PATTERN.format(
            people=stringify(self._puzzle.people),
            furniture=stringify(FURNITURE_DATA_DICT.values()),
            rooms=stringify(self._puzzle.crime_scene.rooms))

    def _add_clue(self, parsed_clue):
        pass

    def get_puzzle(self):
        return self._puzzle