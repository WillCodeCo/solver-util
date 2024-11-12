from __future__ import annotations
import typing
import enum
from titan.solver_util.solver_process.types import (
    SolverProcessException,
    SolverState,
    SolverConfig
)
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence
)


class PreflopBetSizingKey(enum.Enum):
    pass

class StraddleType(PreflopBetSizingKey):
    STRADDLE = 'STRADDLE'
    NO_STRADDLE = 'NO_STRADDLE'

class SpotCategory(PreflopBetSizingKey):
    ONE_BET = '1_BET'
    TWO_BET = '2_BET'
    THREE_BET = '3_BET'
    FOUR_BET = '4_BET'
    FIVE_BET = '5_BET'
    N_BET = 'N_BET'

class UnitType(PreflopBetSizingKey):
    POT_SIZE_RATIO_BPS = 'POT-SIZE-RATIO-BPS'
    CHIPS = 'CHIPS'
    PREV_RAISE_RATIO_BPS = 'PREV-RAISE-RATIO-BPS'

class SeatPosition(PreflopBetSizingKey):
    BTN = 'BTN'
    SB = 'SB'
    BB = 'BB'
    LJ = 'LJ'
    HJ = 'HJ'
    CO = 'CO'

class ActingPosition(PreflopBetSizingKey):
    IP = 'IP'
    OOP = 'OOP'

class OpenLimpMode(enum.Enum):
    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'
    BLINDS_ONLY = 'BLINDS_ONLY'
    AUTO = 'AUTO'

class RakeConfig:

    __slots__ = (   '_rake_amount_bps',
                    '_rake_cap'   )

    def __init__(self, rake_amount_bps: int, rake_cap: int):
        self._rake_amount_bps = rake_amount_bps
        self._rake_cap = rake_cap

    def rake_amount_bps(self):
        return self._rake_amount_bps

    def rake_cap(self):
        return self._rake_cap

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self.rake_amount_bps() == other.rake_amount_bps()) and
                    (self.rake_cap() == other.rake_cap())   )

    def serialize_to_dict(self) -> dict:
        return {
            'rake_amount_bps': self.rake_amount_bps(),
            'rake_cap': self.rake_cap()
        }

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> RakeConfig:
        try:
            return cls( rake_amount_bps=int(some_dict['rake_amount_bps']),
                        rake_cap=int(some_dict['rake_cap']) )
        except KeyError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with missing key: {e}")
        except ValueError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid value: {e}")
        except TypeError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid type: {e}")

class PreflopBetSizing:
    pass

class PreflopFixedBetSizing(PreflopBetSizing):

    __slots__ = ('_values', '_extra_amount_per_limper', '_unit_type')

    def __init__(self, values: typing.Tuple[int], extra_amount_per_limper: int,
                                                    unit_type: UnitType):
        self._values = values
        self._extra_amount_per_limper = extra_amount_per_limper
        self._unit_type = unit_type

    def values(self):
        return self._values

    def extra_amount_per_limper(self):
        return self._extra_amount_per_limper

    def unit_type(self):
        return self._unit_type

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self.values() == other.values()) and
                    (self.extra_amount_per_limper() == other.extra_amount_per_limper()) and
                    (self.unit_type() == other.unit_type())   )

    def serialize_to_dict(self) -> dict:
        return {    'extra_amount_per_limper': self.extra_amount_per_limper(),
                    'values': self.values(),
                    'unit': self.unit_type().value  }

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> RakeConfig:
        try:
            unit_type = UnitType(some_dict['unit'].upper())
            values = tuple((int(v) for v in some_dict['values']))                        
            extra_amount_per_limper = int(some_dict.get('extra_amount_per_limper', 0))
            assert len(values) > 0, "`values` cannot be empty !"
            return cls( values=values,                        
                        extra_amount_per_limper=extra_amount_per_limper,
                        unit_type=unit_type )
        except AssertionError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict: {e}")
        except KeyError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with missing key: {e}")
        except ValueError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid value: {e}")
        except TypeError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid type: {e}")



class PreflopPotSizeBetSizing(PreflopBetSizing):
    
    __slots__ = ('_values', )

    def __init__(self, values: typing.Tuple[int]):
        self._values = values

    def values(self):
        return self._values

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self.values() == other.values())   )

    def serialize_to_dict(self) -> dict:
        return {'values': self.values(),
                'unit': UnitType.POT_SIZE_RATIO_BPS.value}

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> RakeConfig:
        try:
            return cls(values=tuple((int(v) for v in some_dict['values'])))
        except KeyError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with missing key: {e}")
        except ValueError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid value: {e}")
        except TypeError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid type: {e}")

class PreflopPrevRaiseRatioBetSizing(PreflopBetSizing):

    __slots__ = ('_values', )

    MIN_VALUE = 10000

    def __init__(self, values: typing.Tuple[int]):
        self._values = values

    def values(self):
        return self._values

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self.values() == other.values())   )

    def serialize_to_dict(self) -> dict:
        return {'values': self.values(),
                'unit': UnitType.PREV_RAISE_RATIO_BPS.value}

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> RakeConfig:
        try:
            values=tuple((int(v) for v in some_dict['values']))
            assert all(v for v in values), f"Values {values} did not meet the minimum expected value for {cls.__name__} of {cls.MIN_VALUE}"
            return cls(values)
        except KeyError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with missing key: {e}")
        except ValueError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid value: {e}")
        except TypeError as e:
            raise ValueError(f"Could not create {cls.__name__} from dict with invalid type: {e}")


class PreflopBetSizingFactory:

    @classmethod
    def create_bet_sizing_from_dict(cls, some_dict: dict) -> PreflopBetSizing:
        try:
            assert 'unit' in some_dict, "'unit' must be present"
            unit_type = UnitType(some_dict['unit'].upper())
            if unit_type == UnitType.CHIPS:
                assert set(some_dict.keys()).issubset({'unit', 'values', 'extra_amount_per_limper'}), "Invalid keys in bet_sizing_dict"
                return PreflopFixedBetSizing.create_from_dict(some_dict)
            elif unit_type == UnitType.POT_SIZE_RATIO_BPS:
                assert set(some_dict.keys()) == {'unit', 'values'}, "Invalid keys in bet_sizing dictionary"
                return PreflopPotSizeBetSizing.create_from_dict(some_dict)
            elif unit_type == UnitType.PREV_RAISE_RATIO_BPS:
                assert set(some_dict.keys()) == {'unit', 'values'}, "Invalid keys in bet_sizing dictionary"
                return PreflopPrevRaiseRatioBetSizing.create_from_dict(some_dict)
            else:
                assert False, f"Invalid unit `{some_dict['unit']}`"
        except ValueError as e:
            raise ValueError(f"Invalid bet_sizing dictionary: {e}")
        except AssertionError as e:
            raise ValueError(f"Invalid bet_sizing dictionary: {e}")







class _SpotClassBetSizingMap:

    KEY_LOOKUP = (  {key_value.value: key_value for key_value in list(SpotCategory)} |
                    {key_value.value: key_value for key_value in list(StraddleType)} |
                    {key_value.value: key_value for key_value in list(ActingPosition)} |
                    {key_value.value: key_value for key_value in list(SeatPosition)} )

    __slots__ = ('_bet_sizing_map',)

    def __init__(self, bet_sizing_map: dict):
        self._bet_sizing_map = bet_sizing_map

    def lookup_bet_sizing(self, straddle_type: typing.Optional[StraddleType]=None,
                                spot_category: typing.Optional[SpotCategory]=None,
                                seat_position: typing.Optional[SeatPosition]=None,
                                acting_position: typing.Optional[ActingPosition]=None) -> PreflopBetSizing:
        path = ()
        if straddle_type:
            path += (straddle_type.value,)
        if spot_category:
            path += (spot_category.value,)
        if seat_position:
            path += (seat_position.value,)
        if acting_position:
            path += (acting_position.value,)
        # try with most specific path, before generalising by moving to parent
        for path_len in range(len(path), -1, -1):
            try:
                return self._bet_sizing_map[path[:path_len]]
            except KeyError as e:
                continue
        raise LookupError(f"Failed to find PreflopBetSizing for path `{path}`")

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self._bet_sizing_map == other._bet_sizing_map)  )

    def serialize_to_dict(self) -> dict:
        result = {}
        for path, bet_sizing in self._bet_sizing_map.items():
            target_dict = result
            for k in path:
                try:
                    target_dict = target_dict[k]
                except KeyError as e:
                    target_dict[k] = {}
                    target_dict = target_dict[k]
            target_dict['bet_sizing'] = bet_sizing.serialize_to_dict()
        return result

    @classmethod
    def gen_bet_sizings_from_dict(cls, some_dict: dict, cur_path: typing.Tuple[str]):
        for child_key in some_dict.keys():
            if child_key == 'bet_sizing':
                bet_sizing = PreflopBetSizingFactory.create_bet_sizing_from_dict(some_dict[child_key])
                yield (cur_path, bet_sizing)
            elif child_key in cls.KEY_LOOKUP:
                child_path = cur_path + (child_key, )
                yield from cls.gen_bet_sizings_from_dict(some_dict[child_key], child_path)
            else:
                raise ValueError(f"Invalid key `{child_key}` found in bet sizing config !")

    @classmethod
    def create_empty(cls) -> _SpotBetSizingMap:
        return cls({})

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> _SpotClassBetSizingMap:
        bet_sizing_map = {}
        for path, bet_sizing in cls.gen_bet_sizings_from_dict(some_dict, ()):
            bet_sizing_map[path] = bet_sizing
        return cls(bet_sizing_map)




class _SpotBetSizingMap:

    __slots__ = ('_bet_sizing_map',)

    def __init__(self, bet_sizing_map: dict):
        self._bet_sizing_map = bet_sizing_map

    def lookup_bet_sizing(self, action_sequence: ActionSequence):
        try:
            return self._bet_sizing_map[action_sequence]
        except KeyError as e:
            raise LookupError(f"Failed to find PreflopBetSizing for spot at path `{action_sequence}`")

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self._bet_sizing_map == other._bet_sizing_map)  )

    def serialize_to_dict(self) -> dict:
        return {    str(action_sequence): bet_sizing.serialize_to_dict()
                        for action_sequence, bet_sizing in self._bet_sizing_map.items()    }

    @classmethod
    def create_empty(cls) -> _SpotBetSizingMap:
        return cls({})

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> _SpotBetSizingMap:
        bet_sizing_map = {}
        for path, bet_sizing_dict in some_dict.items():
            action_sequence = ActionSequence.create_from_string(path)
            bet_sizing = PreflopBetSizingFactory.create_bet_sizing_from_dict(bet_sizing_dict)
            bet_sizing_map[action_sequence] = bet_sizing
        return cls(bet_sizing_map)



class PreflopBetSizingMap:

    __slots__ = (   '_spot_class_bet_sizing_map',
                    '_spot_bet_sizing_map'  )

    def __init__(self, spot_class_bet_sizing_map: _SpotClassBetSizingMap,
                        spot_bet_sizing_map: _SpotBetSizingMap):
        self._spot_class_bet_sizing_map = spot_class_bet_sizing_map
        self._spot_bet_sizing_map = spot_bet_sizing_map

    def spot_class_bet_sizing_map(self):
        return self._spot_class_bet_sizing_map

    def spot_bet_sizing_map(self):
        return self._spot_bet_sizing_map

    def lookup_bet_sizing_for_spot_class(self, straddle_type: typing.Optional[StraddleType]=None,
                                                spot_category: typing.Optional[SpotCategory]=None,
                                                seat_position: typing.Optional[SeatPosition]=None,
                                                acting_position: typing.Optional[ActingPosition]=None) -> PreflopBetSizing:
        return self._spot_class_bet_sizing_map.lookup_bet_sizing(   straddle_type=straddle_type,
                                                                    spot_category=spot_category,
                                                                    seat_position=seat_position,
                                                                    acting_position=acting_position  )

    def lookup_bet_sizing_for_spot(self, action_sequence: ActionSequence) -> PreflopBetSizing:
        return self._spot_bet_sizing_map.lookup_bet_sizing(action_sequence)

    def serialize_to_dict(self) -> dict:
        return {
            'spot_class':self._spot_class_bet_sizing_map.serialize_to_dict(),
            'spot': self._spot_bet_sizing_map.serialize_to_dict()
        }

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self.spot_class_bet_sizing_map() == other.spot_class_bet_sizing_map()) and
                    (self.spot_bet_sizing_map() == other.spot_bet_sizing_map()) )

    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PreflopBetSizingMap:
        try:
            assert 'spot_class' in some_dict, "'spot_class' must be present"
            assert 'spot' in some_dict, "'spot' must be present"
            spot_class_bet_sizing_map = _SpotClassBetSizingMap.create_from_dict(some_dict['spot_class'])
            spot_bet_sizing_map = _SpotBetSizingMap.create_from_dict(some_dict['spot'])
            return cls( spot_class_bet_sizing_map=spot_class_bet_sizing_map,
                        spot_bet_sizing_map=spot_bet_sizing_map)
        except ValueError as e:
            raise ValueError(f"Failed to create {cls.__name__} from dict: {e}")
        except AssertionError as e:
            raise ValueError(f"Failed to create {cls.__name__} from dict: {e}")

    @classmethod
    def create_empty(cls) -> PostflopBetSizingMap:
        return cls( spot_class_bet_sizing_map=_SpotClassBetSizingMap.create_empty(),
                    spot_bet_sizing_map=_SpotBetSizingMap.create_empty() )



class PreflopSolverConfig(SolverConfig):
    
    __slots__ = (   '_open_limp_mode',
                    '_rake_config',
                    '_bet_sizing_map',
                    '_small_blind_amount',
                    '_big_blind_amount',
                    '_ante_amount',
                    '_deal_order_stack_sizes',
                    '_blind_bet_sequence'  )

    def __init__(self, open_limp_mode: OpenLimpMode,
                        rake_config: RakeConfig,
                        bet_sizing_map: PreflopBetSizingMap,
                        small_blind_amount: int,
                        big_blind_amount: int,
                        ante_amount: int,
                        deal_order_stack_sizes: typing.Tuple[int],
                        blind_bet_sequence: BlindBetSequence):
        self._open_limp_mode = open_limp_mode
        self._rake_config = rake_config
        self._bet_sizing_map = bet_sizing_map
        self._small_blind_amount = small_blind_amount
        self._big_blind_amount = big_blind_amount
        self._ante_amount = ante_amount
        self._deal_order_stack_sizes = deal_order_stack_sizes
        self._blind_bet_sequence = blind_bet_sequence

    def open_limp_mode(self) -> OpenLimpMode:
        return self._open_limp_mode

    def rake_config(self) -> RakeConfig:
        return self._rake_config

    def bet_sizing_map(self) -> PreflopBetSizingMap:
        return self._bet_sizing_map

    def small_blind_amount(self) -> int:
        return self._small_blind_amount

    def big_blind_amount(self) -> int:
        return self._big_blind_amount

    def ante_amount(self) -> int:
        return self._ante_amount

    def deal_order_stack_sizes(self) -> typing.Tuple[int]:
        return self._deal_order_stack_sizes

    def blind_bet_sequence(self) -> BlindBetSequence:
        return self._blind_bet_sequence

    def __eq__(self, other):
        return (    (type(self) == type(other)) and
                    (self.open_limp_mode() == other.open_limp_mode()) and
                    (self.rake_config() == other.rake_config()) and
                    (self.bet_sizing_map() == other.bet_sizing_map()) and
                    (self.small_blind_amount() == other.small_blind_amount()) and
                    (self.ante_amount() == other.ante_amount()) and
                    (self.deal_order_stack_sizes() == other.deal_order_stack_sizes()) and
                    (self.blind_bet_sequence() == other.blind_bet_sequence())  )

    def serialize_to_dict(self) -> dict:
        if hasattr(self, '_serialize_to_dict_cache'):
            return self._serialize_to_dict_cache
        else:
            self._serialize_to_dict_cache = {
                'open_limp_mode': (self.open_limp_mode().value),
                'rake_config': self.rake_config().serialize_to_dict(),
                'bet_sizing_map': self.bet_sizing_map().serialize_to_dict(),
                'small_blind_amount': self.small_blind_amount(),
                'big_blind_amount': self.big_blind_amount(),
                'ante_amount': self.ante_amount(),
                'deal_order_stack_sizes': self.deal_order_stack_sizes(),
                'blind_bet_sequence': str(self.blind_bet_sequence())
            }
            return self._serialize_to_dict_cache



    @classmethod
    def create_from_dict(cls, some_dict: dict) -> PreflopSolverConfig:
        try:
            try:
                open_limp_mode = OpenLimpMode(some_dict['open_limp_mode'])
            except ValueError as e:
                raise ValueError(f"Cannot create {cls.__name__}. Invalid value for 'open_limp_mode'")
            result = cls(   open_limp_mode=open_limp_mode,
                            rake_config=RakeConfig.create_from_dict(some_dict['rake_config']),
                            bet_sizing_map=PreflopBetSizingMap.create_from_dict(some_dict['bet_sizing_map']),
                            small_blind_amount=int(some_dict['small_blind_amount']),
                            big_blind_amount=int(some_dict['big_blind_amount']),
                            ante_amount=int(some_dict['ante_amount']),
                            deal_order_stack_sizes=tuple(int(v) for v in some_dict['deal_order_stack_sizes']),
                            blind_bet_sequence=BlindBetSequence.create_from_string(some_dict['blind_bet_sequence'])  )
            # include this caching for a performance improvement
            result._serialize_to_dict_cache = some_dict
            return result
        except KeyError as e:
            raise ValueError(f"Cannot create {cls.__name__}. Missing field `{e}`")
        except AssertionError as e:
            raise ValueError(f"Cannot create {cls.__name__}. {e}")
        except TypeError as e:
            raise ValueError(f"Could not create {cls.__name__} due to type mismatch: {e}")

