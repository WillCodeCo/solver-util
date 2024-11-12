import logging
import pytest
import tempfile
import pathlib
import json
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
from titan.solver_util.solution_tree import (
    RandomValueFactory,
    SolutionTree,
    SolutionTreeException
)
from titan.solver_util.solution_tree_store import (
    SolutionTreeStore
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



def gen_random_solution_tree(num_trees):
    for i in range(num_trees):
        yield RandomValueFactory.create_solution_tree(  tree_height=4,
                                                        range_size=1326,
                                                        num_bet_sizes=3 )


def test_solution_tree_store():

    SAMPLE_TREES = list(gen_random_solution_tree(10))
    SAMPLE_CONFIGS = [create_mock_postflop_config() for x in range(10)]

    with tempfile.TemporaryDirectory() as working_dir:
        working_path = pathlib.Path(working_dir)

        store_path = working_path / 'store'
        store_path.mkdir()
        store = SolutionTreeStore.create_empty(store_path=store_path)
        for tree, config in zip(SAMPLE_TREES, SAMPLE_CONFIGS):
            store.add_postflop_solution_tree(   solver_config_dict=config.serialize_to_dict(),
                                                action_sequence=ActionSequence.create_from_string(''),
                                                is_path_solve=False,
                                                solution_tree=tree  )
            store.save_index()
        # Check that we start with many indexes
        num_indexes = sum(1 for _ in (store_path / 'index').rglob('*.gz'))
        assert num_indexes == len(SAMPLE_TREES)
        # check that the cleanup results in there being a single one
        store.clean_up_indexes()        
        num_indexes = sum(1 for _ in (store_path / 'index').rglob('*.gz'))
        assert num_indexes == 1
        # ensure index is good
        assert len(store.index().serialize_to_dict()) == 10
        for tree, config in zip(SAMPLE_TREES, SAMPLE_CONFIGS):
            index_key = store.index().create_postflop_index_key(is_path_solve=False,
                                                                action_sequence=ActionSequence.create_from_string(''),
                                                                solver_config_dict=config.serialize_to_dict())
            entries = list(store.index().gen_entries_for_key(index_key))
            assert len(entries) == 1
            assert store.get_solution_tree(key=entries[0].solution_tree_key()) == tree



        # ensure we can rebuild index from scratch
        old_index_json = json.dumps(store.index().serialize_to_dict(), sort_keys=True)
        store.rebuild_index()
        assert json.dumps(store.index().serialize_to_dict(), sort_keys=True) == old_index_json

