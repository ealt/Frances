from puzzle_pb2 import Puzzle


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

    def get_puzzle(self):
        return self._puzzle