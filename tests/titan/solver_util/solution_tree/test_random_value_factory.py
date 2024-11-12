import logging
import pytest
import timeit
import numpy as np
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solution_tree import (
    RandomValueFactory,
    RaiseOption,
    FoldOption,
    CallOption,
    CheckOption,
    SolutionTreeException,
    SolutionTree
)


logger = logging.getLogger(__name__)



def test_create_raise_option():
    option = RandomValueFactory.create_raise_option()
    assert option is not None
    assert option.amount() > 0
    assert option.pot_size_ratio_bps() > 0

def test_create_strategy_options():
    options = RandomValueFactory.create_strategy_options(can_check=True, num_bet_sizes=4)
    assert len(options) == 6
    # check unique action strings
    assert len({option.action_string() for option in options}) == len(options)
    assert type(options[0]) == FoldOption
    assert type(options[1]) == CheckOption
    for option in options[2:]:
        assert type(option) == RaiseOption
        assert option.amount() > 0
        assert option.pot_size_ratio_bps() >= 0


def test_create_range_matrix():
    range_matrix = RandomValueFactory.create_range_matrix(num_options=4, range_size=1326)
    assert range_matrix.shape() == (1326, 4)
    assert range_matrix.values().shape == (1326, 4)

def test_create_strategy_matrix():
    for x in range(100):
        strat_matrix = RandomValueFactory.create_strategy_matrix(num_options=4, range_size=1326)
        assert strat_matrix.shape() == (1326, 4)
        assert strat_matrix.values().shape == (1326, 4)
        # check each row sums to 1
        for row in range(1326):
            assert len(strat_matrix.values()[row]) == 4        
            # sum should equal 100% (10000 bps)  or 0%
            assert np.sum(strat_matrix.values()[row]) in {0, 10000}


def test_create_ev_matrix():
    ev_matrix = RandomValueFactory.create_ev_matrix(num_options=4, range_size=1326)
    assert ev_matrix.shape() == (1326, 4)
    assert ev_matrix.values().shape == (1326, 4)


def expected_bfs_traversal_paths(tree, node):   
    to_visit = [node]
    while to_visit:
        node = to_visit.pop(0)
        yield node.action_sequence()
        for option in node.strategy_options():            
            child_action_sequence = node.action_sequence() + ActionSequence.create_from_string(option.action_string())
            try:
                to_visit.append(tree.get_node(child_action_sequence))
            except SolutionTreeException:
                break

def test_create_solution_tree():
    tree_height = 6
    num_bet_sizes = 4
    tree = RandomValueFactory.create_solution_tree( tree_height=tree_height,
                                                    range_size=1326,
                                                    num_bet_sizes=num_bet_sizes )
    bfs_nodes = list(tree.gen_nodes_in_bfs_traversal())
    num_children = num_bet_sizes + 2
    total_node_count = sum((num_children**d for d in range(tree_height + 1)))

    assert len(bfs_nodes) == total_node_count
    bfs_paths = [node.action_sequence() for node in bfs_nodes]
    expected_bfs_paths = list(expected_bfs_traversal_paths(tree, tree.root_node()))
    assert bfs_paths == expected_bfs_paths

    # check the gen_child_nodes() method
    for node in bfs_nodes:
        if (node.is_leaf_spot()):
            continue
        assert type(node.action_sequence()) == ActionSequence
        action_sequence = node.action_sequence()
        expected_child_action_sequences = [ action_sequence + ActionSequence.create_from_string(option.action_string())
                                                for option in node.strategy_options()  ]
        child_action_sequences = [n.action_sequence() for n in node.children()]
        assert expected_child_action_sequences == child_action_sequences
        # ensure correct leaf/non leaf nodes
        assert node.is_leaf_spot() == (node.depth() == tree_height)

    # the last nodes should all be leaves
    first_leaf_node_index = len(bfs_nodes) - (num_children**tree_height)
    for node in bfs_nodes[:first_leaf_node_index]:
        assert not node.is_leaf_spot()
    for node in bfs_nodes[first_leaf_node_index:]:
        assert node.is_leaf_spot()


def test_create_solution_tree_from_path():
    tree_height = 6
    num_bet_sizes = 4
    action_sequence = ActionSequence.create_from_string('ccfr200c')
    tree = RandomValueFactory.create_solution_tree_from_path(   tree_height=tree_height,
                                                                range_size=1326,
                                                                num_bet_sizes=num_bet_sizes,
                                                                action_sequence=action_sequence )

    nodes = list(tree.gen_nodes_in_bfs_traversal())
    assert len(nodes) == len(action_sequence) + 1

    for i, prefix in enumerate(action_sequence.gen_prefixes()):
        assert nodes[i].is_leaf_spot() == (nodes[i].depth() == tree_height)
        assert type(nodes[i].action_sequence()) == ActionSequence
        assert nodes[i].action_sequence() == prefix



def test_create_solution_tree_performance():

    def create_tree():
        tree_height = 7
        num_bet_sizes = 1
        tree = RandomValueFactory.create_solution_tree( tree_height=tree_height,
                                                        range_size=169,
                                                        num_bet_sizes=num_bet_sizes )

    time_msecs =  (timeit.timeit(lambda: create_tree(), number=10)/10) * 1000
    logger.info(f"Time to create the tree: {time_msecs} ms")
