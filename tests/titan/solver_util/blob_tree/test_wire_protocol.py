import logging
import pytest
from titan.solver_util.blob_tree import (
    BlobTree,
    BlobTreeNode,
    RandomValueFactory,
    wire_protocol
)

logger = logging.getLogger(__name__)



def gen_serialized_nodes_from_tree(tree: BlobTree):
    for node in tree.gen_nodes_in_bfs_traversal(tree.ROOT_NODE_ID):
        # figure out how big it will be
        node_buf_size = wire_protocol.Serializer.serialized_size_of_blob_tree_node(node)
        dest_buf = memoryview(bytearray(node_buf_size))
        wire_protocol.Serializer.serialize_blob_tree_node(dest_buf, node)
        yield dest_buf


def test_serialize_a_node():
    tree = RandomValueFactory.create_blob_tree(num_nodes=10)
    node = tree.get_node(5)
    # figure out how big it will be
    node_buf_size = wire_protocol.Serializer.serialized_size_of_blob_tree_node(node)
    dest_buf = memoryview(bytearray(node_buf_size))
    # serialize
    wire_protocol.Serializer.serialize_blob_tree_node(dest_buf, node)
    # deserialize into a clone
    cloned_node, bytes_read = wire_protocol.Deserializer.deserialize_blob_tree_node(dest_buf)
    # check it
    assert bytes_read == node_buf_size
    assert cloned_node == node

def test_serialize_tree():
    tree = RandomValueFactory.create_blob_tree(num_nodes=10)
    cloned_tree = BlobTree()
    for node_buf in gen_serialized_nodes_from_tree(tree):
        cloned_node, _ = wire_protocol.Deserializer.deserialize_blob_tree_node(node_buf)
        cloned_tree.add_node(cloned_node)
    assert cloned_tree == tree