from __future__ import annotations
import typing
import re
from titan.solver_util.spot_models import (
    ActionSequence,
    BlindBetSequence,
)

class HandHistoryParser:

    CARD = r'[2-9TJQKA][cdhs]'
    ACTION_SEQUENCE = r'(?:[xcf]|r[0-9]+)+'
    BLIND_BET_SEQUENCE = r'(?:[sb]\d+(?::\d+)?)+'

    PREFLOP_HAND = r'(?:('+BLIND_BET_SEQUENCE+r');)?('+ACTION_SEQUENCE+r')'
    FLOP_HAND = (   PREFLOP_HAND +
                    r'\[('+CARD+CARD+CARD+r')\]' + r'('+ACTION_SEQUENCE + r')' )
    TURN_HAND = (   FLOP_HAND +
                    r'\[('+CARD+r')\]' + '('+ACTION_SEQUENCE + r')' )
    RIVER_HAND = (  TURN_HAND +
                    r'\[('+CARD+r')\]' + '('+ACTION_SEQUENCE + r')' )

    CARD_PATTERN = re.compile(r'[2-9TJQKA][cdsh]')
    PREFLOP_HAND_PATTERN = re.compile(r'^'+PREFLOP_HAND+r'$')
    FLOP_HAND_PATTERN = re.compile(r'^'+FLOP_HAND+r'$')
    TURN_HAND_PATTERN = re.compile(r'^'+TURN_HAND+r'$')
    RIVER_HAND_PATTERN = re.compile(r'^'+RIVER_HAND+r'$')


    @classmethod
    def pattern_match_groups(cls, hand_history: str):
        if hand_history.count('[') == 0:
            return cls.PREFLOP_HAND_PATTERN.match(hand_history).groups()
        elif hand_history.count('[') == 1:
            return cls.FLOP_HAND_PATTERN.match(hand_history).groups()
        elif hand_history.count('[') == 2:
            return cls.TURN_HAND_PATTERN.match(hand_history).groups()
        elif hand_history.count('[') == 3:
            return cls.RIVER_HAND_PATTERN.match(hand_history).groups()
        else:
            raise ValueError(f"Invalid hand_history `{hand_history}`")

    @classmethod
    def parse_blind_bet_sequence(cls, hand_history: str):
        pattern_match_groups = cls.pattern_match_groups(hand_history)
        if not pattern_match_groups[0]:
            raise ValueError(f"No blind_bet_sequence found in hand_history `{hand_history}`")
        return BlindBetSequence.create_from_string(pattern_match_groups[0])

    @classmethod
    def parse_community_cards(cls, hand_history: str):
        pattern_match_groups = cls.pattern_match_groups(hand_history)
        return tuple(cls.CARD_PATTERN.findall(''.join(group for group in pattern_match_groups[2::2])))

    @classmethod
    def parse_action_sequences(cls, hand_history: str):
        pattern_match_groups = cls.pattern_match_groups(hand_history)
        return tuple(ActionSequence.create_from_string(action_sequence_str)
                        for action_sequence_str in pattern_match_groups[1::2])
