from __future__ import annotations
import gzip
import typing
from titan.solver_util.blob_tree import (
    BlobTreeNode
)
from titan.solver_util.solution_tree import (
    SolutionTree
)
from titan.solver_util.blob_tree.wire_protocol import (
    Serializer as BlobTreeSerializer
)
from titan.solver_util.solution_tree.wire_protocol import (
    Serializer as SolutionTreeSerializer
)

class SolutionTreeWriter:

    ROOT_NODE_ID = 0
       
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
    def write_blob_tree_node(cls, fileobj: typing.BinaryIO, blob_tree_node: BlobTreeNode):
        node_buf_size = BlobTreeSerializer.serialized_size_of_blob_tree_node(blob_tree_node)
        dest_buf = memoryview(bytearray(node_buf_size))
        BlobTreeSerializer.serialize_blob_tree_node(dest_buf, blob_tree_node)
        fileobj.write(dest_buf)

    @classmethod
    def write(cls, path: str, solution_tree: SolutionTree):
        try:
            with open(path, 'wb') as f:
                for blob_tree_node in cls.gen_blob_tree_nodes(solution_tree):
                    cls.write_blob_tree_node(f, blob_tree_node)
        except IOError as e:
            raise ValueError(f"IO Failure in {cls.__name__}.write() for path `{path}`: {e}")

    @classmethod
    def write_compressed(cls, path: str, solution_tree: SolutionTree):
        try:
            with gzip.open(path, 'wb') as f:
                for blob_tree_node in cls.gen_blob_tree_nodes(solution_tree):
                    cls.write_blob_tree_node(f, blob_tree_node)
        except IOError as e:
            raise ValueError(f"IO Failure in {cls.__name__}.write() for path `{path}`: {e}")

