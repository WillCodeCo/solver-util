import typing
import logging
from titan.solver_util.spot_models.types import (
    BlindBet,
    BlindBetSequence,
    Action,
    CheckAction,
    CallAction,
    FoldAction,
    RaiseAction,
    ActionSequence,
    SeatStack,
    SeatSpend,
    Spot,
    ButtonAssignment
)

logger = logging.getLogger(__name__)



class SeatOrdering:

    @classmethod
    def next_seat(cls, ordered_seats: typing.Tuple[int], selected_seat: int) -> int:
        if ordered_seats[-1] <= selected_seat:
            # we wrap around if selected_seat is the last one or beyond
            return ordered_seats[0]
        else:
            return next((seat for seat in ordered_seats if seat > selected_seat))

    @classmethod
    def previous_seat(cls, ordered_seats: typing.Tuple[int], selected_seat: int) -> int:
        if ordered_seats[0] >= selected_seat:
            # we wrap around if selected_seat is the first one or before
            return ordered_seats[-1]
        else:
            return next((seat for seat in ordered_seats[::-1] if seat < selected_seat))


    @classmethod
    def deal_ordering(cls, seats: typing.Tuple[int],
                            button_assignment: ButtonAssignment) -> typing.Tuple[int]:
        if not button_assignment.has_dealer():
            raise ValueError((  f"There should always be a dealer seat. Even if it is assigned to a " +
                                f"non-playing seat." ))
        ordered_seats = tuple(sorted(seats))
        if button_assignment.dealer_seat() >= seats[-1]:
            # it is already in deal order !
            return ordered_seats
        else:
            pos = next((    i for i in range(len(seats))
                                if ordered_seats[i] > button_assignment.dealer_seat()    ))
            return ordered_seats[pos:] + ordered_seats[:pos]



    @classmethod
    def blind_bet_ordering(cls, seats: typing.Tuple[int],
                            button_assignment: ButtonAssignment) -> typing.Tuple[int]:
        if not button_assignment.has_dealer():
            raise ValueError((  f"There should always be a dealer seat. Even if it is assigned to a " +
                                f"non-playing seat." ))
        if not button_assignment.has_big_blind():
            raise ValueError((  f"There should always be a big blind seat." ))
        # Enact special headsup rule ?
        if len(seats) == 2:
            ordered_seats = tuple(sorted(seats))
            try:
                sb_pos = ordered_seats.index(button_assignment.small_blind_seat())
                return ordered_seats[sb_pos:] + ordered_seats[:sb_pos]
            except ValueError:
                pass
            # small blind is dead, so start with big blind                            
            try:
                bb_pos = ordered_seats.index(button_assignment.big_blind_seat())
                return ordered_seats[bb_pos:] + ordered_seats[:bb_pos]
            except ValueError:
                raise ValueError(f"Big blind assignment was not found in the seats !")
        else:
            if (    button_assignment.has_small_blind() and 
                    button_assignment.small_blind_seat() == button_assignment.dealer_seat()  ):
                raise ValueError((  f"Did not expect there to be a seat marked as SB and BTN in " +
                                    f"non-headsup hand"  ))
            return cls.deal_ordering(seats, button_assignment)



    @classmethod
    def preflop_act_ordering(cls, seats: typing.Tuple[int],
                            button_assignment: ButtonAssignment,
                            blind_bet_sequence: BlindBetSequence) -> typing.Tuple[int]:

        if not button_assignment.has_dealer():
            raise ValueError((  f"There should always be a dealer seat. Even if it is assigned to a " +
                                f"non-playing seat." ))
        if not button_assignment.has_big_blind():
            raise ValueError((  f"There should always be a big blind seat." ))
        # heads up rule ?
        if len(seats) == 2:
            # big blind acts last
            if button_assignment.big_blind_seat() == seats[0]:
                return (seats[1], seats[0])
            elif button_assignment.big_blind_seat() == seats[1]:
                return seats
            else:
                raise ValueError(f"There must be a big blind seat in headsup hands !")
        else:
            deal_ordered_seats = cls.deal_ordering(seats, button_assignment)
            # straddles             
            straddle_seats_pos = [  i for i, blind_bet in enumerate(blind_bet_sequence)
                                        if blind_bet.is_straddle()  ]                                        
            if straddle_seats_pos:
                pos = straddle_seats_pos[-1] + 1
            else:
                try:
                    bb_pos = deal_ordered_seats.index(button_assignment.big_blind_seat())
                except ValueError:
                    raise ValueError(f"Big blind assignment was not found in the seats !")
                pos = bb_pos + 1
            return deal_ordered_seats[pos:] + deal_ordered_seats[:pos]


    @classmethod
    def postflop_act_ordering(cls, seats: typing.Tuple[int],
                            button_assignment: ButtonAssignment) -> typing.Tuple[int]:
        # dealer acts last
        return cls.deal_ordering(seats, button_assignment)




class NextSpotHelper:


    @classmethod
    def add_folded_seat(cls, seat_folds: typing.Tuple[int], seat: int) -> typing.Tuple[int]:
        return seat_folds[:seat] + (True,) + seat_folds[seat+1:]

    @classmethod
    def replace_seat_spend(cls, seat_spends: typing.Tuple[SeatSpend],
                                seat: int,
                                to_spend: SeatSpend) -> typing.Tuple[SeatSpend]:
        return seat_spends[:seat] + (to_spend, ) + seat_spends[seat+1:]


class BettingRound:

    @classmethod
    def next_spot(cls, current_spot: Spot, action: Action):
        if not current_spot.has_next_seats_to_act():
            raise ValueError((  f"Cannot invoke {cls.__name__}.next_spot() " +
                                f"on a Spot that has no next_seats_to_act !"  ))
        acting_seat = current_spot.next_seats_to_act()[0]
        if type(action) == FoldAction:
            seat_folds = NextSpotHelper.add_folded_seat(current_spot.seat_folds(),
                                                        acting_seat)
            return Spot(ordered_seats=current_spot.ordered_seats(),
                        stack_sizes=current_spot.stack_sizes(),
                        seat_folds=seat_folds,
                        seat_spends=current_spot.seat_spends(),
                        next_seats_to_act=current_spot.next_seats_to_act()[1:])
        elif type(action) == CheckAction:
            if (not current_spot.can_check(acting_seat)):
                raise ValueError((  f"Cannot allow seat {acting_seat} to CHECK when there "+
                                    f"is a bet that must be called in {cls.__name__}.next_spot()" ))
            return Spot(ordered_seats=current_spot.ordered_seats(),
                        stack_sizes=current_spot.stack_sizes(),
                        seat_folds=current_spot.seat_folds(),
                        seat_spends=current_spot.seat_spends(),
                        next_seats_to_act=current_spot.next_seats_to_act()[1:])
        elif type(action) == CallAction:
            if (current_spot.can_check(acting_seat)):
                raise ValueError((  f"Cannot allow seat {acting_seat} to CALL when there "+
                                    f"is nothing to call in {cls.__name__}.next_spot()" ))
            available_to_call = current_spot.stack_sizes()[acting_seat] - current_spot.seat_spends()[acting_seat].dead_amount()
            spend_live_amount = min(available_to_call,
                                    current_spot.maximum_bet())
            to_spend = SeatSpend(   live_amount=spend_live_amount,
                                    dead_amount=current_spot.seat_spends()[acting_seat].dead_amount()  )
            seat_spends = NextSpotHelper.replace_seat_spend(seat_spends=current_spot.seat_spends(),
                                                            seat=acting_seat,
                                                            to_spend=to_spend)
            return Spot(ordered_seats=current_spot.ordered_seats(),
                        stack_sizes=current_spot.stack_sizes(),
                        seat_folds=current_spot.seat_folds(),
                        seat_spends=seat_spends,
                        next_seats_to_act=current_spot.next_seats_to_act()[1:])
        elif type(action) == RaiseAction:
            to_spend = SeatSpend(   live_amount=action.amount(),
                                    dead_amount=current_spot.seat_spends()[acting_seat].dead_amount()  )
            # check we arent spending too much !
            if to_spend.total_amount() > current_spot.stack_sizes()[acting_seat]:
                raise ValueError((  f"Cannot allow seat {acting_seat} to raise beyond "+
                                    f"the available stacks in {cls.__name__}.next_spot()" ))
            # update it
            seat_spends = NextSpotHelper.replace_seat_spend(seat_spends=current_spot.seat_spends(),
                                                            seat=acting_seat,
                                                            to_spend=to_spend)
            # make it
            return Spot(ordered_seats=current_spot.ordered_seats(),
                        stack_sizes=current_spot.stack_sizes(),
                        seat_folds=current_spot.seat_folds(),
                        seat_spends=seat_spends,
                        next_seats_to_act=tuple(current_spot.gen_next_active_seats(acting_seat)))
        else:
            raise ValueError(f"Invalid action type `{type(action)}` in {cls.__name__}.next_spot()")


    @classmethod
    def gen_next_spots(cls, current_spot: Spot, action_sequence: ActionSequence):
        cur_spot = current_spot
        for action in action_sequence:
            cur_spot = cls.next_spot(cur_spot, action)
            yield cur_spot

    @classmethod
    def is_betting_round_complete(cls, current_spot: Spot) -> bool:
        return (not current_spot.has_next_seats_to_act())

    @classmethod
    def is_betting_over_in_hand(cls, current_spot: Spot) -> bool:
        return (current_spot.num_active_seats() < 2) and (current_spot.num_active_seats_need_to_call() == 0)



class PreflopBettingRound(BettingRound):  


    @classmethod
    def create_blind_seat_spends(cls, ordered_seats: typing.Tuple[int],
                                        button_assignment: ButtonAssignment,
                                        blind_bet_sequence: BlindBetSequence) -> typing.Tuple[SeatSpend]:
        num_seats_at_table = ordered_seats[-1] + 1
        # initialize spends at zero
        seat_spends = [SeatSpend(0,0) for _ in range(num_seats_at_table)]
        # spends for the blinds
        blind_bet_seats = SeatOrdering.blind_bet_ordering(  seats=ordered_seats,
                                                            button_assignment=button_assignment )
        for seat, blind_bet in zip(blind_bet_seats, blind_bet_sequence):
            seat_spends[seat] = SeatSpend(  live_amount=blind_bet.live_amount(),
                                            dead_amount=blind_bet.dead_amount()  )
        return tuple(seat_spends)

    @classmethod
    def create_initial_spot(cls, seat_stacks: typing.Tuple[SeatStack],
                                button_assignment: ButtonAssignment,
                                blind_bet_sequence: BlindBetSequence) -> Spot:
        # the seats
        ordered_seats = tuple(sorted([ss.seat() for ss in seat_stacks]))
        num_seats_at_table = ordered_seats[-1] + 1
        # initialize stack sizes
        stack_sizes  = [0] * num_seats_at_table
        for seat_stack in seat_stacks:
            stack_sizes[seat_stack.seat()] = seat_stack.stack_size()
        # init seat folds to false
        seat_folds = tuple((False for _ in range(num_seats_at_table)))
        # initialize spends at zero
        seat_spends = cls.create_blind_seat_spends(ordered_seats=ordered_seats,
                                                    button_assignment=button_assignment,
                                                    blind_bet_sequence=blind_bet_sequence)
        # what is the acting order ?
        next_seats_to_act = SeatOrdering.preflop_act_ordering(  seats=ordered_seats,
                                                                button_assignment=button_assignment,
                                                                blind_bet_sequence=blind_bet_sequence  )
        return Spot(ordered_seats=ordered_seats,
                    stack_sizes=tuple(stack_sizes),
                    seat_folds=seat_folds,
                    seat_spends=seat_spends,
                    next_seats_to_act=next_seats_to_act)



class PostflopBettingRound(BettingRound):


    @classmethod
    def create_initial_spot(cls, button_assignment: ButtonAssignment, prev_spot: Spot) -> Spot:
        # what is the acting order ?
        next_seats_to_act = SeatOrdering.postflop_act_ordering( seats=prev_spot.ordered_seats(),
                                                                button_assignment=button_assignment )
        next_seats_to_act = tuple(( seat for seat in next_seats_to_act
                                        if prev_spot.is_active_seat(seat) ))
        # reset the spends for this round
        seat_spends = tuple((SeatSpend(0,0) for _ in prev_spot.seat_spends()))
        return Spot(ordered_seats=prev_spot.ordered_seats(),
                    stack_sizes=prev_spot.remaining_stack_sizes(),
                    seat_folds=prev_spot.seat_folds(),
                    seat_spends=seat_spends,
                    next_seats_to_act=next_seats_to_act)


class FlopBettingRound(PostflopBettingRound):
    pass

class TurnBettingRound(PostflopBettingRound):
    pass

class RiverBettingRound(PostflopBettingRound):

    @classmethod
    def is_betting_over_in_hand(cls, current_spot: Spot) -> bool:
        return BettingRound.is_betting_round_complete(current_spot) or BettingRound.is_betting_over_in_hand(current_spot)
