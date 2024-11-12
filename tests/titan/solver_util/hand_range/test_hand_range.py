import logging
import pytest
import random
from titan.solver_util.hand_range import (
    PreflopHandRange,
    PostflopHandRange,
    HandComboMap
)


logger = logging.getLogger(__name__)


def is_equal_range_string(rs_a, rs_b):
    return sorted(rs_a.split(',')) == sorted(rs_b.split(','))

def test_hand_range_construction():    
    range_strings = [   
        "AA,KK,QQ,JJ,TT,99,88,77,66,55,44,33,22,AK,AQ,AJ,AT,A9,A8,A7,A6,A5,A4,A3,A2s,A2o:0.9,KQ,KJ,KT,K9,K8,K7,K6,K5s,K5o:0.43,K4s,K3s,K2s,QJ,QT,Q9,Q8,Q7s,Q6s,Q5s,Q4s,Q3s,Q2s,JT,J9,J8,J7s,J7o:0.12,J6s,J5s,J4s,J3s,J2s,T9,T8,T7s,T7o:0.46,T6s,T5s,T4s,T3s:0.91,T2s:0.43,98,97s,97o:0.89,96s,95s,87,86s,86o:0.66,85s,84s:0.78,76s,76o:0.65,75s,74s,65s,65o:0.59,64s,63s,54s,53s,52s:0.26,43s:0.92",
        "",
        "99:0.11,88,77,66,55,44,33,22,ATo:0.3,A9s:0.85,A9o:0.59,A8,A7s,A7o:0.87,A6s,A6o:0.82,A5s:0.83,A5o:0.42,A4s:0.85,A4o:0.47,A3s,A3o:0.79,A2s,A2o:0.82,KQo:0.49,KJs:0.62,KJo,KT,K9s,K9o:0.44,K8s,K8o:0.94,K7,K6,K5s,K5o:0.9,K4,K3s,K3o:0.83,K2s,K2o:0.63,QJs:0.6,QJo,QTs:0.3,QTo,Q9s:0.76,Q9o:0.52,Q8s,Q8o:0.67,Q7s,Q7o:0.78,Q6s,Q6o:0.43,Q5s,Q5o:0.08,Q4s,Q3s,Q2s,JTo:0.81,J9s:0.83,J9o,J8,J7,J6s,J5s,J4s,J3s,J2s,T9o:0.54,T8s:0.67,T8o:0.73,T7s:0.85,T7o:0.78,T6s:0.73,T5s:0.56,T4s:0.83,T3s,T2s,98s:0.4,98o:0.72,97s:0.76,97o:0.93,96s:0.82,96o:0.21,95s:0.87,94s,93s,92s,87s:0.73,87o,86,85s,84s,83s,82s,76,75s,75o:0.69,74s,73s,72s,65,64s,64o:0.39,63s,62s,54s:0.93,54o,53s,52s,43s,42s,32s",
    ]
    for range_string in range_strings:
        hand_range = PostflopHandRange.create_from_string(range_string)
        assert is_equal_range_string(hand_range.serialize_to_string(), range_string)
    # Check that we order appropriately and that we simplify *:1.0 entries
    assert PostflopHandRange.create_from_string('ATo:0.30,A9s:0.85,A5s:1.0,AK:0').serialize_to_string() == 'A5s,A9s:0.85,ATo:0.3'


def test_hand_range_entries():
    range_string = "AA,KK,QQ,JJ,TT,99,88,77,66,55,44,33,22,AK,AQ,AJ,AT,A9,A8,A7,A6,A5,A4,A3,A2s,A2o:0.90,KQ,KJ,KT,K9,K8,K7,K6,K5s,K5o:0.43,K4s,K3s,K2s,QJ,QT,Q9,Q8,Q7s,Q6s,Q5s,Q4s,Q3s,Q2s,JT,J9,J8,J7s,J7o:0.12,J6s,J5s,J4s,J3s,J2s,T9,T8,T7s,T7o:0.46,T6s,T5s,T4s,T3s:0.91,T2s:0.43,98,97s,97o:0.89,96s,95s,87,86s,86o:0.66,85s,84s:0.78,76s,76o:0.65,75s,74s,65s,65o:0.59,64s,63s,54s,53s,52s:0.26,43s:0.92"
    
    p0_range = PostflopHandRange.create_from_string(range_string)

    for entry in p0_range.entries():
        if entry.hand() == 'AA':
            assert entry.normalized_weight() == 1.0
            combos = list(entry.gen_combos())
            assert len(combos) == len(set(combos))
            assert set(combos) == {'AdAc', 'AhAd', 'AsAh', 'AhAc', 'AsAc', 'AsAd'}
        elif entry.hand() == 'A2o':
            assert entry.normalized_weight() == 0.9
        elif entry.hand() == 'K5o':
            assert entry.normalized_weight() == 0.43


def create_random_preflop_range_string(rng):
    ALL_HANDS = tuple(HandComboMap.gen_preflop_hands())
    assert len(ALL_HANDS) == 169
    result = []
    for hand in random.sample(ALL_HANDS, rng.randint(30, 169)):
        result.append(f"{hand}:{round(rng.random(),4)}")
    return ','.join(result)

