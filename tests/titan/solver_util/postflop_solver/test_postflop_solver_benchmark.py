import json
import logging
import pytest
import random
import typing
from titan.solver_util import spot_models
from titan.solver_util import solution_tree
from titan.solver_util.hand_range import (
    HandComboMap
)
from titan.solver_util.postflop_solver import (
    PostflopSolverConfig,
    PlayerRange,
    SolveTreeSpec,
    SolveAlgorithm,
    PostflopSolverBenchmark,
    PostflopSolverBenchmarkFactory
)


logger = logging.getLogger(__name__)


def create_seat_stacks(deal_order_stack_sizes) -> typing.Tuple[spot_models.SeatStack]:
    return tuple((  spot_models.SeatStack(  seat=seat,
                                            stack_size=stack_size  )
                        for seat, stack_size in enumerate(deal_order_stack_sizes)  ))


def create_button_assignment(num_seats) -> spot_models.ButtonAssignment:
    if num_seats == 2:
        # special headsup rule
        btn_sb_seat = 1
        return spot_models.ButtonAssignment(dealer_seat=btn_sb_seat,
                                            big_blind_seat=0,
                                            small_blind_seat=btn_sb_seat)
    else:
        return spot_models.ButtonAssignment(dealer_seat=(num_seats - 1), # last seat is dealer
                                            big_blind_seat=1,
                                            small_blind_seat=0)

def create_blind_bet_sequence(num_seats):
    return spot_models.BlindBetSequence.create_default( num_seats=num_seats,
                                                        big_blind_amount=100,
                                                        small_blind_amount=50,
                                                        ante_amount=50,
                                                        has_small_blind=True,
                                                        num_straddles=0  )


def create_random_action_sequences(deal_order_stack_sizes, button_assignment, blind_bet_sequence):
    num_seats = len(deal_order_stack_sizes)
    action_sequences = []
    # make sure flop sequence is generated too
    while len(action_sequences) < 2:
        action_sequences = tuple(spot_models.RandomValueFactory.gen_action_sequences(   seat_stacks=create_seat_stacks(deal_order_stack_sizes),
                                                                                        button_assignment=create_button_assignment(num_seats),
                                                                                        blind_bet_sequence=blind_bet_sequence  ))
    return action_sequences



def create_random_stacks():
    num_seats = random.randint(2, 4)
    return tuple(random.randint(1000, 5000) for _ in range(num_seats))

def create_random_config(deal_order_stack_sizes, blind_bet_sequence, action_sequences):
    return PostflopSolverConfig(solve_tree_spec=SolveTreeSpec.create_empty(), # doesnt matter here,
                                num_threads=64,
                                solving_time=30,
                                deal_order_stack_sizes=deal_order_stack_sizes,
                                big_blind_amount=100,
                                blind_bet_sequence=blind_bet_sequence,
                                preflop_action_sequence=action_sequences[0],
                                flop_action_sequence=action_sequences[1] if len(action_sequences) > 1 else spot_models.ActionSequence.create_empty(),
                                turn_action_sequence=action_sequences[2] if len(action_sequences) > 2 else spot_models.ActionSequence.create_empty(),
                                community_cards=('2s', '5d', 'Jh'),
                                player_ranges=tuple(PlayerRange.create_uniform() for _ in deal_order_stack_sizes),
                                solve_algorithm=SolveAlgorithm.DEFAULT)


def create_random_player_hole_cards(num_players: int):
    return random.sample(list(HandComboMap.gen_all_combos()), k=num_players)

def create_solver_config_solution_tree():
    deal_order_stack_sizes = create_random_stacks()
    blind_bet_sequence = create_blind_bet_sequence(num_seats=len(deal_order_stack_sizes))
    button_assignment = create_button_assignment(num_seats=len(deal_order_stack_sizes))
    action_sequences = create_random_action_sequences(deal_order_stack_sizes, button_assignment, blind_bet_sequence)
    prev_action_sequences = action_sequences[:-1]
    last_action_sequence = action_sequences[-1]
    solver_config = create_random_config(deal_order_stack_sizes, blind_bet_sequence, prev_action_sequences)
    tree = solution_tree.RandomValueFactory.create_solution_tree_from_path( tree_height=len(last_action_sequence),
                                                                            range_size=1326,
                                                                            num_bet_sizes=3,
                                                                            action_sequence=last_action_sequence  )
    return (solver_config, tree)

def test_postflop_solver_benchmark():
    benchmark_factory = PostflopSolverBenchmarkFactory()
    solver_configs = []
    trees = []
    for i in range(30):
        (solver_config, tree) = create_solver_config_solution_tree()
        solver_configs.append(solver_config)
        trees.append(tree)
        num_players = len(solver_config.deal_order_stack_sizes())
        benchmark_factory.add_benchmark_entry(  solver_config=solver_config,
                                                solution_tree=tree,
                                                deal_order_hole_cards=create_random_player_hole_cards(num_players)  )
    # check benchmark is good
    postflop_solver_benchmark = benchmark_factory.postflop_solver_benchmark()

    for tree, entry in zip(trees, postflop_solver_benchmark.entries()):

        solved_spot_extract_lookup = dict(zip(entry.action_sequences(), entry.solved_spot_extracts()))

        for action_sequence in solved_spot_extract_lookup.keys():

            logger.info(f"testing solved_spot_extract for spot `{action_sequence}`")
            strategy_options = tree.get_node(action_sequence).solved_spot().strategy_options()
            ev_matrix = tree.get_node(action_sequence).solved_spot().ev_matrix()
            strat_matrix = tree.get_node(action_sequence).solved_spot().strategy_matrix()

            assert len(strategy_options) > 0
            assert len(solved_spot_extract_lookup[action_sequence].ev_matrix_rows()) > 0
            assert len(solved_spot_extract_lookup[action_sequence].strategy_matrix_rows()) > 0
            assert strategy_options == solved_spot_extract_lookup[action_sequence].strategy_options()
            for ev_matrix_row in solved_spot_extract_lookup[action_sequence].ev_matrix_rows():
                assert tuple(ev_matrix.lookup(ev_matrix_row.index())) == ev_matrix_row.values()
            for strat_matrix_row in solved_spot_extract_lookup[action_sequence].strategy_matrix_rows():
                assert tuple(strat_matrix.lookup(strat_matrix_row.index())) == strat_matrix_row.values()

    cloned_postflop_solver_benchmark = PostflopSolverBenchmark.create_from_dict(json.loads(json.dumps(postflop_solver_benchmark.serialize_to_dict())))
    # make sure it is equal
    assert cloned_postflop_solver_benchmark == postflop_solver_benchmark