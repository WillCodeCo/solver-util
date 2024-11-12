import logging
import pytest
import timeit
from titan.solver_util.spot_models import (
    BlindBet,
    SeatOrdering,
    BlindBetSequence,
    ButtonAssignment,
    Action,
    CheckAction,
    CallAction,
    FoldAction,
    RaiseAction,
    ActionSequence,
    SeatStack,
    SeatSpend,
    Spot,
    BettingRound,
    PreflopBettingRound,
    PostflopBettingRound,
    FlopBettingRound,
    TurnBettingRound,
    RiverBettingRound,
    RandomValueFactory
)

logger = logging.getLogger(__name__)


def test_action_sequence():    
    action_sequence = ActionSequence.create_from_string('cxr100fr3000')
    assert action_sequence[0] == CallAction()
    assert action_sequence[0] != FoldAction()
    assert action_sequence[0] != CheckAction()
    assert action_sequence == ActionSequence((  CallAction(),
                                                CheckAction(),
                                                RaiseAction(100),
                                                FoldAction(),
                                                RaiseAction(3000) ))
    # check we can hash them
    s = set()
    s.add(action_sequence)
    s.add(action_sequence[0])
    # check the prefixes
    prefixes = list(action_sequence.gen_prefixes())
    assert prefixes[0] == ActionSequence(())
    assert prefixes[-1] == action_sequence
    assert len(prefixes) == len(action_sequence) + 1
    # parent
    assert action_sequence.parent() == ActionSequence.create_from_string('cxr100f')
    # string representation
    assert str(action_sequence) == 'cxr100fr3000'
    # concat action sequence
    assert (ActionSequence.create_empty() + CallAction()) == ActionSequence.create_from_string('c')
    assert (ActionSequence.create_from_string('cxr100fr3000') + ActionSequence.create_from_string('f')) == ActionSequence.create_from_string('cxr100fr3000f')



    

def test_blind_bet_sequence():
    blind_bet_sequence = BlindBetSequence.create_from_string('b100b100:50s200:50')
    assert blind_bet_sequence[0] == BlindBet(live_amount=100, dead_amount=0, is_straddle=False)
    assert blind_bet_sequence == BlindBetSequence(( BlindBet(   live_amount=100,
                                                                dead_amount=0,
                                                                is_straddle=False  ),
                                                    BlindBet(   live_amount=100,
                                                                dead_amount=50,
                                                                is_straddle=False  ),
                                                    BlindBet(   live_amount=200,
                                                                dead_amount=50,
                                                                is_straddle=True  ) ))
    # check we can hash them
    s = set()
    s.add(blind_bet_sequence)
    s.add(blind_bet_sequence[0])
    # parent
    assert blind_bet_sequence.parent() == BlindBetSequence.create_from_string('b100b100:50')
    # string representation
    assert str(blind_bet_sequence) == 'b100b100:50s200:50'


def test_blind_bet_sequence_creation():

    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=2,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0 )

    assert str(blind_bet_sequence) == 'b50:50b100:50'


    button_assignment = ButtonAssignment(   dealer_seat=3,
                                            big_blind_seat=4,
                                            small_blind_seat=3  )
    blind_bet_seats = SeatOrdering.blind_bet_ordering(  seats=(3, 4),
                                                        button_assignment=button_assignment )
    assert blind_bet_seats == (3, 4)


    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=6,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=1  )

    assert str(blind_bet_sequence) == 'b50:50b100:50s200:50b0:50b0:50b0:50'


    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            big_blind_seat=2,
                                            small_blind_seat=1  )
    blind_bet_seats = SeatOrdering.blind_bet_ordering(  seats=(5, 2, 3, 0, 4, 1),
                                                        button_assignment=button_assignment )
    assert blind_bet_seats == (1, 2, 3, 4, 5, 0)



    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=6,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )

    assert str(blind_bet_sequence) == 'b50:50b100:50b0:50b0:50b0:50b0:50'


def test_preflop_seat_spends():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=3,
                                stack_size=10000  ),
                    SeatStack(  seat=8,
                                stack_size=10000  ),
                    SeatStack(  seat=7,
                                stack_size=10000  ),
                    SeatStack(  seat=6,
                                stack_size=10000  ) )
    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=3,
                                            small_blind_seat=5,
                                            big_blind_seat=6  )

    # is small blind present ?
    has_small_blind = ( button_assignment.has_small_blind() and
                        button_assignment.small_blind_seat() in ordered_seats )

    num_seats = len(seat_stacks)
    num_seats_at_table = ordered_seats[-1] + 1
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=has_small_blind,
                                                            num_straddles=1  )
    seat_spends = PreflopBettingRound.create_blind_seat_spends( ordered_seats=ordered_seats,
                                                                button_assignment=button_assignment,
                                                                blind_bet_sequence=blind_bet_sequence )



    assert len(seat_spends) == num_seats_at_table
    assert seat_spends == ( SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=50,   dead_amount=50),    # SB + ante
                            SeatSpend(live_amount=100,  dead_amount=50),    # BB + ante
                            SeatSpend(live_amount=200,  dead_amount=50),    # straddle
                            SeatSpend(live_amount=0,    dead_amount=50) )   # ante


def test_preflop_seat_spends_dead_button():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=3,
                                stack_size=10000  ),
                    SeatStack(  seat=8,
                                stack_size=10000  ),
                    SeatStack(  seat=7,
                                stack_size=10000  ),
                    SeatStack(  seat=6,
                                stack_size=10000  ) )
    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=1,  # dealer button is on an inactive seat
                                            small_blind_seat=3,
                                            big_blind_seat=5  )

    # is small blind present ?
    has_small_blind = ( button_assignment.has_small_blind() and
                        button_assignment.small_blind_seat() in ordered_seats )

    num_seats = len(seat_stacks)
    num_seats_at_table = ordered_seats[-1] + 1
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=has_small_blind,
                                                            num_straddles=0  )
    seat_spends = PreflopBettingRound.create_blind_seat_spends( ordered_seats=ordered_seats,
                                                                button_assignment=button_assignment,
                                                                blind_bet_sequence=blind_bet_sequence )



    assert len(seat_spends) == num_seats_at_table
    assert seat_spends == ( SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=50,   dead_amount=50),    # SB+ante
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=100,  dead_amount=50),    # BB + ante
                            SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=50) )   # ante


def test_preflop_seat_spends_dead_sb():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=3,
                                stack_size=10000  ),
                    SeatStack(  seat=8,
                                stack_size=10000  ),
                    SeatStack(  seat=7,
                                stack_size=10000  ),
                    SeatStack(  seat=6,
                                stack_size=10000  ) )
    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=3,
                                            small_blind_seat=4, # dead small blind
                                            big_blind_seat=5  )

    # is small blind present ?
    has_small_blind = ( button_assignment.has_small_blind() and
                        button_assignment.small_blind_seat() in ordered_seats )

    num_seats = len(seat_stacks)
    num_seats_at_table = ordered_seats[-1] + 1
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=has_small_blind,
                                                            num_straddles=0  )
    seat_spends = PreflopBettingRound.create_blind_seat_spends( ordered_seats=ordered_seats,
                                                                button_assignment=button_assignment,
                                                                blind_bet_sequence=blind_bet_sequence )



    assert len(seat_spends) == num_seats_at_table
    assert seat_spends == ( SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=0),     # (inactive seat)
                            SeatSpend(live_amount=100,  dead_amount=50),    # BB + ante
                            SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=50),    # ante
                            SeatSpend(live_amount=0,    dead_amount=50) )   # ante



def test_preflop_seat_spends_headsup():

    seat_stacks = ( SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=2,
                                stack_size=10000  ) )
    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=3,
                                            small_blind_seat=5,
                                            big_blind_seat=2  )

    # is small blind present ?
    has_small_blind = ( button_assignment.has_small_blind() and
                        button_assignment.small_blind_seat() in ordered_seats )

    num_seats = len(seat_stacks)
    num_seats_at_table = ordered_seats[-1] + 1
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=has_small_blind,
                                                            num_straddles=0  )
    seat_spends = PreflopBettingRound.create_blind_seat_spends( ordered_seats=ordered_seats,
                                                                button_assignment=button_assignment,
                                                                blind_bet_sequence=blind_bet_sequence )

    assert len(seat_spends) == num_seats_at_table
    assert seat_spends == ( SeatSpend(live_amount=0,    dead_amount=0),    # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=0),    # (inactive seat)
                            SeatSpend(live_amount=100,  dead_amount=50),   # big blind
                            SeatSpend(live_amount=0,    dead_amount=0),    # (inactive seat)
                            SeatSpend(live_amount=0,    dead_amount=0),    # (inactive seat)
                            SeatSpend(live_amount=50,   dead_amount=50) )  # small blind + ante


def test_preflop_betting_round():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=3,
                                stack_size=10000  ),
                    SeatStack(  seat=2,
                                stack_size=10000  ),
                    SeatStack(  seat=7,
                                stack_size=10000  ),
                    SeatStack(  seat=6,
                                stack_size=10000  ) )
    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=8,
                                            small_blind_seat=0,
                                            big_blind_seat=2  )
    num_seats = len(seat_stacks)
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )


    initial_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )

    assert set(initial_spot.seat_stacks()) == set(seat_stacks)
    assert set(initial_spot.remaining_seat_stacks()) == set((   SeatStack(  seat=0,
                                                                            stack_size=10000-100  ),
                                                                SeatStack(  seat=5,
                                                                            stack_size=10000-50  ),
                                                                SeatStack(  seat=3,
                                                                            stack_size=10000-50  ),
                                                                SeatStack(  seat=2,
                                                                            stack_size=10000-150  ),
                                                                SeatStack(  seat=7,
                                                                            stack_size=10000-50  ),
                                                                SeatStack(  seat=6,
                                                                            stack_size=10000-50  ) ))



    action_sequence = ActionSequence.create_from_string('ccr9950ffcff')
    spots = list(PreflopBettingRound.gen_next_spots(initial_spot,
                                                    action_sequence))

    assert initial_spot.next_seats_to_act() == (3, 5, 6, 7, 0, 2)
    # call
    assert spots[0].next_seats_to_act() == (5, 6, 7, 0, 2)
    # call
    assert spots[1].next_seats_to_act() == (6, 7, 0, 2)
    # r9950  (all-in)
    assert spots[2].next_seats_to_act() == (7, 0, 2, 3, 5)
    # fold
    assert spots[3].next_seats_to_act() == (0, 2, 3, 5)
    # fold
    assert spots[4].next_seats_to_act() == (2, 3, 5)
    # call and go all in
    assert spots[5].next_seats_to_act() == (3, 5)
    # fold
    assert spots[6].next_seats_to_act() == (5,)
    # fold
    assert spots[7].next_seats_to_act() == ()

    expected_folds = {}
    expected_folds[0] = {}
    expected_folds[1] = {}
    expected_folds[2] = {}
    expected_folds[3] = {7}
    expected_folds[4] = {7, 0}
    expected_folds[5] = {7, 0}
    expected_folds[6] = {7, 0, 3}
    expected_folds[7] = {7, 0, 3, 5}



    for spot_index, expected_folds in expected_folds.items():
        for seat in ordered_seats:
            if seat in expected_folds:
                assert spots[spot_index].is_folded_seat(seat)
            else:
                assert (not spots[spot_index].is_folded_seat(seat))


    expected_all_ins = {}
    expected_all_ins[0] = {}
    expected_all_ins[1] = {}
    expected_all_ins[2] = {6}
    expected_all_ins[3] = {6}
    expected_all_ins[4] = {6}
    expected_all_ins[5] = {6,2}
    expected_all_ins[6] = {6,2}
    expected_all_ins[7] = {6,2}



    for spot_index, expected_all_ins in expected_all_ins.items():
        for seat in ordered_seats:
            if seat in expected_all_ins:
                assert spots[spot_index].is_all_in_seat(seat)
            else:
                assert (not spots[spot_index].is_all_in_seat(seat))



    assert initial_spot.num_active_seats() == 6
    assert spots[0].num_active_seats() == 6
    assert spots[1].num_active_seats() == 6
    assert spots[2].num_active_seats() == 5
    assert spots[3].num_active_seats() == 4
    assert spots[4].num_active_seats() == 3
    assert spots[5].num_active_seats() == 2
    assert spots[6].num_active_seats() == 1
    assert spots[7].num_active_seats() == 0


    assert not PreflopBettingRound.is_betting_round_complete(spots[5])
    assert not PreflopBettingRound.is_betting_over_in_hand(spots[5])
    assert PreflopBettingRound.is_betting_round_complete(spots[7])
    assert PreflopBettingRound.is_betting_over_in_hand(spots[7])



def test_postflop_betting_round():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=3,
                                stack_size=10000  ),
                    SeatStack(  seat=2,
                                stack_size=10000  ),
                    SeatStack(  seat=7,
                                stack_size=10000  ),
                    SeatStack(  seat=6,
                                stack_size=10000  ) )
    button_assignment = ButtonAssignment(   dealer_seat=8,
                                            small_blind_seat=0,
                                            big_blind_seat=2  )
    num_seats = len(seat_stacks)
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )


    initial_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )

    action_sequence = ActionSequence.create_from_string('ccffff')
    
    spots = list(PreflopBettingRound.gen_next_spots(initial_spot, action_sequence))
    assert initial_spot.num_active_seats() == 6
    assert spots[0].num_active_seats() == 6
    assert spots[1].num_active_seats() == 6
    assert spots[2].num_active_seats() == 5
    assert spots[3].num_active_seats() == 4
    assert spots[4].num_active_seats() == 3
    assert spots[5].num_active_seats() == 2

    assert PreflopBettingRound.is_betting_round_complete(spots[-1])
    assert not PreflopBettingRound.is_betting_over_in_hand(spots[-1])
    # next active seats after the dealer
    assert tuple(spots[-1].gen_next_active_seats(origin_seat=7)) == (3, 5)


    flop_spot = FlopBettingRound.create_initial_spot(   button_assignment=button_assignment,
                                                        prev_spot=spots[-1]  )

    assert flop_spot.next_seats_to_act() == (3, 5)

    flop_spot = FlopBettingRound.next_spot(flop_spot, CheckAction())
    assert not PreflopBettingRound.is_betting_over_in_hand(flop_spot)

    flop_spot = FlopBettingRound.next_spot(flop_spot, CheckAction())
    assert not FlopBettingRound.is_betting_over_in_hand(flop_spot)

    # if this were the river, then the hand would be over !
    assert RiverBettingRound.is_betting_over_in_hand(flop_spot)


def test_pot_contributions():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ),
                    SeatStack(  seat=1,
                                stack_size=10000  ),
                    SeatStack(  seat=2,
                                stack_size=10000  ),
                    SeatStack(  seat=7,
                                stack_size=10000  ),
                    SeatStack(  seat=6,
                                stack_size=10000  ) )
    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=1,
                                            big_blind_seat=2  )
    num_seats = len(seat_stacks)
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )


    initial_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )


    action_sequence = ActionSequence.create_from_string('r300cffff')
    preflop_spots = list(PreflopBettingRound.gen_next_spots(initial_spot, action_sequence))


    flop_spot = FlopBettingRound.create_initial_spot(   button_assignment=button_assignment,
                                                        prev_spot=preflop_spots[-1]  )

    action_sequence = ActionSequence.create_from_string('r200r400c')
    last_flop_spot = None
    for last_flop_spot in FlopBettingRound.gen_next_spots(flop_spot, action_sequence):
        pass


    pot_contributions = tuple(( initial_stack_size - remaining_stack_size
                                    for (initial_stack_size,
                                        remaining_stack_size) in zip(initial_spot.stack_sizes(),
                                                                    last_flop_spot.remaining_stack_sizes()) ))

    initial_stack_sizes = initial_spot.stack_sizes()
    final_stack_sizes = last_flop_spot.remaining_stack_sizes()
    pot_contributions = tuple(( initial_stack_sizes[seat] - final_stack_sizes[seat]
                                    for seat in ordered_seats ))

    assert pot_contributions == (50, 100, 150, 350+400, 350+400, 50)



def run_the_situation_in_model():
    # For situation 'cccccx[JsThAd]r14468ccccc[4c]xxxx[9s]'

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=14968  ),
                    SeatStack(  seat=2,
                                stack_size=3150  ),
                    SeatStack(  seat=3,
                                stack_size=38152  ),
                    SeatStack(  seat=5,
                                stack_size=27710  ),
                    SeatStack(  seat=6,
                                stack_size=25741  ),
                    SeatStack(  seat=7,
                                stack_size=27513  ) )

    button_assignment = ButtonAssignment(   dealer_seat=7,
                                            small_blind_seat=0,
                                            big_blind_seat=2  )
    num_seats = len(seat_stacks)

    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=500,
                                                            small_blind_amount=250,
                                                            ante_amount=0,
                                                            has_small_blind=True,
                                                            num_straddles=0 )
    spots = []
    # preflop spots
    spots += [PreflopBettingRound.create_initial_spot(  seat_stacks=seat_stacks,
                                                        button_assignment=button_assignment,
                                                        blind_bet_sequence=blind_bet_sequence )]
    action_sequence = ActionSequence.create_from_string('cccccx')
    spots += list(PreflopBettingRound.gen_next_spots(spots[-1], action_sequence))
    # flop spots
    spots += [FlopBettingRound.create_initial_spot( button_assignment=button_assignment,
                                                    prev_spot=spots[-1]  )]
    action_sequence = ActionSequence.create_from_string('r14468ccccc')
    spots += list(FlopBettingRound.gen_next_spots(spots[-1], action_sequence))
    # turn spots
    spots += [TurnBettingRound.create_initial_spot( button_assignment=button_assignment,
                                                    prev_spot=spots[-1]  )]
    action_sequence = ActionSequence.create_from_string('xxxx')
    spots += list(TurnBettingRound.gen_next_spots(spots[-1], action_sequence))
    # river spots
    spots += [RiverBettingRound.create_initial_spot(button_assignment=button_assignment,
                                                    prev_spot=spots[-1])]


def test_preflop_round_over():

    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=2,
                                stack_size=10000  ),
                    SeatStack(  seat=3,
                                stack_size=10000  ),
                    SeatStack(  seat=5,
                                stack_size=10000  ) )

    ordered_seats = sorted((ss.seat() for ss in seat_stacks))
    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=2,
                                            big_blind_seat=3  )
    num_seats = len(seat_stacks)

    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=num_seats,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0 )




    initial_spot = PreflopBettingRound.create_initial_spot(  seat_stacks=seat_stacks,
                                                        button_assignment=button_assignment,
                                                        blind_bet_sequence=blind_bet_sequence )

    assert initial_spot.stack_sizes() == (  10000,
                                            0,          # inactive seat
                                            10000,
                                            10000,
                                            0,          # inactive seat
                                            10000  )
    assert initial_spot.remaining_stack_sizes() == (10000-50,
                                                    0,          # inactive seat
                                                    10000-100,
                                                    10000-150,
                                                    0,          # inactive seat
                                                    10000-50)


    action_sequence = ActionSequence.create_from_string('c')
    spots = list(PreflopBettingRound.gen_next_spots(initial_spot,
                                                    action_sequence))


    assert spots[-1].next_seats_to_act() == (0, 2, 3)



    action_sequence = ActionSequence.create_from_string('cffx')
    spots = list(PreflopBettingRound.gen_next_spots(initial_spot,
                                                    action_sequence))


    expected_folds = {}
    expected_folds[0] = {}
    expected_folds[1] = {0}
    expected_folds[2] = {0, 2}
    expected_folds[3] = {0, 2}


    for spot_index, expected_folds in expected_folds.items():
        for seat in ordered_seats:
            if seat in expected_folds:
                assert spots[spot_index].is_folded_seat(seat)
            else:
                assert (not spots[spot_index].is_folded_seat(seat))



    assert spots[-1].num_active_seats() == 2
    assert spots[-1].next_seats_to_act() == ()
    assert PreflopBettingRound.is_betting_round_complete(spots[-1])


def test_spot_model_performance():
    time_msecs =  (timeit.timeit(lambda: run_the_situation_in_model(), number=1000)/1000) * 1000
    logger.info(f"Time to model the situation in spot models: {time_msecs} ms")



def test_spot_model_ends_on_turn():
    # For situation 'b10b20;fr50ccff[7c9c8s]r20r100cf[5c]xr200r800c'
    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=730  ),
                    SeatStack(  seat=1,
                                stack_size=3080  ),
                    SeatStack(  seat=2,
                                stack_size=2190  ),
                    SeatStack(  seat=3,
                                stack_size=3790  ),
                    SeatStack(  seat=4,
                                stack_size=2240  ),
                    SeatStack(  seat=5,
                                stack_size=3690  ) )

    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=1,
                                            big_blind_seat=2  )
    num_seats = len(seat_stacks)
    blind_bet_sequence = BlindBetSequence.create_from_string('b10b20')
    spots = []
    # preflop spots
    spots += [PreflopBettingRound.create_initial_spot(  seat_stacks=seat_stacks,
                                                        button_assignment=button_assignment,
                                                        blind_bet_sequence=blind_bet_sequence )]
    # check preflop play order
    assert spots[-1].next_seats_to_act() == (3, 4, 5, 0, 1, 2)
    # gen street spots
    action_sequence = ActionSequence.create_from_string('fr50ccff')
    spots += list(PreflopBettingRound.gen_next_spots(spots[-1], action_sequence))    
    # check folds
    assert spots[-1].is_folded_seat(3)
    assert spots[-1].is_folded_seat(1)
    assert spots[-1].is_folded_seat(2)
    # flop spots
    spots += [FlopBettingRound.create_initial_spot( button_assignment=button_assignment,
                                                    prev_spot=spots[-1]  )]
    # check flop play order
    assert spots[-1].next_seats_to_act() == (4, 5, 0)
    # gen street spots
    action_sequence = ActionSequence.create_from_string('r20r100cf')
    spots += list(FlopBettingRound.gen_next_spots(spots[-1], action_sequence))
    # check folds
    assert spots[-1].is_folded_seat(4)
    # turn spots
    spots += [TurnBettingRound.create_initial_spot( button_assignment=button_assignment,
                                                    prev_spot=spots[-1]  )]
    # check turn play order
    assert spots[-1].next_seats_to_act() == (5, 0)
    # gen street spots
    action_sequence = ActionSequence.create_from_string('xr200r800c')
    spots += list(TurnBettingRound.gen_next_spots(spots[-1], action_sequence))
    # should be all in so hand is over
    assert spots[-1].is_all_in_seat(0)
    assert TurnBettingRound.is_betting_round_complete(spots[-1])




def test_spot_model_preflop_ends_on_call():
    # For situation 'b10b20;r50fr150cfr410r4840cfc'
    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=2410 ),
                    SeatStack(  seat=1,
                                stack_size=2400  ),
                    SeatStack(  seat=2,
                                stack_size=1510  ),
                    SeatStack(  seat=3,
                                stack_size=4840  ),
                    SeatStack(  seat=4,
                                stack_size=2890  ),
                    SeatStack(  seat=5,
                                stack_size=1360  ) )

    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=1,
                                            big_blind_seat=2  )
    num_seats = len(seat_stacks)
    blind_bet_sequence = BlindBetSequence.create_from_string('b10b20')
    spots = []
    # preflop spots
    spots += [PreflopBettingRound.create_initial_spot(  seat_stacks=seat_stacks,
                                                        button_assignment=button_assignment,
                                                        blind_bet_sequence=blind_bet_sequence )]
    # check preflop play order
    assert spots[-1].next_seats_to_act() == (3, 4, 5, 0, 1, 2)
    # gen street spots
    action_sequence = ActionSequence.create_from_string('r50fr150cfr410r4840cf')
    spots += list(PreflopBettingRound.gen_next_spots(spots[-1], action_sequence))    
    # check not finished
    assert not PreflopBettingRound.is_betting_round_complete(spots[-1])
    assert not PreflopBettingRound.is_betting_over_in_hand(spots[-1])
    spots += [PreflopBettingRound.next_spot(spots[-1], CallAction())]
    # check finished
    assert PreflopBettingRound.is_betting_round_complete(spots[-1])
    assert PreflopBettingRound.is_betting_over_in_hand(spots[-1])



def test_all_in_needs_to_be_called():
    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=10000  ),
                    SeatStack(  seat=1,
                                stack_size=10000  ) )
    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=0,
                                            big_blind_seat=1  )
    blind_bet_sequence = BlindBetSequence.create_from_string('b50b100')
    initial_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )
    action_sequence = ActionSequence.create_from_string('r10000')
    spots = list(PreflopBettingRound.gen_next_spots(initial_spot, action_sequence))
    assert not PreflopBettingRound.is_betting_round_complete(spots[-1])
    assert not PreflopBettingRound.is_betting_over_in_hand(spots[-1])



    @classmethod
    def create_hand_history_string(cls, seat_stacks, button_assignment, blind_bet_sequence):
        result = str(blind_bet_sequence)
        fake_community_cards = (";", "[??????]", "[??]", "[??]")
        for i, action_sequence in enumerate(cls.gen_action_sequences(seat_stacks, button_assignment, blind_bet_sequence)):
            result += fake_community_cards[i] + str(action_sequence)
        return result



def test_random_value_factory():
    seat_stacks = ( SeatStack(  seat=0,
                                stack_size=5000 ),
                    SeatStack(  seat=1,
                                stack_size=5000  ))
    button_assignment = ButtonAssignment(   dealer_seat=0,
                                            small_blind_seat=0,
                                            big_blind_seat=1 )
    blind_bet_sequence = BlindBetSequence.create_from_string('b10b20')

    for x in range(100):
        action_sequence_gen = RandomValueFactory.gen_action_sequences(seat_stacks, button_assignment, blind_bet_sequence)
        hand_history_str = str(blind_bet_sequence)
        fake_community_cards = (";", "[??????]", "[??]", "[??]")
        for i, action_sequence in enumerate(action_sequence_gen):
            hand_history_str += fake_community_cards[i] + str(action_sequence)
        assert hand_history_str.startswith('b10b20')
        logger.info(f"Created random hand history: {hand_history_str}")



def test_all_in_calling_blinds():
    seat_stacks = ( 
            SeatStack(  seat=0,
                        stack_size=101300  ),
            SeatStack(  seat=1,
                        stack_size=45383  ),
            SeatStack(  seat=2,
                        stack_size=48688  ),
            SeatStack(  seat=3,
                        stack_size=49950  ),
            SeatStack(  seat=4,
                        stack_size=50350  ),
            SeatStack(  seat=5,
                        stack_size=369  ),
        )
    button_assignment = ButtonAssignment(   dealer_seat=5,
                                            small_blind_seat=0,
                                            big_blind_seat=1 )
    blind_bet_sequence = BlindBetSequence.create_from_string('b200:50b400:50b0:50b0:50b0:50b0:50')

    initial_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                            button_assignment=button_assignment,
                                                            blind_bet_sequence=blind_bet_sequence )
    action_sequence = ActionSequence.create_from_string('r1000ffcr2600fr5800')
    spots = [initial_spot] + list(PreflopBettingRound.gen_next_spots(initial_spot, action_sequence))


    BTN_SEAT_INDEX = 5

    assert spots[0].next_seats_to_act() == (2, 3, 4, 5, 0, 1)
    assert spots[0].seat_spends()[BTN_SEAT_INDEX].total_amount() == 50
    assert spots[0].remaining_stack_sizes()[BTN_SEAT_INDEX] == seat_stacks[BTN_SEAT_INDEX].stack_size() - 50
    # r1000
    assert spots[1].next_seats_to_act() == (3, 4, 5, 0, 1)
    # f
    assert spots[2].next_seats_to_act() == (4, 5, 0, 1)
    # f
    assert spots[3].next_seats_to_act() == (5, 0, 1)
    # c (BTN ALL IN)    
    assert spots[4].seat_spends()[BTN_SEAT_INDEX].dead_amount() == 50
    assert spots[4].seat_spends()[BTN_SEAT_INDEX].live_amount() == seat_stacks[BTN_SEAT_INDEX].stack_size() - 50
    assert spots[4].is_all_in_seat(seat=5)


