from __future__ import annotations
import typing
from titan.solver_util.spot_models import (
    ActionSequence,
    FoldAction,
    BlindBetSequence,
    ButtonAssignment,
    SeatStack,
    Spot,
    BettingRound,
    PreflopBettingRound,
    FlopBettingRound,
    TurnBettingRound,
    RiverBettingRound,
    SeatOrdering
)
from titan.solver_util.hand_history.hand_history_parser import (
    HandHistoryParser
)



class PlayingSeat:
    
    __slots__ = (   '_seat',
                    '_stack_size',
                    '_hole_cards',  )

    def __init__(self, seat: int, stack_size: int, hole_cards: typing.Optional[typing.Tuple[str, str]] = None):
        self._seat = seat
        self._stack_size = stack_size
        self._hole_cards = hole_cards

    def seat(self) -> int:
        return self._seat

    def stack_size(self) -> int:
        return self._stack_size

    def has_hole_cards(self) -> bool:
        return (self._hole_cards is not None)

    def hole_cards(self) -> typing.Tuple[str, str]:
        if (not self.has_hole_cards()):
            raise ValueError(f"PlayingSeat has no hole cards !")
        return self._hole_cards


class HandHistory:

    DEFAULT_NAME = 'hand'
    
    __slots__ = (   '_name',
                    '_ante_amount',
                    '_big_blind_amount',
                    '_small_blind_amount',
                    '_playing_seats',
                    '_button_assignment',
                    '_blind_bet_sequence',
                    '_action_sequences',
                    '_community_cards'  )

    def __init__(self, name: str, ante_amount: int, big_blind_amount: int, small_blind_amount: int,
                                                                playing_seats: typing.Tuple[PlayingSeat, ...],
                                                                button_assignment: ButtonAssignment,
                                                                blind_bet_sequence: BlindBetSequence,
                                                                action_sequences: typing.Tuple[ActionSequence, ...],
                                                                community_cards: typing.Tuple[str, ...]  ):
        self._name = name
        self._ante_amount = ante_amount
        self._big_blind_amount = big_blind_amount
        self._small_blind_amount = small_blind_amount
        self._playing_seats = playing_seats
        self._button_assignment = button_assignment
        self._blind_bet_sequence = blind_bet_sequence        
        self._action_sequences = action_sequences
        self._community_cards = community_cards

    def name(self) -> str:
        return self._name

    def ante_amount(self) -> int:
        return self._ante_amount

    def big_blind_amount(self) -> int:
        return self._big_blind_amount

    def small_blind_amount(self) -> int:
        return self._small_blind_amount

    def button_assignment(self) -> ButtonAssignment:
        return self._button_assignment

    def playing_seats(self) -> typing.Tuple[PlayingSeat, ...]:
        return self._playing_seats

    def blind_bet_sequence(self) -> BlindBetSequence:
        return self._blind_bet_sequence

    def action_sequences(self) -> typing.Tuple[ActionSequence, ...]:
        return self._action_sequences

    def num_players(self) -> int:
        return len(self.playing_seats())

    def num_players_in_flop(self) -> int:
        num_folds = sum(1 for action in self.preflop_action_sequence() if type(action) == FoldAction)
        return self.num_players() - num_folds

    def has_flop(self) -> bool:
        return len(self.action_sequences()) >= 2

    def has_turn(self) -> bool:
        return len(self.action_sequences()) >= 3

    def has_river(self) -> bool:
        return len(self.action_sequences()) >= 4

    def preflop_action_sequence(self) -> ActionSequence:
        return self.action_sequences()[0]

    def flop_action_sequence(self) -> ActionSequence:
        if not self.has_flop():
            raise ValueError(f"HandHistory did not go to the FLOP !")
        return self.action_sequences()[1]

    def turn_action_sequence(self) -> ActionSequence:
        if not self.has_turn():
            raise ValueError(f"HandHistory did not go to the TURN !")
        return self.action_sequences()[2]

    def river_action_sequence(self) -> ActionSequence:
        if not self.has_river():
            raise ValueError(f"HandHistory did not go to the RIVER !")
        return self.action_sequences()[3]

    def community_cards(self) -> typing.Tuple[str, ...]:
        return self._community_cards

    def gen_deal_order_playing_seats(self) -> typing.Tuple[PlayingSeat, ...]:
        seat_dict = {ps.seat(): ps for ps in self.playing_seats()}
        for seat in SeatOrdering.deal_ordering( seats=list(seat_dict.keys()),
                                                button_assignment=self.button_assignment() ):
            yield seat_dict[seat]


    def gen_preflop_spots(self):
        seat_stacks = tuple(SeatStack(seat=ps.seat(), stack_size=ps.stack_size()) for ps in self.playing_seats())
        initial_spot = PreflopBettingRound.create_initial_spot( seat_stacks=seat_stacks,
                                                                button_assignment=self.button_assignment(),
                                                                blind_bet_sequence=self.blind_bet_sequence() )
        yield initial_spot
        yield from BettingRound.gen_next_spots(initial_spot, self.preflop_action_sequence())


    def gen_flop_spots(self):
        for last_spot in self.gen_preflop_spots():
            pass
        assert last_spot
        initial_spot = FlopBettingRound.create_initial_spot(button_assignment=self.button_assignment(),
                                                            prev_spot=last_spot)
        yield initial_spot
        yield from BettingRound.gen_next_spots(initial_spot, self.flop_action_sequence())

    def gen_turn_spots(self):
        for last_spot in self.gen_flop_spots():
            pass
        assert last_spot
        initial_spot = TurnBettingRound.create_initial_spot(button_assignment=self.button_assignment(),
                                                            prev_spot=last_spot)
        yield initial_spot
        yield from BettingRound.gen_next_spots(initial_spot, self.turn_action_sequence())

    def gen_river_spots(self):
        for last_spot in self.gen_turn_spots():
            pass
        assert last_spot
        initial_spot = RiverBettingRound.create_initial_spot(button_assignment=self.button_assignment(),
                                                            prev_spot=last_spot)
        yield initial_spot
        yield from BettingRound.gen_next_spots(initial_spot, self.river_action_sequence())

    def situation_string(self):
        result = f"{self.blind_bet_sequence()};{self.preflop_action_sequence()}"
        if self.has_flop():
            result += f"[{''.join(self.community_cards()[:3])}]{self.flop_action_sequence()}"
        if self.has_turn():
            result += f"[{self.community_cards()[3]}]{self.turn_action_sequence()}"
        if self.has_river():
            result += f"[{self.community_cards()[4]}]{self.river_action_sequence()}"
        return result

    def serialize_to_dict(self) -> dict:
        return {
            'name': self.name(),
            'players': [{   'seat': ps.seat(),
                            'hole_cards': ''.join(ps.hole_cards()) if ps.has_hole_cards() else '',
                            'stack_size': ps.stack_size()  } for ps in self.playing_seats()  ],
            'ante_amount': self.ante_amount(),
            'small_blind_amount': self.small_blind_amount(),
            'big_blind_amount': self.big_blind_amount(),
            'small_blind_seat': self.button_assignment().small_blind_seat(),
            'big_blind_seat': self.button_assignment().big_blind_seat(),
            'dealer_seat': self.button_assignment().dealer_seat(),
            'hand_history': self.situation_string()
        }

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> HandHistory:
        try:
            name = some_dict.get('name', cls.DEFAULT_NAME)
            playing_seats = tuple(( PlayingSeat(seat=p['seat'],
                                                stack_size=p['stack_size'],
                                                hole_cards=p.get('hole_cards', None)) for p in some_dict['players'] ))
            button_assignment = ButtonAssignment(   dealer_seat=some_dict['dealer_seat'],
                                                    big_blind_seat=some_dict['big_blind_seat'],
                                                    small_blind_seat=some_dict['small_blind_seat'] )
            hand_history_str = some_dict['hand_history']
            community_cards = HandHistoryParser.parse_community_cards(hand_history_str)
            all_action_sequences = tuple(HandHistoryParser.parse_action_sequences(hand_history_str))
            # validate
            if len(all_action_sequences) == 1:
                # flop
                assert len(community_cards) == 0, f"Did not expect any community_cards for preflop-only hand history"
            elif len(all_action_sequences) == 2:
                # flop
                assert len(community_cards) == 3, f"Expected 3 community_cards not {len(community_cards)}"
            elif len(all_action_sequences) == 3:
                # turn
                assert len(community_cards) == 4, f"Expected 4 community_cards not {len(community_cards)}"
            elif len(all_action_sequences) == 4:
                # turn
                assert len(community_cards) == 5, f"Expected 5 community_cards not {len(community_cards)}"
            else:
                raise ValueError(f"Invalid number ({len(all_action_sequences)}) of action sequences in `{hand_history_str}`")

            return cls( name=name,
                        ante_amount=some_dict['ante_amount'],
                        big_blind_amount=some_dict['big_blind_amount'],
                        small_blind_amount=some_dict['small_blind_amount'],
                        playing_seats=playing_seats,
                        button_assignment=button_assignment,
                        blind_bet_sequence=HandHistoryParser.parse_blind_bet_sequence(hand_history_str),
                        action_sequences=all_action_sequences,
                        community_cards=community_cards )
        except KeyError as e:
            raise ValueError(f"Failed to create {cls.__name__} due to missing field `{e}` !")



