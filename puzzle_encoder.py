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

    def get_puzzle(self):
        return self._puzzle