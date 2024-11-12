import logging
import pytest
import random
import typing
import numpy as np
from titan.solver_util import spot_models 
from titan.solver_util.spot_models import (
    BlindBet,
    SeatOrdering,
    BlindBetSequence,
    ButtonAssignment,
    BettingRound,
    Action,
    ActionSequence,
    SeatStack,
    CallAction,
    RaiseAction,
    CheckAction,
    FoldAction,
    Spot,
    PreflopBettingRound,
    FlopBettingRound,
    TurnBettingRound,
    RiverBettingRound
)
from titan.solver_util.solved_street import (
    SolvedStreet
)
from titan.solver_util import solution_tree 
from titan.solver_util.solution_tree import (
    StrategyOption,
    FoldOption,
    CallOption,
    CheckOption,
    RaiseOption,
    SolvedSpot,
)
from titan.solver_util.hand_range import (
    HandRange,
    HandComboMap,
)
from titan.solver_util.postflop_solver import (
    PlayerRange,
    PostflopRangeMap
)
from titan.solver_util.preflop_solver import (
    PreflopRangeMap
)



logger = logging.getLogger(__name__)

PREFLOP_RANGE_SIZE = 169
POSTFLOP_RANGE_SIZE = 1326


class SpotHelper:

    BETTING_ROUND_CLASSES = (   PreflopBettingRound,
                                FlopBettingRound,
                                TurnBettingRound,
                                RiverBettingRound  )

    @classmethod
    def create_new_street_spot(cls, seat_stacks: typing.Tuple[SeatStack],
                                    button_assignment: ButtonAssignment,
                                    blind_bet_sequence: BlindBetSequence,
                                    prev_action_sequences: typing.Tuple[ActionSequence]) -> Spot:
        # first spot after blinds
        cur_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )
        # rest of spots before this round
        for i, action_sequence in enumerate(prev_action_sequences):
            for cur_spot in cls.BETTING_ROUND_CLASSES[i].gen_next_spots(cur_spot, action_sequence):
                pass
            cur_spot = cls.BETTING_ROUND_CLASSES[i+1].create_initial_spot(  button_assignment=button_assignment,
                                                                            prev_spot=cur_spot )
        # last spot will be returned
        return cur_spot




class RandomSolvedSpotFactory:

    @classmethod
    def create_strategy_option(cls, action: Action) -> StrategyOption:
        if type(action) == CheckAction:
            return CheckOption()
        elif type(action) == CallAction:
            return CallOption()
        elif type(action) == FoldAction:
            return FoldOption()
        elif type(action) == RaiseAction:
            return RaiseOption( amount=action.amount(),
                                pot_size_ratio_bps = 42 ) # we don't care about pot_size_ratio !
        else:
            raise ValueError(f"Invalid type of action `{type(action)}`")

    @classmethod
    def create_random_actions_for_spot(cls, spot: Spot, include_action: Action, num_bet_sizes: int, min_raise: int):
        possible_actions = spot_models.RandomValueFactory.create_actions_for_spot(spot, num_bet_sizes, min_raise)
        if include_action not in possible_actions:
            raise_actions = possible_actions[2:-1] + (include_action,)
            raise_actions = tuple(sorted(list(raise_actions), key=lambda action: action.amount()))
            return  possible_actions[:2] + raise_actions
        return possible_actions

    @classmethod
    def create_random_solved_spot_for_spot(cls, spot: Spot, include_action: Action, num_bet_sizes: int, min_raise: int,
                                                                                                        range_size):
        possible_actions = cls.create_random_actions_for_spot(spot, include_action, num_bet_sizes, min_raise)
        options = tuple(cls.create_strategy_option(action) for action in possible_actions)

        strategy_matrix = solution_tree.RandomValueFactory.create_strategy_matrix(num_options=len(options),
                                                                    range_size=range_size)
        ev_matrix = solution_tree.RandomValueFactory.create_ev_matrix(num_options=len(options),
                                                        range_size=range_size)
        return SolvedSpot(options, strategy_matrix, ev_matrix)



    @classmethod
    def gen_solved_spots_for_spot(cls, spot: Spot, action_sequence: ActionSequence, min_raise: int, range_size: int):
        cur_spot = spot
        for action in action_sequence:
            yield cls.create_random_solved_spot_for_spot(   spot=cur_spot,
                                                            include_action=action,
                                                            num_bet_sizes=spot_models.RandomValueFactory.NUM_BET_SIZES,
                                                            min_raise=min_raise,
                                                            range_size=range_size  )
            cur_spot = BettingRound.next_spot(current_spot=cur_spot, action=action)
            if not cur_spot.has_next_seats_to_act():
                break
        yield solution_tree.RandomValueFactory.create_leaf_solved_spot()

    @classmethod
    def gen_solved_spots(cls, seat_stacks: typing.Tuple[SeatStack, ...], button_assignment: ButtonAssignment,
                                                                    blind_bet_sequence: BlindBetSequence,
                                                                    prev_action_sequences: typing.Tuple[ActionSequence, ...],
                                                                    action_sequence: ActionSequence):
        cur_spot = SpotHelper.create_new_street_spot(   seat_stacks=seat_stacks,
                                                        button_assignment=button_assignment,
                                                        blind_bet_sequence=blind_bet_sequence,
                                                        prev_action_sequences=prev_action_sequences )
        min_raise = blind_bet_sequence[1].live_amount()
        range_size = PREFLOP_RANGE_SIZE if prev_action_sequences == () else POSTFLOP_RANGE_SIZE
        yield from cls.gen_solved_spots_for_spot(   spot=cur_spot,
                                                    action_sequence=action_sequence,
                                                    min_raise=min_raise,
                                                    range_size=range_size  )






def test_random_solved_spot_factory():
    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=5000 ),
                    SeatStack(  seat=1,
                                stack_size=5000  ))
    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=0,
                                            big_blind_seat=1 )
    blind_bet_sequence = BlindBetSequence.create_from_string('b10b20')
    all_action_sequences = list(spot_models.RandomValueFactory.gen_action_sequences(seat_stacks=seat_stacks,
                                                                                    button_assignment=button_assignment,
                                                                                    blind_bet_sequence=blind_bet_sequence ))
    preflop_action_sequence = all_action_sequences[0]
    solved_spots = list(RandomSolvedSpotFactory.gen_solved_spots(   seat_stacks=seat_stacks,
                                                                    button_assignment=button_assignment,
                                                                    blind_bet_sequence=blind_bet_sequence,
                                                                    prev_action_sequences=(),
                                                                    action_sequence=preflop_action_sequence  ))

    assert len(solved_spots) == len(preflop_action_sequence) + 1 # include the leaf solved spot too
    for solved_spot, action in zip(solved_spots, preflop_action_sequence):
        try:
            chosen_option = next((option for option in solved_spot.strategy_options()
                                    if option.action_string() == str(action)))
        except StopIteration:
            pytest.fail(f"Couldn't find expected option for action {action}")
                                                


def ensure_valid_preflop_solved_street(solved_street: SolvedStreet, action_sequence: ActionSequence,
                                                            solved_spots: typing.Tuple[SolvedSpot, ...]):
    assert solved_street.is_complete()
    assert solved_street.is_final_street() == PreflopBettingRound.is_betting_over_in_hand(solved_street.last_spot())

    seat_actions = list(solved_street.gen_seat_actions())
    assert len(seat_actions) == len(action_sequence)
    #
    ## Test we get the correct strategy vector for each seat
    #
    expected_strat_vectors_for_seat = {}
    for i, (seat, action) in enumerate(seat_actions):
        option_index = next(i for i, option in enumerate(solved_spots[i].strategy_options()) if option.action_string() == str(action))        
        try:
            expected_strat_vectors_for_seat[seat].append(solved_spots[i].strategy_matrix().values()[:, option_index])
        except KeyError:
            expected_strat_vectors_for_seat[seat] = [solved_spots[i].strategy_matrix().values()[:, option_index]]
    # check it
    for seat, _ in solved_street.gen_seat_actions():
        strat_vectors_for_seat = list(solved_street.gen_strategy_vectors_for_seat(seat))
        assert len(strat_vectors_for_seat) == len(expected_strat_vectors_for_seat[seat])
        for v, vv in zip(strat_vectors_for_seat, expected_strat_vectors_for_seat[seat]):
            assert (v==vv).all()
    #
    ## Test we get the correct PlayerRange for each seat
    #
    acting_seats = solved_street.acting_seats()
    seat_player_ranges = {seat: pr for seat, pr in zip(acting_seats, solved_street.gen_flop_player_ranges(acting_seats))}
    for seat, strat_vectors in expected_strat_vectors_for_seat.items():
        for hand in HandComboMap.gen_preflop_hands():
            hand_weight = strat_vectors[0][PreflopRangeMap.index_for_hand(hand)] / PlayerRange.MAX_VALUE
            for strat_vector in strat_vectors[1:]:
                hand_weight = hand_weight * (strat_vector[PreflopRangeMap.index_for_hand(hand)] / PlayerRange.MAX_VALUE)
            hand_weight = int(round(hand_weight * PlayerRange.MAX_VALUE, 4))
            

            sum_for_hand = sum(seat_player_ranges[seat].values()[PostflopRangeMap.index_for_hand(combo)]
                                    for combo in HandComboMap.gen_combos_for_hand(hand))
            min_for_hand = min(seat_player_ranges[seat].values()[PostflopRangeMap.index_for_hand(combo)]
                                    for combo in HandComboMap.gen_combos_for_hand(hand))
            max_for_hand = max(seat_player_ranges[seat].values()[PostflopRangeMap.index_for_hand(combo)]
                                    for combo in HandComboMap.gen_combos_for_hand(hand))
            assert abs(sum_for_hand - hand_weight) < 2  # allow for small rounding errors
            assert min_for_hand == sum_for_hand // HandComboMap.num_combos_for_hand(hand)
            assert max_for_hand == (sum_for_hand // HandComboMap.num_combos_for_hand(hand)) + (sum_for_hand % HandComboMap.num_combos_for_hand(hand))



def ensure_valid_postflop_solved_street(solved_street: SolvedStreet, action_sequence: ActionSequence,
                                                            solved_spots: typing.Tuple[SolvedSpot, ...]):
    assert solved_street.is_complete()
    assert solved_street.is_final_street() == ( (BettingRound.is_betting_over_in_hand(solved_street.last_spot())) or
                                                (solved_street.street_index() == 3) and (BettingRound.is_betting_round_complete(solved_street.last_spot())) )

    seat_actions = list(solved_street.gen_seat_actions())
    assert len(seat_actions) == len(action_sequence)
    #
    ## Test we get the correct strategy vector for each seat
    #
    expected_strat_vectors_for_seat = {}
    for i, (seat, action) in enumerate(seat_actions):
        option_index = next(i for i, option in enumerate(solved_spots[i].strategy_options()) if option.action_string() == str(action))        
        try:
            expected_strat_vectors_for_seat[seat].append(solved_spots[i].strategy_matrix().values()[:, option_index])
        except KeyError:
            expected_strat_vectors_for_seat[seat] = [solved_spots[i].strategy_matrix().values()[:, option_index]]
    # check it
    for seat, _ in solved_street.gen_seat_actions():
        strat_vectors_for_seat = list(solved_street.gen_strategy_vectors_for_seat(seat))
        assert len(strat_vectors_for_seat) == len(expected_strat_vectors_for_seat[seat])
        for v, vv in zip(strat_vectors_for_seat, expected_strat_vectors_for_seat[seat]):
            assert (v==vv).all()
    #
    ## Test we get the correct PlayerRange for each seat
    #

    # start by creating some random initial ranges
    rand_1326_range_fn = lambda: np.random.uniform( low=0,
                                                    high=PlayerRange.MAX_VALUE+1,
                                                    size=(POSTFLOP_RANGE_SIZE,) ).astype(np.int32)
    acting_seats = solved_street.acting_seats()
    initial_player_ranges = tuple(PlayerRange(rand_1326_range_fn()) for _ in acting_seats)

    if solved_street.street_index() == 1:
        seat_player_ranges = {seat: pr for seat, pr in zip( acting_seats,
                                                            solved_street.gen_turn_player_ranges(acting_seats,
                                                                                                initial_player_ranges) )}
    elif solved_street.street_index() == 2:
        seat_player_ranges = {seat: pr for seat, pr in zip( acting_seats,
                                                            solved_street.gen_river_player_ranges(acting_seats,
                                                                                                initial_player_ranges) )}
    else:
        pytest.fail(f"Unexpected street_index {solved_street.street_index()}")

    for seat, initial_player_range in zip(acting_seats, initial_player_ranges):
        strat_vectors = expected_strat_vectors_for_seat[seat]
        for combo in HandComboMap.gen_all_combos():
            initial_weight = initial_player_range.values()[PostflopRangeMap.index_for_hand(combo)]
            combo_weight = strat_vectors[0][PostflopRangeMap.index_for_hand(combo)] / PlayerRange.MAX_VALUE
            for strat_vector in strat_vectors[1:]:
                combo_weight = combo_weight * (strat_vector[PostflopRangeMap.index_for_hand(combo)] / PlayerRange.MAX_VALUE)
            combo_weight = int(round((initial_weight * combo_weight), 4))
            assert abs(seat_player_ranges[seat].values()[PostflopRangeMap.index_for_hand(combo)] - combo_weight) < 2 # allow small rounding differences




def test_solved_street():
    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=5000 ),
                    SeatStack(  seat=1,
                                stack_size=5000  ))
    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=0,
                                            big_blind_seat=1 )
    blind_bet_sequence = BlindBetSequence.create_from_string('b10b20')

    for x in range(100):
        all_action_sequences = tuple(spot_models.RandomValueFactory.gen_action_sequences(seat_stacks=seat_stacks,
                                                                                        button_assignment=button_assignment,
                                                                                        blind_bet_sequence=blind_bet_sequence ))
        logger.info(f"Testing SolvedStreet for hand: {'[]'.join((str(action_sequence) for action_sequence in all_action_sequences))}")
        last_street_action_sequence = all_action_sequences[-1]
        solved_spots_gen = RandomSolvedSpotFactory.gen_solved_spots(seat_stacks=seat_stacks,
                                                                    button_assignment=button_assignment,
                                                                    blind_bet_sequence=blind_bet_sequence,
                                                                    prev_action_sequences=all_action_sequences[:-1],
                                                                    action_sequence=last_street_action_sequence)
        # use our 'solver' result and make a SolvedStreet instance
        solved_street = SolvedStreet.create_unsolved(   seat_stacks=seat_stacks,
                                                        button_assignment=button_assignment,
                                                        blind_bet_sequence=blind_bet_sequence,
                                                        action_sequences=all_action_sequences  )

        solved_spots = list(solved_spots_gen)
        assert len(solved_spots) == len(last_street_action_sequence) + 1

        i = 0
        while not solved_street.is_complete():
            if solved_street.has_next_action():
                logger.info(f"Adding solved_spot for action {solved_street.next_action()} from seat {solved_street.next_acting_seat()}")
                assert solved_street.next_action() == last_street_action_sequence[i]
            else:
                logger.info(f"Adding final leaf solved_spot")
                assert solved_spots[i].is_leaf_spot()
            solved_street.add_solved_spot(solved_spot=solved_spots[i])
            i += 1

        if solved_street.is_final_street():
            logger.info(f"Skipping range calculation since it is the final street")
            continue

        if solved_street.street_index() == 0:
            ensure_valid_preflop_solved_street(solved_street, last_street_action_sequence, solved_spots)
        else:
            ensure_valid_postflop_solved_street(solved_street=solved_street,
                                                action_sequence=last_street_action_sequence,
                                                solved_spots=solved_spots)