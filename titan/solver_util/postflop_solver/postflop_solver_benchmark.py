from __future__ import annotations
import typing
from titan.solver_util.solution_tree import (
    StrategyOption,
    FoldOption,
    CallOption,
    CheckOption,
    RaiseOption,
    SolvedSpot
)
from titan.solver_util.postflop_solver.types import (
    PostflopSolverConfig
)
from titan.solver_util.postflop_solver.postflop_range_map import (
    PostflopRangeMap
)
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence,
    ButtonAssignment,
    SeatStack,
    Spot,
    BettingRound,
    PreflopBettingRound,
    FlopBettingRound,
    TurnBettingRound,
    RiverBettingRound
)
from titan.solver_util.hand_range.hand_combo_map import (
    HandComboMap
)

class MatrixRow:

    __slots__ = (   '_index',
                    '_values'  )

    def __init__(self, index: int, values: typing.Tuple[int, ...]):
        self._index = index
        self._values = values

    def index(self) -> int:
        return self._index

    def values(self) -> typing.Tuple[int, ...]:
        return self._values

    def __str__(self):
        return f"{self.__class__.__name__}(index={self.index()}, values={self.values()})"

    def __repr__(self):
        return f"{self.__class__.__name__}(index={self.index()}, values={self.values()})"

    def __eq__(self, other):
        return (    type(other) == type(self) and
                    other.index() == self.index()  and
                    other.values() == self.values()  )

    def __hash__(self):
        return hash((self.index(), self.values()))

    def serialize_to_dict(self) -> dict:
        return {'index': self.index(), 'values': self.values()}

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> MatrixRow:
        try:
            return cls( index=int(some_dict['index']),
                        values=tuple(int(v) for v in some_dict['values']) )
        except KeyError as e:
            raise ValueError(f"{cls.__name__}.create_from_dict() failed:  Missing key `{e}`")



class SolvedSpotExtract:

    __slots__ = (   '_strategy_options',
                    '_ev_matrix_rows',
                    '_strategy_matrix_rows'  )

    def __init__(self, strategy_options: typing.Tuple[StrategyOption, ...],
                        ev_matrix_rows: typing.Tuple[MatrixRow, ...],
                        strategy_matrix_rows: typing.Tuple[MatrixRow, ...]):
        self._strategy_options = strategy_options
        self._ev_matrix_rows = ev_matrix_rows
        self._strategy_matrix_rows = strategy_matrix_rows

    @classmethod
    def serialize_strategy_option(cls, strategy_option: StrategyOption):
        if type(strategy_option) == FoldOption:
            return ('f',)
        elif type(strategy_option) == CheckOption:
            return ('x',)
        elif type(strategy_option) == CallOption:
            return ('c',)
        elif type(strategy_option) == RaiseOption:
            return ('r', strategy_option.amount(), strategy_option.pot_size_ratio_bps())

    @classmethod
    def deserialize_strategy_option(cls, option_tuple: tuple) -> StrategyOption:
        if option_tuple[0] == 'f':
            return FoldOption()
        elif option_tuple[0] == 'x':
            return CheckOption()
        elif option_tuple[0] == 'c':
            return CallOption()
        elif option_tuple[0] == 'r':
            try:
                return RaiseOption( amount=int(option_tuple[1]),
                                    pot_size_ratio_bps=int(option_tuple[2]) )
            except (ValueError, IndexError) as e:
                raise ValueError(f"Failed to deserialize RaiseOption from `{option_tuple}`")
            return RaiseOption(amount)
        else:
            raise ValueError(f"Failed to deserialize StrategyOption from `{option_tuple}`")


    def strategy_options(self) -> typing.Tuple[StrategyOption, ...]:
        return self._strategy_options

    def ev_matrix_rows(self) -> typing.Tuple[MatrixRow, ...]:
        return self._ev_matrix_rows

    def strategy_matrix_rows(self) -> typing.Tuple[MatrixRow, ...]:
        return self._strategy_matrix_rows

    def __str__(self):
        return f"{self.__class__.__name__}(strategy_options={tuple(str(opt) for opt in self.strategy_options())}, ev_matrix_rows={self.ev_matrix_rows()}, strategy_matrix_rows={self.strategy_matrix_rows()})"

    def __repr__(self):
        return f"{self.__class__.__name__}(strategy_options={tuple(repr(opt) for opt in self.strategy_options())}, ev_matrix_rows={self.ev_matrix_rows()}, strategy_matrix_rows={self.strategy_matrix_rows()})"

    def __eq__(self, other):
        return (    type(other) == type(self) and
                    other.strategy_options() == self.strategy_options()  and
                    other.ev_matrix_rows() == self.ev_matrix_rows() and
                    other.strategy_matrix_rows() == self.strategy_matrix_rows()  )

    def __hash__(self):
        return hash((self.strategy_options(), self.ev_matrix_rows(), self.strategy_matrix_rows()))

    def serialize_to_dict(self) -> dict:
        return {
            'strategy_options': tuple(self.serialize_strategy_option(opt) for opt in self.strategy_options()),
            'ev_matrix_rows': tuple(row.serialize_to_dict() for row in self.ev_matrix_rows()),
            'strategy_matrix_rows': tuple(row.serialize_to_dict() for row in self.strategy_matrix_rows()),
        }

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> SolvedSpotExtract:
        try:
            return cls( strategy_options=tuple(cls.deserialize_strategy_option(opt) for opt in some_dict['strategy_options']),
                        ev_matrix_rows=tuple(MatrixRow.create_from_dict(r) for r in some_dict['ev_matrix_rows']),
                        strategy_matrix_rows=tuple(MatrixRow.create_from_dict(r) for r in some_dict['strategy_matrix_rows']) )
        except KeyError as e:
            raise ValueError(f"{cls.__name__}.create_from_dict() failed:  Missing key `{e}`")

    @classmethod
    def create_from_solved_spot(cls, solved_spot: SolvedSpot, combo_indexes: typing.Tuple[int, ...]) -> SolvedSpotExtract:
        return cls( strategy_options=solved_spot.strategy_options(),
                    ev_matrix_rows=tuple(MatrixRow(i, tuple(int(v) for v in solved_spot.ev_matrix().lookup(i))) for i in combo_indexes),
                    strategy_matrix_rows=tuple(MatrixRow(i, tuple(int(v) for v in solved_spot.strategy_matrix().lookup(i))) for i in combo_indexes) )


class PostflopSolverBenchmarkEntry:

    __slots__ = (   '_solver_config',
                    '_action_sequences',
                    '_solved_spot_extracts' )

    def __init__(self, solver_config: PostflopSolverConfig, action_sequences: typing.Tuple[ActionSequence, ...], solved_spot_extracts: typing.Tuple[SolvedSpotExtract, ...]):
        self._solver_config = solver_config
        self._action_sequences = action_sequences
        self._solved_spot_extracts = solved_spot_extracts

    def solver_config(self) -> PostflopSolverConfig:
        return self._solver_config

    def action_sequences(self) -> typing.Tuple[ActionSequence, ...]:
        return self._action_sequences

    def solved_spot_extracts(self) -> typing.Tuple[SolvedSpotExtract, ...]:
        return self._solved_spot_extracts

    def __str__(self):
        return f"{self.__class__.__name__}(solver_config={self.solver_config()}, action_sequences={self.action_sequences()}, solved_spot_extracts={self.solved_spot_extracts()})"

    def __repr__(self):
        return f"{self.__class__.__name__}(solver_config={self.solver_config()}, action_sequences={self.action_sequences()}, solved_spot_extracts={self.solved_spot_extracts()})"

    def __eq__(self, other):
        return (    type(other) == type(self) and
                    other.solver_config() == self.solver_config()  and
                    other.action_sequences() == self.action_sequences() and
                    other.solved_spot_extracts() == self.solved_spot_extracts()  )

    def __hash__(self):
        return hash((self.solver_config(), self.action_sequences(), self.solved_spot_extracts()))

    def serialize_to_dict(self) -> dict:
        return {
            'solver_config': self.solver_config().serialize_to_dict(),
            'action_sequences': tuple(str(action_sequence) for action_sequence in self.action_sequences()),
            'solved_spot_extracts': tuple(sse.serialize_to_dict() for sse in self.solved_spot_extracts())
        }

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PostflopSolverBenchmarkEntry:
        try:
            return cls( solver_config=PostflopSolverConfig.create_from_dict(some_dict['solver_config']),
                        action_sequences=tuple(ActionSequence.create_from_string(action_sequence_str) for action_sequence_str in some_dict['action_sequences']),
                        solved_spot_extracts=tuple(SolvedSpotExtract.create_from_dict(sse_dict) for sse_dict in some_dict['solved_spot_extracts']) )
        except KeyError as e:
            raise ValueError(f"{cls.__name__}.create_from_dict() failed:  Missing key `{e}`")

class PostflopSolverBenchmark:

    __slots__ = (   '_entries' )

    def __init__(self, entries: typing.Tuple[PostflopSolverBenchmarkEntry, ...]):
        self._entries = entries

    def entries(self) -> typing.Tuple[PostflopSolverBenchmarkEntry, ...]:
        return self._entries

    def __str__(self):
        return f"{self.__class__.__name__}(entries={self.entries()})"

    def __repr__(self):
        return f"{self.__class__.__name__}(entries={self.entries()})"

    def __eq__(self, other):
        return (    type(other) == type(self) and
                    other.entries() == self.entries()  )

    def __hash__(self):
        return hash(self.entries())

    def serialize_to_dict(self) -> dict:
        return {'entries': tuple(entry.serialize_to_dict() for entry in self.entries())}

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PostflopSolverBenchmark:
        try:
            return cls(entries=tuple(PostflopSolverBenchmarkEntry.create_from_dict(entry_dict) for entry_dict in some_dict['entries']))
        except KeyError as e:
            raise ValueError(f"{cls.__name__}.create_from_dict() failed:  Missing key `{e}`")





class _SpotModelHelper:

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
            for cur_spot in BettingRound.gen_next_spots(cur_spot, action_sequence):
                pass
            cur_spot = cls.BETTING_ROUND_CLASSES[i+1].create_initial_spot(  button_assignment=button_assignment,
                                                                            prev_spot=cur_spot )
        # last spot will be returned
        return cur_spot

    @classmethod
    def create_round_number(cls, solver_config: PostflopSolverConfig) -> int:
        action_sequences = (solver_config.preflop_action_sequence(), solver_config.flop_action_sequence(), solver_config.turn_action_sequence())
        for last_round_number, action_sequence in enumerate(action_sequences):
            if len(action_sequence) == 0:
                return last_round_number + 1
        return 3 # RIVER

    @classmethod
    def create_seat_stacks(cls, solver_config: PostflopSolverConfig) -> typing.Tuple[SeatStack]:
        return tuple((  SeatStack(  seat=seat,
                                    stack_size=stack_size  )
                            for seat, stack_size in enumerate(solver_config.deal_order_stack_sizes())  ))

    @classmethod
    def create_button_assignment(cls, solver_config: PostflopSolverConfig) -> ButtonAssignment:
        num_seats = len(solver_config.deal_order_stack_sizes())
        if num_seats == 2:
            # special headsup rule
            btn_sb_seat = 1
            return ButtonAssignment(dealer_seat=btn_sb_seat,
                                    big_blind_seat=0,
                                    small_blind_seat=btn_sb_seat)
        else:
            return ButtonAssignment(dealer_seat=(num_seats - 1), # last seat is dealer
                                    big_blind_seat=1,
                                    small_blind_seat=0)

    @classmethod
    def create_initial_spot(cls, solver_config: PostflopSolverConfig):
        street_action_sequences = ( solver_config.preflop_action_sequence(),
                                    solver_config.flop_action_sequence(),
                                    solver_config.turn_action_sequence() )
        return cls.create_new_street_spot(  seat_stacks=cls.create_seat_stacks(solver_config),
                                            button_assignment=cls.create_button_assignment(solver_config),
                                            blind_bet_sequence=solver_config.blind_bet_sequence(),
                                            prev_action_sequences=street_action_sequences[:cls.create_round_number(solver_config)]  )

    @classmethod
    def create_spot_with_cache(cls, initial_spot: Spot, action_sequence: ActionSequence, spot_cache: dict):
        # empty action sequence ?
        if not action_sequence:
            return initial_spot
        try:
            return spot_cache[action_sequence]
        except KeyError:
            action = action_sequence[-1]
            prev_spot = cls.create_spot_with_cache(initial_spot, action_sequence[:-1], spot_cache)
            if (BettingRound.is_betting_round_complete(prev_spot)) or (BettingRound.is_betting_over_in_hand(prev_spot)):
                raise ValueError(f"Did not expect prev_spot `{action_sequence[:-1]}` to be a leaf node !")
            spot = BettingRound.next_spot(prev_spot, action_sequence[-1])
            spot_cache[action_sequence] = spot
            return spot




class PostflopSolverBenchmarkFactory:

    @classmethod
    def create_solved_spot_extract(cls, spot: Spot, solved_spot: SolvedSpot, deal_order_hole_cards: typing.Tuple[str, ...]):
        if (BettingRound.is_betting_round_complete(spot)) or (BettingRound.is_betting_over_in_hand(spot)):
            raise ValueError(f"{cls.__name__}.create_entry_for_spot() cannot be called for a leaf spot !")
        acting_seat = spot.next_seats_to_act()[0]
        postflop_hand = HandComboMap.normalize_hand(deal_order_hole_cards[acting_seat])       
        return SolvedSpotExtract.create_from_solved_spot(   solved_spot=solved_spot,
                                                            combo_indexes=(PostflopRangeMap.index_for_hand(postflop_hand),)  )


    @classmethod
    def create_entry_from_solution_tree(cls, solver_config: PostflopSolverConfig, solution_tree: SolutionTree, deal_order_hole_cards: typing.Tuple[str, ...]) -> PostflopSolverBenchmarkEntry:
        initial_spot = _SpotModelHelper.create_initial_spot(solver_config)
        spot_cache = {}
        action_sequences = []
        solved_spot_extracts = []
        for node in solution_tree.gen_nodes_in_bfs_traversal():
            cur_spot = _SpotModelHelper.create_spot_with_cache( initial_spot=initial_spot,
                                                                action_sequence=node.action_sequence(),
                                                                spot_cache=spot_cache )
            if (BettingRound.is_betting_round_complete(cur_spot)) or (BettingRound.is_betting_over_in_hand(cur_spot)):
                continue
            action_sequences.append(node.action_sequence())
            solved_spot_extracts.append(cls.create_solved_spot_extract( spot=cur_spot,
                                                                        solved_spot=node.solved_spot(),
                                                                        deal_order_hole_cards=deal_order_hole_cards  ))
        return PostflopSolverBenchmarkEntry(solver_config=solver_config,
                                            action_sequences=tuple(action_sequences),
                                            solved_spot_extracts=tuple(solved_spot_extracts))


    def __init__(self):
        self._benchmark_entries = []

    def add_benchmark_entry(self, solver_config: PostflopSolverConfig, solution_tree: SolutionTree, deal_order_hole_cards: typing.Tuple[str, ...]):
        self._benchmark_entries.append(self.create_entry_from_solution_tree(solver_config, solution_tree, deal_order_hole_cards))

    def postflop_solver_benchmark(self):
        return PostflopSolverBenchmark(tuple(self._benchmark_entries))
