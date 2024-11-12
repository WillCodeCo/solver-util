import json
import re
import pickle
import logging
import pytest
import random
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence
)
from titan.solver_util.postflop_solver import (
    PostflopSolverConfig,
    PlayerRange,
    SolveAlgorithm,
    PlayerCount,
    Street,
    ActingPosition,
    SpotCategory,
    SolveTreeSpec
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

EXAMPLE_TREE_STRING = """[ // PlayerCount.TWO_PLAYERS
    [ // Street.FLOP
        [ // ActingPosition.FIRST_TO_ACT
            [], // SpotCategory.DONK
            [0.33, 0.75, 1.5], // SpotCategory.BET
            [0.66, 1.0], // SpotCategory.ONE_RAISE
            [0.66, 1000], // SpotCategory.TWO_RAISE
            [0.66, 1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [], // SpotCategory.DONK
            [0.33, 0.75, 1.5], // SpotCategory.BET
            [0.66, 1.0], // SpotCategory.ONE_RAISE
            [0.66, 1000], // SpotCategory.TWO_RAISE
            [0.66, 1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.TURN
        [ // ActingPosition.FIRST_TO_ACT
            [], // SpotCategory.DONK
            [0.5, 1.5], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [], // SpotCategory.DONK
            [0.5, 1.5], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.RIVER
        [ // ActingPosition.FIRST_TO_ACT
            [], // SpotCategory.DONK
            [0.5, 1.5], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [], // SpotCategory.DONK
            [0.66, 1.5], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ]
],
[ // PlayerCount.THREE_PLAYERS
    [ // Street.FLOP
        [ // ActingPosition.FIRST_TO_ACT
            [0.5], // SpotCategory.DONK
            [0.33, 0.75], // SpotCategory.BET
            [0.66], // SpotCategory.ONE_RAISE
            [0.66, 1000], // SpotCategory.TWO_RAISE
            [0.66, 1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.5], // SpotCategory.DONK
            [0.33, 0.75], // SpotCategory.BET
            [0.66], // SpotCategory.ONE_RAISE
            [0.66, 1000], // SpotCategory.TWO_RAISE
            [0.66, 1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [], // SpotCategory.DONK
            [0.33, 0.75], // SpotCategory.BET
            [0.66], // SpotCategory.ONE_RAISE
            [0.66, 1000], // SpotCategory.TWO_RAISE
            [0.66, 1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.TURN
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.RIVER
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ]
],
[ // PlayerCount.FOUR_PLAYERS
    [ // Street.FLOP
        [ // ActingPosition.FIRST_TO_ACT
            [0.5], // SpotCategory.DONK
            [0.33, 0.75], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75, 1000], // SpotCategory.TWO_RAISE
            [0.75, 1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.5], // SpotCategory.DONK
            [0.33, 0.75], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75, 1000], // SpotCategory.TWO_RAISE
            [0.75, 1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [], // SpotCategory.DONK
            [0.33, 0.75], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75, 1000], // SpotCategory.TWO_RAISE
            [0.75, 1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.TURN
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.RIVER
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ]
],
[ // PlayerCount.FIVE_PLAYERS
    [ // Street.FLOP
        [ // ActingPosition.FIRST_TO_ACT
            [0.33], // SpotCategory.DONK
            [0.33], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.33], // SpotCategory.DONK
            [0.33], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.33], // SpotCategory.DONK
            [0.33], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.TURN
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.RIVER
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ]
],
[ // PlayerCount.SIX_PLAYERS
    [ // Street.FLOP
        [ // ActingPosition.FIRST_TO_ACT
            [0.33], // SpotCategory.DONK
            [0.33], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.33], // SpotCategory.DONK
            [0.33], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.33], // SpotCategory.DONK
            [0.33], // SpotCategory.BET
            [0.75], // SpotCategory.ONE_RAISE
            [0.75], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.TURN
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ],
    [ // Street.RIVER
        [ // ActingPosition.FIRST_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.SECOND_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ],
        [ // ActingPosition.N_TO_ACT
            [0.66], // SpotCategory.DONK
            [0.66], // SpotCategory.BET
            [1.0], // SpotCategory.ONE_RAISE
            [1.0], // SpotCategory.TWO_RAISE
            [1000], // SpotCategory.N_RAISE
        ]
    ]
]
"""


EXAMPLE_DICT_TREE = {
    PlayerCount.TWO_PLAYERS: {
        Street.FLOP: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300, 6600,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600, 10000000,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300, 6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6000, 10000000,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.TURN: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (5000,),
                SpotCategory.BET: (5000, 10000,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (5000,),
                SpotCategory.BET: (5000, 10000,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.RIVER: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (7500,),
                SpotCategory.BET: (5000, 10000,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (10000000,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (2500, 10000000,),
                SpotCategory.BET: (6600, 12500,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (10000000,),
                SpotCategory.N_RAISE: (10000000,),
            }
        }
    },
    PlayerCount.THREE_PLAYERS: {
        Street.FLOP: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.TURN: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.RIVER: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        }
    },
    PlayerCount.FOUR_PLAYERS: {
        Street.FLOP: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.TURN: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.RIVER: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        }
    },
    PlayerCount.FIVE_PLAYERS: {
        Street.FLOP: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.TURN: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.RIVER: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        }
    },
    PlayerCount.SIX_PLAYERS: {
        Street.FLOP: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (),
                SpotCategory.BET: (3300,),
                SpotCategory.ONE_RAISE: (5000,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.TURN: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        },
        Street.RIVER: {
            ActingPosition.FIRST_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.SECOND_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            },
            ActingPosition.N_TO_ACT: {
                SpotCategory.DONK: (6600,),
                SpotCategory.BET: (6600,),
                SpotCategory.ONE_RAISE: (6600,),
                SpotCategory.TWO_RAISE: (6600,),
                SpotCategory.N_RAISE: (10000000,),
            }
        }
    }
}


def ensure_tree_file_string_match(value_a: str, value_b: str) -> bool:
    # remove comments
    value_a = re.sub(r'\/\/.*', '', value_a)
    value_b = re.sub(r'\/\/.*', '', value_b)
    # ignore .0
    value_a = value_a.replace('.0,', ',').replace('.0]',']')
    value_b = value_b.replace('.0,', ',').replace('.0]',']')
    # remove spaces
    value_a = value_a.replace('\t','').replace(' ','').strip()
    value_b = value_b.replace('\t','').replace(' ','').strip()
    assert value_a == value_b


def create_mock_config():
    solve_tree_spec = SolveTreeSpec.create_from_dict(EXAMPLE_TREE_SPEC_JSON)
    stack_sizes = (10000, 10000, 10000, 10000)

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



def ensure_pickling_works(value):
    value_bytes = pickle.dumps(value)
    assert value_bytes
    cloned_value = pickle.loads(value_bytes)
    assert cloned_value == value

def test_postflop_config_pickling():
    player_range = PlayerRange.create_uniform()
    for x in range(PlayerRange.SIZE):
        player_range.values()[x] = random.randint(PlayerRange.MIN_VALUE, PlayerRange.MAX_VALUE+1)
    ensure_pickling_works(player_range)
    ensure_pickling_works(create_mock_config())


def test_default_postflop_tree_spec():
    solve_tree_spec = SolveTreeSpec.create_empty()
    assert solve_tree_spec
    assert SolveTreeSpec.create_from_dict(solve_tree_spec.serialize_to_dict())
    
def test_create_postflop_tree_spec_from_dict_with_enums():
    assert SolveTreeSpec.create_from_dict(EXAMPLE_DICT_TREE)

def test_postflop_tree_spec():
    solve_tree_spec = SolveTreeSpec.create_from_dict(EXAMPLE_TREE_SPEC_JSON)
    assert json.dumps(solve_tree_spec.serialize_to_dict(), sort_keys=True) == json.dumps(EXAMPLE_TREE_SPEC_JSON, sort_keys=True)
    ensure_tree_file_string_match(solve_tree_spec.create_tree_file_string(), EXAMPLE_TREE_STRING)



def test_postflop_config_serialization():
    config = create_mock_config()
    config_str = json.dumps(config.serialize_to_dict())
    cloned_config = PostflopSolverConfig.create_from_dict(json.loads(config_str))
    assert cloned_config == config
    assert json.dumps(cloned_config.serialize_to_dict()) == config_str
