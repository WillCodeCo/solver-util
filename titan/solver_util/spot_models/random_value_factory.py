import typing
import random
from titan.solver_util.spot_models.types import (
    Action,
    ActionSequence,
    SeatStack,
    CallAction,
    RaiseAction,
    CheckAction,
    FoldAction,
    Spot
)
from titan.solver_util.spot_models.spot_models import (
    BettingRound,
    PreflopBettingRound,
    FlopBettingRound,
    TurnBettingRound,
    RiverBettingRound
)


class RandomValueFactory:

    NUM_BET_SIZES = 4

    @classmethod
    def create_raise_action(cls, min_raise: int, max_raise: int):
        amount = random.randint(min_raise, max_raise)
        return RaiseAction(amount)

    @classmethod
    def create_possible_actions(cls, can_check: bool, num_bet_sizes: int, min_raise: int, max_raise: int):
        raise_actions = set()
        if min_raise == max_raise:
            raise_actions.add(RaiseAction(min_raise))
        elif min_raise < max_raise:
            raise_actions = set()
            while len(raise_actions) < num_bet_sizes:
                raise_actions.add(cls.create_raise_action(min_raise, max_raise))
            raise_actions = sorted(list(raise_actions), key=lambda action: action.amount())
        if can_check:
            return (FoldAction(), CheckAction()) + tuple(raise_actions)
        else:
            return (FoldAction(), CallAction()) + tuple(raise_actions)

    @classmethod
    def create_actions_for_spot(cls, spot: Spot, num_bet_sizes: int, min_raise: int):
        acting_seat = spot.next_seats_to_act()[0]
        max_raise = spot.seat_spends()[acting_seat].live_amount() + spot.remaining_stack_sizes()[acting_seat]
        if min_raise < max_raise and (min_raise/max_raise) >= 0.8:
            num_bet_sizes = 1
            min_raise = max_raise
        return cls.create_possible_actions( can_check=spot.can_check(acting_seat),
                                            num_bet_sizes=num_bet_sizes,
                                            min_raise=min_raise,
                                            max_raise=max_raise )

    @classmethod
    def select_action(cls, possible_actions: typing.Tuple[Action, ...]) -> Action:
        # dont fold if we can check
        if CheckAction() in possible_actions:
            return random.choice(tuple(action for action in possible_actions if action != FoldAction()))
        return random.choice(possible_actions)

    @classmethod
    def create_action_sequence(cls, betting_round_class, initial_spot: Spot, num_bet_sizes: int, min_raise: int):
        cur_spot = initial_spot
        result = ActionSequence.create_empty()
        while ( (not betting_round_class.is_betting_over_in_hand(cur_spot)) and
                (not betting_round_class.is_betting_round_complete(cur_spot)) ):
            possible_actions = cls.create_actions_for_spot( spot=cur_spot,
                                                            num_bet_sizes=num_bet_sizes,
                                                            min_raise=min_raise )            
            action = cls.select_action(possible_actions)
            if type(action) == RaiseAction:
                 min_raise = action.amount() + 1
            result = result + action
            cur_spot = betting_round_class.next_spot(current_spot=cur_spot, action=action)
        return result


    @classmethod
    def gen_action_sequences(cls, seat_stacks, button_assignment, blind_bet_sequence):
        cur_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )
        # preflop
        action_sequence = cls.create_action_sequence(   betting_round_class=PreflopBettingRound,
                                                        initial_spot=cur_spot,
                                                        num_bet_sizes=cls.NUM_BET_SIZES,
                                                        min_raise=blind_bet_sequence[1].live_amount()  )
        yield action_sequence
        for cur_spot in PreflopBettingRound.gen_next_spots(cur_spot, action_sequence):
            pass
        # is the hand over ?
        if PreflopBettingRound.is_betting_over_in_hand(cur_spot):
            return
        # rest of spots before this round
        for betting_round_class in (FlopBettingRound,
                                    TurnBettingRound,
                                    RiverBettingRound):
            cur_spot = betting_round_class.create_initial_spot( button_assignment=button_assignment,
                                                                prev_spot=cur_spot )
            action_sequence = cls.create_action_sequence(   betting_round_class=betting_round_class,
                                                            initial_spot=cur_spot,
                                                            num_bet_sizes=cls.NUM_BET_SIZES,
                                                            min_raise=blind_bet_sequence[1].live_amount()  )
            yield action_sequence
            for cur_spot in FlopBettingRound.gen_next_spots(cur_spot, action_sequence):
                pass
            # is the hand over ?
            if betting_round_class.is_betting_over_in_hand(cur_spot):
                break


