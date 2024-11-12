from __future__ import annotations
import pathlib
import json
import os
from titan.solver_util.solution_tree import (
    SolutionTreeNode,
    SolutionTree,
    SolutionTreeException,
    SolutionTreeBuilder
)
from titan.solver_util.blob_tree import (
    BlobTreeNode
)

from titan.solver_util.blob_tree.wire_protocol import (
    Deserializer as BlobTreeDeserializer,
    Serializer as BlobTreeSerializer
)
from titan.solver_util.solution_tree.wire_protocol import (
    Deserializer as SolutionTreeDeserializer,
    Serializer as SolutionTreeSerializer
)


class SolverResult:

    __slots__ = (   '_log_lines',
                    '_output_lines',
                    '_error_lines',
                    '_event_dicts' )

    def __init__(self, log_lines: typing.Tuple[str, ...], output_lines: typing.Tuple[str, ...],
                                                        error_lines: typing.Tuple[str, ...],
                                                        event_dicts: typing.Tuple[dict, ...]):
        self._log_lines = log_lines
        self._output_lines = output_lines
        self._error_lines = error_lines
        self._event_dicts = event_dicts

    def log_lines(self):
        return self._error_lines

    def output_lines(self):
        return self._output_lines

    def error_lines(self):
        return self._error_lines

    def event_dicts(self):
        return self._event_dicts

    def __eq__(self, other):
        return (type(other) == type(self) and
                other.log_lines() == self.log_lines() and
                other.output_lines() == self.output_lines() and
                other.error_lines() == self.error_lines() and
                other.event_dicts() == self.event_dicts())

    def __hash__(self):
        return hash((self.log_lines(), self.output_lines(), self.error_lines(), self.event_dicts()))



class FailedSolve(SolverResult):

    __slots__ = ('_exception_msg',)

    def __init__(self, log_lines: typing.Tuple[str, ...], output_lines: typing.Tuple[str, ...],
                                                        error_lines: typing.Tuple[str, ...],
                                                        event_dicts: typing.Tuple[dict, ...],
                                                        exception_msg: str):
        super().__init__(   log_lines=log_lines,
                            output_lines=output_lines,
                            error_lines=error_lines,
                            event_dicts=event_dicts  )
        self._exception_msg = exception_msg

    def exception_msg(self):
        return self._exception_msg

    def __eq__(self, other):
        return (super().__eq__(other) and
                other.exception_msg() == self.exception_msg())

    def __hash__(self):
        return hash((super().__hash__(), self.exception_msg()))


class CompletedSolve(SolverResult):

    __slots__ = ('_solution_tree',)

    def __init__(self, log_lines: typing.Tuple[str, ...], output_lines: typing.Tuple[str, ...],
                                                        error_lines: typing.Tuple[str, ...],
                                                        event_dicts: typing.Tuple[dict, ...],
                                                        solution_tree: SolutionTree):
        super().__init__(   log_lines=log_lines,
                            output_lines=output_lines,
                            error_lines=error_lines,
                            event_dicts=event_dicts  )
        self._solution_tree = solution_tree

    def solution_tree(self):
        return self._solution_tree

    def __eq__(self, other):
        return (super().__eq__(other) and other.solution_tree() == self.solution_tree())

    def __hash__(self):
        return hash((super().__hash__(), self.solution_tree()))



class MetadataSerializer:
    
    @classmethod
    def write_dict_to_file(cls, path: str, some_dict: dict):
        with open(path, 'w') as f:
            json.dump(some_dict, f, indent=4)

    @classmethod
    def serialize_to_filesystem(cls, path: str, metadata_name: str, metadata: dict):
        cls.write_dict_to_file(pathlib.Path(path) / f"{metadata_name}.json", metadata)


class MetadataDeserializer:

    @classmethod
    def is_metadata_path(cls, path: str) -> bool:
        p = pathlib.Path(path)
        return p.is_file() and p.suffix == 'json'


    @classmethod
    def read_dict_from_file(cls, path: str):
        with open(path, 'r') as f:
            return json.load(f)

    @classmethod
    def deserialize_from_filesystem(cls, path: str, metadata_name: str) -> SolverResult:
        try:
            return cls.read_dict_from_file(pathlib.Path(path) / f"{metadata_name}.json")
        except FileNotFoundError as e:
            raise ValueError(f"Failed to deserialize_from_filesystem() due to missing file: {e}")


class SolverResultSerializer:
    

    @classmethod
    def write_lines_to_file(cls, path: str, lines: typing.Tuple[str, ...]):
        with open(path, 'w') as f:
            for l in lines:
                f.write(l + os.linesep)

    @classmethod
    def write_dicts_to_file(cls, path: str, dicts: typing.Tuple[dict, ...]):
        cls.write_lines_to_file(path, (json.dumps(d) for d in dicts))


    @classmethod
    def gen_blob_tree_nodes(cls, solution_tree: SolutionTree):
        node_id_lookup = {}
        for node_id, node in enumerate(solution_tree.gen_nodes_in_bfs_traversal()):
            # serialize to a blob buffer
            blob_buf_size = SolutionTreeSerializer.serialized_size_of_solved_spot(node.solved_spot())
            blob_buf = memoryview(bytearray(blob_buf_size))
            SolutionTreeSerializer.serialize_solved_spot(blob_buf, node.solved_spot())
            # keep track of node_ids
            action_sequence = node.action_sequence()
            node_id_lookup[action_sequence] = node_id
            # figure out the parent node_id
            parent_action_sequence = action_sequence.parent()
            parent_node_id = node_id_lookup[parent_action_sequence]
            # which child index is it ?
            if node_id > 0:
                parent_node = solution_tree.get_node(parent_action_sequence)
                child_id = str(action_sequence[-1])
            else:
                child_id = ''
            # create node
            yield BlobTreeNode( node_id=node_id,
                                parent_node_id=parent_node_id,
                                child_id=child_id,
                                blob_bytes=blob_buf  )


    @classmethod
    def write_solution_tree(cls, path: str, solution_tree: SolutionTree):
        with open(path, 'wb') as f:
            for blob_tree_node in cls.gen_blob_tree_nodes(solution_tree):
                # figure out how big it will be
                node_buf_size = BlobTreeSerializer.serialized_size_of_blob_tree_node(blob_tree_node)
                dest_buf = memoryview(bytearray(node_buf_size))
                BlobTreeSerializer.serialize_blob_tree_node(dest_buf, blob_tree_node)
                f.write(dest_buf)

    @classmethod
    def serialize_to_filesystem(cls, path: str, solver_result: SolverResult):
        p = pathlib.Path(path)
        cls.write_lines_to_file(p / 'log.txt', solver_result.log_lines())
        cls.write_lines_to_file(p / 'output.txt', solver_result.output_lines())
        cls.write_lines_to_file(p / 'error.txt', solver_result.error_lines())
        cls.write_dicts_to_file(p / 'events.jsonl', solver_result.event_dicts())
        if type(solver_result) == FailedSolve:
            cls.write_lines_to_file(p / 'exception.txt', (solver_result.exception_msg(),))
        elif type(solver_result) == CompletedSolve:
            cls.write_solution_tree(p / 'solution-tree.bin', solver_result.solution_tree())
        else:
            raise ValueError(f"Unexpected soler_result type `{type(solver_result)}` !")

class SolverResultDeserializer:

    ROOT_NODE_ID = 0
    
    @classmethod
    def gen_lines_from_file(cls, path: str):
        with open(path, 'r') as f:
            for l in f.readlines():
                yield l.rstrip(os.linesep)

    @classmethod
    def gen_event_dicts_from_file(cls, path: str):
        yield from (json.loads(line) for line in cls.gen_lines_from_file(path))

    @classmethod
    def gen_blob_tree_nodes_from_file(cls, path: str):
        with open(path, 'rb') as f:
            src_buffer = memoryview(f.read())
            offset = 0
            while offset < len(src_buffer):
                node, bytes_read = BlobTreeDeserializer.deserialize_blob_tree_node(src_buffer[offset:])
                offset += bytes_read
                yield node

    @classmethod
    def gen_solution_tree_nodes(cls, path: str, builder: SolutionTreeBuilder):
        for blob_node in cls.gen_blob_tree_nodes_from_file(path):
            solved_spot, _ = SolutionTreeDeserializer.deserialize_solved_spot(blob_node.blob_bytes())
            # root node ?
            if blob_node.node_id() == cls.ROOT_NODE_ID:
                yield builder.create_root_node( node_id=blob_node.node_id(),
                                                solved_spot=solved_spot )
            else:
                yield builder.create_child_node(node_id=blob_node.node_id(),
                                                parent_node_id=blob_node.parent_node_id(),
                                                action_string=blob_node.child_id(),
                                                solved_spot=solved_spot)

    @classmethod
    def read_solution_tree(cls, path: str) -> SolutionTree:
        builder = SolutionTreeBuilder()
        for solution_tree_node in cls.gen_solution_tree_nodes(path, builder):
            pass
        return builder.build_solution_tree()



    @classmethod
    def is_solver_result_path(cls, path: str) -> bool:
        p = pathlib.Path(path)
        return (    ((p / 'log.txt').is_file()) and
                    ((p / 'output.txt').is_file()) and
                    ((p / 'error.txt').is_file()) and
                    ((p / 'events.jsonl').is_file()) and
                    ((p / 'solution-tree.bin').is_file() or ((p / 'exception.txt').is_file()))  )


    @classmethod
    def deserialize_from_filesystem(cls, path: str) -> SolverResult:
        p = pathlib.Path(path)
        try:
            log_lines = tuple(cls.gen_lines_from_file(p / 'log.txt'))
            output_lines = tuple(cls.gen_lines_from_file(p / 'output.txt'))
            error_lines = tuple(cls.gen_lines_from_file(p / 'error.txt'))
            event_dicts = tuple(cls.gen_event_dicts_from_file(p / 'events.jsonl'))

            if (p / 'exception.txt').is_file():
                exception_msg = '\n'.join(cls.gen_lines_from_file(p / 'exception.txt'))
                return FailedSolve( log_lines=log_lines,
                                    output_lines=output_lines,
                                    error_lines=error_lines,
                                    event_dicts=event_dicts,
                                    exception_msg=exception_msg )
            else:
                solution_tree = cls.read_solution_tree(p / 'solution-tree.bin')
                return CompletedSolve(  log_lines=log_lines,
                                        output_lines=output_lines,
                                        error_lines=error_lines,
                                        event_dicts=event_dicts,
                                        solution_tree=solution_tree  )
        except FileNotFoundError as e:
            raise ValueError(f"Failed to deserialize_from_filesystem() due to missing file: {e}")





class SolvingSession:

    def __init__(self, path: str):
        self._path = path

    def path(self) -> str:
        return self._path

    def has_child(self, child_name: str) -> bool:
        return (pathlib.Path(self.path()) / child_name).is_dir()

    def gen_solver_result_names(self):
        for child_path in pathlib.Path(self.path()).iterdir():
            if child_path.is_dir():
                if SolverResultDeserializer.is_solver_result_path(child_path):
                    yield child_path.name

    def gen_solving_session_names(self):
        for child_path in pathlib.Path(self.path()).iterdir():
            if child_path.is_dir():
                if not SolverResultDeserializer.is_solver_result_path(child_path):
                    yield child_path.name

    def gen_metadata_names(self):
        for sub_path in pathlib.Path(self.path()).iterdir():
            if SolverResultDeserializer.is_metadata_path(sub_path):
                yield sub_path.name

    def get_solver_result(self, child_name: str) -> SolverResult:
        child_path = pathlib.Path(self.path()) / child_name
        return SolverResultDeserializer.deserialize_from_filesystem(child_path)

    def get_solving_session(self, child_name: str) -> SolvingSession:
        child_path = pathlib.Path(self.path()) / child_name
        return SolvingSession.create_from_path(child_path)

    def get_metadata(self, metadata_name: str) -> dict:
        return MetadataDeserializer.deserialize_from_filesystem(self.path(), metadata_name)

    def add_solver_result(self, child_name: str, solver_result: SolverResult):
        if self.has_child(child_name):
            raise ValueError(f"Cannot add_solver_result() because `{child_name}` already exists !")
        # create directory
        child_path = pathlib.Path(self.path()) / child_name
        child_path.mkdir()
        # serialize to files
        SolverResultSerializer.serialize_to_filesystem(child_path, solver_result)

    def add_metadata(self, metadata_name: str, metadata: dict):
        # create file
        MetadataSerializer.serialize_to_filesystem(self.path(), metadata_name, metadata)

    def create_solving_session(self, child_name: str):
        if self.has_child(child_name):
            raise ValueError(f"Cannot create_solving_session() because `{child_name}` already exists !")
        # create directory
        child_path = pathlib.Path(self.path()) / child_name
        child_path.mkdir()
        return SolvingSession(child_path)

    @classmethod
    def create_from_path(cls, path: str) -> SolvingSession:
        p = pathlib.Path(path)
        if not p.is_dir():
            raise ValueError(f"Cannot call {cls.__name__}.create_from_path() for a path `{path}` that does not represent a directory")
        elif not any(p.iterdir()):
            raise ValueError(f"Cannot call {cls.__name__}.create_from_path() for empty directory `{path}`")
        return cls(path)
        
    @classmethod
    def create_empty(cls, path: str) -> SolvingSession:
        p = pathlib.Path(path)
        if not p.is_dir():
            raise ValueError(f"Cannot call {cls.__name__}.create_empty() for a path `{path}` that does not represent a directory")
        elif any(p.iterdir()):
            raise ValueError(f"Cannot call {cls.__name__}.create_empty() for non-empty directory `{path}`")
        return cls(path)


