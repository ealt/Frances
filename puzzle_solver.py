from ortools.sat.python import cp_model

from puzzle_modeler import PuzzleModeler
from puzzle_pb2 import Puzzle
from google.protobuf.pyext._message import RepeatedCompositeContainer
from typing import Tuple


def get_name(messages: RepeatedCompositeContainer, message_id: int) -> str:
    for message in messages:
        if message.id == message_id:
            return message.name


class PuzzleSolver:

    def __init__(self, puzzle: Puzzle) -> None:
        self._puzzle = puzzle
        self._n = len(self._puzzle.people)
        self._modeler = PuzzleModeler(puzzle)

    def solve(self) -> str:
        self._solver = cp_model.CpSolver()
        self._status = self._solver.Solve(self._modeler.model)
        if self._status == cp_model.OPTIMAL:
            self._set_solution()
        return self._solver.StatusName(self._status)

    @property
    def solution(self) -> Puzzle.Solution:
        return self._puzzle.solution

    def verdict(self) -> str:
        murderer_id = self._puzzle.solution.murderer_id
        victim_id = self._get_victim_id()
        room_id = self._get_room_of_person(victim_id)
        return '{murderer} murdered {victim} in the {room}!'.format(
            murderer=get_name(self._puzzle.people, murderer_id),
            victim=get_name(self._puzzle.people, victim_id),
            room=get_name(self._puzzle.crime_scene.rooms, room_id))

    def _set_solution(self) -> None:
        self._set_positions()
        self._set_murderer()

    def _set_positions(self) -> None:
        del self._puzzle.solution.positions[:]
        for person_id in range(self._n):
            row, column = self._get_position(person_id)
            position = self._puzzle.solution.positions.add(person_id=person_id)
            position.coordinate.row = row
            position.coordinate.column = column

    def _get_position(self, person_id: int) -> Tuple[int, int]:
        for row in range(self._n):
            for col in range(self._n):
                if self._solver.Value(
                        self._modeler.occupancies[person_id][row][col]):
                    return (row, col)
        raise AttributeError

    def _set_murderer(self) -> None:
        victim_id = self._get_victim_id()
        murder_room_id = self._get_room_of_person(victim_id)
        for person in self._puzzle.people:
            if (person.type == Puzzle.Person.SUSPECT and
                    self._get_room_of_person(person.id) == murder_room_id):
                self._puzzle.solution.murderer_id = person.id
                break

    def _get_victim_id(self) -> int:
        for person in self._puzzle.people:
            if person.type == Puzzle.Person.VICTIM:
                return person.id
        raise AttributeError

    def _get_room_of_person(self, person_id: int) -> int:
        coordinate = self._puzzle.solution.positions[person_id].coordinate
        room_id = self._modeler.get_room_of_coordinate(coordinate)
        return room_id
