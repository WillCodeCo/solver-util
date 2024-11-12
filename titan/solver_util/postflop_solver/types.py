from __future__ import annotations
import typing
import enum
import numpy as np
from numpy import typing as npt
from titan.solver_util.solver_process.types import (
    SolverProcessException,
    SolverState,
    SolverConfig
)
from titan.solver_util.spot_models import (
    BlindBetSequence,
    ActionSequence
)
from titan.solver_util.hand_range import (
    HandComboMap,
    HandRange,
    PostflopHandRange,
    HandRangeEntry
)
from titan.solver_util.postflop_solver.postflop_range_map import (
    PostflopRangeMap
)




class PlayerRange:

    SIZE = PostflopRangeMap.RANGE_SIZE
    MIN_VALUE = HandRangeEntry.MIN_WEIGHT
    MAX_VALUE = HandRangeEntry.MAX_WEIGHT

    __slots__ = ('_values',)

    def __init__(self, values: npt.NDArray[np.int32]):
        self._values = values

    def __eq__(self, other):
        return np.array_equal(self.values(), other.values())

    def shape(self):
        return self._values.shape

    def values(self) -> npt.NDArray[np.int32]:
        return self._values

    def lookup_combo(self, combo: str) -> int:
        return self._values[PostflopRangeMap.index_for_hand(combo)]

    def gen_combos_for_hand(self, hand: str):
        yield from HandComboMap.gen_combos_for_hand(hand)

    def as_hand_range(self) -> PostflopHandRange:
        """Calculate the simplest possible HandRange for this PlayerRange object

        It will generate the hands in a reduced form, as simple as possible, that
        represents the range in the values array.

        Returns:
            PostflopHandRange: The return value. A PostflopHandRange object that represents this PlayerRange
        """
        return PostflopHandRange.create_from_hands_and_weights( hands=PostflopRangeMap.gen_hands(),
                                                                weights=self.values() ).simplified_hand_range()

    def serialize_to_string(self) -> str:
        return self.as_hand_range().serialize_to_string()

    @classmethod
    def create_uniform(cls):
        return cls(np.full(shape=(cls.SIZE,), fill_value=cls.MAX_VALUE, dtype=np.int32))

    @classmethod
    def create_zero(cls):
        return cls(np.full(shape=(cls.SIZE,), fill_value=cls.MIN_VALUE, dtype=np.int32))

    @classmethod
    def create_from_hand_range(cls, hand_range: HandRange):
        values = np.full(shape=(cls.SIZE,), fill_value=cls.MIN_VALUE, dtype=np.int32)
        for entry in hand_range.entries():
            for combo, weight in zip(entry.gen_combos(), entry.gen_weights()):
                values[PostflopRangeMap.index_for_hand(combo)] = weight
        return cls(values)

    @classmethod
    def create_from_string(cls, some_string: str) -> PlayerRange:
        return cls.create_from_hand_range(PostflopHandRange.create_from_string(some_string))





class SolveTreeSpecKey(enum.Enum):
    pass


class PlayerCount(SolveTreeSpecKey):
    TWO_PLAYERS = '2_PLAYERS'
    THREE_PLAYERS = '3_PLAYERS'
    FOUR_PLAYERS = '4_PLAYERS'
    FIVE_PLAYERS = '5_PLAYERS'
    SIX_PLAYERS = '6_PLAYERS'

class Street(SolveTreeSpecKey):
    FLOP = 'FLOP'
    TURN = 'TURN'
    RIVER = 'RIVER'

class ActingPosition(SolveTreeSpecKey):
    FIRST_TO_ACT = 'FIRST_TO_ACT'
    SECOND_TO_ACT = 'SECOND_TO_ACT'
    N_TO_ACT = 'N_TO_ACT'

class SpotCategory(SolveTreeSpecKey):
    DONK = 'DONK'
    BET = 'BET'
    ONE_RAISE = '1_RAISE'
    TWO_RAISE = '2_RAISE'
    N_RAISE = 'N_RAISE'


class SolveAlgorithm(enum.Enum):
    CFR = 'CFR'
    MONTE_CARLO = 'MONTE_CARLO'
    DEFAULT = 'DEFAULT'


class SolveTreeSpec:

    # We are communicating in 'basis point' style units
    #   where 1.0 or (100%)  equals 10000 bps    
    BASIS_POINTS_PER_1 = 10000


    POSITIONS_HU = (ActingPosition.FIRST_TO_ACT,
                    ActingPosition.SECOND_TO_ACT  )
    POSITIONS = (   ActingPosition.FIRST_TO_ACT,
                    ActingPosition.SECOND_TO_ACT,
                    ActingPosition.N_TO_ACT  )

    __slots__ = ('_fields',)

    def __init__(self, fields: dict):
        self._fields = fields

    def fields(self) -> dict:
        return self._fields

    @classmethod
    def serialize_value(cls, value: int) -> str:
        if (value % cls.BASIS_POINTS_PER_1) == 0:
            return str(value // cls.BASIS_POINTS_PER_1)
        else:
            return str(round(value / cls.BASIS_POINTS_PER_1, 2))

    def serialize_to_dict(self) -> dict:
        return self._fields

    def create_tree_file_string(self) -> str:
        result_lines = []
    
        available_players = list(PlayerCount)
        # ignore any trailing players not present (if its not completely empty)
        if PlayerCount.TWO_PLAYERS in self._fields:
            while available_players and (available_players[-1] not in self._fields):
                available_players.pop()

        for player_count in available_players:
            # which positions are available for this player count ?
            available_positions = self.POSITIONS_HU if player_count == PlayerCount.TWO_PLAYERS else self.POSITIONS
            # output
            result_lines.append(f"[ // {player_count}")
            for street in Street:
                result_lines.append(f"\t[ // {street}")
                for position in available_positions:
                    result_lines.append(f"\t\t[ // {position}")
                    for spot_category in SpotCategory:
                        try:
                            s_values = [self.serialize_value(v)
                                            for v in self._fields[player_count.value][street.value][position.value][spot_category.value]   ]
                            s_values = ', '.join(s_values)
                            result_lines.append(f"\t\t\t[{s_values}], // {spot_category}")
                        except KeyError:
                            result_lines.append(f"\t\t\t[], // {spot_category}")
                    # finish position block
                    maybe_comma = ',' if position != available_positions[-1] else ''
                    result_lines.append(f"\t\t]{maybe_comma}")
                # finish street block
                maybe_comma = ',' if street != Street.RIVER else ''
                result_lines.append(f"\t]{maybe_comma}")
            # finish player block
            maybe_comma = ',' if player_count != available_players[-1] else ''
            result_lines.append(f"]{maybe_comma}")
        return '\n'.join(result_lines)


    def __eq__(self, other):
        return ((type(self) == type(other)) and
                (self.fields() == other.fields()))

    @classmethod
    def create_empty(cls):
        fields = {}
        for player_count in PlayerCount:
            # which positions are available for this player count ?
            available_positions = cls.POSITIONS_HU if player_count == PlayerCount.TWO_PLAYERS else cls.POSITIONS
            #
            fields[player_count.value] = {}
            for street in Street:
                fields[player_count.value][street.value] = {}
                for position in available_positions:
                    fields[player_count.value][street.value][position.value] = {}
                    for spot_category in SpotCategory:
                        fields[player_count.value][street.value][position.value][spot_category.value] = ()
        return cls(fields)

    @classmethod
    def create_from_dict(cls, some_dict: dict):
        try:
            fields = {}
            for player_count in PlayerCount:
                # which positions are available for this player count ?
                available_positions = cls.POSITIONS_HU if player_count == PlayerCount.TWO_PLAYERS else cls.POSITIONS
                #
                fields[player_count.value] = {}
                for street in Street:
                    fields[player_count.value][street.value] = {}
                    for position in available_positions:
                        fields[player_count.value][street.value][position.value] = {}
                        for spot_category in SpotCategory:
                            try:
                                # dict might have enums for keys
                                fields[player_count.value][street.value][position.value][spot_category.value] = tuple(some_dict[player_count][street][position][spot_category])
                            except KeyError:
                                # or string keys
                                fields[player_count.value][street.value][position.value][spot_category.value] = tuple(some_dict[player_count.value][street.value][position.value][spot_category.value])

            return cls(fields)
        except KeyError as e:
            raise ValueError(f"{cls.__name__}.create_from_dict() failed:  Missing key `{e}`")





class PostflopSolverConfig(SolverConfig):
    
    __slots__ = (   '_serialize_to_dict_cache',
                    '_solve_tree_spec',
                    '_num_threads',
                    '_solving_time',
                    '_deal_order_stack_sizes',
                    '_big_blind_amount',
                    '_blind_bet_sequence',                  
                    '_preflop_action_sequence',
                    '_flop_action_sequence',
                    '_turn_action_sequence',
                    '_community_cards',
                    '_player_ranges',
                    '_solve_algorithm',
                    '_force_action_sequence'  )

    def __init__(self, solve_tree_spec: SolveTreeSpec,
                        num_threads: int,
                        solving_time: int,
                        deal_order_stack_sizes: typing.Tuple[int],
                        big_blind_amount: int,
                        blind_bet_sequence: BlindBetSequence,
                        preflop_action_sequence: ActionSequence,
                        flop_action_sequence: ActionSequence,
                        turn_action_sequence: ActionSequence,
                        community_cards: typing.Tuple[str],
                        player_ranges: typing.Tuple[PlayerRange],
                        solve_algorithm: SolveAlgorithm = SolveAlgorithm.DEFAULT,
                        force_action_sequence: ActionSequence = ActionSequence.create_empty()):
        self._solve_tree_spec = solve_tree_spec
        self._num_threads = num_threads
        self._solving_time = solving_time
        self._deal_order_stack_sizes = deal_order_stack_sizes
        self._big_blind_amount = big_blind_amount
        self._blind_bet_sequence = blind_bet_sequence
        self._preflop_action_sequence = preflop_action_sequence
        self._flop_action_sequence = flop_action_sequence
        self._turn_action_sequence = turn_action_sequence
        self._community_cards = community_cards
        self._player_ranges = player_ranges
        self._solve_algorithm = solve_algorithm
        self._force_action_sequence = force_action_sequence

    def solve_tree_spec(self):
        return self._solve_tree_spec

    def num_threads(self):
        return self._num_threads

    def solving_time(self):
        return self._solving_time

    def deal_order_stack_sizes(self):
        return self._deal_order_stack_sizes

    def big_blind_amount(self):
        return self._big_blind_amount

    def blind_bet_sequence(self):
        return self._blind_bet_sequence

    def preflop_action_sequence(self):
        return self._preflop_action_sequence

    def flop_action_sequence(self):
        return self._flop_action_sequence

    def turn_action_sequence(self):
        return self._turn_action_sequence

    def community_cards(self):
        return self._community_cards

    def player_ranges(self):
        return self._player_ranges

    def solve_algorithm(self):
        return self._solve_algorithm

    def force_action_sequence(self) -> ActionSequence:
        return self._force_action_sequence

    def __eq__(self, other):
        return ((type(self) == type(other)) and
                (self.solve_tree_spec() == other.solve_tree_spec()) and
                (self.num_threads() == other.num_threads()) and
                (self.solving_time() == other.solving_time()) and
                (self.deal_order_stack_sizes() == other.deal_order_stack_sizes()) and
                (self.big_blind_amount() == other.big_blind_amount()) and
                (self.blind_bet_sequence() == other.blind_bet_sequence()) and
                (self.preflop_action_sequence() == other.preflop_action_sequence()) and
                (self.flop_action_sequence() == other.flop_action_sequence()) and
                (self.turn_action_sequence() == other.turn_action_sequence()) and
                (self.community_cards() == other.community_cards()) and
                (self.player_ranges() == other.player_ranges()) and
                (self.solve_algorithm() == other.solve_algorithm()) and
                (self.force_action_sequence() == other.force_action_sequence()))

    def serialize_to_dict(self) -> dict:
        if hasattr(self, '_serialize_to_dict_cache'):
            return self._serialize_to_dict_cache
        else:
            self._serialize_to_dict_cache = {
                'solve_tree_spec': self.solve_tree_spec().serialize_to_dict() if self.solve_tree_spec() else None,
                'num_threads': self.num_threads(),
                'solving_time': self.solving_time(),
                'deal_order_stack_sizes': self.deal_order_stack_sizes(),
                'big_blind_amount': self.big_blind_amount(),
                'blind_bet_sequence': str(self.blind_bet_sequence()),
                'preflop_action_sequence': str(self.preflop_action_sequence()),
                'flop_action_sequence': str(self.flop_action_sequence()),
                'turn_action_sequence': str(self.turn_action_sequence()),
                'community_cards': self.community_cards(),
                'player_ranges': tuple((pr.serialize_to_string() for pr in self.player_ranges())),
                'solve_algorithm': self.solve_algorithm().value,
                'force_action_sequence': str(self.force_action_sequence())
            }
            return self._serialize_to_dict_cache

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PostflopSolverConfig:
        try:
            result = cls(   solve_tree_spec=SolveTreeSpec.create_from_dict(some_dict['solve_tree_spec']) if some_dict['solve_tree_spec'] else None,
                            num_threads=int(some_dict['num_threads']),
                            solving_time=int(some_dict['solving_time']),
                            deal_order_stack_sizes=tuple((int(ss) for ss in some_dict['deal_order_stack_sizes'])),
                            big_blind_amount=int(some_dict['big_blind_amount']),
                            blind_bet_sequence=BlindBetSequence.create_from_string(some_dict['blind_bet_sequence']),
                            preflop_action_sequence=ActionSequence.create_from_string(some_dict['preflop_action_sequence']),
                            flop_action_sequence=ActionSequence.create_from_string(some_dict['flop_action_sequence']),
                            turn_action_sequence=ActionSequence.create_from_string(some_dict['turn_action_sequence']),
                            community_cards=tuple((str(card) for card in some_dict['community_cards'])),
                            player_ranges=tuple((   PlayerRange.create_from_string(pr)
                                                        for pr in some_dict['player_ranges'])  ),
                            solve_algorithm=SolveAlgorithm(some_dict.get('solve_algorithm', SolveAlgorithm.DEFAULT.value)),
                            force_action_sequence=ActionSequence.create_from_string(some_dict.get('force_action_sequence', '')) )
            # include this caching for a performance improvement
            result._serialize_to_dict_cache = some_dict
            return result
        except KeyError as e:
            raise ValueError(f"Cannot create {cls.__name__}. Missing field `{e}`")
        except AssertionError as e:
            raise ValueError(f"Cannot create {cls.__name__}. {e}")
        except TypeError as e:
            raise ValueError(f"Could not create {cls.__name__} due to type mismatch: {e}")