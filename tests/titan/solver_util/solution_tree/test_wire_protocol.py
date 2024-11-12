import logging
import pytest
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.blob_tree import (
    BlobTreeNode
)
from titan.solver_util.solution_tree import (
    RandomValueFactory,
    SolvedSpot,
    SolutionTree,
    SolutionTreeException,
    SolutionTreeBuilder
)
from titan.solver_util.solution_tree import wire_protocol

logger = logging.getLogger(__name__)



def gen_blob_tree_nodes(tree: SolutionTree):
    node_id_lookup = {}
    for node_id, node in enumerate(tree.gen_nodes_in_bfs_traversal()):
        # serialize to a blob buffer
        blob_buf_size = wire_protocol.Serializer.serialized_size_of_solved_spot(node.solved_spot())
        blob_buf = memoryview(bytearray(blob_buf_size))
        wire_protocol.Serializer.serialize_solved_spot(blob_buf, node.solved_spot())
        # keep track of node_ids
        action_sequence = node.action_sequence()
        node_id_lookup[action_sequence] = node_id
        # figure out the parent node_id
        parent_action_sequence = action_sequence.parent()
        parent_node_id = node_id_lookup[parent_action_sequence]
        # which child index is it ?
        if node_id > 0:
            parent_node = tree.get_node(parent_action_sequence)
            child_id = str(action_sequence[-1])
        else:
            child_id = ''
        # create node
        yield BlobTreeNode( node_id=node_id,
                            parent_node_id=parent_node_id,
                            child_id=child_id,
                            blob_bytes=blob_buf  )



def test_serialize_a_node():
    tree = RandomValueFactory.create_solution_tree( tree_height=4,
                                                    range_size=1326,
                                                    num_bet_sizes=3 )
    node = tree.root_node()
    # figure out how big it will be
    node_buf_size = wire_protocol.Serializer.serialized_size_of_solved_spot(node.solved_spot())
    dest_buf = memoryview(bytearray(node_buf_size))
    # serialize
    wire_protocol.Serializer.serialize_solved_spot(dest_buf, node.solved_spot())
    # deserialize into a clone
    cloned_node, bytes_read = wire_protocol.Deserializer.deserialize_solved_spot(dest_buf)
    # check it
    assert bytes_read == node_buf_size
    assert node.strategy_options() == cloned_node.strategy_options()
    assert node.strategy_matrix() == cloned_node.strategy_matrix()
    assert node.ev_matrix() == cloned_node.ev_matrix()



def test_serialize_tree():
    tree = RandomValueFactory.create_solution_tree( tree_height=4,
                                                    range_size=1326,
                                                    num_bet_sizes=3 )
    builder = SolutionTreeBuilder()
    for i, blob_node in enumerate(gen_blob_tree_nodes(tree)):
        solved_spot, _ = wire_protocol.Deserializer.deserialize_solved_spot(blob_node.blob_bytes())
        if i == 0:
            builder.create_root_node(   node_id=blob_node.node_id(),
                                        solved_spot=solved_spot   )
        else:
            builder.create_child_node(  node_id=blob_node.node_id(),
                                        parent_node_id=blob_node.parent_node_id(),
                                        action_string=blob_node.child_id(),
                                        solved_spot=solved_spot )
    cloned_tree = builder.build_solution_tree()
    assert cloned_tree == tree