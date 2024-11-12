from __future__ import annotations
import typing
import enum
import hashlib
import json
from titan.solver_util.solver_process import (
    SolverConfig
)
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence
)



class _DictHashHelper:

    @classmethod
    def consistent_hash(cls, some_dict: dict) -> str:
        m = hashlib.sha256()
        m.update(json.dumps(some_dict, sort_keys=True).encode('ascii'))
        return m.hexdigest()


class SolverType(enum.Enum):
    POSTFLOP = 'POSTFLOP'
    PREFLOP = 'PREFLOP'

class SolveMode(enum.Enum):
    PATH = 'PATH'
    SUBTREE = 'SUBTREE'
    

class SolutionTreeMeta:

    __slots__ = (   '_solve_mode',
                    '_solver_type',
                    '_action_sequence',
                    '_solver_config_key',
                    '_solution_tree_key',  )

    def __init__(self, solver_type: SolverType, solve_mode: SolveMode, action_sequence: ActionSequence,
                                                                        solver_config_key: str,
                                                                        solution_tree_key: str):
        self._solver_type = solver_type
        self._solve_mode = solve_mode
        self._action_sequence = action_sequence
        self._solver_config_key = solver_config_key
        self._solution_tree_key = solution_tree_key

    def solver_type(self) -> SolverType:
        return self._solver_type
        
    def solve_mode(self) -> SolveMode:
        return self._solve_mode
        
    def action_sequence(self) -> ActionSequence:
        return self._action_sequence
        
    def solver_config_key(self) -> str:
        return self._solver_config_key
        
    def solution_tree_key(self) -> str:
        return self._solution_tree_key

    def is_path_solve(self) -> bool:
        return (self.solve_mode() == SolveMode.PATH)

    def serialize_to_dict(self) -> dict:
        return {
            'solver_type': self.solver_type().value,
            'solve_mode': self.solve_mode().value,
            'action_sequence': str(self.action_sequence()),
            'solver_config_key': self.solver_config_key(),
            'solution_tree_key': self.solution_tree_key()
        }

    def __eq__(self, other):
        return ((type(self) == type(other)) and
                (self.solver_type() == other.solver_type()) and
                (self.solve_mode() == other.solve_mode()) and
                (self.action_sequence() == other.action_sequence()) and
                (self.solver_config_key() == other.solver_config_key()) and
                (self.solution_tree_key() == other.solution_tree_key()))

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> SolutionTreeStoreKey:
        try:
            return cls( solver_type=SolverType(some_dict['solver_type']),
                        solve_mode=SolveMode(some_dict['solve_mode']),
                        action_sequence=ActionSequence.create_from_string(some_dict['action_sequence']),
                        solver_config_key=some_dict['solver_config_key'],
                        solution_tree_key=some_dict['solution_tree_key'] )
        except KeyError as e:
            raise ValueError(f"Failed to create {cls.__name__} due to a missing field `{e}` in some_dict !")

    def hash(self) -> str:
        return _DictHashHelper.consistent_hash(self.serialize_to_dict())

    @classmethod
    def create(cls, solver_type: SolverType, is_path_solve: bool, action_sequence: ActionSequence, solver_config_key: str, solution_tree_key: str):
        return cls( solver_type=solver_type,
                    solve_mode=(SolveMode.PATH if is_path_solve else SolveMode.SUBTREE),
                    action_sequence=action_sequence,
                    solver_config_key=solver_config_key,
                    solution_tree_key=solution_tree_key )

    @classmethod
    def create_for_preflop(cls, is_path_solve: bool, action_sequence: ActionSequence, solver_config_key: str, solution_tree_key: str):
        return cls.create(  solver_type=SolverType.PREFLOP,
                            is_path_solve=is_path_solve,
                            action_sequence=action_sequence,
                            solver_config_key=solver_config_key,
                            solution_tree_key=solution_tree_key  )

    @classmethod
    def create_for_postflop(cls, is_path_solve: bool, action_sequence: ActionSequence, solver_config_key: str, solution_tree_key: str):
        return cls.create(  solver_type=SolverType.POSTFLOP,
                            is_path_solve=is_path_solve,
                            action_sequence=action_sequence,
                            solver_config_key=solver_config_key,
                            solution_tree_key=solution_tree_key  )


class SolutionTreeStoreIndexEntry:

    __slots__ = (   '_index_key',
                    '_solver_config_key',
                    '_solution_tree_key'  )

    def __init__(self, index_key: str, solver_config_key: str, solution_tree_key: str):
        self._index_key = index_key
        self._solver_config_key = solver_config_key
        self._solution_tree_key = solution_tree_key

    def index_key(self) -> str:
        return self._index_key

    def solver_config_key(self) -> str:
        return self._solver_config_key

    def solution_tree_key(self) -> str:
        return self._solution_tree_key

    def serialize_to_tuple(self):
        return (self.index_key(), self.solver_config_key(), self.solution_tree_key(), )

    def __hash__(self):
        return hash(self.serialize_to_tuple())
    
class SolutionTreeStoreIndex:

    __slots__ = (   '_index_dict',
                    '_size'  )

    def __init__(self, index_dict: dict):
        self._index_dict = index_dict

    def gen_entries(self) -> typing.Iterator[SolutionTreeStoreIndexEntry]:
        for index_key, entries in self._index_dict.items():
            yield from entries

    def gen_entries_for_key(self, index_key: str) -> typing.Iterator[SolutionTreeStoreIndexEntry]:
        try:
            yield from self._index_dict[index_key]
        except KeyError:
            raise ValueError(f"No entries for index_key `{index_key}` !")

    def size(self) -> int:
        return sum(1 for _ in self.gen_entries())
        
    def serialize_to_dict(self) -> dict:
        result = {}
        for entry in sorted(self.gen_entries(), key=lambda entry: entry.serialize_to_tuple()):
            try:
                result[entry.index_key()].append({'solver_config_key': entry.solver_config_key(), 'solution_tree_key': entry.solution_tree_key()})
            except KeyError:
                result[entry.index_key()] = [{'solver_config_key': entry.solver_config_key(), 'solution_tree_key': entry.solution_tree_key()}]
        return result

    def add_entry(self, entry: SolutionTreeStoreIndexEntry):
        try:
            self._index_dict[entry.index_key()].add(entry)
        except KeyError:
            self._index_dict[entry.index_key()] = {entry}

    @classmethod
    def create_preflop_index_key(cls, is_path_solve: bool, action_sequence: ActionSequence, solver_config_dict: dict) -> str:
        dict_to_hash = {
            'solver_type': SolverType.PREFLOP.value,
            'solve_mode': (SolveMode.PATH if is_path_solve else SolveMode.SUBTREE).value,
            'action_sequence': str(action_sequence),
            'solver_config': solver_config_dict
        }
        return _DictHashHelper.consistent_hash(dict_to_hash)

    @classmethod
    def create_postflop_index_key(cls, is_path_solve: bool, action_sequence: ActionSequence, solver_config_dict: dict) -> str:
        # make a hash that ignores solving time
        dict_to_hash = {
            'solver_type': SolverType.POSTFLOP.value,
            'solve_mode': (SolveMode.PATH if is_path_solve else SolveMode.SUBTREE).value,
            'action_sequence': str(action_sequence),
            'solver_config': {**solver_config_dict, **{'solving_time': None}}
        }
        return _DictHashHelper.consistent_hash(dict_to_hash)

    @classmethod
    def ensure_valid_dict_serialization(cls, some_dict: dict) -> bool:
        try:
            for index_key, entries in some_dict.items():
                assert (type(index_key) == str), f"index_key must be a string"
                assert (type(entries) == list), f"entries must be a list"
                for entry in entries:
                    assert type(entry) == dict, f"element `{entry}` has type `{type(entry)}` instead of the expected `dict`"
                    assert type(entry['solution_tree_key']) == str, f"entry['solution_tree_key'] `{entry['solution_tree_key']}` has type `{type(entry['solution_tree_key'])}` instead of the expected `str`"
                    assert type(entry['solver_config_key']) == str, f"entry['solver_config_key'] `{entry['solver_config_key']}` has type `{type(entry['solver_config_key'])}` instead of the expected `str`"
        except KeyError as e:
            raise ValueError(f"Field `{e}` is missing")
        except AssertionError as e:
            raise ValueError(f"Invalid dictionary for {cls.__name__}: {e}")

    @classmethod
    def create_empty(cls) -> SolutionTreeStoreIndex:
        return cls(index_dict={})

    @classmethod
    def create_from_entries(cls, entries: typing.Iterator[SolutionTreeStoreIndexEntry]) -> SolutionTreeStoreIndex:
        result = cls.create_empty()
        for entry in entries:
            result.add_entry(entry)
        return result

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> SolutionTreeStoreIndex:
        cls.ensure_valid_dict_serialization(some_dict)
        result = cls.create_empty()
        for index_key, entries in some_dict.items():
            for entry_dict in entries:
                result.add_entry(SolutionTreeStoreIndexEntry(   index_key=index_key,
                                                                solver_config_key=entry_dict['solver_config_key'],
                                                                solution_tree_key=entry_dict['solution_tree_key']  ))
        return result


    @classmethod
    def merge(cls, *indexes: SolutionTreeStoreIndex) -> SolutionTreeStoreIndex:
        result = cls.create_empty()
        for index in indexes:
            for entry in index.gen_entries():
                result.add_entry(entry)
        return result
