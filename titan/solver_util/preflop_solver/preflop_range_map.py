_HANDS = ('22','32s','42s','52s','62s','72s','82s','92s','T2s','J2s','Q2s','K2s','A2s','32o','33','43s','53s','63s','73s','83s','93s','T3s','J3s','Q3s','K3s','A3s','42o','43o','44','54s','64s','74s','84s','94s','T4s','J4s','Q4s','K4s','A4s','52o','53o','54o','55','65s','75s','85s','95s','T5s','J5s','Q5s','K5s','A5s','62o','63o','64o','65o','66','76s','86s','96s','T6s','J6s','Q6s','K6s','A6s','72o','73o','74o','75o','76o','77','87s','97s','T7s','J7s','Q7s','K7s','A7s','82o','83o','84o','85o','86o','87o','88','98s','T8s','J8s','Q8s','K8s','A8s','92o','93o','94o','95o','96o','97o','98o','99','T9s','J9s','Q9s','K9s','A9s','T2o','T3o','T4o','T5o','T6o','T7o','T8o','T9o','TT','JTs','QTs','KTs','ATs','J2o','J3o','J4o','J5o','J6o','J7o','J8o','J9o','JTo','JJ','QJs','KJs','AJs','Q2o','Q3o','Q4o','Q5o','Q6o','Q7o','Q8o','Q9o','QTo','QJo','QQ','KQs','AQs','K2o','K3o','K4o','K5o','K6o','K7o','K8o','K9o','KTo','KJo','KQo','KK','AKs','A2o','A3o','A4o','A5o','A6o','A7o','A8o','A9o','ATo','AJo','AQo','AKo','AA')
_HAND_INDEX_MAP = {k:i for i, k in enumerate(_HANDS)}

class PreflopRangeMap:
    HANDS = _HANDS
    HAND_INDEX_MAP = _HAND_INDEX_MAP    
    RANGE_SIZE = len(HANDS)

    @classmethod
    def gen_hands(cls):
        yield from cls.HANDS
        
    @classmethod
    def index_for_hand(cls, hand:str) -> int:
        return cls.HAND_INDEX_MAP[hand]

    @classmethod
    def hand_for_index(cls, index: int) -> str:
        return cls.HANDS[index]