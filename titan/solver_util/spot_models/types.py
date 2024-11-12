from __future__ import annotations
import re
import typing



class BlindBet(tuple):
    def __new__ (cls, live_amount: int, dead_amount: int, is_straddle: bool):
        return super().__new__(cls, (live_amount, dead_amount, is_straddle))

    def __getnewargs__(self):
        return tuple(self)

    def live_amount(self):
        return self[0]

    def dead_amount(self):
        return self[1]

    def is_straddle(self):
        return self[2]

    def total_amount(self):
        return self.live_amount() + self.dead_amount()

    def __repr__(self):
        return f"BlindBet({self.live_amount()}, {self.dead_amount()}, {self.is_straddle()})"

    def __str__(self):
        if self.is_straddle():
            if self.dead_amount() == 0:
                return f"s{self.live_amount()}"
            else:
                return f"s{self.live_amount()}:{self.dead_amount()}"
        else:
            if self.dead_amount() == 0:
                return f"b{self.live_amount()}"
            else:
                return f"b{self.live_amount()}:{self.dead_amount()}"

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))    )

    def __hash__(self):
        return hash((type(self), tuple(self)))

class BlindBetSequence(tuple):

    STRADDLE_BB_MULTIPLIER = 2
    BLIND_BET_SEQUENCE_PATTERN = re.compile(r"^([sb]\d+|[sb]\d+\:\d+)*$")
    BLIND_BET_PATTERN = re.compile(r"([sb])(\d+)(?:\:(\d+))?")

    def __new__ (cls, blind_bets: typing.Tuple[BlindBet]):
        if type(blind_bets) != tuple:
            raise ValueError((  f"Invalid blind_bets type `{type(blind_bets)}` for " +
                                f"BlindBetSequence. Should be a tuple of BlindBet values."  ))
        return super().__new__(cls, blind_bets)

    def __getnewargs__(self):
        return (tuple(self),)

    def __add__(self, other) -> BlindBetSequence:
        if type(other) not in {BlindBet, BlindBetSequence}:
            raise ValueError(f"Invalid type of `other` (`{type(other)}`) in BlindBetSequence.__add__()")
        return BlindBetSequence(tuple(self) + tuple(other))

    def __repr__(self):
        return 'BlindBetSequence(' +','.join((repr(blind_bet) for blind_bet in self)) + ')'

    def __str__(self):
        return ''.join((str(blind_bet) for blind_bet in self))

    def __getitem__(self, key):
        if type(key) == slice:
            return BlindBetSequence(super().__getitem__(key))
        else:
            return super().__getitem__(key)

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))   )

    def __hash__(self):
        return hash(tuple(self))

    def parent(self) -> BlindBetSequence:
        return self[:-1]

    @classmethod
    def create_from_string(cls, some_string: str) -> BlindBetSequence:
        if not re.match(cls.BLIND_BET_SEQUENCE_PATTERN, some_string):
            raise ValueError(f"Invalid BlindBetSequence `{some_string}`")
        blind_bets = tuple((    BlindBet(   live_amount=int(match[1]),
                                            dead_amount=int(match[2]) if match[2] else 0,
                                            is_straddle=(match[0] == 's')  )
                                    for match in re.findall(cls.BLIND_BET_PATTERN, some_string)  ))
        return BlindBetSequence(blind_bets)
            
    @classmethod
    def create_empty(cls) -> BlindBetSequence:
        return cls(())

    @classmethod
    def create_default(cls, num_seats: int, big_blind_amount: int, small_blind_amount: int,
                            ante_amount: int, has_small_blind: bool, num_straddles: int) -> BlindBetSequence:
        if num_seats == 2:
            if num_straddles > 0:
                raise ValueError(f"Cannot have straddles in heads-up!")
            elif not has_small_blind:
                raise ValueError(f"Small-blind must be present in heads-up hand, because it is the BTN !")
            return BlindBetSequence((   BlindBet(   live_amount=small_blind_amount,
                                                    dead_amount=ante_amount,
                                                    is_straddle=False  ),
                                        BlindBet(   live_amount=big_blind_amount,
                                                    dead_amount=ante_amount,
                                                    is_straddle=False  )   ))
        # otherwise
        if has_small_blind:
            blind_bets = (  BlindBet(   live_amount=small_blind_amount,
                                        dead_amount=ante_amount,
                                        is_straddle=False  ),
                            BlindBet(   live_amount=big_blind_amount,
                                        dead_amount=ante_amount,
                                        is_straddle=False  ) )
        else:
            blind_bets = (  BlindBet(   live_amount=big_blind_amount,
                                        dead_amount=ante_amount,
                                        is_straddle=False  ), )
        # straddlers
        next_straddle_amount = cls.STRADDLE_BB_MULTIPLIER * big_blind_amount
        for _ in range(num_straddles):
            blind_bets += ( BlindBet(   live_amount=next_straddle_amount,
                                        dead_amount=ante_amount,
                                        is_straddle=True  ), )
            next_straddle_amount = cls.STRADDLE_BB_MULTIPLIER * next_straddle_amount
        # rest of the seats need to put antes ?
        if (ante_amount > 0):
            while len(blind_bets) < num_seats:
                blind_bets += ( BlindBet(   live_amount=0,
                                            dead_amount=ante_amount,
                                            is_straddle=False  ), )
        return BlindBetSequence(blind_bets)


class Action(tuple):
    
    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))    )

    def __hash__(self):
        return hash((type(self), tuple(self)))

class CheckAction(Action):

    def __new__ (cls):
        return tuple.__new__(cls, ('x',))

    def __getnewargs__(self):
        return ()

    def __repr__(self):
        return "CheckAction()"

    def __str__(self):
        return "x"

class CallAction(Action):

    def __new__ (cls):
        return tuple.__new__(cls, ('c',))

    def __getnewargs__(self):
        return ()

    def __repr__(self):
        return "CallAction()"

    def __str__(self):
        return "c"

class FoldAction(Action):

    def __new__ (cls):
        return tuple.__new__(cls, ('f',))

    def __getnewargs__(self):
        return ()

    def __repr__(self):
        return "FoldAction()"

    def __str__(self):
        return "f"

class RaiseAction(Action):

    def __new__ (cls, amount: int):
        return tuple.__new__(cls, ('r', amount))

    def __getnewargs__(self):
        return (self.amount(),)

    def amount(self):
        return self[1]

    def __repr__(self):
        return f"RaiseAction({self.amount()})"

    def __str__(self):
        return "r"+str(self.amount())


class ActionSequence(tuple):

    ACTION_SEQUENCE_PATTERN = re.compile(r"^(c|f|x|r\d+)*$")
    ACTION_PATTERN = re.compile(r"(c|f|x|r\d+)")

    def __new__ (cls, actions: typing.Tuple[Action]):
        if type(actions) != tuple:
            raise ValueError((  f"Invalid actions type `{type(actions)}` for " +
                                f"ActionSequence. Should be a tuple of Action values."  ))
        return super().__new__(cls, actions)

    def __getnewargs__(self):
        return (tuple(self),)

    def __add__(self, other) -> ActionSequence:
        if isinstance(other, Action):
            return ActionSequence(tuple(self) + (other,))
        elif type(other) == ActionSequence:
            return ActionSequence(tuple(self) + tuple(other))
        else:
            raise ValueError(f"Invalid type of `other` (`{type(other)}`) in ActionSequence.__add__()")
        

    def __repr__(self):
        return 'ActionSequence(' +','.join((repr(action) for action in self)) + ')'

    def __str__(self):
        return ''.join((str(action) for action in self))

    def __getitem__(self, key):
        if type(key) == slice:
            return ActionSequence(super().__getitem__(key))
        else:
            return super().__getitem__(key)

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))   )

    def __hash__(self):
        return hash(tuple(self))

    def gen_prefixes(self) -> typing.Iterable[ActionSequence]:
        """Generate all ActionSequences that are a prefix of this ActionSequence,
        including itself

        Returns:
            A generator of ActionSequences
        """
        yield from (self[:l] for l in range(0, len(self) + 1))

    def parent(self) -> ActionSequence:
        return self[:-1]

    @classmethod
    def create_from_string(cls, some_string: str) -> ActionSequence:
        if not re.match(cls.ACTION_SEQUENCE_PATTERN, some_string):
            raise ValueError(f"Invalid ActionSequence `{some_string}`")
        actions = []
        for match in re.findall(cls.ACTION_PATTERN, some_string):
            if match[0] == 'c':
                actions.append(CallAction())
            elif match[0] == 'x':
                actions.append(CheckAction())
            elif match[0] == 'f':
                actions.append(FoldAction())
            elif match[0] == 'r':
                try:
                    actions.append(RaiseAction(int(match[1:])))
                except ValueError:
                    raise ValueError(f"Invalid token in ActionSequence `{match}`")
            else:
                raise ValueError(f"Invalid token in ActionSequence `{match}`")
        return ActionSequence(tuple(actions))

    @classmethod
    def create_empty(cls) -> ActionSequence:
        return cls(())

class ButtonAssignment:

    __slots__ = (   '_dealer_seat',
                    '_small_blind_seat',
                    '_big_blind_seat'  )

    def __init__(self, dealer_seat: typing.Optional[int],
                        small_blind_seat: typing.Optional[int],
                        big_blind_seat: typing.Optional[int]):
        self._dealer_seat = dealer_seat
        self._small_blind_seat = small_blind_seat
        self._big_blind_seat = big_blind_seat

    def dealer_seat(self) -> int:
        if (not self.has_dealer()):
            raise ValueError("Dealer button has not been assigned to a seat")
        return self._dealer_seat

    def small_blind_seat(self) -> int:
        if (not self.has_small_blind()):
            raise ValueError("Small blind button has not been assigned to a seat")
        return self._small_blind_seat

    def big_blind_seat(self) -> int:
        if (not self.has_big_blind()):
            raise ValueError("Big blind button has not been assigned to a seat")
        return self._big_blind_seat

    def has_dealer(self) -> bool:
        return (self._dealer_seat is not None)

    def has_small_blind(self) -> bool:
        return (self._small_blind_seat is not None)

    def has_big_blind(self) -> bool:
        return (self._big_blind_seat is not None)



class SeatStack(tuple):

    def __new__(cls, seat: int, stack_size: int):
        return tuple.__new__(cls, (seat, stack_size))

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))    )

    def __hash__(self):
        return hash((type(self), tuple(self)))

    def seat(self) -> int:
        return self[0]

    def stack_size(self) -> int:
        return self[1]



class SeatSpend(tuple):

    def __new__(cls, live_amount: int, dead_amount: int):
        return tuple.__new__(cls, (live_amount, dead_amount))

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))    )

    def __hash__(self):
        return hash((type(self), tuple(self)))

    def live_amount(self) -> int:
        return self[0]

    def dead_amount(self) -> int:
        return self[1]

    def total_amount(self) -> int:
        return self.live_amount() + self.dead_amount()




class Spot(tuple):

    def __new__(cls, ordered_seats: typing.Tuple[int],
                        stack_sizes: typing.Tuple[int],
                        seat_folds: typing.Tuple[bool],
                        seat_spends: typing.Tuple[SeatSpend],
                        next_seats_to_act: typing.Tuple[int]):
        return tuple.__new__(cls, ( ordered_seats,
                                    stack_sizes,
                                    seat_folds,
                                    seat_spends,
                                    next_seats_to_act ))

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (tuple(self) == tuple(other))    )

    def __hash__(self):
        return hash((type(self), tuple(self)))

    def ordered_seats(self) -> typing.Tuple[int]:
        return self[0]

    def stack_sizes(self) -> typing.Tuple[int]:
        return self[1]

    def seat_folds(self) -> typing.Tuple[bool]:
        return self[2]

    def seat_spends(self) -> typing.Tuple[SeatSpend]:
        return self[3]

    def next_seats_to_act(self) -> typing.Tuple[int]:
        return self[4]

    def total_seat_spends(self) -> int:
        return sum((    self.seat_spends()[seat].total_amount()
                            for seat in self.ordered_seats()    ))

    def remaining_stack_sizes(self) -> typing.Tuple[int]:
        return tuple((  self.stack_sizes()[seat] - self.seat_spends()[seat].total_amount()
                            for seat in range(self.num_seats_at_table())  ))

    def seat_stacks(self) -> typing.Tuple[int]:
        return tuple((  SeatStack(seat, self.stack_sizes()[seat])
                            for seat in self.ordered_seats()  ))

    def remaining_seat_stacks(self) -> typing.Tuple[int]:
        return tuple((  SeatStack(seat, self.stack_sizes()[seat] - self.seat_spends()[seat].total_amount())
                            for seat in self.ordered_seats()  ))

    def can_check(self, seat: int) -> bool:
        return (self.seat_spends()[seat].live_amount() == self.maximum_bet())

    def is_folded_seat(self, seat: int) -> bool:
        return self.seat_folds()[seat]

    def is_all_in_seat(self, seat: int) -> bool:
        return (self.seat_spends()[seat].total_amount() == self.stack_sizes()[seat])

    def is_active_seat(self, seat: int) -> bool:
        return (not self.is_folded_seat(seat)) and (not self.is_all_in_seat(seat))

    def has_next_seats_to_act(self) -> bool:
        return (self.next_seats_to_act() != ())

    def maximum_bet(self) -> int:
        return max((    self.seat_spends()[seat].live_amount()
                            for seat in self.ordered_seats()    ))

    def num_seats(self) -> int:
        return len(self.ordered_seats())

    def num_seats_at_table(self) -> int:
        return len(self.stack_sizes())

    def num_active_seats(self) -> int:
        return sum((1 for seat in self.ordered_seats() if self.is_active_seat(seat)))

    def num_active_seats_need_to_call(self) -> int:
        return sum((1 for seat in self.ordered_seats()
                        if ((self.is_active_seat(seat)) and
                            (not self.can_check(seat)))   ))

    def gen_next_active_seats(self, origin_seat: int) -> typing.Iterator[int]:
        ordered_seats = self.ordered_seats()
        if origin_seat >= ordered_seats[-1]:
            # origin seat is at the end of the list, so wrap around !
            pos = 0
        else:
            pos = next((    pos for pos in range(self.num_seats())
                                if ordered_seats[pos] > origin_seat  ))
        return (seat for seat in (ordered_seats[pos:] + ordered_seats[:pos])[:-1]
                        if self.is_active_seat(seat))
