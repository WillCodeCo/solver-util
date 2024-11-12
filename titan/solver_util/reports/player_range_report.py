from __future__ import annotations
import typing
import pathlib
import os
from titan.solver_util.spot_models import (
    SeatStack,
    ActionSequence,
    Action
)
from titan.solver_util.solved_street import (
    SolvedStreet
)
from titan.solver_util.solution_tree import (
    SolutionTree,
    SolutionTreeNode,
    StrategyOption,
)
from titan.solver_util.hand_history import (
    HandHistory
)
from titan.solver_util.preflop_solver.preflop_range_map import (
    PreflopRangeMap
)
from titan.solver_util.postflop_solver.postflop_range_map import (
    PostflopRangeMap
)
from titan.solver_util.postflop_solver import (
    PlayerRange
)

class _ReportNode:

    __slots__ = (   '_input_player_range',
                    '_output_player_ranges',
                    '_children'  )

    def __init__(self, input_player_range: PlayerRange, output_player_ranges: typing.Dict[Action, PlayerRange], children: typing.Dict[str, _ReportNode]):
        self._input_player_range = input_player_range
        self._output_player_ranges = output_player_ranges
        self._children = dict(children)

    def input_player_range(self) -> PlayerRange:
        return self._input_player_range

    def output_player_ranges(self) -> typing.Dict[Action, PlayerRange]:
        return self._output_player_ranges

    def children(self) -> typing.Dict[str, _ReportNode]:
        return self._children

    def has_child(self, child_name: str) -> bool:
        return (child_name in self._children)

    def add_child(self, child_name: str, child_report_node: _ReportNode):
        if self.has_child(child_name):
            raise ValueError(f"Cannot add_child() in {self.__class__.__name__} since child_name `{child_name}` already exists !")
        self._children[child_name] = child_report_node

    def gen_nodes_bfs(self):
        to_visit = [(None, self)]
        while to_visit:
            name, cur_node = to_visit.pop(0)
            for child_name, child_report_node in cur_node.children().items():
                to_visit.append((child_name, child_report_node))
            yield (name, cur_node)

    def save_to_filesystem(self, path: str):
        cur_path = pathlib.Path(path)
        if not cur_path.is_dir():
            raise ValueError(f"Cannot call {self.__class__.__name__}.save_to_filesystem() for a path `{path}` that does not represent a directory")
        # save input player_range
        with open(cur_path / 'input-range.txt', 'w') as f:
            f.write(self.input_player_range().serialize_to_string())
        # save output player range
        with open(cur_path / 'output-ranges.txt', 'w') as f:
            for action, player_range in self.output_player_ranges().items():
                f.write(f"# Action taken: {str(action)}\n")
                range_str = player_range.serialize_to_string()
                range_str = range_str if range_str else '(empty)'
                f.write(range_str +"\n\n")
        # recurse down for children
        for child_name, child_node in self.children().items():
            # make a directory for child
            child_path = (cur_path / child_name)
            if not child_path.is_dir():
                child_path.mkdir()
            child_node.save_to_filesystem(child_path)

class PlayerRangeStreetReport:

    def __init__(self, root_report_node: _ReportNode):
        self._root_report_node = root_report_node

    def root_report_node(self):
        return self._root_report_node

    def gen_nodes_bfs(self):
        yield from self.root_report_node().gen_nodes_bfs()

    def save_to_filesystem(self, path: str):
        self.root_report_node().save_to_filesystem(path)


    @classmethod
    def create(cls, input_player_range_map: typing.Dict[ActionSequence, PlayerRange],
                    output_player_range_map: typing.Dict[ActionSequence, typing.Dict[Action, PlayerRange]], solution_tree: SolutionTree) -> PlayerRangeReport:
        try:
            node_lookup = {}
            node_lookup[ActionSequence.create_empty()] = _ReportNode(   input_player_range=input_player_range_map[ActionSequence.create_empty()],
                                                                        output_player_ranges=output_player_range_map[ActionSequence.create_empty()],
                                                                        children={}  )
            for node in solution_tree.gen_nodes_in_bfs_traversal():
                # skip root node
                if node == solution_tree.root_node():
                    continue
                elif node.is_leaf_spot():
                    continue
                # otherwise
                child_report_node = _ReportNode(input_player_range=input_player_range_map[node.action_sequence()],
                                                output_player_ranges=output_player_range_map[node.action_sequence()],
                                                children={})
                parent_node = node_lookup[node.action_sequence().parent()]
                parent_node.add_child(  child_name=str(node.action_sequence()[-1]),
                                        child_report_node=child_report_node  )
                node_lookup[node.action_sequence()] = child_report_node
            return node_lookup[ActionSequence.create_empty()]
        except KeyError as e:
            raise ValueError(f"Could not resolve player range for action sequence `{str(e)}` in {cls.__name__}.create() !")





class _RangeHelper:

    @classmethod
    def create_solved_street(cls, hand_history: HandHistory, solution_tree: SolutionTree,
                                                                action_sequences: typing.Tuple[ActionSequence, ...]) -> SolvedStreet:
        seat_stacks = tuple(SeatStack(seat=ps.seat(), stack_size=ps.stack_size()) for ps in hand_history.playing_seats())
        solved_street = SolvedStreet.create_unsolved(   seat_stacks=seat_stacks,
                                                        button_assignment=hand_history.button_assignment(),
                                                        blind_bet_sequence=hand_history.blind_bet_sequence(),
                                                        action_sequences=action_sequences )
        for node in solution_tree.gen_nodes_on_path(solved_street.action_sequence()):
            solved_street.add_solved_spot(node.solved_spot())
        return solved_street

    @classmethod
    def gen_player_ranges_for_seat(cls, solved_street: SolvedStreet, seat: int, initial_player_range: PlayerRange):
        for reach_coeff_array in solved_street.gen_reach_coeff_array_for_seat(seat):
            if solved_street.street_index() == 0:
                # preflop street
                yield solved_street.create_flop_player_range(reach_coeff_array)
            else:
                yield solved_street.create_turn_river_player_range(reach_coeff_array, initial_player_range)

    @classmethod
    def gen_seat_output_player_ranges(cls, solved_street: SolvedStreet, initial_player_range_map: dict):

        output_player_range_map = {seat: list(cls.gen_player_ranges_for_seat(   solved_street,
                                                                                seat,
                                                                                initial_player_range_map[seat]  )) for seat in solved_street.acting_seats()}
        for seat, _ in solved_street.gen_seat_actions():
            yield (seat, output_player_range_map[seat].pop(0))

    @classmethod
    def gen_seat_input_player_ranges(cls, solved_street: SolvedStreet, initial_player_range_map: dict):

        output_player_range_map = {seat: list(cls.gen_player_ranges_for_seat(   solved_street,
                                                                                seat,
                                                                                initial_player_range_map[seat]  )) for seat in solved_street.acting_seats()}
        input_player_range_map = {seat: [initial_player_range_map[seat]] + output_player_range_map[seat][:-1] for seat in solved_street.acting_seats()}
        for seat, _ in solved_street.gen_seat_actions():
            yield (seat, input_player_range_map[seat].pop(0))




class PlayerRangeReport:

    __slots__ = ('_player_range_street_reports',)

    def __init__(self, player_range_street_reports: typing.Tuple[PlayerRangeStreetReport, ...]):
        self._player_range_street_reports = player_range_street_reports

    def save_to_filesystem(self, path: str):        
        sub_report_names = ('preflop', 'flop', 'turn', 'river')
        cur_path = pathlib.Path(path)
        for sub_report_name, report in zip(sub_report_names, self._player_range_street_reports):
            child_path = (cur_path / sub_report_name)
            if not child_path.is_dir():
                child_path.mkdir()
            report.save_to_filesystem(child_path)


    @classmethod
    def gen_last_street_input_player_ranges(cls, solved_streets: typing.Tuple[SolvedStreet, ...]):
        # initial ranges
        initial_player_range_map = {seat: PlayerRange.create_uniform() for seat in solved_streets[0].acting_seats()}
        for cur_solved_street in solved_streets[:-1]:
            # update the initial range for next step
            for seat, output_player_range in _RangeHelper.gen_seat_output_player_ranges(cur_solved_street,
                                                                                        initial_player_range_map):
                initial_player_range_map[seat] = output_player_range

        for seat, input_player_range in _RangeHelper.gen_seat_input_player_ranges(  solved_streets[-1],
                                                                                    initial_player_range_map  ):
            yield input_player_range

    @classmethod
    def gen_last_street_output_player_ranges(cls, solved_streets: typing.Tuple[SolvedStreet, ...]):
        # initial ranges
        initial_player_range_map = {seat: PlayerRange.create_uniform() for seat in solved_streets[0].acting_seats()}
        for cur_solved_street in solved_streets[:-1]:
            # update the initial range for next step
            for seat, output_player_range in _RangeHelper.gen_seat_output_player_ranges(cur_solved_street,
                                                                                        initial_player_range_map):
                initial_player_range_map[seat] = output_player_range

        for seat, output_player_range in _RangeHelper.gen_seat_output_player_ranges(solved_streets[-1],
                                                                                    initial_player_range_map):
            yield output_player_range


    @classmethod
    def gen_player_range_street_reports(cls, hand_history: HandHistory, solution_trees: typing.Tuple[SolutionTree, ...]) -> PlayerRangeReport:
        solved_street_lookup = {}
        for street_index, solution_tree in enumerate(solution_trees):
            input_player_range_map = {}
            output_player_range_map = {}
            for leaf_node in solution_tree.gen_leaf_nodes():
                # go through all possible paths in the solution tree
                action_sequences = hand_history.action_sequences()[: street_index] + (leaf_node.action_sequence(), )
                solved_street = _RangeHelper.create_solved_street(  hand_history=hand_history,
                                                                    solution_tree=solution_tree,
                                                                    action_sequences=action_sequences  )
                # save the solved street for later
                solved_street_lookup[action_sequences] = solved_street

                solved_streets = tuple(solved_street_lookup[action_sequences[: i+1]] for i in range(len(action_sequences)))


                input_player_range_map.update(dict(zip( leaf_node.action_sequence().gen_prefixes(),
                                                        cls.gen_last_street_input_player_ranges(solved_streets) )))

                for action_sequence, output_player_range in zip(leaf_node.action_sequence().gen_prefixes(), cls.gen_last_street_output_player_ranges(solved_streets)):
                    action = leaf_node.action_sequence()[len(action_sequence)]
                    try:
                        output_player_range_map[action_sequence][action] = output_player_range
                    except KeyError:
                        output_player_range_map[action_sequence] = {action: output_player_range}

            # Now the street is complete we can make a report
            yield PlayerRangeStreetReport.create(   input_player_range_map=input_player_range_map,
                                                    output_player_range_map=output_player_range_map,
                                                    solution_tree=solution_tree  )


    @classmethod
    def create(cls, hand_history: HandHistory, solution_trees: typing.Tuple[SolutionTree, ...]) -> PlayerRangeReport:
        return cls(player_range_street_reports=tuple(cls.gen_player_range_street_reports(hand_history, solution_trees)))
