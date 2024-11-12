from __future__ import annotations
import typing
import pathlib
import os
from titan.solver_util.spot_models import (
    BlindBet,
    Action,
    FoldAction,
    RaiseAction,
    CheckAction,
    CallAction,
    SeatOrdering
)
from titan.solver_util.hand_history import (
    HandHistory,
    PlayingSeat
)
from titan.solver_util.solution_tree import (
    SolutionTree,
    SolutionTreeNode,
    StrategyOption,
)
from titan.solver_util.hand_range import (
    HandComboMap
)
from titan.solver_util.preflop_solver.preflop_range_map import (
    PreflopRangeMap
)
from titan.solver_util.postflop_solver.postflop_range_map import (
    PostflopRangeMap
)



class _ReportEntry:
    pass

class _SeparatorEntry:

    INDENT = ''

    def __init__(self, separator_str: str):
        self._separator_str = separator_str

    def __str__(self):
        return f"{self.INDENT}{self._separator_str}"


class _SolverFeedbackEntry(_ReportEntry):
    pass

class _PreflopFeedbackEntry(_SolverFeedbackEntry):

    __slots__ = (   '_options',
                    '_frequencies',
                    '_evs'  )

    INDENT = '        '
    MAX_FREQUENCY = 10000
    MAX_EV = MAX_FREQUENCY

    def __init__(self, options: typing.Tuple[StrategyOption, ...], frequencies: typing.Tuple[int, ...],
                                                                    evs: typing.Tuple[int, ...]):
        self._options = options
        self._frequencies = frequencies
        self._evs = evs

    def options(self):
        return self._options

    def frequencies(self):
        return self._frequencies

    def evs(self):
        return self._evs

    def __str__(self):
        horiz_border = '------------------------------------------'
        options = [ f"{'FREQ'.rjust(6)}{'EV'.rjust(8)}    OPTION",
                    f"{'----'.rjust(6)}------------------------" ]
        items = zip(self.options(), self.frequencies(), self.evs())
        options += [f"{100*freq/self.MAX_FREQUENCY:>6.1f}{ev/self.MAX_EV:>8.1f}    {opt}"
                        for opt, freq, ev in sorted(items, key=lambda x: -x[1])]
        return (self.INDENT + horiz_border + '\n' +
                self.INDENT+'|'+('\n'+self.INDENT+'|').join(options) + '\n' + 
                self.INDENT + horiz_border)

    @classmethod
    def create(cls, solved_spot: SolvedSpot, hole_cards: str):
        hand = HandComboMap.preflop_hand_for_combo(hole_cards)
        return cls( options=solved_spot.strategy_options(),
                    frequencies=solved_spot.strategy_matrix().values()[PreflopRangeMap.index_for_hand(hand)],
                    evs=solved_spot.ev_matrix().values()[PreflopRangeMap.index_for_hand(hand)] )

class _PostflopFeedbackEntry(_PreflopFeedbackEntry):

    @classmethod
    def create(cls, solved_spot: SolvedSpot, hole_cards: str):
        hand = HandComboMap.normalize_hand(hole_cards)
        return cls( options=solved_spot.strategy_options(),
                    frequencies=solved_spot.strategy_matrix().values()[PostflopRangeMap.index_for_hand(hand)],
                    evs=solved_spot.ev_matrix().values()[PostflopRangeMap.index_for_hand(hand)] )



class _PlayerSpotEntry(_ReportEntry):

    __slots__ = (   '_seat',
                    '_buttons',
                    '_hole_cards',
                    '_stack_size'  )

    INDENT = '    '

    def __init__(self, seat: int, button_assignment: ButtonAssignment, hole_cards: str, stack_size: int):
        self._seat = seat
        self._button_assignment = button_assignment
        self._hole_cards = hole_cards
        self._stack_size = stack_size

    def seat(self):
        return self._seat

    def button_assignment(self):
        return self._button_assignment

    def hole_cards(self):
        return self._hole_cards

    def stack_size(self):
        return self._stack_size

    @classmethod
    def create_buttons(cls, button_assignment: ButtonAssignment, seat: int):
        result = []
        if button_assignment.big_blind_seat() == seat:
            result.append('BB')
        if button_assignment.small_blind_seat() == seat:
            result.append('SB')
        if button_assignment.dealer_seat() == seat:
            result.append('BTN')
        return tuple(result)


    def __str__(self):
        buttons_str = ''.join(f"({btn})" for btn in self.create_buttons(button_assignment=self.button_assignment(),
                                                                        seat=self.seat()))
        player_meta = f"#{self._seat} |{self.hole_cards()}|{buttons_str:>10} [{self.stack_size():>8}]"
        return self.INDENT + player_meta




class _PlayerBlindBetEntry(_PlayerSpotEntry):

    __slots__ = ('_blind_bet',)

    def __init__(self, seat: int, button_assignment: ButtonAssignment, hole_cards: str, stack_size: int, blind_bet: BlindBet):
        super().__init__(   seat=seat,
                            button_assignment=button_assignment,
                            hole_cards=hole_cards,
                            stack_size=stack_size  )
        self._blind_bet = blind_bet

    def blind_bet(self):
        return self._blind_bet

    @classmethod
    def blind_bet_to_str(cls, seat: int, button_assignment: ButtonAssignment, blind_bet: BlindBet) -> str:
        ante_str = f"ANTE({blind_bet.dead_amount()}); " if blind_bet.dead_amount() > 0 else ""
        if blind_bet.is_straddle():
            return ante_str + f"STRADDLE({blind_bet.live_amount()})"
        elif seat == button_assignment.big_blind_seat():
            return ante_str + f"BB({blind_bet.live_amount()})"
        elif seat == button_assignment.small_blind_seat():
            return ante_str + f"SB({blind_bet.live_amount()})"
        elif blind_bet.live_amount() > 0:
            return ante_str + f"POST({blind_bet.live_amount()})"
        elif blind_bet.dead_amount() > 0:
            return ante_str

    def __str__(self) -> str:
        return super().__str__() + ' ' + self.blind_bet_to_str( seat=self.seat(),
                                                                button_assignment=self.button_assignment(),
                                                                blind_bet=self.blind_bet() )

    @classmethod
    def create(cls, button_assignment: ButtonAssignment, seat: int, stack_size: int, blind_bet: BlindBet):
        return cls( seat=seat,
                    button_assignment=button_assignment,
                    hole_cards='****',
                    stack_size=stack_size,
                    blind_bet=blind_bet  )


class _PlayerActionEntry(_PlayerSpotEntry):

    __slots__ = ('_solver_feedback_entry', '_action')

    def __init__(self, seat: int, button_assignment: ButtonAssignment, hole_cards: str, stack_size: int,
                                                                                        solver_feedback_entry: _SolverFeedbackEntry,
                                                                                        action: Action):
        super().__init__(   seat=seat,
                            button_assignment=button_assignment,
                            hole_cards=hole_cards,
                            stack_size=stack_size  )
        self._solver_feedback_entry = solver_feedback_entry
        self._action = action

    def solver_feedback_entry(self):
        return self._solver_feedback_entry

    def action(self):
        return self._action

    @classmethod
    def action_to_str(cls, action: Action) -> str:
        if type(action) == FoldAction:
            return "FOLD"
        elif type(action) == CheckAction:
            return "CHECK"
        elif type(action) == CallAction:
            return "CALL"
        elif type(action) == RaiseAction:
            return f"RAISE {action.amount()}"

    def __str__(self):
        return (    super().__str__() + '\n' +
                    str(self.solver_feedback_entry()) + '\n' +
                    self.INDENT + '    >>\n' +
                    self.INDENT + '    >> ' + self.action_to_str(self.action()) + '\n' +
                    self.INDENT + '    >>'  )

    @classmethod
    def create(cls, button_assignment: ButtonAssignment, hole_cards: str, seat: int, stack_size: int,
                                                                        solver_feedback_entry: _SolverFeedbackEntry,
                                                                        action: Action):
        return cls( seat=seat,
                    button_assignment=button_assignment,
                    hole_cards=hole_cards,
                    stack_size=stack_size,
                    solver_feedback_entry=solver_feedback_entry,
                    action=action )



class PlayerFeedbackReport:

    __slots__ = ('_report_entries',)

    def __init__(self, report_entries: typing.Tuple[_ReportEntry, ...]):
        self._report_entries = report_entries


    def save_to_filesystem(self, path: str):
        cur_path = pathlib.Path(path)
        with open(cur_path / 'feedback.txt', 'w') as f:
            for entry in self._report_entries:
                f.write(f"{entry}\n")

    @classmethod
    def gen_report_entries_for_street(cls, hand_history: HandHistory, spots, action_sequence, solver_feedback_entry_gen):
        playing_seat_map = {ps.seat(): ps for ps in hand_history.playing_seats()}
        for spot, action, solver_feedback_entry in zip(spots, action_sequence, solver_feedback_entry_gen):
            acting_seat = spot.next_seats_to_act()[0]
            stack_size = spot.stack_sizes()[acting_seat] - spot.seat_spends()[acting_seat].total_amount()
            yield _PlayerActionEntry.create(button_assignment=hand_history.button_assignment(),
                                            seat=acting_seat,
                                            hole_cards=''.join(playing_seat_map[acting_seat].hole_cards()),
                                            stack_size=stack_size,
                                            solver_feedback_entry=solver_feedback_entry,
                                            action=action)
            yield _SeparatorEntry('')


    @classmethod
    def gen_report_entries(cls, hand_history: HandHistory, solution_trees: typing.Tuple[SolutionTree, ...]):
        
        # hand summary title
        blind_structure = ( f"{hand_history.small_blind_amount()}/" +
                            f"{hand_history.big_blind_amount()}/" +
                            f"{hand_history.ante_amount()}" )
        yield _SeparatorEntry(f'== HAND: {blind_structure} : {hand_history.situation_string()}')


        # blind bets
        yield _SeparatorEntry("\n==== BLIND BETS\n")

        playing_seat_map = {ps.seat(): ps for ps in hand_history.playing_seats()}
        acting_seats = tuple(ps.seat() for ps in hand_history.playing_seats())

        # check hand history is good
        assert all(ps.has_hole_cards() for ps in hand_history.playing_seats())

        blind_seats = SeatOrdering.blind_bet_ordering(seats=acting_seats,
                                                      button_assignment=hand_history.button_assignment())


        for seat, blind_bet in zip(blind_seats, hand_history.blind_bet_sequence()):
            yield _PlayerBlindBetEntry.create(  button_assignment=hand_history.button_assignment(),
                                                seat=seat,
                                                stack_size=playing_seat_map[seat].stack_size(),
                                                blind_bet=blind_bet  )

        yield _SeparatorEntry("\n==== PREFLOP\n")


        assert len(solution_trees) >= 1

        acting_seat_gen = (spot.next_seats_to_act()[0] for spot in hand_history.gen_preflop_spots())
        hole_cards_gen = (playing_seat_map[seat].hole_cards() for seat in acting_seat_gen)
        solved_spot_gen = (node.solved_spot()
                            for node in solution_trees[0].gen_nodes_on_path(hand_history.preflop_action_sequence()))
        feedback_entry_gen = (_PreflopFeedbackEntry.create(solved_spot, hole_cards)
                                for solved_spot, hole_cards in zip(solved_spot_gen, hole_cards_gen))


        for report_entry in cls.gen_report_entries_for_street(  hand_history=hand_history,
                                                                spots=hand_history.gen_preflop_spots(),
                                                                action_sequence=hand_history.preflop_action_sequence(),
                                                                solver_feedback_entry_gen=feedback_entry_gen  ):
            yield report_entry
        # next street ?
        if not hand_history.has_flop():
            return
        
        assert len(solution_trees) >= 2

        acting_seat_gen = (spot.next_seats_to_act()[0] for spot in hand_history.gen_flop_spots())
        hole_cards_gen = (playing_seat_map[seat].hole_cards() for seat in acting_seat_gen)
        solved_spot_gen = (node.solved_spot()
                            for node in solution_trees[1].gen_nodes_on_path(hand_history.flop_action_sequence()))
        feedback_entry_gen = (_PostflopFeedbackEntry.create(solved_spot, hole_cards)
                                for solved_spot, hole_cards in zip(solved_spot_gen, hole_cards_gen))


        yield _SeparatorEntry(f"\n==== FLOP  [{''.join(hand_history.community_cards()[:3])}]\n")
        for report_entry in cls.gen_report_entries_for_street(  hand_history=hand_history,
                                                                spots=hand_history.gen_flop_spots(),
                                                                action_sequence=hand_history.flop_action_sequence(),
                                                                solver_feedback_entry_gen=feedback_entry_gen  ):
            yield report_entry
        # next street ?
        if not hand_history.has_turn():
            return
        
        assert len(solution_trees) >= 3

        acting_seat_gen = (spot.next_seats_to_act()[0] for spot in hand_history.gen_turn_spots())
        hole_cards_gen = (playing_seat_map[seat].hole_cards() for seat in acting_seat_gen)
        solved_spot_gen = (node.solved_spot()
                            for node in solution_trees[2].gen_nodes_on_path(hand_history.turn_action_sequence()))
        feedback_entry_gen = (_PostflopFeedbackEntry.create(solved_spot, hole_cards)
                                for solved_spot, hole_cards in zip(solved_spot_gen, hole_cards_gen))


        yield _SeparatorEntry(f"\n==== TURN  [{''.join(hand_history.community_cards()[:4])}]\n")
        for report_entry in cls.gen_report_entries_for_street(  hand_history=hand_history,
                                                                spots=hand_history.gen_turn_spots(),
                                                                action_sequence=hand_history.turn_action_sequence(),
                                                                solver_feedback_entry_gen=feedback_entry_gen  ):
            yield report_entry
        # next street ?
        if not hand_history.has_river():
            return
        
        assert len(solution_trees) == 4


        acting_seat_gen = (spot.next_seats_to_act()[0] for spot in hand_history.gen_river_spots())
        hole_cards_gen = (playing_seat_map[seat].hole_cards() for seat in acting_seat_gen)
        solved_spot_gen = (node.solved_spot()
                            for node in solution_trees[3].gen_nodes_on_path(hand_history.river_action_sequence()))
        feedback_entry_gen = (_PostflopFeedbackEntry.create(solved_spot, hole_cards)
                                for solved_spot, hole_cards in zip(solved_spot_gen, hole_cards_gen))

        yield _SeparatorEntry(f"\n==== RIVER [{''.join(hand_history.community_cards())}]\n")
        for report_entry in cls.gen_report_entries_for_street(  hand_history=hand_history,
                                                                spots=hand_history.gen_river_spots(),
                                                                action_sequence=hand_history.river_action_sequence(),
                                                                solver_feedback_entry_gen=feedback_entry_gen  ):
            yield report_entry

    @classmethod
    def create(cls, hand_history: HandHistory, solution_trees: typing.Tuple[SolutionTree, ...]) -> PlayerFeedbackReport:
        return cls(report_entries=tuple(cls.gen_report_entries(hand_history, solution_trees)))
