import logging
import pytest
from titan.solver_util.blob_tree import (
    RandomValueFactory,
    BlobTree
)


logger = logging.getLogger(__name__)


def test_blob_tree():
    nodes = RandomValueFactory.create_blob_tree_nodes(10)

    tree = BlobTree()

    for node in nodes:
        tree.add_node(node)

    # check parent/child relationship
    for node in nodes:
        expected_child_node_ids = {n.node_id() for n in nodes
                                        if ((n.node_id() != tree.ROOT_NODE_ID) and
                                            (n.parent_node_id() == node.node_id()))}
        found_child_node_ids = {n.node_id() for n in tree.gen_child_nodes(node.node_id())}
        assert expected_child_node_ids == found_child_node_ids

    bfs_node_ids = {n.node_id() for n in tree.gen_nodes_in_bfs_traversal(tree.ROOT_NODE_ID)}
    assert bfs_node_ids == set(range(10))


