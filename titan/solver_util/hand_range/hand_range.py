from __future__ import annotations
import typing
import math
import random
from titan.solver_util.hand_range.hand_combo_map import (
    HandComboMap
)


class HandRangeEntry:
    
    __slots__ = (   '_hand',
                    '_weight'  )

    MAX_WEIGHT = 10000
    MIN_WEIGHT = 0
    NORMALIZED_WEIGHT_PRECISION = math.ceil(math.log10((MAX_WEIGHT - MIN_WEIGHT)))

    def __init__(self, hand: str, weight: int):
        self._hand = hand
        self._weight = weight

    def hand(self) -> str:
        return self._hand

    def weight(self) -> int:
        return self._weight

    def normalized_weight(self) -> float:
        return HandRangeEntry.normalize_weight(self._weight)

    def gen_combos(self) -> typing.Iterator[str]:
        yield from HandComboMap.gen_combos_for_hand(self.hand())

    def gen_weights(self) -> typing.Iterator[int]:
        num_combos = HandComboMap.num_combos_for_hand(self.hand())
        for i in range(num_combos):
            yield self.weight()

    @classmethod
    def normalize_weight(cls, weight: int) -> float:
        return round((weight - cls.MIN_WEIGHT) / (cls.MAX_WEIGHT - cls.MIN_WEIGHT), cls.NORMALIZED_WEIGHT_PRECISION)

    @classmethod
    def denormalize_weight(cls, normalized_weight: float) -> int:
        return int(round(((normalized_weight * (cls.MAX_WEIGHT-cls.MIN_WEIGHT)) + cls.MIN_WEIGHT), cls.NORMALIZED_WEIGHT_PRECISION))

    @classmethod
    def serialize_entries_to_string(cls, entries: typing.Iterator[HandRangeEntry]) -> typing.Iterator[str]:
        for entry in entries:
            if entry.weight() == cls.MIN_WEIGHT:
                pass
            elif entry.weight() == cls.MAX_WEIGHT:
                yield entry.hand()
            else:
                yield f"{entry.hand()}:{entry.normalized_weight()}"

    @classmethod
    def gen_entries_from_string(cls, some_string: str):
        some_string = some_string.strip()
        if not some_string:
            return
        # otherwise
        for entry in some_string.replace(' ', ',').split(','):
            try:
                hand, normalized_weight = entry.split(':')
                normalized_weight = float(normalized_weight)
            except ValueError:
                hand, normalized_weight = entry, 1.0
            # de-normalize
            weight = cls.denormalize_weight(normalized_weight)
            if weight >= cls.MIN_WEIGHT:
                yield cls(  hand=hand,
                            weight=weight  )



class PreflopHandRangeEntry(HandRangeEntry):

    def __init__(self, hand: str, weight: int):
        if hand not in HandComboMap.PREFLOP_HANDS:
            raise ValueError(f"Invalid hand for Preflop Range `{hand}`")
        super().__init__(hand, weight)

class PostflopHandRangeEntry(HandRangeEntry):
    pass


class HandRange:

    __slots__ = ('_entries',)


    def __init__(self, entries: typing.Tuple[HandRangeEntry, ...]):
        self._entries = entries

    def entries(self) -> typing.Tuple[HandRangeEntry, ...]:
        return self._entries

    def serialize_to_string(self) -> str:
        return ','.join(HandRangeEntry.serialize_entries_to_string(sorted(self.entries(), key=lambda entry: entry.hand())))

    def gen_simplified_entries(self):
        """Simplify the range entries by finding more efficient groupings
        """
        combo_weight_map = {combo: entry.weight()
                                for entry in self.entries()
                                    for combo in entry.gen_combos()}
        seen_combos = set()
        # some groups overlap so do the biggest one first
        hand_combos_pairs = sorted( HandComboMap.HAND_COMBO_MAP.items(),
                                    key=lambda x:-len(x[1]) )
        for hand, combos in hand_combos_pairs:
            hand_weights = tuple(combo_weight_map.get(combo, 0) for combo in combos)
            # have we already seen entire group ?
            if all(combo in seen_combos for combo in combos):
                continue
            elif all(v==HandRangeEntry.MIN_WEIGHT for v in hand_weights):
                seen_combos |= combos
            elif all(v==hand_weights[0] for v in hand_weights):
                seen_combos |= combos
                yield HandRangeEntry(hand=hand, weight=hand_weights[0])
        # remainder hands
        for remainder_combo in sorted(HandComboMap.HAND_COMBOS - seen_combos):
            yield HandRangeEntry(hand=remainder_combo, weight=combo_weight_map.get(remainder_combo, 0))


    def simplified_hand_range(self) -> HandRange:
        return HandRange(tuple(self.gen_simplified_entries()))


    @classmethod
    def create_from_hands_and_weights(cls, hands: typing.Iterator[str], weights: typing.Iterator[int]):
        return cls( tuple(HandRangeEntry(hand, weight)
                        for hand, weight in zip(hands, weights)) )

    @classmethod
    def create_from_normalized_hands_and_weights(cls, hands: typing.Iterator[str], normalized_weights: typing.Iterator[float]):
        return cls( tuple(HandRangeEntry(hand, HandRangeEntry.denormalize_weight(normalized_weight))
                        for hand, normalized_weight in zip(hands, normalized_weights)) )

    @classmethod
    def create_from_string(cls, some_string: str):
        return cls(tuple(HandRangeEntry.gen_entries_from_string(some_string)))


class PreflopHandRange(HandRange):

    @classmethod
    def create_from_hands_and_weights(cls, hands: typing.Iterator[str], weights: typing.Iterator[int]):
        return cls(tuple(   PreflopHandRangeEntry(hand, weight)
                                for hand, weight in zip(hands, weights)
                                    if weight >= PreflopHandRangeEntry.MIN_WEIGHT  ))

    @classmethod
    def create_from_normalized_hands_and_weights(cls, hands: typing.Iterator[str], normalized_weights: typing.Iterator[float]):
        return cls(tuple(   PreflopHandRangeEntry(hand, PreflopHandRangeEntry.denormalize_weight(normalized_weight))
                                for hand, normalized_weight in zip(hands, normalized_weights)
                                    if normalized_weight > 0  ))
    @classmethod
    def create_from_string(cls, some_string: str):
        return cls(tuple(PreflopHandRangeEntry.gen_entries_from_string(some_string)))


class PostflopHandRange(HandRange):
    pass

