import logging
import pytest
from titan.solver_util.blob_tree import (
    RandomValueFactory
)


logger = logging.getLogger(__name__)


def test_create_nodes():
    nodes = RandomValueFactory.create_blob_tree_nodes(10)
    assert len(nodes) == 10


def test_create_tree():
    tree = RandomValueFactory.create_blob_tree(num_nodes=10)
    assert len(list(tree.gen_nodes_in_bfs_traversal(tree.ROOT_NODE_ID))) == 10

