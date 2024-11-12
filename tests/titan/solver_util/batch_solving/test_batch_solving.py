import json
import logging
import pytest
import random
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence
)
from titan.solver_util.postflop_solver import (
    PostflopSolverConfig,
    SolveTreeSpec,
    PlayerRange,
    SolveAlgorithm
)
from titan.solver_util.preflop_solver import (
    PreflopSolverConfig,
    RakeConfig,
    OpenLimpMode,
    PreflopBetSizingMap,
)
from titan.solver_util.batch_solving import (
    PreflopBatchSolvingEntry,
    PostflopBatchSolvingEntry,
    PostflopBatchSolvingSpec,
    PreflopBatchSolvingSpec
)


logger = logging.getLogger(__name__)



EXAMPLE_TREE_SPEC_JSON = json.loads("""
{
  "2_PLAYERS": {
    "FLOP": {
      "FIRST_TO_ACT": {
        "DONK": [],
        "BET": [3300, 7500, 15000],
        "1_RAISE": [6600, 10000],
        "2_RAISE": [6600, 10000000],
        "N_RAISE": [6600, 10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [],
        "BET": [3300, 7500, 15000],
        "1_RAISE": [6600, 10000],
        "2_RAISE": [6600, 10000000],
        "N_RAISE": [6600, 10000000]
      }
    },
    "TURN": {
      "FIRST_TO_ACT": {
        "DONK": [],
        "BET": [5000, 15000],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [],
        "BET": [5000, 15000],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    },
    "RIVER": {
      "FIRST_TO_ACT": {
        "DONK": [],
        "BET": [5000, 15000],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [],
        "BET": [6600, 15000],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    }
  },
  "3_PLAYERS": {
    "FLOP": {
      "FIRST_TO_ACT": {
        "DONK": [5000],
        "BET": [3300, 7500],
        "1_RAISE": [6600],
        "2_RAISE": [6600, 10000000],
        "N_RAISE": [6600, 10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [5000],
        "BET": [3300, 7500],
        "1_RAISE": [6600],
        "2_RAISE": [6600, 10000000],
        "N_RAISE": [6600, 10000000]
      },
      "N_TO_ACT": {
        "DONK": [],
        "BET": [3300, 7500],
        "1_RAISE": [6600],
        "2_RAISE": [6600, 10000000],
        "N_RAISE": [6600, 10000000]
      }
    },
    "TURN": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    },
    "RIVER": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    }
  },
  "4_PLAYERS": {
    "FLOP": {
      "FIRST_TO_ACT": {
        "DONK": [5000],
        "BET": [3300, 7500],
        "1_RAISE": [7500],
        "2_RAISE": [7500, 10000000],
        "N_RAISE": [7500, 10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [5000],
        "BET": [3300, 7500],
        "1_RAISE": [7500],
        "2_RAISE": [7500, 10000000],
        "N_RAISE": [7500, 10000000]
      },
      "N_TO_ACT": {
        "DONK": [],
        "BET": [3300, 7500],
        "1_RAISE": [7500],
        "2_RAISE": [7500, 10000000],
        "N_RAISE": [7500, 10000000]
      }
    },
    "TURN": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    },
    "RIVER": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    }
  },
  "5_PLAYERS": {
    "FLOP": {
      "FIRST_TO_ACT": {
        "DONK": [3300],
        "BET": [3300],
        "1_RAISE": [7500],
        "2_RAISE": [7500],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [3300],
        "BET": [3300],
        "1_RAISE": [7500],
        "2_RAISE": [7500],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [3300],
        "BET": [3300],
        "1_RAISE": [7500],
        "2_RAISE": [7500],
        "N_RAISE": [10000000]
      }
    },
    "TURN": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    },
    "RIVER": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    }
  },
  "6_PLAYERS": {
    "FLOP": {
      "FIRST_TO_ACT": {
        "DONK": [3300],
        "BET": [3300],
        "1_RAISE": [7500],
        "2_RAISE": [7500],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [3300],
        "BET": [3300],
        "1_RAISE": [7500],
        "2_RAISE": [7500],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [3300],
        "BET": [3300],
        "1_RAISE": [7500],
        "2_RAISE": [7500],
        "N_RAISE": [10000000]
      }
    },
    "TURN": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    },
    "RIVER": {
      "FIRST_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "SECOND_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      },
      "N_TO_ACT": {
        "DONK": [6600],
        "BET": [6600],
        "1_RAISE": [10000],
        "2_RAISE": [10000],
        "N_RAISE": [10000000]
      }
    }
  }
}
""")



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
        "CO": {}
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

def create_mock_postflop_config():
    solve_tree_spec = SolveTreeSpec.create_from_dict(EXAMPLE_TREE_SPEC_JSON)
    stack_sizes = (random.randint(1000, 5000), random.randint(1000, 5000), random.randint(1000, 5000), random.randint(1000, 5000))
    blind_bet_sequence = BlindBetSequence.create_default(   num_seats=4,
                                                            big_blind_amount=100,
                                                            small_blind_amount=50,
                                                            ante_amount=50,
                                                            has_small_blind=True,
                                                            num_straddles=0  )

    return PostflopSolverConfig(solve_tree_spec=solve_tree_spec,
                                num_threads=8,
                                solving_time=1337,
                                deal_order_stack_sizes=stack_sizes,
                                big_blind_amount=100,
                                blind_bet_sequence=blind_bet_sequence,
                                preflop_action_sequence=ActionSequence.create_from_string('cccx'),
                                flop_action_sequence=ActionSequence.create_empty(),
                                turn_action_sequence=ActionSequence.create_empty(),
                                community_cards=('2s', '5d', 'Jh'),
                                player_ranges=( PlayerRange.create_uniform(),
                                                PlayerRange.create_uniform() ),
                                solve_algorithm=SolveAlgorithm.DEFAULT)


def create_mock_preflop_config():
    # create a mock config
    bet_sizing_map = PreflopBetSizingMap.create_from_dict(EXAMPLE_BET_SIZING_JSON)
    stack_sizes = (random.randint(1000, 5000), random.randint(1000, 5000), random.randint(1000, 5000), random.randint(1000, 5000))
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



def test_batch_solving_postflop():
    entries = (
        PostflopBatchSolvingEntry.create_for_path_solve(entry_id='solve-00',
                                                        solver_config=create_mock_postflop_config(),
                                                        action_sequence=ActionSequence.create_from_string('xr500f')),
        PostflopBatchSolvingEntry.create_for_full_tree_solve(   entry_id='solve-01',
                                                                solver_config=create_mock_postflop_config()  ),
    )
    batch_solve_spec = PostflopBatchSolvingSpec(entries)
    assert batch_solve_spec.entries() == entries
    assert batch_solve_spec.entries()[0].action_sequence() == ActionSequence.create_from_string('xr500f')
    assert batch_solve_spec.entries()[1].action_sequence() == ActionSequence.create_empty()
    assert batch_solve_spec.entries()[0].solver_config() != batch_solve_spec.entries()[1].solver_config()
    batch_solve_spec_dict = batch_solve_spec.serialize_to_dict()
    batch_solve_spec_clone = PostflopBatchSolvingSpec.create_from_dict(json.loads(json.dumps(batch_solve_spec_dict)))
    assert batch_solve_spec_clone == batch_solve_spec
    assert batch_solve_spec_clone.entries() == entries


def test_batch_solving_preflop():
    entries = (
        PreflopBatchSolvingEntry.create_for_path_solve( entry_id='solve-00',
                                                        solver_config=create_mock_preflop_config(),
                                                        action_sequence=ActionSequence.create_from_string('xr500f') ),
        PreflopBatchSolvingEntry.create_for_full_tree_solve(entry_id='solve-01',
                                                            solver_config=create_mock_preflop_config()),
    )
    batch_solve_spec = PreflopBatchSolvingSpec(entries)
    assert batch_solve_spec.entries() == entries
    assert batch_solve_spec.entries()[0].action_sequence() == ActionSequence.create_from_string('xr500f')
    assert batch_solve_spec.entries()[1].action_sequence() == ActionSequence.create_empty()
    assert batch_solve_spec.entries()[0].solver_config() != batch_solve_spec.entries()[1].solver_config()
    batch_solve_spec_dict = batch_solve_spec.serialize_to_dict()
    batch_solve_spec_clone = PreflopBatchSolvingSpec.create_from_dict(json.loads(json.dumps(batch_solve_spec_dict)))
    assert batch_solve_spec_clone == batch_solve_spec
    assert batch_solve_spec_clone.entries() == entries

    assert batch_solve_spec_clone.entries()[0].is_path_solve()
    assert not batch_solve_spec_clone.entries()[1].is_path_solve()


    concat_spec = PreflopBatchSolvingSpec.merge(batch_solve_spec, batch_solve_spec_clone)
    assert concat_spec.entries() == batch_solve_spec.entries() + batch_solve_spec_clone.entries()