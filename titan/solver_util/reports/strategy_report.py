from __future__ import annotations
import typing
import pathlib
import os
from titan.solver_util.solution_tree import (
    SolutionTree,
    SolutionTreeNode,
    StrategyOption,
    RaiseOption,
    FoldOption,
    CallOption,
    CheckOption
)
from titan.solver_util.preflop_solver.preflop_range_map import (
    PreflopRangeMap
)
from titan.solver_util.postflop_solver.postflop_range_map import (
    PostflopRangeMap
)

class _StrategyTableEntry:

    __slots__ = ('_hand', '_frequencies')

    def __init__(self, hand: str, frequencies: typing.Tuple[float, ...]):
        self._hand = hand
        self._frequencies = frequencies

    def hand(self) -> str:
        return self._hand

    def frequencies(self) -> typing.Tuple[float, ...]:
        return self._frequencies

    def __str__(self):
        freq_columns = '\t\t'.join((f"{freq * 100:>5.1f}%".center(20) for freq in self.frequencies()))
        return f"{self.hand().ljust(4)}\t\t{freq_columns}"


class _StrategyTable:
    
    __slots__ = ('_strategy_options', '_entries')

    MAX_FREQUENCY = 10000

    def __init__(self, strategy_options: typing.Tuple[StrategyOption, ...], entries: typing.Tuple[_StrategyTableEntry, ...]):
        self._strategy_options = strategy_options
        self._entries = entries

    def strategy_options(self) -> typing.Tuple[StrategyOption, ...]:
        return self._strategy_options

    def entries(self) -> typing.Tuple[_StrategyTableEntry, ...]:
        return self._entries

    def is_leaf(self) -> bool:
        return len(self._entries) == 0

    def __str__(self):
        if self.is_leaf():
            return f"(No strategy table available)"
        header_items = ('HAND', ) + tuple(str(opt).center(20) for opt in self.strategy_options())
        spacer_row = "-" * 25 * len(header_items)
        header_row = '\t\t'.join(header_items)
        rows = '\n'.join(str(entry) for entry in self.entries())
        return header_row + '\n' + spacer_row + '\n' + rows

    @classmethod
    def create_from_solution_tree_node(cls, solution_tree_node: SolutionTreeNode):
        strategy_matrix = solution_tree_node.solved_spot().strategy_matrix()
        options = solution_tree_node.solved_spot().strategy_options()

        if options == ():
            # Leaf node
            return cls(strategy_options=(), entries=())
        elif strategy_matrix.shape() == (PreflopRangeMap.RANGE_SIZE, len(options)):
            entries = ( _StrategyTableEntry(hand=PreflopRangeMap.hand_for_index(i),
                                            frequencies=tuple(strategy_matrix.values()[i] / cls.MAX_FREQUENCY))
                            for i in range(PreflopRangeMap.RANGE_SIZE) )
            return cls( strategy_options=options,
                        entries=tuple(entries) )
        elif strategy_matrix.shape() == (PostflopRangeMap.RANGE_SIZE, len(options)):
            entries = ( _StrategyTableEntry(hand=PostflopRangeMap.hand_for_index(i),
                                            frequencies=tuple(strategy_matrix.values()[i] / cls.MAX_FREQUENCY))
                            for i in range(PostflopRangeMap.RANGE_SIZE) )
            return cls( strategy_options=options,
                        entries=tuple(entries) )
        else:
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_node() " +
                                f"with weirdly shaped strategy_matrix ({strategy_matrix.shape()}) !"  ))


class _ReportNode:

    __slots__ = ('_strategy_table', '_children')

    def __init__(self, strategy_table: _StrategyTable, children: typing.Dict[str, _ReportNode]):
        self._strategy_table = strategy_table
        self._children = dict(children)

    def strategy_table(self) -> _StrategyTable:
        return self._strategy_table

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
        # save strategy table
        with open(cur_path / 'strategy.txt', 'w') as f:
            f.write(str(self.strategy_table()))
        # recurse down for children
        for child_name, child_node in self.children().items():
            # make a directory for child
            child_path = (cur_path / child_name)
            if not child_path.is_dir():
                child_path.mkdir()
            child_node.save_to_filesystem(child_path)



    @classmethod
    def create_from_solution_tree_node(cls, solution_tree_node: SolutionTreeNode, children: typing.Dict[str, _ReportNode]):
        strategy_table = _StrategyTable.create_from_solution_tree_node(solution_tree_node)
        return cls(strategy_table, [])


class StrategyStreetReport:


    def __init__(self, root_report_node: _ReportNode):
        self._root_report_node = root_report_node

    def root_report_node(self):
        return self._root_report_node

    def gen_nodes_bfs(self):
        yield from self.root_report_node().gen_nodes_bfs()

    def save_to_filesystem(self, path: str):
        self.root_report_node().save_to_filesystem(path)


    @classmethod
    def create(cls, solution_tree: SolutionTree) -> StrategyStreetReport:
        root_report_node = None
        report_node_lookup = {}
        for node in solution_tree.gen_nodes_in_bfs_traversal():
            report_node = _ReportNode.create_from_solution_tree_node(   solution_tree_node=node,
                                                                        children={}  )
            report_node_lookup[node.action_sequence()] = report_node
            if root_report_node is not None:
                parent_report_node = report_node_lookup[node.action_sequence()[:-1]]
                child_name = str(node.action_sequence()[-1])
                parent_report_node.add_child(child_name, report_node)
            else:
                root_report_node = report_node
        if not root_report_node:
            raise ValueError(f"Cannot call {cls.__name__}.create() with an empty solution_tree !")
        return root_report_node



class StrategyReport:

    __slots__ = ('_strategy_street_reports',)

    def __init__(self, strategy_street_reports: typing.Tuple[StrategyStreetReport, ...]):
        self._strategy_street_reports = strategy_street_reports

    def save_to_filesystem(self, path: str):        
        sub_report_names = ('preflop', 'flop', 'turn', 'river')
        cur_path = pathlib.Path(path)
        for sub_report_name, report in zip(sub_report_names, self._strategy_street_reports):
            child_path = (cur_path / sub_report_name)
            if not child_path.is_dir():
                child_path.mkdir()
            report.save_to_filesystem(child_path)


    @classmethod
    def create(cls, hand_history: HandHistory, solution_trees: typing.Tuple[SolutionTree, ...]) -> StrategyReport:
        return cls(strategy_street_reports=tuple(StrategyStreetReport.create(solution_tree)
                                                    for solution_tree in solution_trees))