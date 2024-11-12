import typing
import gzip
import json
from titan.solver_util.hand_history.types import (
    HandHistory
)



class HandHistoryFile:

    def __init__(self, hand_file_path: str):
        self._hand_file_path = hand_file_path

    def hand_file_path(self) -> str:
        return self._hand_file_path

    @classmethod
    def gen_hand_histories_from_jsonl_gz_file(cls, compressed_hand_file_path):
        with open(compressed_hand_file_path, 'rb') as file_obj:
            with gzip.GzipFile(fileobj=file_obj) as f:
                for l in f.readlines():
                    yield HandHistory.create_from_dict(json.loads(l))

    @classmethod
    def gen_hand_histories_from_jsonl_file(cls, hand_file_path):
        with open(hand_file_path, 'r') as file_obj:
            for l in file_obj.readlines():
                yield HandHistory.create_from_dict(json.loads(l))

    def gen_all_hands(self):
        if self.hand_file_path().endswith('.jsonl.gz'):
            yield from self.gen_hand_histories_from_jsonl_gz_file(self.hand_file_path())
        elif self.hand_file_path().endswith('.jsonl'):
            yield from self.gen_hand_histories_from_jsonl_file(self.hand_file_path())
        else:
            raise ValueError(f"Unsupported filetype for hand_file_path `{self.hand_file_path()}` !")

    def gen_preflop_hands(self):
        yield from (hand for hand in self.gen_all_hands() if (not hand.has_flop()))

    def gen_flop_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_flop() and (not hand.has_turn()))

    def gen_turn_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_turn() and (not hand.has_river()))

    def gen_river_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_river())

    def gen_headsup_postflop_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_flop() and hand.num_players_in_flop() == 2)

    def gen_non_headsup_postflop_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_flop() and hand.num_players_in_flop() > 2)

    def gen_6max_postflop_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_flop() and hand.num_players_in_flop() <= 6)

    def gen_3max_postflop_hands(self):
        yield from (hand for hand in self.gen_all_hands() if hand.has_flop() and hand.num_players_in_flop() <= 3)
