from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback, OPTIMAL

from puzzle_modeler import PuzzleModeler
from puzzle_pb2 import Puzzle, Role
from google.protobuf.pyext._message import RepeatedCompositeContainer
from typing import Tuple


def get_name(messages: RepeatedCompositeContainer, message_id: int) -> str:
    for message in messages:
        if message.id == message_id:
            return message.name


class SolutionCounter(CpSolverSolutionCallback):

    def __init__(self) -> None:
        CpSolverSolutionCallback.__init__(self)
        self._solution_count = 0

    @property
    def solution_count(self) -> int:
        return self._solution_count

    def on_solution_callback(self) -> None:
        self._solution_count += 1


class PuzzleSolver:

    def __init__(self, puzzle: Puzzle, debug: bool = False) -> None:
        self._puzzle = puzzle
        self._n = len(self._puzzle.people)
        self._modeler = PuzzleModeler(puzzle, debug)

    def solve(self) -> Tuple[str, int]:
        self._solver = CpSolver()
        self._callback = SolutionCounter()
        self._status = self._solver.SearchForAllSolutions(
            self._modeler.model, self._callback)
        if self._status == OPTIMAL:
            self._set_solution()
            self._set_occupancy_repr()
        return (self._solver.StatusName(self._status),
                self._callback.solution_count)

    @property
    def occupancy_repr(self) -> Tuple[str]:
        return self._occupancy_repr

    def verdict(self) -> str:
        return '{murderer} murdered {victim} in the {room}!'.format(
            murderer=get_name(self._puzzle.people, self._murderer_id),
            victim=get_name(self._puzzle.people, self._victim_id),
            room=get_name(self._puzzle.crime_scene.rooms, self._murder_room_id))

    def _set_solution(self) -> None:
        self._set_victim()
        self._set_people_coordinates()
        self._set_murder_room()
        self._set_murderer()

    def _set_victim(self) -> int:
        for person in self._puzzle.people:
            if person.role == Role.VICTIM:
                self._victim_id = person.id
        if self._victim_id is None:
            raise AttributeError

    def _set_people_coordinates(self) -> None:
        for person in self._puzzle.people:
            row, column = self._get_person_coordinates(person.id)
            person.coordinate.row = row
            person.coordinate.column = column

    def _get_person_coordinates(self, person_id: int) -> Tuple[int, int]:
        for row in range(self._n):
            for col in range(self._n):
                if self._solver.Value(self._modeler.occupancies[person_id -
                                                                1][row][col]):
                    return (row, col)
        raise AttributeError

    def _set_murder_room(self):
        victim_coordinate = self._puzzle.people[self._victim_id - 1].coordinate
        self._murder_room_id = self._modeler.get_room_of_coordinate(
            victim_coordinate)

    def _set_murderer(self) -> None:
        for person in self._puzzle.people:
            room_id = self._modeler.get_room_of_coordinate(person.coordinate)
            if person.role == Role.SUSPECT and room_id == self._murder_room_id:
                person.role = Role.MURDERER
                self._murderer_id = person.id
                break

    def _set_occupancy_repr(self) -> None:
        self._occupancy_repr = (self._person_occupancy_repr(person_id)
                                for person_id in range(1, self._n + 1))

    def _person_occupancy_repr(self, person_id: int) -> str:
        col_labels = '   ' + ' '.join([str(col) for col in range(self._n)])
        upper_border = '  \u250C' + '\u2500' * (self._n * 2 - 1) + '\u2510'
        lower_border = '  \u2514' + '\u2500' * (self._n * 2 - 1) + '\u2518'
        rows = [
            f'{row} \u2502' + ' '.join([
                get_name(self._puzzle.people, person_id)[0] if self._solver.
                Value(self._modeler.occupancies[person_id -
                                                1][row][col]) == 1 else ' '
                for col in range(self._n)
            ]) + '\u2502'
            for row in range(self._n)
        ]
        return '\n'.join([col_labels, upper_border] + rows + [lower_border])
