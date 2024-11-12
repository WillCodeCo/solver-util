import logging
import pytest
import random
import string
import tempfile
import pathlib
from titan.solver_util.hand_history import (
    HandHistory
)
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solution_tree import (
    RandomValueFactory,
    SolutionTree,
    SolutionTreeException
)
from titan.solver_util.reports import (
    StrategyReport
)


logger = logging.getLogger(__name__)


def test_strategy_report():

    hand_history = HandHistory.create_from_dict({
        "name": "demo-hh",
        "ante_amount": 0,
        "small_blind_amount": 5,
        "big_blind_amount": 10,
        "small_blind_seat": 0,
        "big_blind_seat": 1,
        "dealer_seat": 0,
        "players": [
            {"seat": 0, "stack_size": 1000, "hole_cards": "2c3c"},
            {"seat": 1, "stack_size": 1000, "hole_cards": "2s3s"},
        ],
        "hand_history": "b5b10;r25c[QsTd4c]xx[Ts]xx[4h]xx",
    })


    solution_trees = (
        RandomValueFactory.create_solution_tree(tree_height=7,
                                                range_size=169,
                                                num_bet_sizes=1 ),
        RandomValueFactory.create_solution_tree(tree_height=2,
                                                range_size=1326,
                                                num_bet_sizes=2 ),
        RandomValueFactory.create_solution_tree(tree_height=2,
                                                range_size=1326,
                                                num_bet_sizes=2 ),
        RandomValueFactory.create_solution_tree(tree_height=2,
                                                range_size=1326,
                                                num_bet_sizes=2 ),
    )


    strategy_report = StrategyReport.create(hand_history=hand_history,
                                            solution_trees=solution_trees)

    # failed solve test
    with tempfile.TemporaryDirectory() as working_dir:

        strategy_report.save_to_filesystem(working_dir)

        assert (pathlib.Path(working_dir) / 'preflop' / 'strategy.txt').is_file()
        assert (pathlib.Path(working_dir) / 'flop' / 'strategy.txt').is_file()
        assert (pathlib.Path(working_dir) / 'turn' / 'strategy.txt').is_file()
        assert (pathlib.Path(working_dir) / 'river' / 'strategy.txt').is_file()