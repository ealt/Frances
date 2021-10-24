import abc
from typing import Dict, List

from puzzle_pb2 import Clue


class PuzzleClueEncoder(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'encode_clue') and
                callable(subclass.encode_clue) or NotImplemented)

    @abc.abstractmethod
    def encode_clue(
        self,
        raw_clue: str,
        room_ids: Dict[str, int],
        people_ids: Dict[str, int],
    ) -> List[Clue]:
        raise NotImplementedError