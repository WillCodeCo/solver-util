from __future__ import annotations
import logging
import typing
import numpy as np
from numpy import typing as npt
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence,
    ButtonAssignment,
    SeatStack,
    Action,
    CheckAction,
    CallAction,
    FoldAction,
    RaiseAction,
    Spot,
    BettingRound,
    PreflopBettingRound,
    FlopBettingRound,
    TurnBettingRound,
    RiverBettingRound
)
from titan.solver_util.solution_tree import (
    SolvedSpot,
    StrategyOption,
    CheckOption,
    CallOption,
    FoldOption,
    RaiseOption,
)
from titan.solver_util.hand_range import (
    HandRange,
    HandComboMap,
    PreflopHandRange,
    PostflopHandRange,
    HandRangeEntry
)
from titan.solver_util.postflop_solver import (
    PlayerRange,
    PostflopRangeMap
)
from titan.solver_util.preflop_solver import (
    PreflopRangeMap
)

logger = logging.getLogger(__name__)




class _SpotModelHelper:

    BETTING_ROUND_CLASSES = (   PreflopBettingRound,
                                FlopBettingRound,
                                TurnBettingRound,
                                RiverBettingRound  )

    PREFLOP_STREET_INDEX = 0
    FLOP_STREET_INDEX = 1
    TURN_STREET_INDEX = 2
    RIVER_STREET_INDEX = 3

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
            for cur_spot in BettingRound.gen_next_spots(cur_spot, action_sequence):
                pass
            cur_spot = cls.BETTING_ROUND_CLASSES[i+1].create_initial_spot(  button_assignment=button_assignment,
                                                                            prev_spot=cur_spot )
        # last spot will be returned
        return cur_spot


class SolvedStreetSpot:

    @classmethod
    def create_action_from_strategy_option(cls, strategy_option: StrategyOption) -> Action:
        if type(strategy_option) == CheckOption:
            return CheckAction()
        elif type(strategy_option) == CallOption:
            return CallAction()
        elif type(strategy_option) == FoldOption:
            return FoldAction()
        elif type(strategy_option) == RaiseOption:
            return RaiseAction(amount=strategy_option.amount())
        else:
            raise ValueError(f"Invalid type of strategy_option `{type(strategy_option)}`")

    @classmethod
    def next_actions(cls, strategy_options: typing.Tuple[StrategyOption, ...]) -> typing.Tuple[Action, ...]:
        return tuple(cls.create_action_from_strategy_option(so) for so in strategy_options)

    @classmethod
    def strategy_vector_for_action(cls, solved_spot: SolvedSpot, target_action: Action) -> npt.NDArray[np.int32]:
        try:
            actions = cls.next_actions(solved_spot.strategy_options())
            option_index = next(i for i, action in enumerate(actions) if action == target_action)
            return solved_spot.strategy_matrix().values()[:, option_index]
        except StopIteration:
            raise ValueError(f"Failed to find action {target_action} in SolvedStreetSpot({actions})!")

        

class SolvedStreet:

    __slots__ = (   '_street_index',
                    '_action_sequence',
                    '_spots',
                    '_solved_spots'  )

    def __init__(self, street_index: int, action_sequence: ActionSequence, spots: typing.Iterator[Spot], solved_spots: typing.Iterator[SolvedSpot]):
        self._street_index = street_index
        self._action_sequence = action_sequence
        self._spots = tuple(spots)
        self._solved_spots = list(solved_spots)

    def street_index(self):
        return self._street_index

    def action_sequence(self):
        return self._action_sequence

    def spots(self):
        return self._spots

    def solved_spots(self):
        return self._solved_spots

    def last_spot(self) -> Spot:
        return self._spots[-1]

    def add_solved_spot(self, solved_spot: SolvedSpot):
        self._solved_spots.append(solved_spot)

    def is_complete(self) -> bool:
        # the last solved spot should be a leaf !
        return (self.solved_spots()) and (self.solved_spots()[-1].is_leaf_spot())

    def next_unsolved_spot(self) -> Spot:
        if self.is_complete():
            raise ValueError(f"SolvedStreet does not have any unsolved spots because it is complete !")
        return self._spots[len(self.solved_spots())]

    def next_acting_seat(self) -> int:
        if self.is_complete():
            raise ValueError(f"SolvedStreet does not have a next_acting_seat because it is complete !")
        return self.next_unsolved_spot().next_seats_to_act()[0]

    def has_next_action(self) -> bool:
        return (    (not self.is_complete()) and
                    (not BettingRound.is_betting_round_complete(self.next_unsolved_spot())) and
                    (not BettingRound.is_betting_over_in_hand(self.next_unsolved_spot()))  )

    def next_action(self) -> Action:
        if self.is_complete():
            raise ValueError(f"SolvedStreet does not have a next_action because it is complete !")
        return self.action_sequence()[len(self.solved_spots())]

    def is_final_street(self) -> bool:
        if (not self.is_complete()):
            raise ValueError(f"SolvedStreet must be completed before we can know if it is the final street or not !")
        return (    (self.street_index() == _SpotModelHelper.RIVER_STREET_INDEX)  or
                    (BettingRound.is_betting_over_in_hand(self.last_spot()))   )

    def gen_seat_actions(self):
        for spot, action in zip(self.spots(), self.action_sequence()):
            yield (spot.next_seats_to_act()[0], action)

    def acting_seats(self):
        return {seat for seat, _ in self.gen_seat_actions()}

    def gen_strategy_vectors_for_seat(self, target_seat: int):
        for (seat, action), solved_spot in zip(self.gen_seat_actions(), self.solved_spots()):
            if seat == target_seat:
                yield SolvedStreetSpot.strategy_vector_for_action(solved_spot, action)

    def gen_reach_coeff_array_for_seat(self, seat: int):
        strategy_vector_gen = self.gen_strategy_vectors_for_seat(seat)
        result = (next(strategy_vector_gen) / HandRangeEntry.MAX_WEIGHT).astype(np.float32)
        yield result
        for strategy_vector in strategy_vector_gen:
            norm_strategy_vector = (strategy_vector / HandRangeEntry.MAX_WEIGHT).astype(np.float32)
            np.multiply(result, norm_strategy_vector, result)
            yield result
        return result

    def create_reach_coeff_array_for_seat(self, seat: int):
        reach_coeff_array = None
        for reach_coeff_array in self.gen_reach_coeff_array_for_seat(seat):
            pass
        if reach_coeff_array is None:
            raise ValueError(f"Created an invalid reach_coeff_array for seat {seat} !")
        return reach_coeff_array

    def create_flop_player_range(self, reach_coeff_array: npt.NDArray[np.float32]) -> PlayerRange:
        if self.street_index() != _SpotModelHelper.PREFLOP_STREET_INDEX:
            raise ValueError(f"Cannot create FLOP player range when SolvedStreet does not represent the PREFLOP street !")
        hand_range = PreflopHandRange.create_from_normalized_hands_and_weights( hands=PreflopRangeMap.gen_hands(),
                                                                                normalized_weights=reach_coeff_array )
        return PlayerRange.create_from_hand_range(hand_range)


    def create_turn_river_player_range(self, reach_coeff_array: npt.NDArray[np.float32],
                                            initial_player_range: PlayerRange) -> PlayerRange:
        return PlayerRange(np.multiply(reach_coeff_array, initial_player_range.values()).astype(np.int32))

    def gen_flop_player_ranges(self, seats: typing.Iterator[int]):
        if self.street_index() != _SpotModelHelper.PREFLOP_STREET_INDEX:
            raise ValueError(f"Cannot gen_flop_player_ranges when SolvedStreet does not represent the PREFLOP street !")
        for seat in seats:
            yield self.create_flop_player_range(self.create_reach_coeff_array_for_seat(seat))

    def gen_turn_player_ranges(self, seats: typing.Iterator[int], player_ranges: typing.Iterator[PlayerRange]):
        if self.street_index() != _SpotModelHelper.FLOP_STREET_INDEX:
            raise ValueError(f"Cannot gen_turn_player_ranges when SolvedStreet does not represent the FLOP street !")
        for seat, player_range in zip(seats, player_ranges):
            yield self.create_turn_river_player_range(self.create_reach_coeff_array_for_seat(seat), player_range)

    def gen_river_player_ranges(self, seats: typing.Iterator[int], player_ranges: typing.Iterator[PlayerRange]):
        if self.street_index() != _SpotModelHelper.TURN_STREET_INDEX:
            raise ValueError(f"Cannot gen_river_player_ranges when SolvedStreet does not represent the TURN street !")
        for seat, player_range in zip(seats, player_ranges):
            yield self.create_turn_river_player_range(self.create_reach_coeff_array_for_seat(seat), player_range)



    @classmethod
    def create(cls, seat_stacks: typing.Tuple[SeatStack], button_assignment: ButtonAssignment,
                                                            blind_bet_sequence: BlindBetSequence,
                                                            action_sequences: typing.Tuple[ActionSequence],
                                                            solved_spots: typing.Tuple[SolvedSpot, ...]) -> SolvedStreet:
        initial_spot = _SpotModelHelper.create_new_street_spot( seat_stacks,
                                                                button_assignment,
                                                                blind_bet_sequence,
                                                                action_sequences[:-1] )
        spots = (initial_spot,) + tuple(BettingRound.gen_next_spots(initial_spot, action_sequences[-1]))
        return cls( street_index=len(action_sequences) - 1,
                    action_sequence=action_sequences[-1],
                    spots=spots,
                    solved_spots=solved_spots )

    @classmethod
    def create_unsolved(cls, seat_stacks: typing.Tuple[SeatStack], button_assignment: ButtonAssignment,
                                                                blind_bet_sequence: BlindBetSequence,
                                                                action_sequences: typing.Tuple[ActionSequence]) -> SolvedStreet:
        return cls.create(  seat_stacks=seat_stacks,
                            button_assignment=button_assignment,
                            blind_bet_sequence=blind_bet_sequence,
                            action_sequences=action_sequences,
                            solved_spots=() )
