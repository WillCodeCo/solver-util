from __future__ import annotations
import typing
import enum
from titan.solver_util.spot_models import (
    ActionSequence,
)
from titan.solver_util.solver_process import (
    SolverConfig
)
from titan.solver_util.postflop_solver import (
    PostflopSolverConfig
)
from titan.solver_util.preflop_solver import (
    PreflopSolverConfig
)

class SolveMode(enum.Enum):
    PATH_SOLVE = 'PATH_SOLVE'
    SUBTREE_SOLVE = 'SUBTREE_SOLVE'

class BatchSolvingEntry:

    __slots__ = (   '_entry_id',
                    '_solver_config',
                    '_action_sequence',
                    '_solve_mode'  )

    def __init__(self, entry_id: str, solver_config: SolverConfig, action_sequence: ActionSequence, solve_mode: SolveMode):
        self._entry_id = entry_id
        self._solver_config = solver_config
        self._action_sequence = action_sequence
        self._solve_mode = solve_mode

    def entry_id(self) -> str:
        return self._entry_id

    def solver_config(self) -> SolverConfig:
        return self._solver_config

    def action_sequence(self) -> ActionSequence:
        return self._action_sequence

    def solve_mode(self) -> SolveMode:
        return self._solve_mode

    def is_path_solve(self) -> bool:
        return self._solve_mode == SolveMode.PATH_SOLVE

    def serialize_to_dict(self) -> dict:
        return {
            'entry_id': self.entry_id(),
            'solver_config': self.solver_config().serialize_to_dict(),
            'action_sequence': str(self.action_sequence()),
            'solve_mode': self.solve_mode().value
        }

    def __eq__(self, other):
        return ((type(self) == type(other)) and
                (self.entry_id() == other.entry_id()) and
                (self.solver_config() == other.solver_config()) and
                (self.solve_mode() == other.solve_mode()) and
                (self.action_sequence() == other.action_sequence()))

    @classmethod
    def create_for_path_solve(cls, entry_id: str, solver_config: SolverConfig, action_sequence: ActionSequence) -> BatchSolvingEntry:
        return cls( entry_id=entry_id,
                    solver_config=solver_config,
                    action_sequence=action_sequence,
                    solve_mode=SolveMode.PATH_SOLVE )

    @classmethod
    def create_for_full_tree_solve(cls, entry_id: str, solver_config: SolverConfig) -> BatchSolvingEntry:
        return cls( entry_id=entry_id,
                    solver_config=solver_config,
                    action_sequence=ActionSequence.create_empty(),
                    solve_mode=SolveMode.SUBTREE_SOLVE )

class PreflopBatchSolvingEntry(BatchSolvingEntry):

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PreflopBatchSolvingEntry:
        try:
            return cls( entry_id=some_dict['entry_id'],
                        solver_config=PreflopSolverConfig.create_from_dict(some_dict['solver_config']),
                        action_sequence=ActionSequence.create_from_string(some_dict['action_sequence']),
                        solve_mode=SolveMode(some_dict['solve_mode']) )
        except KeyError as e:
            raise ValueError(f"Failed to create {cls.__name__} since some_dict is missing field `{e}`")


class PostflopBatchSolvingEntry(BatchSolvingEntry):

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PostflopBatchSolvingEntry:
        try:
            return cls( entry_id=some_dict['entry_id'],
                        solver_config=PostflopSolverConfig.create_from_dict(some_dict['solver_config']),
                        action_sequence=ActionSequence.create_from_string(some_dict['action_sequence']),
                        solve_mode=SolveMode(some_dict['solve_mode']) )
        except KeyError as e:
            raise ValueError(f"Failed to create {cls.__name__} since some_dict is missing field `{e}`")


class BatchSolvingSpec:

    __slots__ = ('_entries',)

    def __init__(self, entries: typing.Tuple[BatchSolvingEntry, ...]):
        self._entries = entries

    def entries(self) -> typing.Tuple[BatchSolvingEntry, ...]:
        return self._entries

    def serialize_to_dict(self) -> dict:
        return {
            'entries': tuple(entry.serialize_to_dict() for entry in self.entries())
        }

    def __eq__(self, other):
        return ((type(self) == type(other)) and
                (self.entries() == other.entries()))

    @classmethod
    def merge(cls, *specs: BatchSolvingSpec) -> BatchSolvingSpec:
        return cls(entries=tuple(spec_entry for spec in specs for spec_entry in spec.entries()))


class PreflopBatchSolvingSpec(BatchSolvingSpec):

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PreflopBatchSolvingSpec:
        try:
            return cls(entries=tuple(PreflopBatchSolvingEntry.create_from_dict(entry_dict)
                                        for entry_dict in some_dict['entries']))
        except KeyError as e:
            raise ValueError(f"Failed to create {cls.__name__} since some_dict is missing field `{e}`")


class PostflopBatchSolvingSpec(BatchSolvingSpec):

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PostflopBatchSolvingSpec:
        try:
            return cls(entries=tuple(PostflopBatchSolvingEntry.create_from_dict(entry_dict)
                                        for entry_dict in some_dict['entries']))
        except KeyError as e:
            raise ValueError(f"Failed to create {cls.__name__} since some_dict is missing field `{e}`")
