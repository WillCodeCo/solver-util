from __future__ import annotations
import gzip
import typing
import pathlib
from titan.solver_util.blob_tree import (
    BlobTreeNode
)
from titan.solver_util.solution_tree import (
    SolutionTree,
    SolutionTreeBuilder
)
from titan.solver_util.blob_tree.wire_protocol import (
    Deserializer as BlobTreeDeserializer
)
from titan.solver_util.solution_tree.wire_protocol import (
    Deserializer as SolutionTreeDeserializer
)



class SolutionTreeReader:

    ROOT_NODE_ID = 0
    
    @classmethod
    def gen_blob_tree_nodes_from_file_obj(cls, fileobj: typing.BinaryIO):
        src_buffer = memoryview(fileobj.read())
        offset = 0
        while offset < len(src_buffer):
            node, bytes_read = BlobTreeDeserializer.deserialize_blob_tree_node(src_buffer[offset:])
            offset += bytes_read
            yield node

    @classmethod
    def gen_blob_tree_nodes_from_gzip_file(cls, path_to_gzip_file: str):
        with gzip.open(path_to_gzip_file, 'rb') as fileobj:
            yield from cls.gen_blob_tree_nodes_from_file_obj(fileobj)

    @classmethod
    def gen_blob_tree_nodes_from_file(cls, path: str):
        with open(path, 'rb') as f:
            yield from cls.gen_blob_tree_nodes_from_file_obj(f)

    @classmethod
    def gen_solution_tree_nodes(cls, blob_tree_nodes: typing.Iterator[BlobTreeNode], builder: SolutionTreeBuilder):
        for blob_node in blob_tree_nodes:
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
    def read(cls, path: str) -> SolutionTree:
        try:
            builder = SolutionTreeBuilder()
            for solution_tree_node in cls.gen_solution_tree_nodes(  blob_tree_nodes=cls.gen_blob_tree_nodes_from_file(path),
                                                                    builder=builder ):            
                pass
            return builder.build_solution_tree()
        except IOError as e:
            raise ValueError(f"IO Failure in {cls.__name__}.load() for path `{path}`: {e}")

    @classmethod
    def read_compressed(cls, path: str) -> SolutionTree:
        try:
            builder = SolutionTreeBuilder()
            for solution_tree_node in cls.gen_solution_tree_nodes(  blob_tree_nodes=cls.gen_blob_tree_nodes_from_gzip_file(path),
                                                                    builder=builder ):            
                pass
            return builder.build_solution_tree()
        except IOError as e:
            raise ValueError(f"IO Failure in {cls.__name__}.load() for path `{path}`: {e}")
