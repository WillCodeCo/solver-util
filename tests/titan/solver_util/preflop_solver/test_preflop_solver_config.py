import logging
import pytest
import pickle
import json
from titan.solver_util.spot_models import (
    ActionSequence,
    CheckAction,
    BlindBetSequence,
    BlindBet
)
from titan.solver_util.preflop_solver import (
    PreflopSolverConfig,
    RakeConfig,
    OpenLimpMode,
    PreflopBetSizingMap,
    PreflopPotSizeBetSizing,
    PreflopPrevRaiseRatioBetSizing,
    PreflopFixedBetSizing,
    StraddleType,
    SpotCategory,
    SeatPosition,
    ActingPosition,
)


logger = logging.getLogger(__name__)


EXAMPLE_BET_SIZING_JSON = json.loads("""
{
  "spot_class": {
    "STRADDLE": {
      "2_BET": {
        "BTN": {
          "bet_sizing": {
            "extra_amount_per_limper": 1000,
            "unit": "chips",
            "values": [
              2250
            ]
          }
        },
        "CO": {
          "bet_sizing": {
            "unit": "prev-raise-ratio-bps",
            "values": [
              25000
            ]
          }
        }
      },
      "3_BET": {
        "BTN": {
          "IP": {
            "bet_sizing": {
              "unit": "pot-size-ratio-bps",
              "values": [
                15000
              ]
            }
          },
          "OOP": {
            "bet_sizing": {
              "unit": "pot-size-ratio-bps",
              "values": [
                8000
              ]
            }
          }
        },
        "CO": {}
      },
      "4_BET": {},
      "5_BET": {}
    },
    "NO_STRADDLE": {
      "bet_sizing": {
        "unit": "pot-size-ratio-bps",
        "values": [
          4242
        ]
      }
    }
  },
  "spot": {
    "": {
      "unit": "chips",
      "values": [
        4242
      ]
    },
    "ccx": {
      "unit": "pot-size-ratio-bps",
      "values": [
        8000
      ]
    },
    "cr200": {
      "unit": "pot-size-ratio-bps",
      "values": [
        1000,
        9000
      ]
    }
  }
}
""")


def create_mock_config():
    # create a mock config
    bet_sizing_map = PreflopBetSizingMap.create_from_dict(EXAMPLE_BET_SIZING_JSON)
    stack_sizes = (10000, 10000, 10000, 10000)
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=len(stack_sizes),
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )

    return PreflopSolverConfig( open_limp_mode=OpenLimpMode.ENABLED,
                                rake_config=RakeConfig( rake_amount_bps=500,
                                                        rake_cap=100 ),
                                bet_sizing_map=bet_sizing_map,
                                small_blind_amount=50,
                                big_blind_amount=100,
                                ante_amount=50,
                                deal_order_stack_sizes=stack_sizes,
                                blind_bet_sequence=blind_bet_sequence  )

def test_empty_preflop_bet_sizing():
    bet_sizing_map = PreflopBetSizingMap.create_empty()
    assert bet_sizing_map
    assert PreflopBetSizingMap.create_from_dict(bet_sizing_map.serialize_to_dict())



def test_preflop_bet_sizing():
    bet_sizing_map = PreflopBetSizingMap.create_from_dict(EXAMPLE_BET_SIZING_JSON)
    bet_sizing = bet_sizing_map.lookup_bet_sizing_for_spot_class( straddle_type=StraddleType.STRADDLE,
                                                                  spot_category=SpotCategory.THREE_BET,
                                                                  seat_position=SeatPosition.BTN,
                                                                  acting_position=ActingPosition.IP  )

    assert type(bet_sizing) == PreflopPotSizeBetSizing
    assert bet_sizing.values() == (15000, )


    bet_sizing = bet_sizing_map.lookup_bet_sizing_for_spot_class( straddle_type=StraddleType.STRADDLE,
                                                                  spot_category=SpotCategory.TWO_BET,
                                                                  seat_position=SeatPosition.CO,
                                                                  acting_position=ActingPosition.IP  )

    assert type(bet_sizing) == PreflopPrevRaiseRatioBetSizing
    assert bet_sizing.values() == (25000, )




    bet_sizing = bet_sizing_map.lookup_bet_sizing_for_spot_class( straddle_type=StraddleType.STRADDLE,
                                                                  spot_category=SpotCategory.TWO_BET,
                                                                  seat_position=SeatPosition.BTN  )
    assert type(bet_sizing) == PreflopFixedBetSizing
    assert bet_sizing.values() == (2250, )
    assert bet_sizing.extra_amount_per_limper() == 1000

    # unrealistic example which should get defaults from general case
    bet_sizing = bet_sizing_map.lookup_bet_sizing_for_spot_class( straddle_type=StraddleType.NO_STRADDLE,
                                                                  spot_category=SpotCategory.TWO_BET,
                                                                  seat_position=SeatPosition.BTN  )
    assert bet_sizing.values() == (4242, )


    bet_sizing = bet_sizing_map.lookup_bet_sizing_for_spot(ActionSequence.create_from_string(''))
    assert bet_sizing.values() == (4242,)

    bet_sizing = bet_sizing_map.lookup_bet_sizing_for_spot(ActionSequence.create_from_string('cr200'))
    assert bet_sizing.values() == (1000, 9000)

def ensure_pickling_works(value):
    value_bytes = pickle.dumps(value)
    assert value_bytes
    cloned_value = pickle.loads(value_bytes)
    assert cloned_value == value

def test_preflop_config_pickling():
    bet_sizing_map = PreflopBetSizingMap.create_from_dict(EXAMPLE_BET_SIZING_JSON)
    ensure_pickling_works(bet_sizing_map)
    ensure_pickling_works(BlindBet(live_amount=99, dead_amount=42, is_straddle=True))
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=6,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )
    ensure_pickling_works(blind_bet_sequence)
    ensure_pickling_works(create_mock_config())
    ensure_pickling_works(CheckAction())
    ensure_pickling_works(ActionSequence.create_from_string('xccr100f'))




def test_preflop_config_serialization():
  config = create_mock_config()
  config_str = json.dumps(config.serialize_to_dict())
  cloned_config = PreflopSolverConfig.create_from_dict(json.loads(config_str))
  assert cloned_config == config
  assert json.dumps(cloned_config.serialize_to_dict()) == config_str

