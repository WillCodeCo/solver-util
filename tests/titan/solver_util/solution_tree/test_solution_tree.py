import logging
import pytest
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solution_tree import (
    RandomValueFactory,
    SolutionTree,
    SolutionTreeException
)


logger = logging.getLogger(__name__)



def test_solution_tree():
    tree = RandomValueFactory.create_solution_tree( tree_height=4,
                                                    range_size=1326,
                                                    num_bet_sizes=3 )

    cur_node = tree.root_node()

    assert len(cur_node.strategy_options()) == 5

    assert cur_node.strategy_matrix().shape() == (1326, 5)

    # Where in the range should we look for a given hand ?
    for idx in range(1326):
        assert len(cur_node.strategy_matrix().lookup(idx)) == len(cur_node.strategy_options())
        assert len(cur_node.ev_matrix().lookup(idx)) == len(cur_node.strategy_options())


def test_solution_tree_nodes_on_path():
    tree = RandomValueFactory.create_solution_tree( tree_height=4,
                                                    range_size=1326,
                                                    num_bet_sizes=0 )

    action_sequence = ActionSequence.create_from_string('fff')
    traversed_nodes = list(tree.gen_nodes_on_path(  action_sequence=action_sequence  ))
    # all nodes on path including root node
    assert len(traversed_nodes) == 4
    # path to root should include root node as well
    assert traversed_nodes[0] == tree.root_node()

    # now do a relative path traversal
    traversed_nodes = list(tree.root_node().gen_descendants_on_path(action_sequence))
    # now this traversal should NOT include the root node
    assert traversed_nodes[0] != tree.root_node()
    assert traversed_nodes[0].action_sequence() == ActionSequence.create_from_string('f')

def test_solution_tree_bfs():
    tree = RandomValueFactory.create_solution_tree( tree_height=7,
                                                    range_size=169,
                                                    num_bet_sizes=1 )

    max_depth = 6
    nodes = list(tree.gen_nodes_in_bfs_traversal(max_depth))
    num_options = 3
    assert len(nodes) == sum((num_options**i for i in range(max_depth+1)))
    # there should be no leafs because we didnt traverse deep enough
    for n in nodes:
        assert not n.is_leaf_spot()