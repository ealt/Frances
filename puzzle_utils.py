from collections import namedtuple
from typing import Optional

from puzzle_pb2 import CrimeSceneFeatureType, Gender, PositionType, Role

GENDER_DICT = {
    'female': Gender.FEMALE,
    'woman': Gender.FEMALE,
    'women': Gender.FEMALE,
    'male': Gender.MALE,
    'man': Gender.MALE,
    'men': Gender.MALE,
}

ROLE_DICT = {
    'suspect': Role.SUSPECT,
    'victim': Role.VICTIM,
    'murderer': Role.MURDERER,
}

FeatureData = namedtuple('FeatureData', ['name', 'type', 'position_type'])

FEATURE_DATA_DICT = {
    'wall':
        FeatureData('wall', CrimeSceneFeatureType.WALL, None),
    'corner':
        FeatureData('corner', CrimeSceneFeatureType.CORNER, None),
    'window':
        FeatureData('window', CrimeSceneFeatureType.WINDOW, None),
    'chair':
        FeatureData('chair', CrimeSceneFeatureType.CHAIR,
                    PositionType.OCCUPIABLE_SPACE),
    'bed':
        FeatureData('bed', CrimeSceneFeatureType.BED,
                    PositionType.OCCUPIABLE_SPACE),
    'carpet':
        FeatureData('carpet', CrimeSceneFeatureType.CARPET,
                    PositionType.OCCUPIABLE_SPACE),
    'plant':
        FeatureData('plant', CrimeSceneFeatureType.PLANT,
                    PositionType.BLOCKED_SPACE),
    'tv':
        FeatureData('tv', CrimeSceneFeatureType.TV, PositionType.BLOCKED_SPACE),
    'table':
        FeatureData('table', CrimeSceneFeatureType.TABLE,
                    PositionType.BLOCKED_SPACE),
}

NUMBERS_NAMES = {
    0: 'zero',
    1: 'one',
    2: 'two',
    3: 'three',
    4: 'four',
    5: 'five',
    6: 'six',
    7: 'seven',
    8: 'eight',
    9: 'nine',
}

NUMBER_VALUES = {name: value for value, name in NUMBERS_NAMES.items()}
NUMBER_VALUES['a'] = 1
NUMBER_VALUES['an'] = 1
NUMBER_VALUES['another'] = 1


def get_number_value(name: str) -> Optional[int]:
    if name.isdigit():
        return int(name)
    if name in NUMBER_VALUES:
        return NUMBER_VALUES[name]
    return None